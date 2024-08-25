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
  # Set the object to a known commit and branch.
  tag = '7e869f8de5bc0e1b5edc44682d5fd330e68b0d74'
  branch_name = 'test_status'

  # Set the target branch/commit.
  tree_a.update(tag, branch_name, force=True)

  yield tree_a

  # Cleanup.
  recursive_git_blast(tree_a.path)

  # Update to our known commit.
  tree_a.update(tag, branch_name, force=True)


def test_gordion_status(demo_a):
  """
  Verifies the gordion -s behavior.
  """

  # From top of repoA.
  with gordion.utils.pushd(demo_a.path):
    root_path = gordion.app.root.gordion_root(os.getcwd())
    root = gordion.Tree(root_path)
    print(gordion.app.status.get_status(root))
