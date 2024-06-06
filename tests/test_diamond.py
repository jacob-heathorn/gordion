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

  # Create the repo object and ensure it.
  repo = gordion.Repository(path)
  repo.ensure(url)

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


def test_tag_mismatch(repoA):
  """
  Verifies update will error if two of the same repository reference have different tags.
  """

  # Add a commit to repository D
  repo_d_path = os.path.join(repoA.path, 'gordion', 'gordion_demo_d')
  repo_d = gordion.Repository(repo_d_path)
  repo_d.handle.index.commit("Empty commit for test_tag_mismatch")

  # Make B point to D's new commit but not C
  repo_b_path = os.path.join(repoA.path, 'gordion', 'gordion_demo_b')
  repo_b = gordion.Repository(repo_b_path)
  repo_b.yeditor.write_repository_tag('gordion_demo_d', repo_d.handle.head.commit.hexsha)
  repo_b.handle.index.add(os.path.join(repo_b_path, 'gordion.yaml'))
  repo_b.handle.index.commit("Point to latest D")
  repoA.yeditor.write_repository_tag('gordion_demo_b', repo_b.handle.head.commit.hexsha)
  repoA.handle.index.add(os.path.join(repoA.path, 'gordion.yaml'))
  repoA.handle.index.commit("Point to latest B")

  # Now update, it should raise error, tag mismatch
  # repoA.update(repoA.handle.head.commit.hexsha, 'develop')

  # with pytest.raises(gordion.UpdateLocalBranchAheadError) as context:
  #   repoA.update(baseline_commit, "test_single")
  # expected = gordion.UpdateLocalBranchAheadError(repoA.path, 'test_single', 'origin/test_single', 1)
  # assert str(context.value) == str(expected)


# TODO looks like I'll need a force update at this point.
# def test_path_mismatch(repoA):
#   """
#   Verifies update will error if two repositories are attempted to be cloned at different paths.
#   """

#   pass
