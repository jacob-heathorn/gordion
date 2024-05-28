import os
# from gordion.repository import Repository
import subprocess
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
  path = os.path.join(REPOS_DIR, 'west_demo_a')
  url = 'https://github.com/jacob-heathorn/west_demo_a.git'

  # Create the repo object, this will clone.
  repo = gordion.Repository(path, url, 'TODO', 'TODO')

  yield repo


@pytest.fixture
def repoA(repoA_session):
  """
  This puts the repoA object back into a well-known state for each test case.
  """
  # Set the object to a known commit on the develop branch.
  repoA_session.target_tag = '163f847f32fba7307dd94366560d7d55ffe3c144'
  repoA_session.target_branch_name = 'develop'

  # Use the underlying Repo handle object to reset the commit
  develop = repoA_session.handle.heads['develop']
  develop.checkout()
  target_commit = repoA_session.handle.commit(repoA_session.target_tag)
  repoA_session.handle.head.reset(commit=target_commit, index=True, working_tree=True)

  # Delete all local branches except develop
  branches = list(repoA_session.handle.branches)
  for branch in branches:
    if branch.name != 'develop':
      repoA_session.handle.delete_head(branch, force=True)

  yield repoA_session


def test_verify_tag(repoA):
  # Verify HEAD of active branch exists.
  repoA._verify_tag('163f847f32fba7307dd94366560d7d55ffe3c144')

  # Verify older commit of active branch exists.
  repoA._verify_tag('1c518ee74d9c619321fea12e90c7a721dfddb0ee')

  # Verify a tag that only exists on a different remote branch (testbranch1) in fact exists.
  repoA._verify_tag('4a96229f1c4eb7c5c8f4d630513cca5919abcd7a')

  # Verify that an ill-formed commit will raise an error.
  with pytest.raises(BadName):
    repoA._verify_tag("123")


def test_does_local_branch_have_commit(repoA):
  # Verify HEAD of active branch returns true.
  commit = repoA._verify_tag('163f847f32fba7307dd94366560d7d55ffe3c144')
  assert gordion.Repository._does_local_branch_have_commit(repoA.handle, 'develop', commit)

  # Verify older commit of active branch returns true
  commit = repoA._verify_tag('1c518ee74d9c619321fea12e90c7a721dfddb0ee')
  assert gordion.Repository._does_local_branch_have_commit(repoA.handle, 'develop', commit)

  # Verify remote branch (testbranch1) that is not local returns false.
  assert not gordion.Repository._does_local_branch_have_commit(repoA.handle, 'testbranch1', commit)

  # Now checkout testbranch1 so it exists locally, then switch back to develop. The same function
  # should return true.
  repoA.handle.git.checkout('-b', 'testbranch1', 'origin/testbranch1')
  repoA.handle.branches['develop'].checkout()
  assert gordion.Repository._does_local_branch_have_commit(repoA.handle, 'testbranch1', commit)

  # Verfiy commit on remote but not on local returns false.
  commit = repoA._verify_tag('15289e899626fdb9aa187ab4b5888facf86e3ed8')
  assert not gordion.Repository._does_local_branch_have_commit(repoA.handle, 'develop', commit)

  # For sanity, pull develop, same function should return true now.
  repoA.handle.remotes.origin.pull('develop')
  assert gordion.Repository._does_local_branch_have_commit(repoA.handle, 'develop', commit)


def test_update_active_branch_commits_ahead(repoA):
  """
  Verifies that updating the active branch will ERROR if it is ahead of the remote.
  """
  # Create newer commit on the active develop branch.
  repoA.handle.index.commit("Empty commit for testing")

  # Verify update error. User needs to save the commits, or force the update.
  with pytest.raises(gordion.UpdateLocalBranchAheadError) as context:
    repoA.update()
  expected = gordion.UpdateLocalBranchAheadError(repoA.path, 'develop', 'origin/develop', 1)
  assert str(context.value) == str(expected)


def test_update_nonactive_local_branch_commits_ahead(repoA):
  """
  Verifies that updating a non-active local branch will ERROR if it is ahead of the remote.
  """

  # Add a commit to "testbranch1"
  repoA.handle.git.checkout('-b', 'testbranch1', 'origin/testbranch1')
  repoA.handle.index.commit("Empty commit for testing")
  repoA.handle.branches['develop'].checkout()

  # Set the target branch name before update.
  repoA.target_branch_name = "testbranch1"

  # Verify update error. User needs to save the commits, or force the update.
  with pytest.raises(gordion.UpdateLocalBranchAheadError) as context:
    repoA.update()
  expected = gordion.UpdateLocalBranchAheadError(
      repoA.path, 'testbranch1', 'origin/testbranch1', 1)
  assert str(context.value) == str(expected)


def test_update_local_branch_no_remote(repoA):
  """
  Verifies that updating a local branch will ERROR if it does not have a remote tracking branch.
  """

  # Create a new local branch, with no remote, and checkout develop again."
  repoA.handle.git.checkout('-b', 'testbranch2')
  repoA.handle.branches['develop'].checkout()

  # Prepare update to point to testbranch2:HEAD~1
  repoA.target_branch_name = 'testbranch2'
  repoA.target_tag = repoA.handle.branches['testbranch2'].commit.parents[0].hexsha

  # Verify update error. User needs to create a tracking branch.
  with pytest.raises(gordion.UpdateNoTrackingBranchError) as context:
    repoA.update()
  expected = gordion.UpdateNoTrackingBranchError(repoA.path, 'testbranch2')
  assert str(context.value) == str(expected)


def test_does_remote_branch_have_commit(repoA):
  """
  Verifies behavior of _does_remote_branch_have_commit()
  """

  # Verify a commit is on remote branch but not local.
  commit = repoA._verify_tag('65bf30cb0303e7c90f832fcedba83d7dd91dccab')
  assert not gordion.Repository._does_local_branch_have_commit(repoA.handle, 'develop', commit)
  assert gordion.Repository._does_remote_branch_have_commit(repoA.handle, 'develop', commit)

  # Verifies a commit on local but not remote.
  repoA.handle.index.commit("Empty commit test_does_remote_branch_have_commit()")
  commit = repoA.handle.active_branch.commit
  assert gordion.Repository._does_local_branch_have_commit(repoA.handle, 'develop', commit)
  assert not gordion.Repository._does_remote_branch_have_commit(repoA.handle, 'develop', commit)

  # If remote branch does not exist, it just returns false.
  assert not gordion.Repository._does_remote_branch_have_commit(repoA.handle, 'noname', commit)


def test_update_remote_branch_only(repoA):
  """
  Verifies that update will create a new local branch to track the remote branch if it does not
  exist yet and remote branch has the target commit.
  """
  repoA.target_branch_name = "testbranch1"
  repoA.update()
  assert repoA.handle.head.reference.name == "testbranch1"
  assert repoA.handle.head.commit.hexsha == repoA.target_tag


def test_update_local_fastforward(repoA):
  """
  If there is a local branch, but it does not contain the commit, but the remote branch does contain
  the commit, update will fastforward.
  """

  # Choose a tag 2 commits ahead of our baseline test commit on develop.
  repoA.target_tag = '65bf30cb0303e7c90f832fcedba83d7dd91dccab'
  repoA.update()


def test_local_branch_wrong_tracking_branch(repoA):
  """
  If there is a local branch that matches the remote branch by name, but it has the wrong tracking
  branch, error.
  """

  # Checkout testbranch1 locally but link it to the wrong remote branch.
  repoA.handle.git.checkout('-b', 'testbranch1', 'origin/develop')
  repoA.target_branch_name = 'testbranch1'
  repoA.target_tag = '4a96229f1c4eb7c5c8f4d630513cca5919abcd7a'
  with pytest.raises(gordion.UpdateWrongTrackingBranchError) as context:
    repoA.update()
  expected = gordion.UpdateWrongTrackingBranchError(repoA.path, 'testbranch1', 'origin/develop')
  assert str(context.value) == str(expected)


def test_branch_does_not_have_commit_but_commit_exists(repoA):
  """
  Verifies that update will checkout a commit in a detached head state if it exists,
  but it cannot find it on the specified branch.
  """

  # Choose a tag that exists on 'testbranch1' but not on develop.
  repoA.target_tag = '4a96229f1c4eb7c5c8f4d630513cca5919abcd7a'
  repoA.update()
  assert repoA.handle.head.is_detached
  assert repoA.handle.head.commit.hexsha == repoA.target_tag


def test_detached_head_unsaved_commit(repoA):
  """
  Verifies update will ERROR if we are in a detached head state, and the HEAD commit does not exist
  on a branch somewhere.
  """
  # Go to detached HEAD state.
  repoA.target_tag = '4a96229f1c4eb7c5c8f4d630513cca5919abcd7a'
  repoA.update()
  assert repoA.handle.head.is_detached

  # Now add a commit.
  repoA.handle.index.commit("Commit while in detached HEAD state.")

  # Now verify that update errors.
  with pytest.raises(gordion.UpdateDetachedHeadNotSavedError) as context:
    repoA.update()
  expected = gordion.UpdateDetachedHeadNotSavedError(repoA.path)
  assert str(context.value) == str(expected)


def test_dont_specify_branch(repoA):
  """
  Verifies that if you don't specify the branch, it will checkout the commit in detached head state.
  """
  repoA.target_branch_name = []
  repoA.update()
  assert repoA.handle.head.is_detached
  assert repoA.handle.head.commit.hexsha == repoA.target_tag


def test_update_dirty_repo(repoA):
  """
  Verifieds update will error if the repository is dirty and the HEAD is about to move.
  """

  # Make an arbitrary change.
  file_path = os.path.join(repoA.path, 'README.md')
  with open(file_path, 'w') as file:
    file.write('test_uncommitted_edits wrote this.\n')

  # Attempt to move the HEAD and verify error.
  repoA.target_tag = '55553d4a26bde22bec5817c17f803e9569cbb970'
  with pytest.raises(gordion.UpdateRepoIsDirtyError) as context:
    repoA.update()
  expected = gordion.UpdateRepoIsDirtyError(repoA.path)
  assert str(context.value) == str(expected)

  # If you don't move the HEAD, but change the branch while it's dirty, it's OK actually.
  repoA.target_tag = '163f847f32fba7307dd94366560d7d55ffe3c144'
  repoA.target_branch_name = 'testbranch1'
  repoA.update()
