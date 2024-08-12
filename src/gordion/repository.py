import os
import subprocess
import git
import gordion
from abc import abstractmethod
import shutil


class Repository:
  """
  Encapsulates a git repository in the gordion context.

  """

  def __init__(self, path: str, url: str = '') -> None:
    self.path = path
    self.name = os.path.basename(self.path)
    self.url = Repository._derive_url(path, url)
    self.default_branch_name = ''
    self.fetched = False
    self.handle: git.Repo = []
    self._ensure()

  @staticmethod
  def _derive_url(path: str, url: str):
    # Derive url if necessary.
    if not url:
      assert gordion.Repository._exists(path)
      repo = git.Repo(path)
      url = repo.remotes.origin.url
    else:
      if gordion.Repository._exists(path):
        repo = git.Repo(path)
        assert url == repo.remotes.origin.url

    return url

  @abstractmethod
  def _relpath(self):
      pass

  def _ensure(self):
    """
    Clones the repository if necessary and creates the underlying git repository handle.
    """

    # Clone if necessary. At this point the mirror should exist regardless of whether the repository
    # exists. so ensure it first.
    cache = gordion.Cache()
    mirror_path, self.default_branch_name = cache.ensure_mirror(self.url)
    if not Repository._exists(self.path):
      args = ['git', 'clone', '--reference', mirror_path, self.url, self.path]
      subprocess.check_call(args, stderr=subprocess.STDOUT)

    # Reload objects.
    self.handle = git.Repo(self.path)

  def update(self, tag: str, branch_name: str, force: bool = False) -> None:
    """
    Updates the repository to the specified commit and optional branch, as long as information will
    not be lost in the process, otherwise it will raise descriptive errors about what to do next.

    """
    commit: git.Commit = self._verify_tag(tag)

    # If the commit does not change, we are done. Allow user to manually checkout a HEAD or
    # different branch name and still satisfy the update.
    if self.handle.head.commit.hexsha != commit.hexsha:
      self._update_moving_commit(commit, branch_name, force)

  def _update_moving_commit(self, commit: git.Commit, branch_name: str,
                            force: bool = False) -> None:
    """
    The internal version of the update() method. Called only if the commit moves.
    """
    # Verify that we don't have an unsaved HEAD that would be lost by the update.
    if self.handle.head.is_detached:
      self._verify_head_wont_be_lost(commit)

    # Verify we don't have uncommitted chages that could be lost by the update.
    if self.handle.is_dirty(untracked_files=True):
      if commit.hexsha != self.handle.head.commit.hexsha:
        raise gordion.UpdateRepoIsDirtyError(self.path)

    # Check if a branch HAS NOT been specified.
    if not branch_name:
      # Checkout the target commit in a detached HEAD state as long as it is not dangling.
      self._check_dangling_commit(commit)
      self.handle.git.checkout(commit)

    # A branch HAS been specified
    else:
      # Check if a local branch by the target name has the target commit.
      if Repository._does_local_branch_have_commit(self.handle, branch_name, commit):
        self._checkout_local_branch_commit(branch_name, commit, force)

      # Tag is not on the specified local branch.
      else:

        self._fetch_once()

        # Check if a remote branch by the target name has the target commit.
        if Repository._does_remote_branch_have_commit(self.handle, branch_name, commit):
          self._checkout_remote_branch_commit(branch_name, commit, force)

        # We could not find the commit on a local or remote branch by the designated name, so just
        # checkout the commit in a detached head state.
        else:
          # Checkout the target commit in a detached HEAD state as long as it is not dangling.
          self._check_dangling_commit(commit)
          self.handle.git.checkout(commit)

  def _checkout_local_branch_commit(self, branch_name: str, commit: git.Commit, force: bool):
    local_branch = self.handle.branches[branch_name]

    # Check if target commit is HEAD of local branch.
    if commit == local_branch.commit:
      local_branch.checkout()

    # Target commit is in local branch history.
    else:
      # Need to fetch for this part of the logic.
      self._fetch_once()

      # Make sure the local branch is setup to track the expected remote branch.
      local_branch = self.handle.branches[branch_name]
      tracking_branch = self._verify_local_branch_has_correct_tracking_branch(local_branch)

      # Make sure the local branch is not ahead of tracking branch, since we're moving the
      # local HEAD, information would be lost.
      if not force:
        self._verify_local_commits_not_ahead(local_branch, tracking_branch)

      # Good to go move the local branch HEAD to the target commit.
      print(f"{self._relpath()}: checking out {local_branch.name}:{commit.hexsha}")
      local_branch.checkout()
      self.handle.head.reset(commit=commit, index=True, working_tree=True)

  def _checkout_remote_branch_commit(self, branch_name: str, commit: git.Commit, force: bool):
    # Check if there is a local branch to match the remote branch.
    local_branches = [branch.name for branch in self.handle.branches]

    if branch_name in local_branches:
      # Make sure the local branch is setup to track the expected remote branch.
      local_branch = self.handle.branches[branch_name]
      tracking_branch = self._verify_local_branch_has_correct_tracking_branch(local_branch)

      # Make sure the local branch is not ahead of tracking branch, since we're moving the
      # local HEAD, information would be lost.
      if not force:
        self._verify_local_commits_not_ahead(local_branch, tracking_branch)

      # Good to go move the local branch HEAD to the target commit.
      print(f"{self._relpath()}: checking out {local_branch.name}:{commit.hexsha}")
      local_branch.checkout()
      self.handle.head.reset(commit=commit, index=True, working_tree=True)

    # There is no local branch yet, create it, and reset it to the target commit.
    else:
      self.handle.git.checkout('-b', branch_name, f'origin/{branch_name}')
      self.handle.head.reset(commit=commit, index=True, working_tree=True)

  def _check_dangling_commit(self, commit):
    """
    Checks if the commit is dangling (does not belong to a branch) and raises an error if it is
    because we don't like that business.
    """
    dangling_commit = True
    for ref in self.handle.references:
      for reachable_commit in self.handle.iter_commits(ref):
        if commit.hexsha == reachable_commit.hexsha:
          dangling_commit = False

    if dangling_commit:
      raise gordion.DanglingCommitError(self.path, commit.hexsha)

  def _verify_head_wont_be_lost(self, commit):
    """
    This function should be used while in a detached head sate. It Raises an error if update will
    move the HEAD AND the HEAD is a commit that is not saved on a local or remote branch somewhere.
    """
    head_commit = self.handle.head.commit

    # Check if the target commit is different from the HEAD commit
    if commit.hexsha != head_commit.hexsha:
      # Check if the local HEAD commit is contained in a local or remote branch
      local_branches = [branch for branch in self.handle.branches if head_commit.hexsha in [
          commit.hexsha for commit in branch.commit.iter_parents()]]
      if not local_branches:
        self._fetch_once()
        remote_branches = [branch for branch in self.handle.remotes.origin.refs if
                           head_commit.hexsha in [commit.hexsha for commit in
                                                  branch.commit.iter_parents()]]
        if not remote_branches:
          raise gordion.UpdateDetachedHeadNotSavedError(self.path)

  def _verify_local_commits_not_ahead(self, local_branch, remote_branch):
    merge_base = self.handle.merge_base(local_branch, remote_branch)

    commits_ahead = list(self.handle.iter_commits(
        f'{merge_base[0].hexsha}..{local_branch.commit.hexsha}'))
    if commits_ahead:
      raise gordion.UpdateLocalBranchAheadError(self.path, local_branch.name,
                                                remote_branch.name, len(commits_ahead))

  def _verify_local_branch_has_correct_tracking_branch(self, local_branch):
    if local_branch.tracking_branch():
      remote_branch = local_branch.tracking_branch()
      if remote_branch.name != f"origin/{local_branch.name}":
        raise gordion.UpdateWrongTrackingBranchError(self.path, local_branch.name,
                                                     remote_branch.name)
      else:
        return remote_branch
    else:
      raise gordion.UpdateNoTrackingBranchError(self.path, local_branch.name)

  @staticmethod
  def _does_remote_branch_have_commit(repo: git.Repo, branch_name: str,
                                      commit: git.Repo.commit) -> bool:
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

  def _verify_tag(self, tag: str) -> git.Commit:
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
      self._fetch_once()

      # If this throws a Value error again, then the commit really does not exist. If it throws a
      # BadName error, the tag/commit is ill-formed.
      commit = self.handle.commit(tag)
      return commit

    return commit

  @staticmethod
  def _does_local_branch_have_commit(repo: git.Repo, branch_name: str,
                                     commit: git.Repo.commit) -> bool:
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
      repo = git.Repo(path)
      # Compare the absolute paths to determine if 'path' is the repository root
      return os.path.abspath(repo.working_tree_dir) == os.path.abspath(path)
    except (git.NoSuchPathError, git.InvalidGitRepositoryError):
      # If Repo initialization fails, the path is not a Git repository
      return False

  def _fetch_once(self):
    """
    Fetches only once for the lifetime of this Repository object.
    """
    if not self.fetched:
      # NOTE: The `--prune` option deletes local remote-tracking branches that no longer have
      # corresponding branches on the remote repository. When a child repository deletes a remote
      # branch (e.g. a PR is merged), we want the parent repository to see that deletion. Assuming
      # the user deletes the local branch too, then gordion cannot checkout that branch from their
      # local git cache, which would otherwise feel unexpected.
      self.handle.git.fetch('--prune')
      self.fetched = True

  @staticmethod
  def safe_delete(repo_path, force: bool = False):
    """
    Deletes the repository as long as information will not be lost. Generates an error if the
    repository has unsaved branches/commits or if it has stashes.
    """
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
    print(f"Deleting repository: {repo_path}")
    shutil.rmtree(repo_path)
