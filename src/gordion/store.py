import os
import gordion
import git
import shutil
from typing import List


# TODO move this to a dedicated singleton.py in utils folder.
def singleton(cls):
  instances = {}

  def get_instance(*args, **kwargs):
    if cls not in instances:
      instances[cls] = cls(*args, **kwargs)
    return instances[cls]
  return get_instance


@singleton
class Store:
  """
  Singleton class dedicated to managing the gordion/ folder.
  """

  def __init__(self) -> None:
    self.path = ''

  def setup(self, root_repository_path):
    """
    User must call this function once with the root gordion repository path, where we will store the
    gordion/ folder managed by this class.
    """
    self.path = os.path.join(root_repository_path, 'gordion')

  def print(self):
    assert self.path
    print(f"gordion dir: {self.path}")

  # TODO static
  def safe_remove_repo(self, repo_path, force: bool = False):
    """
    Deletes the repository as long as information will not be lost. Generates an error if the
    repository has unsaved branches/commits or if it has stashes.
    """
    assert self.path
    assert gordion.Repository._exists(repo_path)
    repo = git.Repo(repo_path)

    # Check if repository has local changes.
    if repo.is_dirty(untracked_files=True):
      if not force:
        raise gordion.UnsafeRemoveDirty(repo_path)

    # Check if any information would be lost from local branches if we delete this repository.
    for local_branch in repo.branches:
      # If there is a tracking branch, ensure the local branch is not ahead of it.
      tracking_branch = local_branch.tracking_branch()
      if tracking_branch:
        merge_base = repo.merge_base(local_branch, tracking_branch)
        commits_ahead = list(repo.iter_commits(
            f'{merge_base[0].hexsha}..{local_branch.commit.hexsha}'))

        if commits_ahead:
          raise gordion.UnsafeRemoveLocalBranchAhead(repo_path, local_branch.name,
                                                     tracking_branch.name, len(commits_ahead))

      # There is no tracking branch, so error.
      else:
        raise gordion.UnsafeRemoveLocalBranchNoTrackingBranch(repo_path, local_branch.name)

    # Error if the repository has stashes that will be lost by the deletion.
    stashes = repo.git.stash('list')
    if stashes:
      raise gordion.UnsafeRemoveStashes(repo_path, stashes)

    # If we reach here, it's safe to delete the repository
    print(f"Deleting directory: {repo_path}")
    shutil.rmtree(repo_path)

  def trim_repos(self, keep_repos: List[str], force: bool = False):
    """
    Removes repositories that are not listed in the keep_repos argument.
    """

    # Delete git repositories.
    for dirpath, dirnames, _ in os.walk(self.path, topdown=True):
      for dirname in dirnames:
        full_dirpath = os.path.join(dirpath, dirname)
        if (os.path.exists(full_dirpath) and not gordion.is_related_path(full_dirpath,
                                                                         keep_repos)):
          if gordion.Repository._exists(full_dirpath):
            gordion.Store().safe_remove_repo(full_dirpath, force)

    # Delete everything else that is not related to the gordion paths.
    for dirpath, dirnames, _ in os.walk(self.path, topdown=True):
      for dirname in dirnames:
        full_dirpath = os.path.join(dirpath, dirname)
        if (os.path.exists(full_dirpath) and not gordion.is_related_path(full_dirpath,
                                                                         keep_repos)):
          print(f"Deleting directory: {full_dirpath}")
          assert not gordion.Repository._exists(full_dirpath)  # Removed above.
          shutil.rmtree(full_dirpath)
