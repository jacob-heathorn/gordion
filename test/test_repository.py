import os
from gordion.repository import Repository

assert 'TOXTEMPDIR' in os.environ, "you must run these tests using tox"

REPOS_DIR = os.path.join(os.environ['TOXTEMPDIR'], 'repos')


def test_is_git_repository():

  path = os.path.join(REPOS_DIR, 'west_example_a')
  url = 'dontcare'
  tag = 'dontcare'
  branch = 'dontcare'

  # Repository does not exist yet
  repo = Repository(path, url, tag, branch)
  assert not repo._is_git_repository()
