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
    self.children: dict[str, Tree] = {}
    self.workspace = gordion.Workspace()
    # TODO encapsulate
    self.committed = False

    # TODO reuse
    self.children1: dict[str, Tree] = {}
    self.parents1: dict[str, Tree] = {}

  def update(self, tag: str, branch_name: str, force: bool = False) -> None:
    """
    Updates this repository and it's children.
    """
    # First check/fix dangling .dependencies folders
    root = self._root()
    if self is root:
      self.workspace.unify_dependencies()

    # Check for duplicate tag first. We have to do this here because the repo needs to veriy and
    # compare commits.
    root._check_same_repo_different_tag(self.repo)
    self.repo.update(tag, branch_name, force)

    self.repo.yeditor.reload()
    self._update_children(branch_name, force)

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
        self.children[child_name] = child

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

# =================================================================================================
# Git Command Analogs
#
# TODO re-usable run function
# Ability to check if all repositories in a path will satisfy a set of requirements:
# 1) branch name. (for adding, commiting)
# 2)

# steps:
# 1) Trace the path, get all repositories. If it is traceable, return the trace.
# 2) For each function, you can loop through the trace, and check things like branch name.

#
# A trace() sets the children if possible, and returns true if complete, otherwise it will return
# listings that are not traced successfully.

  def trace(self) -> bool:
    self.children = {}
    full: bool = True
    if self.repo.yeditor.exists():
      assert self.repo.yeditor.yaml_data
      for child_name, child_info in self.repo.yeditor.yaml_data['repositories'].items():
        child_url = child_info['url']
        child_tag = child_info['tag']
        child_repo = gordion.Workspace().get_repository(child_name)

        if child_repo:
          if gordion.utils.compare_urls(child_repo.url, child_url):
            child_listed_commit = child_repo.verify_tag_nothrow(child_tag)
            if child_listed_commit and child_repo.handle.head.commit == child_listed_commit:
              child_tree = gordion.Tree(child_repo, self)
              self.children[child_name] = child_tree
              if not child_tree.trace():
                full = False
            else:
              full = False
          else:
            full = False
        else:
          full = False
    return full

  def lineage_has_changes_staged(self) -> bool:
    if self.repo.handle.is_dirty(index=True, working_tree=False, untracked_files=False):
      return True

    for _, child in self.children.items():
      if child.repo.handle.is_dirty(index=True, working_tree=False,
                                    untracked_files=False) or child.lineage_has_changes_staged():
        return True
    return False

  # def find_repos_with_wrong_branch_for_lineage(self, branch_name: str) -> List[gordion.Repository]:
  #   found: List[gordion.Repository] = []

  #   # Add this repo if it is not the correct branch, and any of it's offspring have changes.
  #   if not self.repo.is_branch(branch_name):
  #     for _, child in self.children.items():
  #       if child.lineage_has_changes_staged():
  #         found.append(self.repo)
  #         break

  #   # Recurse
  #   for _, child in self.children.items():
  #     found.extend(child.find_repos_with_wrong_branch_for_lineage(branch_name))

  #   def make_unique_by_path(objects):
  #     unique_objects = {}
  #     for obj in objects:
  #       unique_objects[obj.repo.path] = obj
  #     return list(unique_objects.values())

  #   return make_unique_by_path(found)

  def find_referencers(self, other):
    referencers: List[gordion.Tree] = []

    # Check if children reference other.
    for _, child in self.children.items():
      if child.repo.name == other.repo.name:
        referencers.append(self)
      else:
        referencers.extend(child.find_referencers(other))

    # TODO duplicate code.
    def make_unique_by_path(objects):
      unique_objects = {}
      for obj in objects:
        unique_objects[obj.repo.path] = obj
      return list(unique_objects.values())

    return make_unique_by_path(referencers)

  def commit(self, branch_name: str, message: str) -> bool:

    if self.trace():
      # First make sure branch names are correct.
      if not self.verify_changes_are_branch(branch_name):
        print("TODO error not all changes are on this branch See 'gor status'")
        return

      # Now make sure lineage is correct branch.
      # TODO a referencer cannot have unadded changes to the gordion file
      found = self.find_repos_with_wrong_branch_for_lineage(branch_name)
      if len(found) > 0:
        for repo in found:
          print(f"{repo.name} has needs to checkout branch due to lineage.")

      # Recurse into children.
      for _, child in self.children.items():
        child.commit(branch_name, message)

        # If the child committed, update it's referencers
        if child.committed:
          commit = child.repo.handle.head.commit
          root = self._root()
          referencers = root.find_referencers(child)
          for referencer in referencers:
            # Update gordion.yaml.
            if not referencer.repo.yeditor.read_repository_tag(child.repo.name) == commit.hexsha:
              referencer.repo.yeditor.write_repository_tag(child.repo.name, commit.hexsha)
              # Add changes to referencer.
              referencer.repo.add(branch_name, "gordion.yaml")
              # Commit referencer.
              # Only double newline first time.
              if referencer.committed:
                full_message = referencer.repo.handle.head.commit.message
              else:
                full_message = message
              full_message += f"\n\n* Bump {child.repo.name} to {commit.hexsha}"

              referencer.repo.commit(message=full_message, amend=referencer.committed)
              referencer.committed = True

      # Commit this one if it has staged changes.
      if self.repo.has_staged_changes():
        if self.committed:
          message = referencer.repo.head.commit.message
        self.repo.commit(message=message, amend=self.committed)
        self.committed = True

    else:
      print("TODO error could not trace reposiotry tree. See 'gor status'")

    return self.committed
