import os
import gordion
import pytest
import git

assert 'TOXTEMPDIR' in os.environ, "you must run these tests using tox"

REPOS_DIR = os.path.join(os.environ['TOXTEMPDIR'], 'repos')
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture(scope="session")
def repo_a_session():
  """
  Creates the repo_a object only once for the lifetime of this session. This is important so the
  "fetch_once" doesn't fetch every test case, which saves time.
  """
  path = os.path.join(REPOS_DIR, 'gordion_demo_a')
  url = 'https://github.com/jacob-heathorn/gordion_demo_a.git'

  # Create the repo object and ensure it.
  repo = gordion.Tree(path)
  repo.ensure(url)

  yield repo


def git_clean(path):
  if os.path.exists(path):
    repo = git.Repo(path)
    repo.git.reset('--hard')
    repo.git.clean('-fdx')
    repo.git.stash('clear')


def git_delete_non_develop_branches(path):
  if os.path.exists(path):
    repo = git.Repo(path)
    repo.branches['develop'].checkout()
    branches = list(repo.branches)
    for branch in branches:
      if branch.name != 'develop':
        repo.delete_head(branch, force=True)


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


class MockRepository:
  def __init__(self, url: str, path: str, listed_path: str) -> None:
    self.url = url
    self.path = path
    self.name = os.path.basename(self.path)
    self.listed_path = listed_path

  def _listed_path(self):
    return self.listed_path
