import gordion
import os
from typing import List, Optional, Tuple
from dataclasses import dataclass


class Tree:
  """
  Wraps a gordion.Repository to add tree functionality. A gordion repository can have children
  gordion repositories that have children and so on.
  """

  def __init__(self, repo: gordion.Repository, parent=None) -> None:
    self.repo: gordion.Repository = repo
    self.parent: Tree = parent
    self.workspace = gordion.Workspace()

  def update(self, tag: str, branch_name: str, force: bool = False) -> None:
    """
    Updates this repository and it's children.
    """
    root = self._root()

    # Clean dirty cached repositories before updating (only at root level)
    if self is root:
      workspace = gordion.Workspace()
      for _, repo in workspace.repos().items():
        if workspace.is_dependency(repo.path) and repo.handle.is_dirty(untracked_files=True):
          print(f"Cleaning dirty cached repository: {repo.path}")
          # Reset any staged or modified files
          repo.handle.git.reset('--hard', 'HEAD')
          # Remove any untracked files
          repo.handle.git.clean('-fd')

    # Check for duplicate tag first. We have to do this here because the repo needs to veriy and
    # compare commits.
    root._check_same_repo_different_tag(self.repo)
    self.repo.update(tag, branch_name, force)

    self.repo.yeditor.reload()
    self._update_children(branch_name, force)

    if self is root:
      self.workspace.trim_repositories()
      # Trim orphaned workspace caches
      cache = gordion.Cache()
      cache.trim()

  def _update_children(self, branch_name: str, force: bool):
    """
    Updates the children repository listed in this repositorie's yaml.
    """
    root = self._root()

    # Open the gordion yaml file for this repository if it exists.
    if self.repo.yeditor.exists():
      assert self.repo.yeditor.yaml_data
      for child_name, child_info in self.repo.yeditor.yaml_data['repositories'].items():
        child_url = child_info['url']
        child_tag = child_info['tag']
        child_repo: Optional[gordion.Repository] = None

        # First verify we don't have a duplicates before working with this child.
        root._check_same_name_different_url(child_name, child_url)
        root._check_different_name_same_url(child_name, child_url)

        working = self.workspace.working(name=child_name, url=None)
        dependencies = self.workspace.dependencies(name=child_name, url=None)
        if len(working) == 0:
          if len(dependencies) == 0:
            child_path = os.path.join(self.workspace.dependencies_path, child_name)

            # If there is exactly one dependency already with this url, different name, move it.
            deps_by_url = self.workspace.dependencies(name=None, url=child_url)
            if len(deps_by_url) == 1:
              dep = next(iter(deps_by_url.values()))
              child_repo = gordion.Repository.safe_move(dep.path, child_path)
            # Otherwise delete and reclone.
            else:
              for _, dep in deps_by_url.items():
                gordion.Repository.safe_delete(dep.path)
              child_repo = gordion.Repository.clone(child_path, child_url)

          # Only one dependency repo with this name...
          elif len(dependencies) == 1:
            child_repo = next(iter(dependencies.values()))
            expected_path = os.path.join(self.workspace.dependencies_path, child_repo.name)

            # If it has the wrong url..
            if not gordion.utils.compare_urls(child_repo.url, child_url):
              gordion.Repository.safe_delete(child_repo.path)
              child_repo = gordion.Repository.clone(expected_path, child_url)

            # If it has the wrong path...
            if child_repo.path != expected_path:
              child_repo = gordion.Repository.safe_move(child_repo.path, expected_path)

          # More than one dependency. This is an edge case. Delete them and re-clone is easiest.
          else:
            for _, dependency in dependencies.items():
              gordion.Repository.safe_delete(dependency.path)
            child_path = os.path.join(self.workspace.dependencies_path, child_name)
            child_repo = gordion.Repository.clone(child_path, child_url)

        # There is exactly one working repo with this name...
        elif len(working) == 1:
          child_repo = next(iter(working.values()))

          # If it has the wrong url..
          if not gordion.utils.compare_urls(child_repo.url, child_url):
            raise gordion.UpdateWorkingRepositoryWrongUrlError(
                child_repo.path, child_repo.url, child_url)

          # If there are dependencies, delete them.
          for _, dependency in dependencies.items():
            gordion.Repository.safe_delete(dependency.path)

        # There is more than one working repo with this name...
        else:
          raise gordion.UpdateMultipleRepositoriesAlreadyExistsError(child_path, working)

        # Delete dependencies that have the same url, different name.
        dependencies = self.workspace.dependencies(name=child_name, url=None)

        assert child_repo
        child = Tree(child_repo, self)
        child.update(child_tag, branch_name, force)

  def _root(self):
    """
    Recursively returns the root repository object.
    """
    if self.parent:
      return self.parent._root()
    else:
      return self

  def _check_different_name_same_url(self, name, url):
    """
    Recursively checks for different listings that have the same repo.
    """
    # Collect all child listings that are the same repository (same effective url).
    listings, _ = self.listings(name=None, url=url)

    # Check each listing to see if there are any that are a different name.
    for listing in listings:
      if listing.name != name:
        raise gordion.UpdateDifferentNameSameUrlError(name, listings)

  def _check_same_name_different_url(self, name: str, url: str):
    """
    Recursively checks for duplicate listings with different urls in this tree.
    """

    listings, _ = self.listings(name, url=None)

    # Raise an error if any listing doesn't match the target url.
    for listing in listings:
      if not gordion.utils.compare_urls(listing.url, url):
        raise gordion.UpdateSameNameDifferentUrlError(name, listings)

  def _check_same_repo_different_tag(self, target: gordion.Repository):
    """
    Recursively checks the target repository & tag for duplicate listings with different tags in
    this tree.
    """

    # Filter for an exact match to the name and url.
    listings, _ = self.listings(target.name, target.url)

    # Raise an error if any two listings don't match tags.
    listing_0_commit = target.verify_tag(listings[0].tag)
    for listing_n in listings:
      listing_n_commit = target.verify_tag(listing_n.tag)
      if listing_n_commit != listing_0_commit:
        raise gordion.UpdateSameRepoDifferentTagError(target.path, listings)

  @dataclass
  class Listing:
    name: str
    url: str
    tag: str
    file: Optional[str]

  def listings(self, name: Optional[str], url: Optional[str],
               recursing: bool = False) -> Tuple[List[Listing], bool]:
    """
    Generates a list of Listings in the recursable Tree, including the self. A listing holds
    information as-listed in the gordion.yaml file, unless it is the root which doesn't have a
    parent gordion.yaml file.
    """
    complete = True
    # Add self if not recursing.
    listings = []
    if not recursing:
      listings.append(
          gordion.Tree.Listing(
              self.repo.name,
              self.repo.url,
              self.repo.handle.head.commit.hexsha,
              None))

    # Get all listings in the tree.
    if self.repo.yeditor.exists():
      for child_name, child_info in self.repo.yeditor.yaml_data['repositories'].items():
        child_url = child_info['url']
        child_tag = child_info['tag']

        # Add this listing.
        listings.append(
            gordion.Tree.Listing(
                child_name,
                child_url,
                child_tag,
                self.repo.yeditor.fullfile))

        # Get the child repository from the workspace by name if possible. We can recurse if it has
        # the correct url and tag.
        child_repo = self.workspace.get_repository(child_name)
        if child_repo:
          if gordion.utils.compare_urls(child_repo.url, child_url):
            # Try to verify the tag, but don't error, it just means we cannot recurse if it fails.
            child_listed_commit = None
            try:
              child_listed_commit = child_repo.verify_tag(child_tag)
            except Exception:
              pass

            # If we have the child commit and it the head of the repo, we can recurse.
            if child_listed_commit:
              if child_repo.handle.head.commit == child_listed_commit:
                tree = gordion.Tree(child_repo)
                child_listings, complete = tree.listings(name=name, url=url, recursing=True)
                listings.extend(child_listings)
              else:
                complete = False
            else:
              complete = False
        else:
          complete = False

    # Filter by name and url once at the top level.
    if not recursing:
      if name:
        listings = [listing for listing in listings if name == listing.name]
      if url:
        listings = [listing for listing in listings if gordion.utils.compare_urls(listing.url, url)]

    return listings, complete

  def is_listed(self, repo: gordion.Repository) -> Tuple[bool, bool]:
    listings, complete = self.listings(name=repo.name, url=None)
    is_listed = len(listings) > 0
    return is_listed, complete

  @staticmethod
  def find(path: str):
    """
    Returns the gordion repository Tree object containing this path.
    """
    current_repo_path = gordion.utils.get_repository_root(path)

    # If we are not in a git repository, then we are not in a gordion repository.
    if current_repo_path is None:
      raise gordion.NotARepositoryError()

    repo = gordion.Workspace().repos().get(current_repo_path)
    assert repo is not None
    return gordion.Tree(repo)  # type: ignore[union-attr]

  @staticmethod
  def format_listing_tag(listing: Listing) -> str:
    # Format file.
    formatted_file = ""
    if listing.file:
      partial_path = os.path.join(
          os.path.basename(os.path.dirname(listing.file)),
          os.path.basename(listing.file))
      formatted_file = f"{gordion.utils.filelink(listing.file, partial_path)}"
    else:
      formatted_file = f"{listing.name}*"

    # Format tag.
    repo = gordion.Workspace().get_repository(listing.name)
    formatted_tag = ""
    if repo:
      formatted_tag = repo.try_resolve_tag(listing.tag)
    else:
      formatted_tag = "repository DNE"

    return f"* {formatted_file} : {listing.name} : {formatted_tag}"

  @staticmethod
  def format_listing_url(listing: Listing) -> str:
    formatted_file = ""
    if listing.file:
      partial_path = os.path.join(
          os.path.basename(os.path.dirname(listing.file)),
          os.path.basename(listing.file))
      formatted_file = f"{gordion.utils.filelink(listing.file, partial_path)}"
    else:
      formatted_file = f"{listing.name}*"
    formatted_url = f"{gordion.utils.hyperlink(listing.url, listing.url)}"
    return f"* {formatted_file} : {listing.name} : {formatted_url}"
