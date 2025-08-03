import os
import gordion
import pytest

assert 'TOXTEMPDIR' in os.environ, "you must run these tests using tox"

REPOS_DIR = os.path.join(os.environ['TOXTEMPDIR'], 'repos')
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

# Create repos directory if it doesn't exist
if not os.path.exists(REPOS_DIR):
  os.mkdir(REPOS_DIR)


# =================================================================================================
# Fixtures

@pytest.fixture(scope='session')
def repository_a_session():
  """
  Creates the gordion.Repository interface for gordion_demo_a only once for the lifetime of this
  session. This is important so the "fetch_once" doesn't fetch every test case, which saves time.
  """
  path = os.path.join(REPOS_DIR, 'gordion_demo_a')
  url = 'https://github.com/jacob-heathorn/gordion_demo_a.git'

  # Create the gordion.Repository interface.
  repo = gordion.Repository.ensure(path, url)
  
  # Initialize workspace with the repository path
  workspace = gordion.Workspace()
  workspace.setup(subpath=path)

  yield repo


@pytest.fixture
def repository_a(repository_a_session):
  """
  Function-scoped fixture that ensures repository_a is at the tip of develop branch.
  Inherits from repository_a_session to reuse the setup.
  """
  repo = repository_a_session
  
  # Ensure we're on develop branch at the latest commit
  if 'develop' in repo.handle.heads:
    develop_branch = repo.handle.heads['develop']
    develop_branch.checkout()
    # Pull latest changes to ensure we're at tip
    repo.handle.git.reset('--hard', 'origin/develop')
  
  yield repo


@pytest.fixture
def tree_a(repository_a_session):
  """
  This puts the gordion.Tree session object back into a well-known state for each test case.
  """
  # Setup
  #
  # Set the object to a known commit on the develop branch.
  tag = 'c9da3e67006cbb03b6810d2e5b8effebb0f0b674'
  branch_name = 'develop'

  # Set the target branch/commit.
  tree_a = gordion.Tree(repository_a_session)
  tree_a.update(tag, branch_name, force=True)

  # Ensure dependencies are in cache, not in workspace
  workspace = gordion.Workspace()

  # Move reposities to the cache.
  for name in ['gordion_demo_b', 'gordion_demo_c', 'gordion_demo_d']:
    repo = workspace.get_repository(name)
    if repo and not workspace.is_dependency(repo.path):
      # Repository is in workspace, move it back to cache
      cache_path = os.path.join(workspace.dependencies_path, name)
      if not os.path.exists(cache_path):
        gordion.Repository.safe_move(repo.path, cache_path)

  yield tree_a

  # Cleanup.
  recursive_git_blast_workspace()

  # Update to our known commit.
  tree_a.update(tag, branch_name, force=True)


@pytest.fixture
def tree_a_local(repository_a_session):
  """
  This creates a tree_a but ensures all repositories are in the local workspace.
  """
  # Setup
  #
  # Set the object to a known commit on the develop branch.
  tag = 'c9da3e67006cbb03b6810d2e5b8effebb0f0b674'
  branch_name = 'develop'

  # Set the target branch/commit.
  tree_a = gordion.Tree(repository_a_session)
  tree_a.update(tag, branch_name, force=True)

  # Move dependencies from cache to local workspace root
  workspace = gordion.Workspace()

  # Move each dependency repository from cache to workspace root
  for name in ['gordion_demo_b', 'gordion_demo_c', 'gordion_demo_d']:
    repo = workspace.get_repository(name)
    if repo and workspace.is_dependency(repo.path):
      new_path = os.path.join(REPOS_DIR, name)
      if not os.path.exists(new_path):
        gordion.Repository.safe_move(repo.path, new_path)

  yield tree_a

  # Cleanup.
  recursive_git_blast_workspace()

  # Update to our known commit.
  tree_a.update(tag, branch_name, force=True)


# =================================================================================================
# Helpers

def git_clean(repo):
  repo.handle.git.reset('--hard')
  repo.handle.git.clean('-fdx')
  repo.handle.git.stash('clear')


def git_delete_non_develop_branches(repo):
  repo.handle.branches['develop'].checkout()
  branches = list(repo.handle.branches)
  for branch in branches:
    if branch.name != 'develop':
      repo.handle.delete_head(branch, force=True)


def recursive_git_blast_workspace():
  for _, repo in gordion.Workspace().repos().items():
    git_clean(repo)
    git_delete_non_develop_branches(repo)
    repo.yeditor.reload()
