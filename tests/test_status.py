# Verifies the gordion -s behavior

import gordion
from gordion.utils import green, bold_green, bold_blue, red, bold_red, yellow
import pytest
from tests.conftest import recursive_git_blast
import os


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


# =================================================================================================
# Nominal status test


NOMINAL_STATUS = \
  f"""{bold_green('gordion_demo_a')} {green('test_status')}:{green('7e869f8')}
└──{bold_blue('gordion')}
    ├──{bold_green('gordion_demo_d')} {green('develop')}:{green('1e58b64')}
    ├──{bold_blue('level_1')}
    │   └──{bold_green('gordion_demo_b')} {green('develop')}:{green('64d65c2')}
    └──{bold_blue('level_2')}
        └──{bold_green('gordion_demo_c')} {green('develop')}:{green('ef7aabb')}"""


def test_nominal_status(demo_a):
  """
  Verifies the nominal status string (all green).
  """

  root_path = gordion.app.root.gordion_root(demo_a.path)
  root = gordion.Tree(root_path)
  assert NOMINAL_STATUS == gordion.app.status.get_status(root)


# =================================================================================================
# Tests for repository status


TEST_DANGLING_REPOSITORY_STATUS = \
  f"""{bold_green('gordion_demo_a')} {green('test_dangling_repository')}:{green('cf343cd')}
└──{bold_blue('gordion')}
    ├──{bold_green('gordion_demo_d')} {green('develop')}:{green('1e58b64')}
    ├──{bold_blue('level_1')}
    │   └──{bold_green('gordion_demo_b')} {green('develop')}:{green('64d65c2')}
    └──{bold_blue('level_2')}
        └──{bold_red('gordion_demo_c')} {'develop'}:{'ef7aabb'}"""


def test_dangling_repository(demo_a):
  """
  Verifies the repository will appear RED if it is unlisted. The commit and branch will appear
  white.
  """

  # Checkout branch test_dangling_repository.
  demo_a.handle.git.checkout('-b', 'test_dangling_repository', 'origin/test_dangling_repository')

  # Get actual status and verify.
  root_path = gordion.app.root.gordion_root(demo_a.path)
  root = gordion.Tree(root_path)
  assert TEST_DANGLING_REPOSITORY_STATUS == gordion.app.status.get_status(root)


# =================================================================================================
# Tests for commit status


def test_wrong_commit(demo_a):
  """
  Verifies the commit will appear RED if it does not match the parent gordion.yaml file.
  """

  # In demoC, checkout HEAD~1
  demo_c = demo_a.children['gordion_demo_c']
  demo_c.handle.head.reset('HEAD~1', index=True, working_tree=True)

  # Get the expected status string.
  demo_c_new_commit = demo_c.handle.head.commit.hexsha[:7]
  expected_status = NOMINAL_STATUS.replace(green('ef7aabb'), red(demo_c_new_commit))

  # Get actual status and verify.
  root_path = gordion.app.root.gordion_root(demo_a.path)
  root = gordion.Tree(root_path)
  assert expected_status == gordion.app.status.get_status(root)


def test_dirty_commit(demo_a):
  """
  Verifies the commit have a "-dirty" flag if there are uncommitted changes.
  """

  # Make demoB dirty.
  file_path = os.path.join(demo_a.children['gordion_demo_b'].path, 'README.md')
  with open(file_path, 'w') as file:
    file.write('test_dirty_commit wrote this.\n')

  # Get the expected status string.
  expected_status = NOMINAL_STATUS.replace(green('64d65c2'), green('64d65c2') + yellow('-dirty'))

  # Get actual status and verify.
  root_path = gordion.app.root.gordion_root(demo_a.path)
  root = gordion.Tree(root_path)
  assert expected_status == gordion.app.status.get_status(root)
