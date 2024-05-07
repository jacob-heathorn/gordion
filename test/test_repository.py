import os
from gordion.repository import Repository
import subprocess
import unittest
import gordion

assert 'TOXTEMPDIR' in os.environ, "you must run these tests using tox"

REPOS_DIR = os.path.join(os.environ['TOXTEMPDIR'], 'repos')
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

class TestRepository(unittest.TestCase):
  
  def test_exists(self):
    url = 'dontcare'
    tag = 'dontcare'
    branch = 'dontcare'

    # Repository does not exist yet
    path = os.path.join(REPOS_DIR, 'west_demo_a')
    repo = Repository(path, url, tag, branch)
    self.assertFalse(repo._exists())

    # A file inside a repository is not an existing repository
    path = os.path.join(SCRIPT_DIR)
    repo = Repository(path, url, tag, branch)
    self.assertFalse(repo._exists())

    # This file lives in the gordion repository gordion root directory is an existing repository.
    path = os.path.join(SCRIPT_DIR, '..')
    repo = Repository(path, url, tag, branch)
    self.assertTrue(repo._exists())

  # TODO make it work with ssh url.
  def test_update(self):
    path = os.path.join(REPOS_DIR, 'west_demo_a')
    url = 'https://github.com/jacob-heathorn/west_demo_a.git'
    tag = '163f847f32fba7307dd94366560d7d55ffe3c144'
    branch = 'develop'

    repo = Repository(path, url, tag, branch)
    self.assertFalse(repo._exists())
    repo.update()
    self.assertTrue(repo._exists())

    # Create newer commit on same branch.
    args = ["git", "-C", path, "commit", "--allow-empty", "-m", "Empty commit for testing"]
    subprocess.check_call(args)

    # Verify update error. User needs to save the commits, or force the update.
    with self.assertRaises(gordion.ActiveBranchAheadError) as context:
      repo.update()
    expected = gordion.ActiveBranchAheadError(path, 'develop', 'origin/develop', 1)
    self.assertEqual(str(context.exception), str(expected))

    # # Older commit same branch.
    # tag = 'f68eccca87b05ca29c3a9ae0d71475f8f33115cd'
    # repo = Repository(path, url, tag, branch)
    # repo.update()

    # TODO test remote is ahead.