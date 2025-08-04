# Tests for the gordion.Repository interface. That means we are dealing with a single repository,
# which does not recursively manage children.

import os
import gordion
import pytest
import git
from test.conftest import recursive_git_blast_workspace


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


def test_exists():
  # A file inside a repository is not an existing repository
  path = os.path.join(SCRIPT_DIR)
  assert not gordion.Repository.exists(path)

  # Verify this repository root is a git repository path.
  path = os.path.join(SCRIPT_DIR, '..')
  assert gordion.Repository.exists(path)


@pytest.fixture
def demo_a(repository_a):
  """
  This puts the gordion.Repository session object back into a well-known state for each test case.
  """

  # Set the object to a known commit on the test_single branch.
  tag = 'a415fa52649601f17fccf6d17616281213b117b8'
  branch_name = 'test_single'

  # Set the target branch/commit
  repository_a.update(tag, branch_name, force=True)
  yield repository_a

  # Cleanup.
  recursive_git_blast_workspace()

  # Update to our known commit.
  repository_a.update(tag, branch_name, force=True)


def test_verify_tag(demo_a):
  # Verify HEAD of active branch exists.
  demo_a.verify_tag(demo_a.handle.head.commit.hexsha)

  # Verify older commit of active branch exists.
  demo_a.verify_tag(demo_a.handle.head.commit.parents[0].hexsha)

  # Verify a tag that only exists on a different remote branch (test_single_1) in fact exists.
  demo_a.verify_tag('05090461f38c8b725d89bf30a31c716383778b48')

  # Verify that an ill-formed commit will raise an error.
  with pytest.raises(git.BadName):
    demo_a.verify_tag("123")


def test_does_local_branch_have_commit(demo_a):
  """
  Verifies the behavior of _does_local_branch_have_commit()
  """

  # Verify HEAD of active branch returns true
  assert demo_a.handle.active_branch.name == 'test_single'
  head_commit = demo_a.handle.active_branch.commit
  assert demo_a._does_local_branch_have_commit('test_single', head_commit)

  # Verify older commit of active branch returns true
  older_commit = head_commit.parents[0]
  assert demo_a._does_local_branch_have_commit('test_single', older_commit)

  # Verify remote branch (test_single_1) that is not local returns false.
  assert not demo_a._does_local_branch_have_commit('test_single_1', head_commit)

  # Now checkout "test_single_1" so it exists locally, then switch back to "test_single". The same
  # check should return true.
  demo_a.handle.git.checkout('-b', 'test_single_1', 'origin/test_single_1')
  demo_a.handle.branches['test_single'].checkout()
  assert demo_a._does_local_branch_have_commit('test_single_1', head_commit)

  # Verfiy commit on remote but not on local returns false.
  future_commit = demo_a.verify_tag('04518b39225d45f69fc9a2f9f5c0dba1fe6a6227')
  assert not demo_a._does_local_branch_have_commit('test_single', future_commit)


def test_update_active_branch_commits_ahead(demo_a):
  """
  Verifies that updating the active branch will ERROR if it is ahead of the remote.
  """
  baseline_commit = demo_a.handle.head.commit.hexsha

  # Create newer commit on the active 'test_single' branch.
  demo_a.handle.index.commit("Empty commit for testing")

  # Verify update error. User needs to save the commits, or force the update.
  with pytest.raises(gordion.UpdateLocalBranchAheadError) as context:
    demo_a.update(baseline_commit, "test_single")
  expected = gordion.UpdateLocalBranchAheadError(demo_a.path, 'test_single', 'origin/test_single',
                                                 1)
  assert str(context.value) == str(expected)


def test_update_nonactive_local_branch_commits_ahead(demo_a):
  """
  Verifies that updating a non-active local branch will ERROR if it is ahead of the remote.
  """
  # Add a commit to "test_single_1"
  demo_a.handle.git.checkout('-b', 'test_single_1', 'origin/test_single_1')
  demo_a.handle.index.commit("Empty commit for testing")
  demo_a.handle.branches['test_single'].checkout()

  # Verify update error. User needs to save the commits, or force the update.
  # NOTE: the commit needs to move, so checkout HEAD~1
  with pytest.raises(gordion.UpdateLocalBranchAheadError) as context:
    demo_a.update(demo_a.handle.commit('HEAD~1').hexsha, "test_single_1")
  expected = gordion.UpdateLocalBranchAheadError(demo_a.path, 'test_single_1',
                                                 'origin/test_single_1', 1)
  assert str(context.value) == str(expected)


def test_update_local_branch_no_remote(demo_a):
  """
  Verifies that updating a local branch will ERROR if it does not have a remote tracking branch.
  """

  # Create a new local branch, with no remote, and checkout develop again."
  demo_a.handle.git.checkout('-b', 'test_branch_no_remote')
  demo_a.handle.branches['test_single'].checkout()

  # Point the update to test_branch_no_remote:HEAD~1. Verify update error. User needs to create a
  # tracking branch.
  branch_name = 'test_branch_no_remote'
  tag = demo_a.handle.branches['test_branch_no_remote'].commit.parents[0].hexsha

  # Verify update error. User needs to create a tracking branch.
  with pytest.raises(gordion.UpdateNoTrackingBranchError) as context:
    demo_a.update(tag, branch_name)
  expected = gordion.UpdateNoTrackingBranchError(demo_a.path, 'test_branch_no_remote')
  assert str(context.value) == str(expected)


def test_does_remote_branch_have_commit(demo_a):
  """
  Verifies behavior of _does_remote_branch_have_commit()
  """

  # Verify a commit is on remote branch but not local.
  commit = demo_a.verify_tag('04518b39225d45f69fc9a2f9f5c0dba1fe6a6227')
  assert not demo_a._does_local_branch_have_commit('test_single', commit)
  assert demo_a._does_remote_branch_have_commit('test_single', commit)

  # If remote branch does not exist, it just returns false.
  assert not demo_a._does_remote_branch_have_commit('noname', commit)

  # Verifies a commit on local but not remote.
  demo_a.handle.index.commit("Empty commit test_does_remote_branch_have_commit()")
  commit = demo_a.handle.active_branch.commit
  assert demo_a._does_local_branch_have_commit('test_single', commit)
  assert not demo_a._does_remote_branch_have_commit('test_single', commit)


def test_update_remote_branch_only(demo_a):
  """
  Verifies that update will create a new local branch to track the remote branch if it does not
  exist yet AND the remote branch has the target commit.
  """
  new_commit = demo_a.handle.commit('HEAD~1').hexsha
  demo_a.update(new_commit, "test_single_1")
  assert demo_a.handle.head.reference.name == "test_single_1"
  assert demo_a.handle.head.commit.hexsha == new_commit


def test_update_local_fastforward(demo_a):
  """
  If there is a local branch, but it does not contain the commit, but the remote branch does
  contain the commit, update will fastforward.
  """

  # Choose a tag ahead of our baseline commit.
  demo_a.update('a415fa52649601f17fccf6d17616281213b117b8', "test_single")


def test_local_branch_wrong_tracking_branch(demo_a):
  """
  If there is a local branch that matches the remote branch by name, but it has the wrong tracking
  branch, error.
  """
  baseline_commit = demo_a.handle.head.commit.hexsha

  # Checkout "test_single_1" locally but link it to the wrong remote branch.
  demo_a.handle.git.checkout('-b', 'test_single_1', 'origin/test_single')
  with pytest.raises(gordion.UpdateWrongTrackingBranchError) as context:
    demo_a.update(baseline_commit, "test_single_1")
  expected = gordion.UpdateWrongTrackingBranchError(demo_a.path, 'test_single_1',
                                                    'origin/test_single')
  assert str(context.value) == str(expected)


def test_detached_head_unsaved_commit(demo_a):
  """
  Verifies update will ERROR if we are in a detached head state, and the HEAD commit does not
  exist on a branch somewhere.
  """
  # Go to detached HEAD state.
  baseline_commit = demo_a.handle.head.commit.hexsha
  demo_a.handle.git.checkout(baseline_commit)
  assert demo_a.handle.head.is_detached

  # Now add a commit.
  demo_a.handle.index.commit("Commit while in detached HEAD state.")

  # Now verify that update errors.
  with pytest.raises(gordion.UpdateDetachedHeadNotSavedError) as context:
    demo_a.update(baseline_commit, "test_single")
  expected = gordion.UpdateDetachedHeadNotSavedError(demo_a.path)
  assert str(context.value) == str(expected)


def test_requested_branch_does_not_have_commit(demo_a):
  """
  Verifies that update will checkout will first try the default branch, then checkout in detached
  head state if it cannot find the commit on the specified branch.
  """

  # If the commit moves, and exists on the default branch but not the requested branch, it will go
  # there. Choose a commit on develop but not test_single_1.
  new_commit = demo_a.verify_tag('8a477c37ae584072dd1c7909c5000f5e2677fec5')
  demo_a.update(new_commit, "test_single_1")
  assert demo_a.handle.active_branch.name == "develop"
  assert demo_a.handle.head.commit == new_commit

  # If the commit moves, and exists on a non-default branch, but not the requested branch, it will
  # checkout detached HEAD. Choose a commit that exists on test_single_1 only.
  new_commit = demo_a.verify_tag('05090461f38c8b725d89bf30a31c716383778b48')
  demo_a.update(new_commit, "test_single")
  assert demo_a.handle.head.is_detached
  assert demo_a.handle.head.commit == new_commit


def test_dont_specify_branch(demo_a):
  """
  Verifies that if you don't specify the branch, it will checkout the commit on the default branch
  if it exists there. If it doesn't exist there it will check it out in a detached head state.
  """
  # If commit does not move, it'll stay on the branch checked out.
  baseline_commit = demo_a.handle.head.commit
  demo_a.update(baseline_commit, None)
  assert not demo_a.handle.head.is_detached
  assert demo_a.handle.active_branch.name == "test_single"
  assert demo_a.handle.head.commit == baseline_commit

  # If the commit moves, and exists on the default branch (develop) it will go there. Choose a
  # commit that only exists on develop branch.
  new_commit = demo_a.verify_tag('8a477c37ae584072dd1c7909c5000f5e2677fec5')
  demo_a.update(new_commit, None)
  assert demo_a.handle.active_branch.name == "develop"
  assert demo_a.handle.head.commit == new_commit

  # If the commit does not exist on the default branch, it'll checkout in detached HEAD state.
  demo_a.update(baseline_commit, None)
  assert demo_a.handle.head.is_detached
  assert demo_a.handle.head.commit == baseline_commit


def test_update_dirty_repo(demo_a):
  """
  Verifies update will error if the repository is dirty and the HEAD is about to move.
  """

  # Make an arbitrary change.
  file_path = os.path.join(demo_a.path, 'README.md')
  with open(file_path, 'w') as file:
    file.write('test_uncommitted_edits wrote this.\n')

  # Attempt to move the HEAD and verify error.
  tag = demo_a.handle.head.commit.parents[0].hexsha
  with pytest.raises(gordion.UpdateRepoIsDirtyError) as context:
    demo_a.update(tag, "test_single")
  expected = gordion.UpdateRepoIsDirtyError(demo_a.path)
  assert str(context.value) == str(expected)

  # If you don't move the HEAD, but change the branch while it's dirty, it's OK actually.
  tag = demo_a.handle.head.commit.hexsha
  demo_a.update(tag, "test_single")
