import os
import gordion
import pytest
from tests.conftest import recursive_git_blast


@pytest.fixture
def demo_a(tree_a):
  """
  This puts the gordion.Tree session object back into a well-known state for each test case.
  """
  # Setup
  #
  # Set the object to a known commit on the develop branch.
  tag = 'c9da3e67006cbb03b6810d2e5b8effebb0f0b674'
  branch_name = 'develop'

  # Set the target branch/commit.
  tree_a.update(tag, branch_name, force=True)

  yield tree_a

  # Cleanup.
  recursive_git_blast(tree_a.path)

  # Update to our known commit.
  tree_a.update(tag, branch_name, force=True)


def test_gordion_root(demo_a):
  """
  Verifies the gordion -r behavior.
  """

  # From top of repoA.
  with gordion.utils.pushd(demo_a.path):
    assert demo_a.path == gordion.app.root.gordion_root(os.getcwd())

  # From the gordion directory in repoA.
  with gordion.utils.pushd(os.path.join(demo_a.path, 'gordion')):
    assert demo_a.path == gordion.app.root.gordion_root(os.getcwd())

  # From one level above repoA.
  with gordion.utils.pushd(os.path.join(demo_a.path, '..')):
    with pytest.raises(gordion.NotAGordionRepositoryError):
      gordion.app.root.gordion_root(os.getcwd())

  # From repoB under repoA
  with gordion.utils.pushd(os.path.join(demo_a.path, 'gordion', 'gordion_demo_b')):
    assert demo_a.path == gordion.app.root.gordion_root(os.getcwd())

  # Cause repoC to dangle and then try from there.
  demo_a.yeditor.yaml_data['repositories']['gordion_demo_c']['path'] = '/heyo/gordion_demo_c'
  demo_a.yeditor.save()
  with gordion.utils.pushd(os.path.join(demo_a.path, 'gordion', 'gordion_demo_c')):
    with pytest.raises(gordion.DanglingGordionRepositoryError) as context:
      gordion.app.root.gordion_root(os.getcwd())

    expected = gordion.DanglingGordionRepositoryError(
      os.path.join(demo_a.path, 'gordion', 'gordion_demo_c'), demo_a.path)
    assert str(context.value) == str(expected)
