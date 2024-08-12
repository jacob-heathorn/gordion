import os
import gordion
import pytest

assert 'TOXTEMPDIR' in os.environ, "you must run these tests using tox"

REPOS_DIR = os.path.join(os.environ['TOXTEMPDIR'], 'repos')
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture(scope="session")
def tree_a():
  """
  Creates the gordion.Tree interface for gordion_demo_a only once for the lifetime of this session.
  This is important so the "fetch_once" doesn't fetch every test case, which saves time.
  """
  path = os.path.join(REPOS_DIR, 'gordion_demo_a')
  url = 'https://github.com/jacob-heathorn/gordion_demo_a.git'

  store = gordion.Store()
  store.setup(path)

  # Create the gordion.Tree interface.
  repo = gordion.Tree(path, url)

  yield repo


@pytest.fixture(scope="session")
def repository_a():
  """
  Creates the gordion.Repository interface for gordion_demo_a only once for the lifetime of this
  session. This is important so the "fetch_once" doesn't fetch every test case, which saves time.
  """
  path = os.path.join(REPOS_DIR, 'gordion_demo_a')
  url = 'https://github.com/jacob-heathorn/gordion_demo_a.git'

  store = gordion.Store()
  store.setup(path)

  # Create the gordion.Repository interface.
  repo = gordion.Repository(path, url)

  yield repo


def git_clean(path):
  if gordion.Repository._exists(path):
    repo = gordion.Repository(path)
    repo.handle.git.reset('--hard')
    repo.handle.git.clean('-fdx')
    repo.handle.git.stash('clear')


def git_delete_non_develop_branches(path):
  if gordion.Repository._exists(path):
    repo = gordion.Repository(path)
    repo.handle.branches['develop'].checkout()
    branches = list(repo.handle.branches)
    for branch in branches:
      if branch.name != 'develop':
        repo.handle.delete_head(branch, force=True)


def recursive_git_blast(path):
  # Cleanup root directory.
  git_clean(path)
  git_delete_non_develop_branches(path)

  # Cleanup child directories.
  for root, dirs, _ in os.walk(path):
    for dir in dirs:
      dir = os.path.join(root, dir)
      if gordion.Repository._exists(dir):
        git_clean(dir)
        git_delete_non_develop_branches(dir)
