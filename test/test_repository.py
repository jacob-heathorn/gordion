import os
from gordion.repository import Repository

assert 'TOXTEMPDIR' in os.environ, "you must run these tests using tox"

REPOS_DIR = os.path.join(os.environ['TOXTEMPDIR'], 'repos')
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


def test_repository_exists():

  url = 'dontcare'
  tag = 'dontcare'
  branch = 'dontcare'

  # Repository does not exist yet
  path = os.path.join(REPOS_DIR, 'west_example_a')
  repo = Repository(path, url, tag, branch)
  assert not repo._exists()

  # A file inside a repository is not an existing repository
  path = os.path.join(SCRIPT_DIR)
  repo = Repository(path, url, tag, branch)
  assert not repo._exists()

  # This file lives in the gordion repository gordion root directory is an existing repository.
  path = os.path.join(SCRIPT_DIR, '..')
  repo = Repository(path, url, tag, branch)
  assert repo._exists()
