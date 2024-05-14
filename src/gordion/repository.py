import os
import subprocess
from git import Repo, NoSuchPathError, InvalidGitRepositoryError
import gordion


class Repository:
  """
  Encapsulates a git repository in the gordion context.

  """

  def __init__(self, path: str, url: str, tag: str, branch: str) -> None:
    self.path = path

    # Clone if necessary.
    if not Repository._exists(path):
      cache = gordion.Cache()
      mirror_path = cache.ensure_mirror(url)

      args = ['git', 'clone', '--reference', mirror_path, url, self.path]
      subprocess.check_call(args, stderr=subprocess.STDOUT)

    self.handle = Repo(self.path)
    self.target_tag = tag
    self.target_branch_name = branch

  def update(self, force=False) -> None:
    """
    Clones the repository if it does not exist, otherwise updates it to the requested branch:tag

    """

    # TODO make sure git operations don't do anything until we know the whole thing would succeed?
    # At least for the current repository. For nested repository, something could go wrong, leaving
    # things in a broken state. but that's ok because the repository itself is a well understood
    # state.

    # Check if branch is constant.
    if self.handle.active_branch.name == self.target_branch_name:
      # Check if commit is constant
      target_commit = self.handle.commit(self.target_tag)
      if target_commit == self.handle.active_branch.commit:
        pass  # nothing to do.

      # The commit changes.
      else:
        # Fetch remote information
        origin = self.handle.remotes.origin
        origin.fetch()

        # Check if active branch contains the target commit.
        if target_commit in self.handle.active_branch.commit.traverse():
          self._update_active_branch(target_commit, force)

        # Active branch does not contain target commit.
        else:
          pass
          # Check if remote branch contains target commit.
          # remote_ref = repo.refs[remote_branch]

    # Branch changes.
    else:
      if (self._is_target_branch_at_target_commit()):
        self.handle.branches[self.target_branch_name].checkout()
      else:
        raise "todo"

  def _is_target_branch_at_target_commit(self):
    target_commit = self.handle.commit(self.target_tag)
    target_branch = self.handle.branches[self.target_branch_name]
    return target_branch.commit.hexsha == target_commit.hexsha

  def _update_active_branch(self, target_commit, force: bool):
    # Resolve the local and remote branch references
    local_branch = self.handle.heads[self.target_branch_name]
    remote_branch_ref = f'origin/{self.target_branch_name}'
    remote_branch = self.handle.remotes['origin'].refs[self.target_branch_name]

    # Find the latest common ancestor between the two branches
    merge_base = self.handle.merge_base(local_branch, remote_branch)

    # Make sure there is a common history.
    if not merge_base:
      pass
      # TODO f"No common history between {local_branch_name} and {remote_branch_ref}." raise
      # gordion.OperationError("Error, the active branch cannot be updated because it differes from
      # the remote branch. TODO need to..")

    # Compare local commits that are ahead of the merge base but not in the remote branch
    commits_ahead = list(self.handle.iter_commits(
        f'{merge_base[0].hexsha}..{local_branch.commit.hexsha}'))

    # Compare remote commits that are ahead of the merge base but not in the local branch
    commits_behind = list(self.handle.iter_commits(
        f'{merge_base[0].hexsha}..{remote_branch.commit.hexsha}'))

    # Evaluate comparison results
    if commits_ahead and commits_behind:
      print(f"TODO: {self.target_branch_name} and {remote_branch_ref} have diverged with"
            f"{len(commits_ahead)} local commit(s) ahead and {len(commits_behind)} remote"
            f"commit(s) behind.")
    elif commits_ahead:
      if not force:
        raise gordion.UpdateActiveBranchAheadError(
            self.path, self.target_branch_name, remote_branch_ref, len(commits_ahead))
      else:
        # TODO print messages about what commits have been lost.
        self.handle.git.reset('--hard', target_commit)

    elif commits_behind:
      # Reset the branch to the specific commit
      print("\nhere commits behind")
      self.handle.git.reset('--hard', target_commit)

      # return f"{local_branch_name} is behind {remote_branch_ref} by {len(commits_behind)}
      # commit(s)."
    # else:
    #     return f"{local_branch_name} and {remote_branch_ref} are up-to-date."

  @staticmethod
  def _exists(path: str) -> bool:
    try:
        # Initialize the Repo object
      repo = Repo(path)
      # Compare the absolute paths to determine if 'path' is the repository root
      return os.path.abspath(repo.working_tree_dir) == os.path.abspath(path)
    except (NoSuchPathError, InvalidGitRepositoryError):
      # If Repo initialization fails, the path is not a Git repository
      return False
