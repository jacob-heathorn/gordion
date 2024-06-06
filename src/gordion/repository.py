import os
import subprocess
from git import Repo, NoSuchPathError, InvalidGitRepositoryError
import gordion


class Repository:
  """
  Encapsulates a git repository in the gordion context.

  """

  def __init__(self, path: str, parent=None) -> None:
    self.path = path
    self.url = ''
    self.fetched = False
    self.parent: Repository = parent
    # TODO: ability to  grab this from the parent with a dictionary?
    self.parent_listing: str = ''
    self.children: list[Repository] = []
    self.yeditor = gordion.YamlEditor(os.path.join(self.path, 'gordion.yaml'))

    if Repository._exists(self.path):
      self.ensure()

  def ensure(self, url: str = ''):
    """
    Clones the repository if necessary and creates the underlying git repository handle.
    """

    # Derive url if necessary.
    if not url:
      assert Repository._exists(self.path)
      self.handle = Repo(self.path)
      self.url = self.handle.remotes.origin.url
    else:
      self.url = url
      if Repository._exists(self.path):
        assert self.url == self.handle.remotes.origin.url

    # Check for a duplicates repository cloned at different paths.
    self._check_duplicate_repo_path(self._root())

    # Clone if necessary.
    if not Repository._exists(self.path):
      cache = gordion.Cache()
      mirror_path = cache.ensure_mirror(self.url)

      args = ['git', 'clone', '--reference', mirror_path, self.url, self.path]
      subprocess.check_call(args, stderr=subprocess.STDOUT)

    # Reload objects.
    self.handle = Repo(self.path)
    self.yeditor.reload()

  def _relpath(self) -> str:
    return os.path.relpath(self.path, os.path.dirname(self._root().path))

  def update(self, tag: str, branch_name: str) -> None:
    """
    Updates the repository to the specified commit and optional branch, as long as information will
    not be lost in the process, otherwise it will raise descriptive errors about what to do next.

    """

    commit = self._verify_tag(tag)

    # Verify that we don't have an unsaved HEAD that would be lost by the update.
    if self.handle.head.is_detached:
      self._verify_head_wont_be_lost(commit)

    # Verify we don't have uncommitted chages that could be lost by the update.
    if self.handle.is_dirty(untracked_files=True):
      if commit.hexsha != self.handle.head.commit.hexsha:
        raise gordion.UpdateRepoIsDirtyError(self.path)

        # Check if a branch HAS NOT been specified.
    if not branch_name:
      # Checkout the target commit in a detached HEAD state
      self.handle.git.checkout(commit)

    # A branch HAS been specified
    else:
      # Check if a local branch by the target name has the target commit.
      if Repository._does_local_branch_have_commit(self.handle, branch_name, commit):
        local_branch = self.handle.branches[branch_name]
        # Check if target commit is HEAD of local branch.
        if commit.hexsha == local_branch.commit.hexsha:
          local_branch.checkout()

        # Target commit is in local branch history.
        else:
          # Need to fetch for this part of the logic.
          self.fetch_once()

          # Make sure the local branch is setup to track the expected remote branch.
          local_branch = self.handle.branches[branch_name]
          tracking_branch = Repository._verify_local_branch_has_correct_tracking_branch(
              self.handle, local_branch)

          # Make sure the local branch is not ahead of tracking branch, since we're moving the
          # local HEAD, information would be lost.
          Repository._verify_local_commits_not_ahead(self.handle, local_branch, tracking_branch)

          # Good to go move the local branch HEAD to the target commit.
          local_branch.checkout()
          self.handle.head.reset(commit=commit, index=True, working_tree=True)

      # Tag is not on a local branch
      else:
        self.fetch_once()

        # Check if a remote branch by the target name has the target commit.
        if Repository._does_remote_branch_have_commit(self.handle, branch_name, commit):

          # Check if there is a local branch to match the remote branch.
          local_branches = [branch.name for branch in self.handle.branches]

          if branch_name in local_branches:
            # Make sure the local branch is setup to track the expected remote branch.
            local_branch = self.handle.branches[branch_name]
            tracking_branch = Repository._verify_local_branch_has_correct_tracking_branch(
                self.handle, local_branch)

            # Make sure the local branch is not ahead of tracking branch, since we're moving the
            # local HEAD, information would be lost.
            Repository._verify_local_commits_not_ahead(self.handle, local_branch, tracking_branch)

            # Good to go move the local branch HEAD to the target commit.
            local_branch.checkout()
            self.handle.head.reset(commit=commit, index=True, working_tree=True)

          # There is no local branch yet, create it, and reset it to the target commit.
          else:
            self.handle.git.checkout('-b', branch_name, f'origin/{branch_name}')
            self.handle.head.reset(commit=commit, index=True, working_tree=True)

        # We could not find the commit on a local or remote branch by the designated name, so just
        # checkout the commit in a detached head state.
        else:
          self.handle.git.checkout(commit)

    self.yeditor.reload()
    self._update_children(branch_name)

  def _check_duplicate_repo_path(self, other):
    host, username, repo_name = gordion.extract_repo_details(self.url)
    other_host, other_username, other_repo_name = gordion.extract_repo_details(other.url)

    # Check if the remote repository is the same
    if host == other_host and username == other_username and repo_name == other_repo_name:
      # Make sure the repository has the same local path.
      if self.path != other.path:
        raise gordion.UpdateDuplicateRepoPathError(self.path, other)

      # # Make sure the repository has the same tag.
      # if tag != other.handle.head.commit.hexsha:
      #   raise gordion.UpdateDuplicateRepoTagError(self.path, self.parent_listing, other)

    # Check against the other's children
    for other_child in other.children:
      Repository._check_duplicate_repo_path(self, other_child)

  def _root(self):
    """
    Recursively returns the root reposoitory object.
    """
    if self.parent:
      return self.parent._root()
    else:
      return self

  def _update_children(self, branch_name: str):
    root = self._root()
    self.children = []

    # Open the gordion yaml file for this repository if it exists.
    if self.yeditor.exists():
      for child_name, child_info in self.yeditor.yaml_data['repositories'].items():
        # Create child repository objects
        # TODO: non-default child path/name

        child_path = os.path.join(root.path, 'gordion', child_name)
        child_tag = child_info['tag']
        child_url = child_info['url']
        listing_file = os.path.join(self._relpath(), 'gordion.yaml')
        yaml_listing = f"{listing_file} : {child_name} : {child_tag}"
        child = Repository(child_path, self)
        child.parent_listing = yaml_listing
        child.ensure(child_url)
        child.update(child_tag, branch_name)
        self.children.append(child)

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
        self.fetch_once()
        remote_branches = [branch for branch in self.handle.remotes.origin.refs if
                           head_commit.hexsha in [commit.hexsha for commit in
                                                  branch.commit.iter_parents()]]
        if not remote_branches:
          raise gordion.UpdateDetachedHeadNotSavedError(self.path)

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
