import gordion
import os
import git
import shutil
from typing import List


class Tree(gordion.Repository):
  """
  Adds gordion tree functionality to the repository class.

  """

  def __init__(self, path: str, url: str = '', parent=None) -> None:
    super().__init__(path, url)
    self.parent: Tree = parent
    self.children: dict[str, Tree] = {}
    self.yeditor = gordion.YamlEditor(os.path.join(self.path, 'gordion.yaml'))

  def _root(self):
    """
    Recursively returns the root repository object.
    """
    if self.parent:
      return self.parent._root()
    else:
      return self

  def _relpath(self) -> str:
    return os.path.relpath(self.path, os.path.dirname(self._root().path))

  def _listed_path(self) -> str:
    listed_path = ''
    if self.parent:
      gpath = self.parent.yeditor.read_repository_gpath(self.name)
      listed_path = f"{self.parent._relpath()} lists {gpath}"
    else:
      listed_path = f"{self._relpath()} (root)"

    return listed_path

  def update(self, tag: str, branch_name: str, force: bool = False) -> None:
    # TODO make it become commit inside repo, check for duplicate tag while it's only a string here.
    commit: git.Commit = self._verify_tag(tag)

    # Check for duplicate tag
    root = self._root()
    self._check_duplicate_repo_tag(tag, root)

    super().update(commit, branch_name, force)

    self.yeditor.reload()
    self._update_children(branch_name, force)

    # Cleanup detached repositories.
    if self is root:
      self._clean_detached_repos(force)

  def _list_child_repository_paths(self) -> List[str]:
    paths = []
    for _, repo in self.children.items():
      paths.append(repo.path)
      paths.extend(repo._list_child_repository_paths())
    return paths

  @staticmethod
  def _safe_remove_repo(path, force: bool = False):
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
    root = self._root()
    self.children = {}

    # Open the gordion yaml file for this repository if it exists.
    if self.yeditor.exists():
      assert self.yeditor.yaml_data
      for child_name, child_info in self.yeditor.yaml_data['repositories'].items():
        # Create child repository objects
        gpath = self.yeditor.read_repository_gpath(child_name)
        child_path = os.path.join(root.path, 'gordion', gpath)

        # TODO these go here
        # _check_different_repo_same_path
        # _check_duplicate_repo_path
        #
        # if url != repo.remotes.origin.url:
        #   self._check_different_repo_same_path(self._root())
        #   gordion.Tree._safe_remove_repo(self.path)

        child = Tree(child_path, child_info['url'], self)
        child.update(child_info['tag'], branch_name, force)
        self.children[child_name] = child

  def _check_different_repo_same_path(self, other):
    """
    Recursively checks the repository path against another repository and it's children.
    """
    host, username, repo_name = gordion.extract_repo_details(self.url)
    other_host, other_username, other_repo_name = gordion.extract_repo_details(other.url)

    # Check if the remote repository is the same
    if host != other_host or username != other_username or repo_name != other_repo_name:
      # Make sure the repository does not have the same local path.
      if self.path == other.path:
        raise gordion.UpdateDifferentRepoSamePathError(self, other)

    # Check against the other's children
    for _, other_child in other.children.items():
      Tree._check_different_repo_same_path(self, other_child)

  def _check_duplicate_repo_path(self, other):
    """
    Recursively checks the repository path against another repository and it's children.
    """
    host, username, repo_name = gordion.extract_repo_details(self.url)
    other_host, other_username, other_repo_name = gordion.extract_repo_details(other.url)

    # Check if the remote repository is the same
    if host == other_host and username == other_username and repo_name == other_repo_name:
      # Make sure the repository has the same local path.
      if self.path != other.path:
        raise gordion.UpdateDuplicateRepoPathError(self, other)

    # Check against the other's children
    for _, other_child in other.children.items():
      Tree._check_duplicate_repo_path(self, other_child)
