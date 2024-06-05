import os
import gordion
import pytest

assert 'TOXTEMPDIR' in os.environ, "you must run these tests using tox"

REPOS_DIR = os.path.join(os.environ['TOXTEMPDIR'], 'repos')
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture(scope="session")
def repoA_session():
  """
  Creates the repoA object only once for the lifetime of this session. This is important so the
  "fetch_once" doesn't fetch every test case, which saves time.
  """
  path = os.path.join(REPOS_DIR, 'gordion_demo_a')
  url = 'https://github.com/jacob-heathorn/gordion_demo_a.git'

  # Create the repo object, this will clone if necessary
  repo = gordion.Repository(path, url)
  repo.ensure()

  yield repo


@pytest.fixture
def repoA(repoA_session):
  """
  This puts the repoA object back into a well-known state for each test case.
  """

  # Delete all local branches except develop (can't be deleted) to start fresh.
  repoA_session.handle.branches['develop'].checkout()
  branches = list(repoA_session.handle.branches)
  for branch in branches:
    if branch.name != 'develop':
      repoA_session.handle.delete_head(branch, force=True)

  # Set the object to a known commit on the test_single branch.
  tag = repoA_session.handle.head.commit.hexsha
  branch_name = 'develop'

  # Set the target branch/commit
  repoA_session.update(tag, branch_name)
  assert repoA_session.handle.head.commit.hexsha == tag
  assert repoA_session.handle.active_branch.name == branch_name

  yield repoA_session


def test_diamond_clone(repoA):
  """
  Verifies nominal recursive clone of the diamond
  """

  repoA.update(repoA.handle.head.commit.hexsha, 'develop')
