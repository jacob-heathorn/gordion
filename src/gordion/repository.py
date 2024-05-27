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
            self.handle, local_branch)

        # Make sure the local branch is not ahead of tracking branch, since we're moving the
        # local HEAD, information would be lost.
        Repository._verify_local_commits_not_ahead(self.handle, local_branch, tracking_branch)

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
              self.handle, local_branch)

          # Make sure the local branch is not ahead of tracking branch, since we're moving the
          # local HEAD, information would be lost.
          Repository._verify_local_commits_not_ahead(self.handle, local_branch, tracking_branch)

          # Good to go move the local branch HEAD to the target commit.
          local_branch.checkout()
          self.handle.head.reset(commit=target_commit, index=True, working_tree=True)

        # There is no local branch yet, create it, and reset it to the target commit.
        else:
          self.handle.git.checkout('-b', self.target_branch_name,
                                   f'origin/{self.target_branch_name}')
          self.handle.head.reset(commit=target_commit, index=True, working_tree=True)

      # We could not find the commit on a local or remote branch by the designated name, so just
      # checkout the commit in a detached head state.
      else:
        self.handle.git.checkout(target_commit)

  @staticmethod
  def _verify_local_commits_not_ahead(repo: Repo, local_branch, remote_branch):
    merge_base = repo.merge_base(local_branch, remote_branch)

    commits_ahead = list(repo.iter_commits(
        f'{merge_base[0].hexsha}..{local_branch.commit.hexsha}'))
    if commits_ahead:
      raise gordion.UpdateLocalBranchAheadError(
          repo.working_tree_dir, local_branch.name, remote_branch.name, len(commits_ahead))

  @staticmethod
  def _verify_local_branch_has_correct_tracking_branch(repo: Repo, local_branch):
    if local_branch.tracking_branch():
      remote_branch = local_branch.tracking_branch()
      if remote_branch.name != f"origin/{local_branch.name}":
        raise gordion.UpdateWrongTrackingBranchError(
            repo.working_tree_dir, local_branch.name, remote_branch.name)
      else:
        return remote_branch
    else:
      raise gordion.UpdateNoTrackingBranchError(repo.working_tree_dir, local_branch.name)

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
