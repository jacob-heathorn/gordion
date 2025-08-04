import os
import subprocess
import git
import gordion
from typing import Optional
import shutil


@gordion.utils.registry
class Repository:
  """
  Encapsulates a git repository in the gordion context.

  """

  def __new__(cls, path: str) -> 'Repository':
    """
    Ensures singleton behavior - returns existing instance if already registered.
    """
    normalized_path = os.path.normpath(path)
    existing = cls.registry().get(normalized_path, None)  # type: ignore[attr-defined]
    if existing is not None:
      return existing
    # Create new instance
    instance = super().__new__(cls)
    return instance

  def __init__(self, path: str) -> None:
    """
    The constructor is only meant to be called for a repository that already exists on path. If one
    needs to or might need to be created, use the ensure() method.
    """
    # Skip initialization if already initialized
    if hasattr(self, 'path'):
      return

    self.path = os.path.normpath(path)
    self.name = os.path.basename(self.path)
    assert gordion.Repository.exists(path)
    self.handle: git.Repo = git.Repo(path)
    self.url = self.handle.remotes.origin.url
    self.yeditor = gordion.YamlEditor(os.path.join(self.path, 'gordion.yaml'))
    cache = gordion.Cache()
    _, self.default_branch_name = cache.ensure_mirror(self.url)
    self.fetched = False
    Repository.register(self.path, self)  # type: ignore[attr-defined]

  @staticmethod
  def ensure(path: str, url: str) -> 'gordion.Repository':
    """
    Ensures the repository exists at <path> with <url> and clones it with <url> if not.
    """
    gordion.Cache().ensure_mirror(url)
    repo = gordion.Repository.registry().get(path, None)  # type: ignore[attr-defined]
    if repo:
      if gordion.utils.compare_urls(url, repo.url):
        return repo
      else:
        gordion.Repository.safe_delete(path)

    return gordion.Repository.clone(path, url)

  @staticmethod
  def clone(path, url) -> 'gordion.Repository':
    """
    Clones the repository and returns it.
    """
    assert not gordion.Repository.exists(path)

    # Make sure the target path doesn't already exist as a non-repository.
    if os.path.exists(path):
      raise gordion.UpdateTargetPathExistsError(path)

    # At this point the mirror should exist regardless of whether the repository exists. so ensure
    # it first.
    cache = gordion.Cache()
    mirror_path, _ = cache.ensure_mirror(url)

    # Clone it.
    args = ['git', 'clone', '--reference', mirror_path, url, path]
    subprocess.check_call(args, stderr=subprocess.STDOUT)

    # Now create and return the repo.
    return gordion.Repository(path)

  @staticmethod
  def _derive_url(path: str, url: str):
    # Derive url if necessary.
    if not url:
      assert gordion.Repository.exists(path)
      repo = git.Repo(path)
      url = repo.remotes.origin.url
    else:
      if gordion.Repository.exists(path):
        repo = git.Repo(path)
        # If a repository with the wrong URL already exists at the child path, remove it.
        if not gordion.utils.compare_urls(url, repo.remotes.origin.url):
          gordion.Repository.safe_delete(path)

    return url

  def update(self, tag: str, branch_name: str, force: bool = False) -> None:
    """
    Updates the repository to the specified commit and optional branch, as long as information will
    not be lost in the process, otherwise it will raise descriptive errors about what to do next.

    """
    commit: git.Commit = self.verify_tag(tag)

    # If the commit does not change, we are done. Allow user to manually checkout a HEAD or
    # different branch name and still satisfy the update.
    if self.handle.head.commit.hexsha != commit.hexsha:
      self._checkout(commit, branch_name, force)

  def _checkout(self, commit: git.Commit, branch_name: str, force: bool = False) -> None:
    """
    Checks out the specified commit and optional branch.
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
      # Try the default branch.
      if not self._try_checkout(self.default_branch_name, commit, force):
        # Checkout the target commit in a detached HEAD state as long as it is not dangling.
        self._check_dangling_commit(commit)
        self.handle.git.checkout(commit)
        self.handle.git.clean("-fdx")

    # A branch HAS been specified.
    else:
      # Try the specified branch.
      if not self._try_checkout(branch_name, commit, force):
        # Try the default branch.
        if not self._try_checkout(self.default_branch_name, commit, force):
          # Checkout the target commit in a detached HEAD state as long as it is not dangling.
          self._check_dangling_commit(commit)
          self.handle.git.checkout(commit)
          self.handle.git.clean("-fdx")

  def _try_checkout(self, branch_name: str, commit: git.Commit, force: bool) -> bool:
    """
    Attempts to checkout the commit on the specified branch, returns the success of the request.
    """
    # Try the local branch.
    if self._try_checkout_local(branch_name, commit, force):
      return True

    # Tag is not on the specified local branch.
    else:

      self._fetch_once()

      # Try the remote branch
      return self._try_checkout_remote(branch_name, commit, force)

  def _try_checkout_local(self, branch_name: str, commit: git.Commit, force: bool) -> bool:
    """
    Attempts to checkout the commit on the specified LOCAL branch, returns the success of the
    request.
    """

    # Check if target commit is HEAD of local branch.
    if self._does_local_branch_have_commit(branch_name, commit):
      local_branch = self.handle.branches[branch_name]  # type: ignore

      if commit == local_branch.commit:
        local_branch.checkout()
        return True

      # Target commit is in local branch history.
      else:
        # Need to fetch for this part of the logic.
        self._fetch_once()

        # Make sure the local branch is setup to track the expected remote branch.
        local_branch = self.handle.branches[branch_name]  # type: ignore
        tracking_branch = self._verify_local_branch_has_correct_tracking_branch(local_branch)

        # Make sure the local branch is not ahead of tracking branch, since we're moving the
        # local HEAD, information would be lost.
        if not force:
          self._verify_local_commits_not_ahead(local_branch, tracking_branch)

        # Good to go move the local branch HEAD to the target commit.
        print(f"{self.path}: checking out {local_branch.name}:{commit.hexsha}")
        local_branch.checkout()
        self.handle.head.reset(commit=commit, index=True, working_tree=True)
        return True

    else:
      return False

  def _try_checkout_remote(self, branch_name: str, commit: git.Commit, force: bool):
    """
    Attempts to checkout the commit on the specified REMOTE branch, returns the success of the
    request.
    """

    if self._does_remote_branch_have_commit(branch_name, commit):
      # Check if there is a local branch to match the remote branch.
      local_branches = [branch.name for branch in self.handle.branches]  # type: ignore

      if branch_name in local_branches:
        # Make sure the local branch is setup to track the expected remote branch.
        local_branch = self.handle.branches[branch_name]  # type: ignore
        tracking_branch = self._verify_local_branch_has_correct_tracking_branch(local_branch)

        # Make sure the local branch is not ahead of tracking branch, since we're moving the
        # local HEAD, information would be lost.
        if not force:
          self._verify_local_commits_not_ahead(local_branch, tracking_branch)

        # Good to go move the local branch HEAD to the target commit.
        print(f"{self.path}: checking out {local_branch.name}:{commit.hexsha}")
        local_branch.checkout()
        self.handle.head.reset(commit=commit, index=True, working_tree=True)
        return True

      # There is no local branch yet, create it, and reset it to the target commit.
      else:
        self.handle.git.checkout('-b', branch_name, f'origin/{branch_name}')
        self.handle.head.reset(commit=commit, index=True, working_tree=True)
        return True

    else:
      return False

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
      local_branches = [branch for branch in self.handle.branches  # type: ignore[attr-defined]
                        if head_commit.hexsha in
                        [commit.hexsha for commit in branch.commit.iter_parents()]]
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

  def _does_remote_branch_have_commit(self, branch_name: str, commit: git.Commit) -> bool:
    """
    Returns true if there is a remote branch with the specified name, that contains the specified
    commit. Otherwise it returns false.
    """
    try:
      remote_branch = self.handle.refs[f"origin/{branch_name}"]  # type: ignore
    except IndexError:
      # The local branch does not exist, so it cannot contain the commit.
      return False

    if commit == remote_branch.commit:
      return True
    else:
      return commit in remote_branch.commit.iter_parents()

  def verify_tag(self, tag: str) -> git.Commit:
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

  def verify_tag_nothrow(self, tag: str) -> Optional[git.Commit]:
    try:
      commit = self.verify_tag(tag)
      return commit
    except BaseException:
      return None

  def _does_local_branch_have_commit(self, branch_name: str, commit: git.Commit) -> bool:
    """
    Returns true if there exist a local branch with the specified name, that contains the specified
    commit. Otherwise it returns false.
    """
    try:
      local_branch = self.handle.heads[branch_name]
    except IndexError:
      # The local branch does not exist, so it cannot contain the commit.
      return False

    if commit == local_branch.commit:
      return True
    else:
      return commit in local_branch.commit.iter_parents()

  @staticmethod
  def exists(path: str) -> bool:
    try:
      # Initialize the Repo object
      repo = git.Repo(path)
      # Compare the absolute paths to determine if 'path' is the repository root
      return os.path.abspath(str(repo.working_tree_dir)) == os.path.abspath(path)
    except (git.NoSuchPathError, git.InvalidGitRepositoryError):
      # If Repo initialization fails, the path is not a Git repository
      return False

  @staticmethod
  def is_gordion(path: str) -> bool:
    """
    Returns true if the repository at <path> has a gordion.yaml file.
    """
    if gordion.Repository.exists(path):
      yeditor = gordion.YamlEditor(os.path.join(path, 'gordion.yaml'))
      if yeditor.exists():
        return True

    return False

  @staticmethod
  def _url(path: str) -> str:
    repo = git.Repo(path)
    return repo.remotes.origin.url

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
  def safe_move(source, destination):
    # If there is already a different repository at the destination, safe delete it.
    if gordion.Repository.exists(destination):
      gordion.Repository.safe_delete(destination)
    # If there is already something else there, error:
    elif os.path.exists(destination):
      raise gordion.UpdateTargetPathExistsError(destination)

    # Move it
    print(f"Moving repository: {source} -> {destination}")
    shutil.move(source, destination)
    gordion.Repository.unregister(key=source)  # type: ignore[attr-defined]

    return gordion.Repository(destination)

  @staticmethod
  def safe_delete(path, force: bool = False):
    """
    Deletes the repository as long as information will not be lost. Generates an error if the
    repository has unsaved branches/commits or if it has stashes.
    """
    assert gordion.Repository.exists(path)
    repo = gordion.Repository.registry().get(path)  # type: ignore[attr-defined]

    # Check if repository has local changes.
    if repo.handle.is_dirty(untracked_files=True):
      if not force:
        raise gordion.UnsafeRemoveDirty(path)

    # Check if any information would be lost from local branches if we delete this repository.
    for local_branch in repo.handle.branches:  # type: ignore[attr-defined]
      # If there is a tracking branch, ensure the local branch is not ahead of it.
      tracking_branch = local_branch.tracking_branch()
      if tracking_branch:
        merge_base = repo.handle.merge_base(local_branch, tracking_branch)
        commits_ahead = list(repo.handle.iter_commits(
            f'{merge_base[0].hexsha}..{local_branch.commit.hexsha}'))

        if commits_ahead:
          raise gordion.UnsafeRemoveLocalBranchAhead(path, local_branch.name,
                                                     tracking_branch.name, len(commits_ahead))

      # There is no tracking branch, so error.
      else:
        raise gordion.UnsafeRemoveLocalBranchNoTrackingBranch(path, local_branch.name)

    # Error if the repository has stashes that will be lost by the deletion.
    stashes = repo.handle.git.stash('list')
    if stashes:
      raise gordion.UnsafeRemoveStashes(path, stashes)

    # If we reach here, it's safe to delete the repository
    print(f"Deleting repository: {path}")
    shutil.rmtree(path)
    gordion.Repository.unregister(path)  # type: ignore[attr-defined]
    gordion.Workspace().delete_empty_parent_folders(path)

  def try_resolve_tag(self, tag: str) -> str:
    resolved_tag = ""
    commit = self.verify_tag_nothrow(tag)
    if commit:
      resolved_tag = commit.hexsha
    else:
      resolved_tag = tag + " (BAD TAG)"
    return resolved_tag

  def get_branch_name(self):
    if self.handle.head.is_detached:
      return "DETACHED HEAD"
    else:
      return self.handle.active_branch.name

  def get_branch_name_or_throw(self):
    branch_name = self.get_branch_name()
    if branch_name == "DETACHED HEAD":
      raise Exception(f"{self.name} is DETACHED HEAD")
    return branch_name

  # =================================================================================================
  # Git Command Analogs

  def is_branch(self, branch_name: str) -> bool:
    return bool(self.handle.active_branch) and self.handle.active_branch.name == branch_name

  def is_dirty(self) -> bool:
    return self.handle.is_dirty(untracked_files=True)

  def has_staged_changes(self) -> bool:
    return self.handle.is_dirty(index=True, working_tree=False, untracked_files=False)

  def add(self, pathspec: str):
    """
    Does 'git add'
    """
    if self.handle.is_dirty(untracked_files=True):
      # Use custom environment to ensure clean output
      with self.handle.git.custom_environment(GIT_TERMINAL_PROMPT="0"):
        self.handle.git.add(pathspec)

  def restore(self, pathspec: str, staged: bool):
    """
    Does 'git restore'
    """
    args = [pathspec]
    if staged:
      args.append("--staged")

    if self.handle.is_dirty(untracked_files=True):
      output = self.handle.git.restore(args)
      if output:
        print(output)

  def commit(self, message: str, amend: bool = False):
    """
    Does 'git commit'
    """
    # Use custom environment to ensure clean output
    with self.handle.git.custom_environment(GIT_TERMINAL_PROMPT="0"):
      if amend:
        self.handle.git.commit("-m", message, "--amend")
      else:
        self.handle.git.commit("-m", message)

  def clean(self, force: bool, dirs: bool, extra: bool):
    """
    Does 'git clean'
    """
    args = ""
    if force:
      args += "f"

    if dirs:
      args += "d"

    if extra:
      args += "x"

    if args:
      args = "-" + args

    output = self.handle.git.clean(args)
    if output:
      print(f"{self.name}: {output}")

  def push(self, set_upstream: bool, delete: bool, remote: Optional[str], branch: str, force: bool):
    """
    Does 'git push'
    """
    # Print progress message
    print(f"Pushing {self.name}...")

    args = []
    if set_upstream:
      args.append('--set-upstream')
      if remote is not None:
        args.append(remote)
      args.append(branch)
    if delete:
      args.append('--delete')
      if remote is not None:
        args.append(remote)
      args.append(branch)

    if force:
      args.append('--force')

    # Use custom environment to ensure clean output
    with self.handle.git.custom_environment(GIT_TERMINAL_PROMPT="0"):
      output = self.handle.git.push(args)
      if output:
        print(output)
