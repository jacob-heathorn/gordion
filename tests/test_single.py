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

  # Create the repo object, this will clone.
  repo = gordion.Repository(path, url, 'TODO', 'TODO')

  yield repo


@pytest.fixture
def repoA(repoA_session):
  """
  This puts the repoA object back into a well-known state for each test case.
  """
  # Set the object to a known commit on the test-single branch.
  repoA_session.target_tag = '26968db5866b41339b9811c809818f44055c8153'
  repoA_session.target_branch_name = 'test_single'

  # Delete all local branches except develop (can't be deleted) to start fresh.
  repoA_session.handle.branches['develop'].checkout()
  branches = list(repoA_session.handle.branches)
  for branch in branches:
    if branch.name != 'develop':
      repoA_session.handle.delete_head(branch, force=True)

  # Set the target branch/commit
  repoA_session.update()
  assert repoA_session.handle.active_branch.name == repoA_session.target_branch_name
  assert repoA_session.handle.head.commit.hexsha == repoA_session.target_tag

  yield repoA_session


def test_verify_tag(repoA):
  # Verify HEAD of active branch exists.
  repoA._verify_tag('26968db5866b41339b9811c809818f44055c8153')

  # Verify older commit of active branch exists.
  repoA._verify_tag('c9da3e67006cbb03b6810d2e5b8effebb0f0b674')

  # Verify a tag that only exists on a different remote branch (test_single_1) in fact exists.
  repoA._verify_tag('48b124f02016d2c2f0858351ba1aed11c8c47341')

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
  future_commit = repoA._verify_tag('9451fe5a88374fae8ccebc92b6dccd52f50c2257')
  assert not gordion.Repository._does_local_branch_have_commit(
      repoA.handle, 'test_single', future_commit)


def test_update_active_branch_commits_ahead(repoA):
  """
  Verifies that updating the active branch will ERROR if it is ahead of the remote.
  """
  # Create newer commit on the active 'test_single' branch.
  repoA.handle.index.commit("Empty commit for testing")

  # Verify update error. User needs to save the commits, or force the update.
  with pytest.raises(gordion.UpdateLocalBranchAheadError) as context:
    repoA.update()
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

  # Set the target branch name before update.
  repoA.target_branch_name = "test_single_1"

  # Verify update error. User needs to save the commits, or force the update.
  with pytest.raises(gordion.UpdateLocalBranchAheadError) as context:
    repoA.update()
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

  # Point the update to test_branch_no_remote:HEAD~1
  repoA.target_branch_name = 'test_branch_no_remote'
  repoA.target_tag = repoA.handle.branches['test_branch_no_remote'].commit.parents[0].hexsha

  # Verify update error. User needs to create a tracking branch.
  with pytest.raises(gordion.UpdateNoTrackingBranchError) as context:
    repoA.update()
  expected = gordion.UpdateNoTrackingBranchError(repoA.path, 'test_branch_no_remote')
  assert str(context.value) == str(expected)


def test_does_remote_branch_have_commit(repoA):
  """
  Verifies behavior of _does_remote_branch_have_commit()
  """

  # Verify a commit is on remote branch but not local.
  commit = repoA._verify_tag('9451fe5a88374fae8ccebc92b6dccd52f50c2257')
  assert not gordion.Repository._does_local_branch_have_commit(repoA.handle, 'test_single', commit)
  assert gordion.Repository._does_remote_branch_have_commit(repoA.handle, 'test_single', commit)

  # If remote branch does not exist, it just returns false.
  assert not gordion.Repository._does_remote_branch_have_commit(repoA.handle, 'noname', commit)

  # Verifies a commit on local but not remote.
  repoA.handle.index.commit("Empty commit test_does_remote_branch_have_commit()")
  commit = repoA.handle.active_branch.commit
  assert gordion.Repository._does_local_branch_have_commit(repoA.handle, 'test_single', commit)
  assert not gordion.Repository._does_remote_branch_have_commit(repoA.handle, 'test_single', commit)


# def test_update_remote_branch_only(repoA):
#   """
#   Verifies that update will create a new local branch to track the remote branch if it does not
#   exist yet and remote branch has the target commit.
#   """
#   repoA.target_branch_name = "testbranch1"
#   repoA.update()
#   assert repoA.handle.head.reference.name == "testbranch1"
#   assert repoA.handle.head.commit.hexsha == repoA.target_tag


# def test_update_local_fastforward(repoA):
#   """
#   If there is a local branch, but it does not contain the commit, but the remote branch does contain
#   the commit, update will fastforward.
#   """

#   # Choose a tag 2 commits ahead of our baseline test commit on develop.
#   repoA.target_tag = '65bf30cb0303e7c90f832fcedba83d7dd91dccab'
#   repoA.update()


# def test_local_branch_wrong_tracking_branch(repoA):
#   """
#   If there is a local branch that matches the remote branch by name, but it has the wrong tracking
#   branch, error.
#   """

#   # Checkout testbranch1 locally but link it to the wrong remote branch.
#   repoA.handle.git.checkout('-b', 'testbranch1', 'origin/develop')
#   repoA.target_branch_name = 'testbranch1'
#   repoA.target_tag = '4a96229f1c4eb7c5c8f4d630513cca5919abcd7a'
#   with pytest.raises(gordion.UpdateWrongTrackingBranchError) as context:
#     repoA.update()
#   expected = gordion.UpdateWrongTrackingBranchError(repoA.path, 'testbranch1', 'origin/develop')
#   assert str(context.value) == str(expected)


# def test_branch_does_not_have_commit_but_commit_exists(repoA):
#   """
#   Verifies that update will checkout a commit in a detached head state if it exists,
#   but it cannot find it on the specified branch.
#   """

#   # Choose a tag that exists on 'testbranch1' but not on develop.
#   repoA.target_tag = '4a96229f1c4eb7c5c8f4d630513cca5919abcd7a'
#   repoA.update()
#   assert repoA.handle.head.is_detached
#   assert repoA.handle.head.commit.hexsha == repoA.target_tag


# def test_detached_head_unsaved_commit(repoA):
#   """
#   Verifies update will ERROR if we are in a detached head state, and the HEAD commit does not exist
#   on a branch somewhere.
#   """
#   # Go to detached HEAD state.
#   repoA.target_tag = '4a96229f1c4eb7c5c8f4d630513cca5919abcd7a'
#   repoA.update()
#   assert repoA.handle.head.is_detached

#   # Now add a commit.
#   repoA.handle.index.commit("Commit while in detached HEAD state.")

#   # Now verify that update errors.
#   with pytest.raises(gordion.UpdateDetachedHeadNotSavedError) as context:
#     repoA.update()
#   expected = gordion.UpdateDetachedHeadNotSavedError(repoA.path)
#   assert str(context.value) == str(expected)


# def test_dont_specify_branch(repoA):
#   """
#   Verifies that if you don't specify the branch, it will checkout the commit in detached head state.
#   """
#   repoA.target_branch_name = []
#   repoA.update()
#   assert repoA.handle.head.is_detached
#   assert repoA.handle.head.commit.hexsha == repoA.target_tag


# def test_update_dirty_repo(repoA):
#   """
#   Verifieds update will error if the repository is dirty and the HEAD is about to move.
#   """

#   # Make an arbitrary change.
#   file_path = os.path.join(repoA.path, 'README.md')
#   with open(file_path, 'w') as file:
#     file.write('test_uncommitted_edits wrote this.\n')

#   # Attempt to move the HEAD and verify error.
#   repoA.target_tag = '55553d4a26bde22bec5817c17f803e9569cbb970'
#   with pytest.raises(gordion.UpdateRepoIsDirtyError) as context:
#     repoA.update()
#   expected = gordion.UpdateRepoIsDirtyError(repoA.path)
#   assert str(context.value) == str(expected)

#   # If you don't move the HEAD, but change the branch while it's dirty, it's OK actually.
#   repoA.target_tag = '163f847f32fba7307dd94366560d7d55ffe3c144'
#   repoA.target_branch_name = 'testbranch1'
#   repoA.update()
