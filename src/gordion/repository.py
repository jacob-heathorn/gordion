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
    self.fetched = False

  # TODO create a fetchonce function that will only fetch one time for the lifetime of the update()
  # function call.
  def update(self, force=False) -> None:
    """
    TODO

    """

    target_commit = self._verify_tag(self.target_tag)

    if Repository._does_local_branch_have_commit(self.handle, self.target_branch_name,
                                                 target_commit):
      local_branch = self.handle.branches[self.target_branch_name]
      # Check if target commit is HEAD of local branch.
      if target_commit.hexsha == local_branch.commit.hexsha:
        local_branch.checkout()

      # Target commit is in local branch history.
      else:
        # Need to fetch for this part of the logic.
        self.fetch_once()

        # Make sure the local branch is setup to track the expected remote branch.
        local_branch = self.handle.branches[self.target_branch_name]
        tracking_branch = Repository._verify_local_branch_has_correct_tracking_branch(
            self.path, local_branch)

        # Make sure the local branch is not ahead of tracking branch, since we're moving the
        # local HEAD, information would be lost.
        Repository._verify_local_commits_not_ahead(
            self.path, self.handle, local_branch, tracking_branch)

        # Good to go move the local branch HEAD to the target commit.
        local_branch.checkout()
        self.handle.head.reset(commit=target_commit, index=True, working_tree=True)

    # Tag is not on a local branch
    else:
      self.fetch_once()

      # Check if the remote branch has the commit
      if Repository._does_remote_branch_have_commit(self.handle, self.target_branch_name,
                                                    target_commit):

        # Check if there is a local branch to match the remote branch.
        local_branches = [branch.name for branch in self.handle.branches]

        if self.target_branch_name in local_branches:
          # Make sure the local branch is setup to track the expected remote branch.
          local_branch = self.handle.branches[self.target_branch_name]
          tracking_branch = Repository._verify_local_branch_has_correct_tracking_branch(
              self.path, local_branch)

          # Make sure the local branch is not ahead of tracking branch, since we're moving the
          # local HEAD, information would be lost.
          Repository._verify_local_commits_not_ahead(
              self.path, self.handle, local_branch, tracking_branch)

          # Good to go move the local branch HEAD to the target commit.
          local_branch.checkout()
          self.handle.head.reset(commit=target_commit, index=True, working_tree=True)

        # There is no local branch yet, create it, and reset it to the target commit.
        else:
          self.handle.git.checkout('-b', self.target_branch_name,
                                   f'origin/{self.target_branch_name}')
          self.handle.head.reset(commit=target_commit, index=True, working_tree=True)

  # TODO get repo path from repo objec this function and one after.

  @staticmethod
  def _verify_local_commits_not_ahead(repo_path, repo: Repo, local_branch, remote_branch):
    merge_base = repo.merge_base(local_branch, remote_branch)

    commits_ahead = list(repo.iter_commits(
        f'{merge_base[0].hexsha}..{local_branch.commit.hexsha}'))
    if commits_ahead:
      raise gordion.UpdateLocalBranchAheadError(
          repo_path, local_branch.name, remote_branch.name, len(commits_ahead))

  @staticmethod
  def _verify_local_branch_has_correct_tracking_branch(repo_path, local_branch):
    if local_branch.tracking_branch():
      remote_branch = local_branch.tracking_branch()
      if remote_branch.name != f"origin/{local_branch.name}":
        raise gordion.UpdateWrongTrackingBranchError(
            repo_path, local_branch.name, remote_branch.name)
      else:
        return remote_branch
    else:
      raise gordion.UpdateNoTrackingBranchError(repo_path, local_branch.name)

  @staticmethod
  def _does_remote_branch_have_commit(repo: Repo, branch_name: str, commit: Repo.commit) -> bool:
    """
    Returns true if there is a remote branch with the specified name, that contains the specified
    commit. Otherwise it returns false.
    """
    try:
      remote_branch = repo.refs[f"origin/{branch_name}"]
    except IndexError:
      # The local branch does not exist, so it cannot contain the commit.
      return False

    if commit == remote_branch.commit:
      return True
    else:
      return commit in remote_branch.commit.iter_parents()

  def _verify_tag(self, tag: str) -> Repo.commit:
    """
    Verifies and returns the commit object for the specified tag if it exists, otherwise throws an
    error. This fuction will perform a fetch if necessary to check if recent remote changes contain
    the tag.
    """
    try:
      commit = self.handle.commit(tag)
    except ValueError:
      # A value error is thrown if the commit is not found. Let's fetch and then try one more time.
      # Fetch takes time and an internet connection, so I only want to do it if I have to.
      self.fetch_once()

      # If this throws a Value error again, then the commit really does not exist. If it throws a
      # BadName error, the tag/commit is ill-formed.
      commit = self.handle.commit(tag)
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

  def fetch_once(self):
    """
    Fetches only once for the lifetime of this Repository object.
    """
    if not self.fetched:
      self.handle.remotes.origin.fetch()
      self.fetched = True
