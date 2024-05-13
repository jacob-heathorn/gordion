import os
from gordion.repository import Repository
import subprocess
import gordion
import pytest
from git import Repo

assert 'TOXTEMPDIR' in os.environ, "you must run these tests using tox"

REPOS_DIR = os.path.join(os.environ['TOXTEMPDIR'], 'repos')
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


def test_exists():
  url = 'dontcare'
  tag = 'dontcare'
  branch = 'dontcare'

  # A file inside a repository is not an existing repository
  path = os.path.join(SCRIPT_DIR)
  repo = Repository(path, url, tag, branch)
  assert not repo._exists()

  # Verify this repository root is a git repository path.
  path = os.path.join(SCRIPT_DIR, '..')
  repo = Repository(path, url, tag, branch)
  assert repo._exists()


@pytest.fixture(scope="module")
def repoA():
  path = os.path.join(REPOS_DIR, 'west_demo_a')
  url = 'https://github.com/jacob-heathorn/west_demo_a.git'
  tag = '163f847f32fba7307dd94366560d7d55ffe3c144'
  branch = 'develop'
  repo = Repository(path, url, tag, branch)

  # Verify update clones the repository
  repo.update(force=True)

  # Delete all local branches except develop
  git_repo = Repo(path)
  branches = list(git_repo.branches)
  for branch in branches:
    if branch.name != 'develop':
      git_repo.delete_head(branch, force=True)

  yield repo


class TestRepositoryUpdate:
  def test_active_branch_ahead(self, repoA):
    """
    Verifies that updating the active branch will error if it is ahead of the remote because commits
    will be lost.
    """
    # Create newer commit on same branch.
    args = ["git", "-C", repoA.path, "commit", "--allow-empty", "-m", "Empty commit for testing"]
    subprocess.check_call(args)

    # Verify update error. User needs to save the commits, or force the update.
    with pytest.raises(gordion.UpdateActiveBranchAheadError) as context:
      repoA.update()
    expected = gordion.UpdateActiveBranchAheadError(repoA.path, 'develop', 'origin/develop', 1)
    assert str(context.value) == str(expected)

  # TODO ability to access underlying handle (repo) object directly

  def test_switch_branch(self, repoA):
    """
    Verifies that switching active local branches during update will succeed because no information
    is lost.
    """

    # Create a new branch and switch to it
    new_branch = repoA.handle.create_head('test_branch')
    new_branch.checkout()

    # Verify update scucceeds because no information is lost.
    repoA.update()


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
