import os
from gordion.repository import Repository
import subprocess
import gordion
import pytest

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


@pytest.fixture
def repoA():
  path = os.path.join(REPOS_DIR, 'west_demo_a')
  url = 'https://github.com/jacob-heathorn/west_demo_a.git'
  tag = '163f847f32fba7307dd94366560d7d55ffe3c144'
  branch = 'develop'
  repo = Repository(path, url, tag, branch)

  # Verify repository does not exist yet
  assert not repo._exists()

  # Verify update clones the repository
  repo.update()
  assert repo._exists()

  yield repo


class TestRepositoryUpdate:
  def test_active_branch_ahead(self, repoA):
    # Create newer commit on same branch.
    args = ["git", "-C", repoA.path, "commit", "--allow-empty", "-m", "Empty commit for testing"]
    subprocess.check_call(args)

    # Verify update error. User needs to save the commits, or force the update.
    with pytest.raises(gordion.UpdateActiveBranchAheadError) as context:
      repoA.update()
    expected = gordion.UpdateActiveBranchAheadError(repoA.path, 'develop', 'origin/develop', 1)
    assert str(context.value) == str(expected)

  # def test2(self, repoA):
  #   repoA.update()


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
