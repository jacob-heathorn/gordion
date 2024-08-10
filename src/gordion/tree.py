import gordion
import os
import git
import shutil
from typing import List


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
    gordion.Store()

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

  def update(self, tag: str, branch_name: str, force: bool = False) -> None:
    """
    Updates this repository and it's children.
    """
    # Check for duplicate tag
    root = self._root()
    self._check_duplicate_repo_tag(tag, root)

    super().update(tag, branch_name, force)

    self.yeditor.reload()
    self._update_children(branch_name, force)

    # Cleanup detached repositories.
    if self is root:
      self._clean_detached_repos(force)

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
  def _safe_remove_repo(path, force: bool = False):
    """
    Deletes the repository as long as information will not be lost. Generates an error if the
    repository has unsaved branches/commits or if it has stashes.
    """
    assert gordion.Repository._exists(path)
    repo = git.Repo(path)

    # Check if repository has local changes.
    if repo.is_dirty(untracked_files=True):
      if not force:
        raise gordion.UnsafeRemoveDirty(path)

    # Check if any information would be lost from local branches if we delete this repository.
    for local_branch in repo.branches:
      # If there is a tracking branch, ensure the local branch is not ahead of it.
      tracking_branch = local_branch.tracking_branch()
      if tracking_branch:
        merge_base = repo.merge_base(local_branch, tracking_branch)
        commits_ahead = list(repo.iter_commits(
            f'{merge_base[0].hexsha}..{local_branch.commit.hexsha}'))

        if commits_ahead:
          raise gordion.UnsafeRemoveLocalBranchAhead(path, local_branch.name,
                                                     tracking_branch.name, len(commits_ahead))

      # There is no tracking branch, so error.
      else:
        raise gordion.UnsafeRemoveLocalBranchNoTrackingBranch(path, local_branch.name)

    # Error if the repository has stashes that will be lost by the deletion.
    stashes = repo.git.stash('list')
    if stashes:
      raise gordion.UnsafeRemoveStashes(path, stashes)

    # If we reach here, it's safe to delete the repository
    print(f"Deleting directory: {path}")
    shutil.rmtree(path)

  def _clean_detached_repos(self, force: bool = False):
    """
    Removes repositories that are not listed in the yaml tree.
    """
    # Get all the paths of all repositories:
    root = self._root()
    child_paths = root._list_child_repository_paths()

    # Delete git repositories.
    for dirpath, dirnames, _ in os.walk(os.path.join(root.path, 'gordion'), topdown=True):
      for dirname in dirnames:
        full_dirpath = os.path.join(dirpath, dirname)
        if (os.path.exists(full_dirpath) and not gordion.is_related_path(full_dirpath,
                                                                         child_paths)):
          if gordion.Repository._exists(full_dirpath):
            gordion.Tree._safe_remove_repo(full_dirpath, force)

    # Delete everything else that is not related to the gordion paths.
    for dirpath, dirnames, _ in os.walk(os.path.join(root.path, 'gordion'), topdown=True):
      for dirname in dirnames:
        full_dirpath = os.path.join(dirpath, dirname)
        if (os.path.exists(full_dirpath) and not gordion.is_related_path(full_dirpath,
                                                                         child_paths)):
          print(f"Deleting directory: {full_dirpath}")
          assert not gordion.Repository._exists(full_dirpath)  # Removed above.
          shutil.rmtree(full_dirpath)

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
        child_path = os.path.join(root.path, 'gordion', gpath)
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
            gordion.Tree._safe_remove_repo(self.path)

        child = Tree(child_path, child_info['url'], self)
        child.update(child_info['tag'], branch_name, force)
        self.children[child_name] = child

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

  def _check_duplicate_repo_tag(self, target_tag, other):
    """
    Recursively checks the repository tag against another repository and it's children.
    """

    if self is not other:
      host, username, repo_name = gordion.extract_repo_details(self.url)
      other_host, other_username, other_repo_name = gordion.extract_repo_details(other.url)

      # Check if the remote repository is the same
      if host == other_host and username == other_username and repo_name == other_repo_name:
        # Make sure the repository has the same tag.
        if target_tag != other.handle.head.commit.hexsha:
          raise gordion.UpdateSameRepoDifferentTagError(self.path, self._listed_path(),
                                                        target_tag, other._listed_path(),
                                                        other.handle.head.commit.hexsha)

    # Check against the other's children
    for _, other_child in other.children.items():
      Tree._check_duplicate_repo_tag(self, target_tag, other_child)
