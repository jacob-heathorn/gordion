import gordion
import os
import git
from typing import List, Optional
from dataclasses import dataclass


class Tree:
  """
  Extends a gordion.Repository to add tree functionality. A gordion repository can have children
  gordion repositories that have children and so on.
  """

  # TODO add_child function.
  def __init__(self, repo: gordion.Repository, parent=None) -> None:
    self.repo: gordion.Repository = repo
    self.parent: Tree = parent
    self.children: dict[str, Tree] = {}
    self.workspace = gordion.Workspace()

  def update(self, tag: str, branch_name: str, force: bool = False) -> None:
    """
    Updates this repository and it's children.
    """
    # Check for duplicate tag first. We have to do this here because the repo needs to veriy and
    # compare commits.
    root = self._root()
    root._check_same_repo_different_tag(self.repo)
    self.repo.update(tag, branch_name, force)

    self.repo.yeditor.reload()
    self._update_children(branch_name, force)

    # TODO move outside of tree so don't need root, so dont need parent?
    if self is root:
      self.workspace.trim_repositories()

  def _update_children(self, branch_name: str, force: bool):
    """
    Updates the children repository listed in this repositorie's yaml.
    """
    root = self._root()
    self.children = {}

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
            child_path = os.path.join(self.workspace.dependencies_path, child_repo.name)
            child_repo = gordion.Repository.clone(child_path, child_url)

        # There is exactly one working repo with this name...
        elif len(working) == 1:
          child_repo = next(iter(dependencies.values()))

          # If it has the wrong url..
          if gordion.utils.compare_urls(child_repo.url, child_url):
            raise gordion.UpdateWorkingRepositoryWrongUrlError(
                child_path, child_repo.url, child_url)

          # If there are dependencies, delete them.
          for _, dependency in dependencies.items():
            gordion.Repository.safe_delete(dependency.path)

        # There is more than one working repo with this name...
        else:
          raise gordion.UpdateMultipleRepositoriesAlreadyExistsError(child_path, working)

        assert child_repo
        child = Tree(child_repo, self)
        child.update(child_tag, branch_name, force)
        self.children[child_name] = child

  def _root(self):
    """
    Recursively returns the root repository object.
    """
    if self.parent:
      return self.parent._root()
    else:
      return self

  def _list_child_repository_paths(self) -> List[str]:
    """
    Returns a list of the child repository paths.
    """
    paths = []
    for _, repo in self.children.items():
      paths.append(repo.path)
      paths.extend(repo._list_child_repository_paths())
    return paths

  def _check_different_name_same_url(self, name, url):
    """
    Recursively checks for different listings that have the same repo.
    """
    # Collect all child listings that are the same repository (same effective url).
    listings = self.listings(name=None, url=url)

    # Check each listing to see if there are any that are a different name.
    for listing in listings:
      if listing.name != name:
        raise gordion.UpdateDifferentNameSameUrlError(name, listings)

  def _check_same_name_different_url(self, name: str, url: str):
    """
    Recursively checks for duplicate listings with different urls in this tree.
    """

    listings = self.listings(name, url=None)

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
    listings = self.listings(target.name, target.url)

    # Raise an error if any two listings don't match tags.
    listing_0_commit = target._verify_tag(listings[0].tag)
    for listing_n in listings:
      listing_n_commit = target._verify_tag(listing_n.tag)
      if listing_n_commit != listing_0_commit:
        raise gordion.UpdateSameRepoDifferentTagError(target.path, listings)

  @ dataclass
  class Listing:
    name: str
    url: str
    tag: str
    file: Optional[str]

  # TODO reconsider recursing argument
  def listings(self, name: Optional[str], url: Optional[str],
               recursing: bool = False) -> List[Listing]:
    """
    Generates a list of Listings in the recursable Tree, including the self. A listing holds
    information as-listed in the gordion.yaml file, unless it is the root which doesn't have a
    parent gordion.yaml file.
    """
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
            child_listed_commit = child_repo._verify_tag(child_tag)
            if child_repo.handle.head.commit == child_listed_commit:
              tree = gordion.Tree(child_repo)
              listings.extend(tree.listings(name=name, url=url, recursing=True))

    # Filter by name and url once at the top level.
    if not recursing:
      if name:
        listings = [listing for listing in listings if name == listing.name]
      if url:
        listings = [listing for listing in listings if gordion.utils.compare_urls(listing.url, url)]

    return listings

  def is_listed(self, repo: gordion.Repository):
    listings = self.listings(name=repo.name, url=None)
    return len(listings) > 0

  @ staticmethod
  def find(path: str) -> str:
    """
    Returns the gordion repository Tree object containing this path.
    """
    current_repo_path = gordion.utils.get_repository_root(path)

    # If we are not in a git repository, then we are not in a gordion repository.
    if current_repo_path is None:
      raise gordion.NotAGordionRepositoryError()

    if gordion.Repository.is_gordion(current_repo_path):
      return gordion.Tree(gordion.Workspace().repos().get(current_repo_path))
    else:
      raise gordion.NotAGordionRepositoryError()
