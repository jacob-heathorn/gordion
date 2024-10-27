import os
import gordion
import pytest

assert 'TOXTEMPDIR' in os.environ, "you must run these tests using tox"

REPOS_DIR = os.path.join(os.environ['TOXTEMPDIR'], 'repos')
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

# Initialize workspace.
if not os.path.exists(REPOS_DIR):
  os.mkdir(REPOS_DIR)
workspace = gordion.Workspace()
workspace.setup(subpath=REPOS_DIR, force=True)


# =================================================================================================
# Fixtures

@pytest.fixture(scope="session")
def repository_a():
  """
  Creates the gordion.Repository interface for gordion_demo_a only once for the lifetime of this
  session. This is important so the "fetch_once" doesn't fetch every test case, which saves time.
  """
  path = os.path.join(REPOS_DIR, 'gordion_demo_a')
  url = 'https://github.com/jacob-heathorn/gordion_demo_a.git'

  # Create the gordion.Repository interface.
  repo = gordion.Repository.ensure(path, url)

  yield repo


@pytest.fixture
def tree_a(repository_a):
  """
  This puts the gordion.Tree session object back into a well-known state for each test case.
  """
  # Setup
  #
  # Set the object to a known commit on the develop branch.
  tag = 'c9da3e67006cbb03b6810d2e5b8effebb0f0b674'
  branch_name = 'develop'

  # Set the target branch/commit.
  tree_a = gordion.Tree(repository_a)
  tree_a.update(tag, branch_name, force=True)

  yield tree_a

  # Cleanup.
  recursive_git_blast(REPOS_DIR)

  # Update to our known commit.
  tree_a.update(tag, branch_name, force=True)


# =================================================================================================
# Helpers

def git_clean(path):
  if gordion.Repository.exists(path):
    repo = gordion.Repository(path)
    repo.handle.git.reset('--hard')
    repo.handle.git.clean('-fdx')
    repo.handle.git.stash('clear')


def git_delete_non_develop_branches(path):
  if gordion.Repository.exists(path):
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
      if gordion.Repository.exists(dir):
        git_clean(dir)
        git_delete_non_develop_branches(dir)
