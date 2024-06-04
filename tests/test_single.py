import os
import gordion
import pytest
from git import Repo, BadName

assert 'TOXTEMPDIR' in os.environ, "you must run these tests using tox"

REPOS_DIR = os.path.join(os.environ['TOXTEMPDIR'], 'repos')
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


def test_exists():
  # A file inside a repository is not an existing repository
  path = os.path.join(SCRIPT_DIR)
  assert not gordion.Repository._exists(path)

  # Verify this repository root is a git repository path.
  path = os.path.join(SCRIPT_DIR, '..')
  assert gordion.Repository._exists(path)


@pytest.fixture(scope="session")
def repoA_session():
  """
  Creates the repoA object only once for the lifetime of this session. This is important so the
  "fetch_once" doesn't fetch every test case, which saves time.
  """
  path = os.path.join(REPOS_DIR, 'gordion_demo_a')
  url = 'https://github.com/jacob-heathorn/gordion_demo_a.git'

  # Create the repo object, this will clone if necessary
  repo = gordion.Repository(path, url)

  yield repo


@pytest.fixture
def repoA(repoA_session):
  """
  This puts the repoA object back into a well-known state for each test case.
  """

  # Delete all local branches except develop (can't be deleted) to start fresh.
  repoA_session.handle.branches['develop'].checkout()
  branches = list(repoA_session.handle.branches)
  for branch in branches:
    if branch.name != 'develop':
      repoA_session.handle.delete_head(branch, force=True)

  # Set the object to a known commit on the test_single branch.
  tag = '26968db5866b41339b9811c809818f44055c8153'
  branch_name = 'test_single'

  # Set the target branch/commit
  repoA_session.update(tag, branch_name)
  assert repoA_session.handle.head.commit.hexsha == tag
  assert repoA_session.handle.active_branch.name == branch_name

  yield repoA_session


def test_verify_tag(repoA):
  # Verify HEAD of active branch exists.
  repoA._verify_tag(repoA.handle.head.commit.hexsha)

  # Verify older commit of active branch exists.
  repoA._verify_tag(repoA.handle.head.commit.parents[0].hexsha)

  # Verify a tag that only exists on a different remote branch (test_single_1) in fact exists.
  repoA._verify_tag('f30a7cbe5592ef4521dad06203d5178e651ecd5b')

  # Verify that an ill-formed commit will raise an error.
  with pytest.raises(BadName):
    repoA._verify_tag("123")


def test_does_local_branch_have_commit(repoA):
  """
  Verifies the behavior of _does_local_branch_have_commit()
  """

  # Verify HEAD of active branch returns true
  assert repoA.handle.active_branch.name == 'test_single'
  head_commit = repoA.handle.active_branch.commit
  assert gordion.Repository._does_local_branch_have_commit(
      repoA.handle, 'test_single', head_commit)

  # Verify older commit of active branch returns true
  older_commit = head_commit.parents[0]
  assert gordion.Repository._does_local_branch_have_commit(
      repoA.handle, 'test_single', older_commit)

  # Verify remote branch (test_single_1) that is not local returns false.
  assert not gordion.Repository._does_local_branch_have_commit(
      repoA.handle, 'test_single_1', head_commit)

  # Now checkout "test_single_1" so it exists locally, then switch back to "test_single". The same
  # check should return true.
  repoA.handle.git.checkout('-b', 'test_single_1', 'origin/test_single_1')
  repoA.handle.branches['test_single'].checkout()
  assert gordion.Repository._does_local_branch_have_commit(
      repoA.handle, 'test_single_1', head_commit)

  # Verfiy commit on remote but not on local returns false.
  future_commit = repoA._verify_tag('a415fa52649601f17fccf6d17616281213b117b8')
  assert not gordion.Repository._does_local_branch_have_commit(
      repoA.handle, 'test_single', future_commit)


def test_update_active_branch_commits_ahead(repoA):
  """
  Verifies that updating the active branch will ERROR if it is ahead of the remote.
  """
  baseline_commit = repoA.handle.head.commit.hexsha

  # Create newer commit on the active 'test_single' branch.
  repoA.handle.index.commit("Empty commit for testing")

  # Verify update error. User needs to save the commits, or force the update.
  with pytest.raises(gordion.UpdateLocalBranchAheadError) as context:
    repoA.update(baseline_commit, "test_single")
  expected = gordion.UpdateLocalBranchAheadError(repoA.path, 'test_single', 'origin/test_single', 1)
  assert str(context.value) == str(expected)


def test_update_nonactive_local_branch_commits_ahead(repoA):
  """
  Verifies that updating a non-active local branch will ERROR if it is ahead of the remote.
  """
  # Add a commit to "test_single_1"
  repoA.handle.git.checkout('-b', 'test_single_1', 'origin/test_single_1')
  repoA.handle.index.commit("Empty commit for testing")
  repoA.handle.branches['test_single'].checkout()

  # Verify update error. User needs to save the commits, or force the update.
  with pytest.raises(gordion.UpdateLocalBranchAheadError) as context:
    repoA.update(repoA.handle.head.commit.hexsha, "test_single_1")
  expected = gordion.UpdateLocalBranchAheadError(
      repoA.path, 'test_single_1', 'origin/test_single_1', 1)
  assert str(context.value) == str(expected)


def test_update_local_branch_no_remote(repoA):
  """
  Verifies that updating a local branch will ERROR if it does not have a remote tracking branch.
  """

  # Create a new local branch, with no remote, and checkout develop again."
  repoA.handle.git.checkout('-b', 'test_branch_no_remote')
  repoA.handle.branches['test_single'].checkout()

  # Point the update to test_branch_no_remote:HEAD~1. Verify update error. User needs to create a
  # tracking branch.
  branch_name = 'test_branch_no_remote'
  tag = repoA.handle.branches['test_branch_no_remote'].commit.parents[0].hexsha

  # Verify update error. User needs to create a tracking branch.
  with pytest.raises(gordion.UpdateNoTrackingBranchError) as context:
    repoA.update(tag, branch_name)
  expected = gordion.UpdateNoTrackingBranchError(repoA.path, 'test_branch_no_remote')
  assert str(context.value) == str(expected)


def test_does_remote_branch_have_commit(repoA):
  """
  Verifies behavior of _does_remote_branch_have_commit()
  """

  # Verify a commit is on remote branch but not local.
  commit = repoA._verify_tag('a415fa52649601f17fccf6d17616281213b117b8')
  assert not gordion.Repository._does_local_branch_have_commit(repoA.handle, 'test_single', commit)
  assert gordion.Repository._does_remote_branch_have_commit(repoA.handle, 'test_single', commit)

  # If remote branch does not exist, it just returns false.
  assert not gordion.Repository._does_remote_branch_have_commit(repoA.handle, 'noname', commit)

  # Verifies a commit on local but not remote.
  repoA.handle.index.commit("Empty commit test_does_remote_branch_have_commit()")
  commit = repoA.handle.active_branch.commit
  assert gordion.Repository._does_local_branch_have_commit(repoA.handle, 'test_single', commit)
  assert not gordion.Repository._does_remote_branch_have_commit(repoA.handle, 'test_single', commit)


def test_update_remote_branch_only(repoA):
  """
  Verifies that update will create a new local branch to track the remote branch if it does not
  exist yet AND the remote branch has the target commit.
  """
  baseline_commit = repoA.handle.head.commit.hexsha
  repoA.update(baseline_commit, "test_single_1")
  assert repoA.handle.head.reference.name == "test_single_1"
  assert repoA.handle.head.commit.hexsha == baseline_commit


def test_update_local_fastforward(repoA):
  """
  If there is a local branch, but it does not contain the commit, but the remote branch does
  contain the commit, update will fastforward.
  """

  # Choose a tag ahead of our baseline commit.
  repoA.update('a415fa52649601f17fccf6d17616281213b117b8', "test_single")


def test_local_branch_wrong_tracking_branch(repoA):
  """
  If there is a local branch that matches the remote branch by name, but it has the wrong tracking
  branch, error.
  """
  baseline_commit = repoA.handle.head.commit.hexsha

  # Checkout "test_single_1" locally but link it to the wrong remote branch.
  repoA.handle.git.checkout('-b', 'test_single_1', 'origin/test_single')
  with pytest.raises(gordion.UpdateWrongTrackingBranchError) as context:
    repoA.update(baseline_commit, "test_single_1")
  expected = gordion.UpdateWrongTrackingBranchError(repoA.path, 'test_single_1', 'origin/develop')
  assert str(context.value) == str(expected)


def test_branch_does_not_have_commit_but_commit_exists(repoA):
  """
  Verifies that update will checkout a commit in a detached head state if it exists,
  but it cannot find it on the specified branch.
  """

  # Choose a tag that exists on 'test_single_1' but not on test_single.
  tag = 'f30a7cbe5592ef4521dad06203d5178e651ecd5b'
  repoA.update(tag, "test_single")
  assert repoA.handle.head.is_detached
  assert repoA.handle.head.commit.hexsha == tag


def test_detached_head_unsaved_commit(repoA):
  """
  Verifies update will ERROR if we are in a detached head state, and the HEAD commit does not 
  exist on a branch somewhere.
  """
  # Go to detached HEAD state.
  baseline_commit = repoA.handle.head.commit.hexsha
  repoA.handle.git.checkout(baseline_commit)
  assert repoA.handle.head.is_detached

  # Now add a commit.
  repoA.handle.index.commit("Commit while in detached HEAD state.")

  # Now verify that update errors.
  with pytest.raises(gordion.UpdateDetachedHeadNotSavedError) as context:
    repoA.update(baseline_commit, "test_single")
  expected = gordion.UpdateDetachedHeadNotSavedError(repoA.path)
  assert str(context.value) == str(expected)


def test_dont_specify_branch(repoA):
  """
  Verifies that if you don't specify the branch, it will checkout the commit in detached head
  state.
  """
  baseline_commit = repoA.handle.head.commit.hexsha
  repoA.update(baseline_commit, None)
  assert repoA.handle.head.is_detached
  assert repoA.handle.head.commit.hexsha == baseline_commit


def test_update_dirty_repo(repoA):
  """
  Verifies update will error if the repository is dirty and the HEAD is about to move.
  """

  # Make an arbitrary change.
  file_path = os.path.join(repoA.path, 'README.md')
  with open(file_path, 'w') as file:
    file.write('test_uncommitted_edits wrote this.\n')

  # Attempt to move the HEAD and verify error.
  tag = repoA.handle.head.commit.parents[0].hexsha
  with pytest.raises(gordion.UpdateRepoIsDirtyError) as context:
    repoA.update(tag, "test_single")
  expected = gordion.UpdateRepoIsDirtyError(repoA.path)
  assert str(context.value) == str(expected)

  # If you don't move the HEAD, but change the branch while it's dirty, it's OK actually.
  tag = repoA.handle.head.commit.hexsha
  repoA.update(tag, "test_single")
