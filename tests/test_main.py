import os
import gordion
import pytest


@pytest.fixture
def repo_a(repo_a_session):
  """
  This puts the repo_a object back into a well-known state for each test case.
  """
  # Setup
  #
  # Set the object to a known commit on the develop branch.
  tag = 'c9da3e67006cbb03b6810d2e5b8effebb0f0b674'
  branch_name = 'develop'

  # Set the target branch/commit.
  repo_a_session.update(tag, branch_name, force=True)

  yield repo_a_session

  # Cleanup
  #
  # Delete all local branches except develop (can't be deleted) to start fresh.
  repo_a_session.handle.branches['develop'].checkout()
  branches = list(repo_a_session.handle.branches)
  for branch in branches:
    if branch.name != 'develop':
      repo_a_session.handle.delete_head(branch, force=True)

  # Git clean.
  def cleanup_repo(path):
    if os.path.exists(path):
      print(f"Git clean {path}")
      repo = gordion.Repository(path)
      repo.ensure()
      repo.handle.git.reset('--hard')
      repo.handle.git.clean('-fdx')

  cleanup_repo(repo_a_session.path)
  cleanup_repo(os.path.join(repo_a_session.path, 'gordion', 'gordion_demo_b'))
  cleanup_repo(os.path.join(repo_a_session.path, 'gordion', 'gordion_demo_c'))
  cleanup_repo(os.path.join(repo_a_session.path, 'gordion', 'gordion_demo_d'))

  # Update to our known commit.
  repo_a_session.update(tag, branch_name, force=True)


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
