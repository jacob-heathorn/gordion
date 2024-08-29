import gordion
import os
import git
from typing import List
from collections import namedtuple


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
    assert gordion.Store().path

  def update(self, tag: str, branch_name: str, force: bool = False) -> None:
    """
    Updates this repository and it's children.
    """
    # Check for duplicate tag
    root = self._root()
    commit: git.Commit = self._verify_tag(tag)
    root._check_duplicate_commit(self, commit)

    super().update(tag, branch_name, force)

    self.yeditor.reload()
    self._update_children(branch_name, force)

    # Cleanup detached repositories.
    if self is root:
      keep_repos = self._list_child_repository_paths()
      gordion.Store().trim_repos(keep_repos, force)

  def _update_children(self, branch_name: str, force: bool):
    """
    Updates the children repository listed in this repositorie's yaml.
    """
    root = self._root()
    self.children = {}

    # Open the gordion yaml file for this repository if it exists.
    if self.yeditor.exists():
      assert self.yeditor.yaml_data
      for child_name, child_info in self.yeditor.yaml_data['repositories'].items():
        # Create child repository objects
        gpath = self.yeditor.read_repository_gpath(child_name)
        child_path = os.path.join(gordion.Store().path, gpath)
        child_url = child_info['url']

        # Check the repository path before creating it.
        Tree._check_different_repo_same_path(child_path, child_url, root)
        Tree._check_same_repo_different_path(child_path, child_url, root)

        # If a repository with the wrong URL already exists at the child path, remove it. We have
        # already checked that a different repository is not listed at the same path, so if one
        # does, then it's dangling anyway (not listed in yaml yet).
        if gordion.Repository._exists(child_path):
          child_repo = git.Repo(child_path)
          if child_url != child_repo.remotes.origin.url:
            gordion.Repository.safe_delete(child_path)

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

  @staticmethod
  def _check_different_repo_same_path(target_path, target_url, other):
    """
    Recursively checks the repository path against another repository and it's children.
    """
    host, username, repo_name = gordion.extract_repo_details(target_url)
    other_host, other_username, other_repo_name = gordion.extract_repo_details(other.url)

    # Check if the remote repository is the same
    if host != other_host or username != other_username or repo_name != other_repo_name:
      # Make sure the repository does not have the same local path.
      if target_path == other.path:
        raise gordion.UpdateDifferentRepoSamePathError(target_path, target_url, other.path,
                                                       other.url)

    # Check against the other's children
    for _, other_child in other.children.items():
      Tree._check_different_repo_same_path(target_path, target_url, other_child)

  @staticmethod
  def _check_same_repo_different_path(target_path, target_url, other):
    """
    Recursively checks the repository path against another repository and it's children.
    """
    host, username, repo_name = gordion.extract_repo_details(target_url)
    other_host, other_username, other_repo_name = gordion.extract_repo_details(other.url)

    # Check if the remote repository is the same
    if host == other_host and username == other_username and repo_name == other_repo_name:
      # Make sure the repository has the same local path.
      if target_path != other.path:
        raise gordion.UpdateSameRepoDifferentPathError(target_path, other.path, other.url)

    # Check against the other's children
    for _, other_child in other.children.items():
      Tree._check_same_repo_different_path(target_path, target_url, other_child)

  def _check_duplicate_commit(self, target, target_commit: git.Commit):
    """
    Recursively checks the target repository & tag for duplicate listings in this tree.
    """

    listings = self.child_listings(target)

    # TODO better error about all mismatched listings.
    for listing in listings:
      if listing.commit != target_commit:
        raise gordion.UpdateSameRepoDifferentTagError(
          target.path, target._listed_path(),
          target_commit, listing.tree._listed_path(),
          listing.commit)

  # TODO use child listings for other errors too. And in status.
  Listing = namedtuple('Listing', ['tree', 'commit'])

  def child_listings(self, target: gordion.Repository) -> List[Listing]:
    """
    Searches the tree for listings of the provided target repository and returns a list of Tuples of
    gordion.Tree and the commit listing of the target repository.
    """
    listings = []

    self.yeditor.reload()
    # Check yaml file for this repository
    if self.yeditor.exists():
      for child_name, child_info in self.yeditor.yaml_data['repositories'].items():
        gpath = self.yeditor.read_repository_gpath(child_name)
        child_path = os.path.join(gordion.Store().path, gpath)

        # Check if the child exists.
        if gordion.Repository._exists(child_path):
          # Check if the existing repository is the correct url before creating the Tree object.
          if gordion.Repository._url(child_path) == child_info['url']:
            child = Tree(child_path, child_info['url'], self)
            child_target_commit = child._verify_tag(child_info['tag'])

            # Check if the child matches the target by name, path, and url
            if (target.name == child_name and target.path == child_path and  # noqa: W504
                target.url == child_info['url']):
              listings.append(gordion.Tree.Listing(tree=child, commit=child_target_commit))

            # Also check the child's children ONLY if the child is the correct tag.
            if child.handle.head.commit == child_target_commit:
              listings.extend(child.child_listings(target))

    return listings
