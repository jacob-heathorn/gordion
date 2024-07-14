import os
import gordion
import pytest

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
  repo = gordion.Repository(path)
  repo.ensure(url)

  yield repo


@pytest.fixture
def repo_a(repo_a_session):
  """
  This puts the repo_a object back into a well-known state for each test case.
  """

  # Clear uncommitted changes.
  repo_a_session.handle.git.reset('--hard')
  repo_a_session.handle.git.clean('-fdx')

  # Delete all local branches except develop (can't be deleted) to start fresh.
  repo_a_session.handle.branches['develop'].checkout()
  branches = list(repo_a_session.handle.branches)
  for branch in branches:
    if branch.name != 'develop':
      repo_a_session.handle.delete_head(branch, force=True)

  # Set the object to a known commit on the develop branch.
  tag = 'c9da3e67006cbb03b6810d2e5b8effebb0f0b674'
  branch_name = 'develop'

  # Set the target branch/commit
  repo_a_session.update(tag, branch_name, force=True)
  assert repo_a_session.handle.head.commit.hexsha == tag
  assert repo_a_session.handle.active_branch.name == branch_name

  yield repo_a_session


def test_gordion_root(repo_a):
  """
  Verifies the gordion -r behavior.
  """

  # From top of repoA.
  with gordion.utils.pushd(repo_a.path):
    assert repo_a.path == gordion.app.main.gordion_root()

  # From the gordion directory in repoA.
  with gordion.utils.pushd(os.path.join(repo_a.path, 'gordion')):
    assert repo_a.path == gordion.app.main.gordion_root()

  # From one level above repoA.
  with gordion.utils.pushd(os.path.join(repo_a.path, '..')):
    with pytest.raises(gordion.NotAGordionRepositoryError):
      gordion.app.main.gordion_root()

  # From repoB under repoA
  with gordion.utils.pushd(os.path.join(repo_a.path, 'gordion', 'gordion_demo_b')):
    assert repo_a.path == gordion.app.main.gordion_root()

  # Cause repoC to dangle and then try from there.
  repo_a.yeditor.yaml_data['repositories']['gordion_demo_c']['path'] = '/heyo/gordion_demo_c'
  repo_a.yeditor.save()
  with gordion.utils.pushd(os.path.join(repo_a.path, 'gordion', 'gordion_demo_c')):
    with pytest.raises(gordion.DanglingGordionRepositoryError) as context:
      gordion.app.main.gordion_root()

    expected = gordion.DanglingGordionRepositoryError(
      os.path.join(repo_a.path, 'gordion', 'gordion_demo_c'), repo_a.path)
    assert str(context.value) == str(expected)
