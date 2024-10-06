import gordion
import os
import git
from typing import List, Optional
from dataclasses import dataclass
import shutil


class Tree(gordion.Repository):
  """
  Extends a gordion.Repository to add tree functionality. A gordion repository can have children
  gordion repositories that have children and so on.
  """

  def __init__(self, path: str, url: str = '', parent=None) -> None:
    super().__init__(path, url)
    self.parent: Tree = parent
    self.children: dict[str, Tree] = {}
    self.yeditor = gordion.YamlEditor(os.path.join(self.path, 'gordion.yaml'))
    self.workspace = gordion.Workspace()

  def update(self, tag: str, branch_name: str, force: bool = False) -> None:
    """
    Updates this repository and it's children.
    """
    # Check for duplicate tag
    # root = self._root()
    # commit: git.Commit = self._verify_tag(tag)
    # TODO restore.
    # root._check_same_repo_different_tag(self, commit)

    super().update(tag, branch_name, force)

    self.yeditor.reload()
    self._update_children(branch_name, force)

    # # Cleanup duplicate repositories.
    # if self is root:
    #   self._delete_duplicates(force)

  # def _delete_duplicates(self, force: bool):
  #   listings = self.listings(None, None)

  #   # First delete duplicates of listings.
  #   for listing in listings:
  #     listed_repo = gordion.Repository(listing.path)
  #     assert listed_repo.handle.remotes.origin.url == listing.url
  #     duplicates = self.workspace.get_repositories_by_url(listed_repo.url)
  #     for duplicate in duplicates:
  #       if duplicate.path != listed_repo.path:
  #         gordion.Repository.safe_delete(path=duplicate.path, force=force)

  #   # Also delete duplicates of any existing repo.
  #   uniques = []
  #   for repo in self.workspace.repos:
  #     if not any(
  #         gordion.utils.compare_urls(repo.handle.remotes.origin.url,
  #                                    unique.handle.remotes.origin.url) for unique in uniques):
  #       uniques.append(repo)
  #   for unique in uniques:
  #     duplicates = self.workspace.get_repositories_by_url(unique.url)
  #     for duplicate in duplicates:
  #       if duplicate.path != unique.path:
  #         gordion.Repository.safe_delete(path=duplicate.path, force=force)

  def _update_children(self, branch_name: str, force: bool):
    """
    Updates the children repository listed in this repositorie's yaml.
    """
    # root = self._root()
    self.children = {}

    # Open the gordion yaml file for this repository if it exists.
    if self.yeditor.exists():
      assert self.yeditor.yaml_data
      for child_name, child_info in self.yeditor.yaml_data['repositories'].items():

        # Manage existing repositories in the workspace, and resolve the child_path
        working, dependencies = self.workspace.get_repositories(child_info['url'])
        child_path = ''

        # If there are no working repositories, than we need to manage the repository in the
        # .dependencies/ space.
        if len(working) == 0:
          # If there are no dependencies yet, set the child_path and it will be cloned.
          if len(dependencies) == 0:
            child_path = os.path.join(self.workspace.dependencies_path, child_name)

          # Ensure there is only one dependency repo at the correct location.
          else:
            child_path = os.path.join(self.workspace.dependencies_path, child_name)
            for dependency in dependencies:
              if dependency.path != child_path:
                gordion.Repository.safe_delete(dependency.path)

        # If there are working repositories, we can remove any dependencies.
        else:
          for dependency in dependencies:
            gordion.Repository.safe_delete(dependency.path)

          # If there is exactly working repository, good, otherwise bad.
          if len(working) == 1:
            child_path = working[0].path
          else:
            child_path = working[0].path
            raise gordion.UpdateMultipleRepositoriesAlreadyExistsError(child_path, working)

        # # Check the repository path before creating it.
        # root._check_different_repo_same_path(child_path, child_url)
        # root._check_same_repo_different_path(child_path, child_url)

        child = Tree(child_path, child_info['url'], self)
        child.update(child_info['tag'], branch_name, force)
        self.children[child_name] = child

  def _root(self):
    """
    Recursively returns the root repository object.
    """
    if self.parent:
      return self.parent._root()
    else:
      return self

  def _relpath(self) -> str:
    """
    Returns the path relative to the root repository.
    """
    return os.path.relpath(self.path, os.path.dirname(self._root().path))

  def _listed_path(self) -> str:
    """
    Describes the parent path listing of this repository.
    """
    listed_path = ''
    if self.parent:
      gpath = self.parent.yeditor.read_repository_gpath(self.name)
      listed_path = f"{self.parent._relpath()} lists {gpath}"
    else:
      listed_path = f"{self._relpath()} (root)"

    return listed_path

  def _list_child_repository_paths(self) -> List[str]:
    """
    Returns a list of the child repository paths.
    """
    paths = []
    for _, repo in self.children.items():
      paths.append(repo.path)
      paths.extend(repo._list_child_repository_paths())
    return paths

  def _check_different_repo_same_path(self, target_path, target_url):
    """
    Recursively checks the repository path against another repository and it's children.
    """

    # Collect all child listings with the same path.
    listings = self.listings(target_path, target_url=None)

    # Check each listing to see if there are any that are a different repo.
    for listing in listings:
      # Check if the listing repository is different from the target repository.
      if not gordion.utils.compare_urls(listing.url, target_url):
        raise gordion.UpdateDifferentRepoSamePathError(target_path, listings)

  def _check_same_repo_different_path(self, target_path, target_url):
    """
    Recursively checks the repository path against another repository and it's children.
    """
    # Collect all child listings that are the same repository (same effective url).
    listings = self.listings(target_path=None, target_url=target_url)

    # Check each listing to see if there are any that are a different path.
    for listing in listings:
      if listing.path != target_path:
        raise gordion.UpdateSameRepoDifferentPathError(target_path, listings)

  def _check_same_repo_different_tag(self, target, target_commit: git.Commit):
    """
    Recursively checks the target repository & tag for duplicate listings with different tags in
    this tree.
    """

    listings = self.listings(target.path, target.url)

    # Raise an error if any two listings don't match tags.
    listing_0_commit = target._verify_tag(listings[0].tag)
    for listing_n in listings:
      listing_n_commit = target._verify_tag(listing_n.tag)
      if listing_n_commit != listing_0_commit:
        raise gordion.UpdateSameRepoDifferentTagError(target.path, listings)

  @dataclass
  class Listing:
    path: str
    listed_path: str
    url: str
    tag: str

  def listings(self, target_path: Optional[str], target_url: Optional[str]) -> List[Listing]:
    """
    Generates a list of Listings in the recursable Tree, including the self. A listing holds
    information as-listed in the gordion.yaml file, unless it is the root which doesn't have a
    parent gordion.yaml file.
    """
    listings = []

    # Check if self matches the target path and/or url
    if not target_path or target_path == self.path:
      if not target_url or gordion.utils.compare_urls(target_url, self.url):
        listings.append(gordion.Tree.Listing(path=self.path, listed_path=self._listed_path(),
                                             url=self.url, tag=self.handle.head.commit.hexsha))

    # Check children.
    self.yeditor.reload()
    if self.yeditor.exists():
      for child_name, child_info in self.yeditor.yaml_data['repositories'].items():
        gpath = self.yeditor.read_repository_gpath(child_name)
        child_path = os.path.join(self.workspace.path, gpath)
        child_url = child_info['url']
        child_tag = child_info['tag']

        # If the child exists, and is the correct url and tag, we can create a Tree object and
        # recurse.
        recursed = False
        if gordion.Repository._exists(child_path):
          if gordion.Repository._url(child_path) == child_url:
            child = Tree(child_path, child_url, self)
            child_listed_commit = child._verify_tag(child_tag)
            if child.handle.head.commit == child_listed_commit:
              listings.extend(child.listings(target_path, target_url))
              recursed = True

        # If we didn't recurse into the child Tree, becasue it was the wrong commit or url, we still
        # need to add it as a listing, if the path and/or url matches the target.
        if not recursed:
          if not target_path or target_path == child_path:
            if not target_url or gordion.utils.compare_urls(target_url, child_url):
              child_listed_path = f"{self._relpath()} lists {gpath}"
              listings.append(gordion.Tree.Listing(path=child_path, listed_path=child_listed_path,
                                                   url=child_url, tag=child_tag))

    return listings

  @staticmethod
  def find(path: str) -> str:
    """
    Returns the gordion repository Tree object containing this path.
    """
    current_repo_path = gordion.utils.get_repository_root(path)

    # If we are not in a git repository, then we are not in a gordion repository.
    if current_repo_path is None:
      raise gordion.NotAGordionRepositoryError()

    if gordion.Repository.is_gordion(current_repo_path):
      return gordion.Tree(current_repo_path)
    else:
      raise gordion.NotAGordionRepositoryError()
