import os
from gordion.repository import Repository

assert 'TOXTEMPDIR' in os.environ, "you must run these tests using tox"

REPOS_PATH = os.path.join(os.environ['TOXTEMPDIR'], 'repos')


def test_is_git_repository():

  url = 'dontcare'
  tag = 'dontcare'
  branch = 'dontcare'

  repo = Repository(REPOS_PATH, url, tag, branch)

  assert not repo._is_git_repository()
