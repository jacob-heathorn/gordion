import os
import gordion
import pytest
# from git import Repo, BadName

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

  # Create the repo object, this will clone.
  repo = gordion.Repository(path, url, 'TODO', 'TODO')

  yield repo


@pytest.fixture
def repoA(repoA_session):
  """
  This puts the repoA object back into a well-known state for each test case.
  """
  # Set the object to a known commit on the develop branch.
  repoA_session.target_tag = 'fb769bfc4facde44449b70ae0c617f6b2553d772'
  repoA_session.target_branch_name = 'develop'

  # Use the underlying Repo handle object to reset the commit
  develop = repoA_session.handle.heads['develop']
  develop.checkout()
  target_commit = repoA_session.handle.commit(repoA_session.target_tag)
  repoA_session.handle.head.reset(commit=target_commit, index=True, working_tree=True)

  # Delete all local branches except develop
  branches = list(repoA_session.handle.branches)
  for branch in branches:
    if branch.name != 'develop':
      repoA_session.handle.delete_head(branch, force=True)

  yield repoA_session


def test_one(repoA):
  yaml_fullfile = os.path.join(REPOS_DIR, 'gordion_demo_a', 'gordion.yaml')

  obj = gordion.Root(yaml_fullfile)

  pass
