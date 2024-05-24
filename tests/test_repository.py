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


@pytest.fixture
def repoA():
  path = os.path.join(REPOS_DIR, 'west_demo_a')
  url = 'https://github.com/jacob-heathorn/west_demo_a.git'
  tag = '163f847f32fba7307dd94366560d7d55ffe3c144'
  branch = 'develop'
  # Create the repo object, this will clone.
  repo = gordion.Repository(path, url, tag, branch)

  # Use the underlying Repo handle object to reset the commit
  develop = repo.handle.heads['develop']
  develop.checkout()
  target_commit = repo.handle.commit(repo.target_tag)
  repo.handle.head.reset(commit=target_commit, index=True, working_tree=True)

  # Delete all local branches except develop
  branches = list(repo.handle.branches)
  for branch in branches:
    if branch.name != 'develop':
      repo.handle.delete_head(branch, force=True)

  yield repo


def test_verify_tag(repoA):
  # Verify HEAD of active branch exists.
  gordion.Repository._verify_tag(repoA.handle, '163f847f32fba7307dd94366560d7d55ffe3c144')

  # Verify older commit of active branch exists.
  gordion.Repository._verify_tag(repoA.handle, '1c518ee74d9c619321fea12e90c7a721dfddb0ee')

  # Verify a tag that only exists on a different remote branch (testbranch1) in fact exists.
  gordion.Repository._verify_tag(repoA.handle, '4a96229f1c4eb7c5c8f4d630513cca5919abcd7a')

  # Verify that an ill-formed commit will raise an error.
  with pytest.raises(BadName):
    gordion.Repository._verify_tag(repoA.handle, "123")


def test_does_local_branch_have_commit(repoA):
  # Verify HEAD of active branch returns true.
  commit = gordion.Repository._verify_tag(repoA.handle, '163f847f32fba7307dd94366560d7d55ffe3c144')
  assert gordion.Repository._does_local_branch_have_commit(repoA.handle, 'develop', commit)

  # Verify older commit of active branch returns true
  commit = gordion.Repository._verify_tag(repoA.handle, '1c518ee74d9c619321fea12e90c7a721dfddb0ee')
  assert gordion.Repository._does_local_branch_have_commit(repoA.handle, 'develop', commit)

  # Verify remote branch (testbranch1) that is not local returns false.
  assert not gordion.Repository._does_local_branch_have_commit(repoA.handle, 'testbranch1', commit)

  # Now checkout testbranch1 so it exists locally, then switch back to develop. The same function
  # should return true.
  repoA.handle.git.checkout('-b', 'testbranch1', 'origin/testbranch1')
  repoA.handle.branches['develop'].checkout()
  assert gordion.Repository._does_local_branch_have_commit(repoA.handle, 'testbranch1', commit)

  # Verfiy commit on remote but not on local returns false.
  commit = gordion.Repository._verify_tag(repoA.handle, '15289e899626fdb9aa187ab4b5888facf86e3ed8')
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
  with pytest.raises(gordion.UpdateActiveBranchAheadError) as context:
    repoA.update()
  expected = gordion.UpdateActiveBranchAheadError(repoA.path, 'develop', 'origin/develop', 1)
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
  with pytest.raises(gordion.UpdateActiveBranchAheadError) as context:
    repoA.update()
  expected = gordion.UpdateActiveBranchAheadError(
      repoA.path, 'testbranch1', 'origin/testbranch1', 1)
  assert str(context.value) == str(expected)


def test_update_local_branch_no_loss(repoA):
  """
  TODO verify update can switch to another local branch with no loss
  """
  pass


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

  # Now verify with a non-active branch.

  # TODO need to verify with a local branch that does not have a remote.

  # class TestRepositoryUpdate:
  # def test_commits_ahead(self, repoA):
  #   """
  #   Verifies that updating the active branch will ERROR if it is ahead of the remote.
  #   """
  #   # Create newer commit on same branch.
  #   repoA.handle.index.commit("Empty commit for testing")

  #   # Verify update error. User needs to save the commits, or force the update.
  #   with pytest.raises(gordion.UpdateActiveBranchAheadError) as context:
  #     repoA.update()
  #   expected = gordion.UpdateActiveBranchAheadError(repoA.path, 'develop', 'origin/develop', 1)
  #   assert str(context.value) == str(expected)

  # def test_commits_behind(self, repoA):
  #   """
  #   Verifies that updating the active branch will SUCCEED if it is behind the remote.
  #   """

  #   original_sha = repoA.handle.head.commit.hexsha

  #   # Go back one commit
  #   current_branch = repoA.handle.head.ref
  #   parent_commit = current_branch.commit.parents[0]
  #   repoA.handle.git.reset(parent_commit.hexsha, hard=True)

  #   # Verify update no error
  #   repoA.update()

  #   assert original_sha == repoA.handle.head.commit.hexsha

  # def test_active_branch_does_not_contain_commit(self, repoA):
  #   """
  #   Verifies that updating the active branch will FAIL if it does not contian the target commit.
  #   """

  #   # Just use a random, well-formatted commit that does not exist.
  #   repoA.target_tag = "163f847f32fba7307dd94366560d7d55ffe3c145"
  #   with pytest.raises(ValueError):
  # #   # Just use a random, well-formatted commit that does not exist.
  #   repoA.target_tag = "163f847f32fba7307dd94366560d7d55ffe3c145"
  #   with pytest.raises(ValueError):
  #     repoA.update()

  #   # Try a random, ill-formed commit
  #   repoA.target_tag = "123"
  #   with pytest.raises(BadName):
  #     repoA.update()
  # # TODO test commit exists in remote, but not local.

  # def test_switch_branch(self, repoA):
  #   """
  #   Verifies that switching active local branches during update will SUCCEED
  #   """

  #   # Create a new branch and switch to it
  #   new_branch = repoA.handle.create_head('test_branch')
  #   new_branch.checkout()
  #   assert repoA.handle.head.reference.name == "test_branch"

  #   # Verify update scucceeds because no information is lost.
  #   repoA.update()
  #   assert repoA.handle.head.reference.name == repoA.target_branch_name
  #   assert repoA.handle.head.commit.hexsha == repoA.target_tag

  # def test_switch_branch_ahead(self, repoA):
  #   """
  #   Verifies that switching active local branches and losing commits will FAIL
  #   """

  #   # Create a new branch and switch to it
  #   new_branch = repoA.handle.create_head('test_branch')
  #   new_branch.checkout()
  #   assert repoA.handle.head.reference.name == "test_branch"

  # def test_update_1(repoA):

  #   repoA.update()

  # def test_update_2(repoA):

  #   # # Create newer commit on same branch.
  #   # args = ["git", "-C", path, "commit", "--allow-empty", "-m", "Empty commit for testing"]
  #   # subprocess.check_call(args)

  #   # # Verify update error. User needs to save the commits, or force the update.
  #   # with self.assertRaises(gordion.UpdateActiveBranchAheadError) as context:
  #   #   repo.update()
  #   # expected = gordion.UpdateActiveBranchAheadError(path, 'develop', 'origin/develop', 1)
  #   # self.assertEqual(str(context.exception), str(expected))

  #   # # Create a new local branch
  #   # args = ["git", "-C", path, "checkout", "-b", "test_branch"]
  #   # subprocess.check_call(args, stderr=subprocess.STDOUT)

  #   # # Verify update scucceeds because no information is lost.
  #   # repo.update()

  #   # # # Older commit same branch.
  #   # # tag = 'f68eccca87b05ca29c3a9ae0d71475f8f33115cd'
  #   # # repo = Repository(path, url, tag, branch)
  #   # # repo.update()

  #   # # TODO test remote is ahead.
