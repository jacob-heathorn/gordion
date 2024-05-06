import os
from gordion.repository import Repository

assert 'TOXTEMPDIR' in os.environ, "you must run these tests using tox"

REPOS_DIR = os.path.join(os.environ['TOXTEMPDIR'], 'repos')
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


def test_is_git_repository():

  url = 'dontcare'
  tag = 'dontcare'
  branch = 'dontcare'

  # Repository does not exist yet
  path = os.path.join(REPOS_DIR, 'west_example_a')
  repo = Repository(path, url, tag, branch)
  assert not repo._is_git_repository()

  # Check that self is a repository
  path = os.path.join(SCRIPT_DIR)
  repo = Repository(path, url, tag, branch)
  assert repo._is_git_repository()
