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
    TODO

    """

    target_commit = Repository._verify_tag(self.handle, self.target_tag)

    if Repository._does_local_branch_have_commit(self.handle, self.target_branch_name,
                                                 target_commit):
      local_branch = self.handle.branches[self.target_branch_name]
      # Check if target commit is HEAD of local branch.
      if target_commit == local_branch.commit:
        local_branch.checkout()

      # Target commit is in local branch history.
      else:
        # Check if local branch is ahead of remote. TODO ensure a remote branch exists.
        origin = self.handle.remotes.origin
        origin.fetch()
        # Find the latest common ancestor between the two branches
        remote_branch = local_branch.tracking_branch()
        merge_base = self.handle.merge_base(local_branch, remote_branch)

        # Compare local commits that are ahead of the merge base but not in the remote branch
        commits_ahead = list(self.handle.iter_commits(
            f'{merge_base[0].hexsha}..{local_branch.commit.hexsha}'))
        if commits_ahead:
          raise gordion.UpdateActiveBranchAheadError(
              self.path, self.target_branch_name, f'origin/{self.target_branch_name}',
              len(commits_ahead))

        # All target branch local commits are contained in remote, reset to the target commit
        else:
          local_branch.checkout()
          self.handle.head.reset(commit=target_commit, index=True, working_tree=True)

      # TODO go to local branch commit

    # At least for the current repository. For nested repository, something could go wrong, leaving
    # things in a broken state. but that's ok because the repository itself is a well understood
    # state.

    # # Branch is constant
    # if self.handle.active_branch.name == self.target_branch_name:
    #   # Commit is constant
    #   target_commit = self.handle.commit(self.target_tag)
    #   if target_commit == self.handle.active_branch.commit:
    #     pass  # nothing to do.

    #   # Commit changes
    #   else:
    #     # Fetch remote information
    #     origin = self.handle.remotes.origin
    #     origin.fetch()

    #     # Active branch contains target commit
    #     if target_commit in self.handle.active_branch.commit.traverse():
    #       # Check if the active branch is behind remote
    #       if (self._is_active_branch_behind_remote()):
    #         # TODO rethink
    #         # Set the active branch to the target commit
    #         self.handle.git.reset(target_commit, hard=True)
    #       else:
    #         self._update_active_branch(target_commit, force)

    #     # Active branch does NOT contain target commit.
    #     else:
    #       # No remote tracking branch
    #       if self.handle.active_branch.tracking_branch() is None:
    #         raise "TODO error active branch does not have remote and does not contain commit"

    #       # Has remote tracking branch
    #       else:
    #         # Tracking branch contains target commit
    #         if self._does_tracking_branch_contain_target_commit():
    #           self.handle.git.reset(target_commit, hard=True)

    #         # Tracking branch does NOT contain target commit
    #         else:
    #           raise gordion.TargetBranchDoesNotContainTag(self)

    #       # Check if remote branch contains target commit.
    #       # remote_ref = repo.refs[remote_branch]

    # # Branch changes.
    # else:
    #   if (self._is_target_branch_at_target_commit()):
    #     self.handle.branches[self.target_branch_name].checkout()
    #   else:
    #     raise "todo"

  # @staticmethod
  # def _go_to_local_branch_commit(repo: Repo, branch_name: str, commit: Repo.commit):
  #   local_branch = repo.branches[branch_name]
  #   if commit == local_branch.commit:
  #     local_branch.checkout()
  #   else
  #   pass

  @staticmethod
  def _verify_tag(repo: Repo, tag: str) -> Repo.commit:
    """
    Verifies and returns the commit object for the specified tag if it exists, otherwise throws an
    error. This fuction will perform a fetch if necessary to check if recent remote changes contain
    the tag.
    """
    try:
      commit = repo.commit(tag)
    except ValueError:
      # A value error is thrown if the commit is not found. Let's fetch and then try one more time.
      # Fetch takes time and an internet connection, so I only want to do it if I have to.
      origin = repo.remotes.origin
      origin.fetch()

      # If this throws a Value error again, then the commit really does not exist. If it throws a
      # BadName error, the tag/commit is ill-formed.
      commit = repo.commit(tag)
      return commit

    return commit

  @staticmethod
  def _does_local_branch_have_commit(repo: Repo, branch_name: str, commit: Repo.commit) -> bool:
    """
    Returns true if there exist a local branch with the specified name, that contains the specified
    commit. Otherwise it returns false.
    """
    try:
      local_branch = repo.heads[branch_name]
    except IndexError:
      # The local branch does not exist, so it cannot contain the commit.
      return False

    if commit == local_branch.commit:
      return True
    else:
      return commit in local_branch.commit.iter_parents()

    # def _is_target_branch_at_target_commit(self):
    #   target_commit = self.handle.commit(self.target_tag)
    #   target_branch = self.handle.branches[self.target_branch_name]
    #   return target_branch.commit.hexsha == target_commit.hexsha

    # def _is_active_branch_behind_remote(self) -> bool:
    #   active_branch = self.handle.active_branch
    #   remote_branch = self.handle.active_branch.tracking_branch()

    #   commits_behind = list(self.handle.iter_commits(f"{active_branch}..{remote_branch}"))
    #   if len(commits_behind) > 0:
    #     return True
    #   return False

    # def _does_tracking_branch_contain_target_commit(self):
    #   remote_branch = self.handle.active_branch.tracking_branch()
    #   target_commit = self.handle.commit(self.target_tag)

    #   for commit in self.handle.iter_commits(remote_branch.name):
    #     if commit.hexsha == target_commit.hexsha:
    #       return True
    #   return False

    # def _update_active_branch(self, target_commit, force: bool):
    #   # Resolve the local and remote branch references
    #   local_branch = self.handle.heads[self.target_branch_name]
    #   remote_branch_ref = f'origin/{self.target_branch_name}'
    #   remote_branch = self.handle.remotes['origin'].refs[self.target_branch_name]

    #   # Find the latest common ancestor between the two branches
    #   merge_base = self.handle.merge_base(local_branch, remote_branch)

    #   # Make sure there is a common history.
    #   if not merge_base:
    #     pass
    #     # TODO f"No common history between {local_branch_name} and {remote_branch_ref}." raise
    #     # gordion.OperationError("Error, the active branch cannot be updated because it differes from
    #     # the remote branch. TODO need to..")

    #   # Compare local commits that are ahead of the merge base but not in the remote branch
    #   commits_ahead = list(self.handle.iter_commits(
    #       f'{merge_base[0].hexsha}..{local_branch.commit.hexsha}'))

    #   # Compare remote commits that are ahead of the merge base but not in the local branch
    #   commits_behind = list(self.handle.iter_commits(
    #       f'{merge_base[0].hexsha}..{remote_branch.commit.hexsha}'))

    #   # Evaluate comparison results
    #   if commits_ahead and commits_behind:
    #     print(f"TODO: {self.target_branch_name} and {remote_branch_ref} have diverged with"
    #           f"{len(commits_ahead)} local commit(s) ahead and {len(commits_behind)} remote"
    #           f"commit(s) behind.")
    #   elif commits_ahead:
    #     if not force:
    #       raise gordion.UpdateActiveBranchAheadError(
    #           self.path, self.target_branch_name, remote_branch_ref, len(commits_ahead))
    #     else:
    #       # TODO print messages about what commits have been lost.
    #       self.handle.git.reset('--hard', target_commit)

    #   elif commits_behind:
    #     # Reset the branch to the specific commit
    #     print("\nhere commits behind")
    #     self.handle.git.reset('--hard', target_commit)

    #     # return f"{local_branch_name} is behind {remote_branch_ref} by {len(commits_behind)}
    #     # commit(s)."
    #   # else:
    #   #     return f"{local_branch_name} and {remote_branch_ref} are up-to-date."

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
