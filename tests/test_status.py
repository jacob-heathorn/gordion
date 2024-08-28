# Verifies the gordion -s behavior

import gordion
from gordion.utils import green, bold_green, bold_blue, red, bold_red, yellow
from gordion.utils import replace_i
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


# =================================================================================================
# Tests for branch status
#
# Verifies root branch color rendering in the following situations:
# Green:
#   1. Child same as root branch.
#   2. Child is default branch, while root branch is not available.
#   3. Child is DETACHED and root/default branches are not available.

# Yellow:
#   4. Child is default branch while root branch is available.
#   5. Child is different branch while root branch is available.
#   6. Child is different branch while default branch is available.
#   7. Child is DETACHED while root or default branch is available.

# Suggestions:
#   8.  (root branch?)
#   9.  (default branch?)
#   10. (ahead)
#   11. (wrong tracking branch)
#   12. (untracked)
#   13. (unsaved)

def test_branch_ahead(demo_a):
  """
  Verifies situations:
    10. (ahead)
    2. Child branch is default branch, while root branch is not available.
       (All children are default branch, and still green)
  """
  demo_a.handle.index.commit("Empty commit for test_branch_color")
  expected = NOMINAL_STATUS.replace(green('test_status'),
                                    green('test_status') + yellow('(ahead)'))
  expected = expected.replace(green('7e869f8'),
                              green(demo_a.handle.head.commit.hexsha[0:7]))
  root = gordion.Tree(gordion.app.root.gordion_root(demo_a.path))
  assert expected == gordion.app.status.get_status(root)


def test_wrong_tracking_branch(demo_a):
  """
  Verifies situations:
    6. Child is different branch while default branch is available.
    9. (default branch?)
    11. (wrong tracking branch)
  """
  demo_c = demo_a.children['gordion_demo_c']
  demo_c.handle.git.checkout('-b', 'different_branch')
  demo_c.handle.active_branch.set_tracking_branch(demo_c.handle.remotes['origin'].refs['develop'])
  expected = replace_i(NOMINAL_STATUS,
                       green('develop'),
                       yellow('different_branch') + yellow('(develop?, wrong tracking branch)'), 2)
  root = gordion.Tree(gordion.app.root.gordion_root(demo_a.path))
  assert expected == gordion.app.status.get_status(root)


def test_child_branch_is_root_branch(demo_a):
  """
  Verifies situations:
    12. (untracked)
    1. Child same as root branch.
  """
  demo_a.handle.git.checkout('-b', 'root_branch')
  demo_b = demo_a.children['gordion_demo_b']
  demo_b.handle.git.checkout('-b', 'root_branch')
  expected = \
    NOMINAL_STATUS.replace(green('test_status'),
                           green('root_branch') + yellow('(untracked)'))
  expected = replace_i(expected,
                       green('develop'),
                       green('root_branch') + yellow('(untracked)'), 1)
  root = gordion.Tree(gordion.app.root.gordion_root(demo_a.path))
  assert expected == gordion.app.status.get_status(root)


def test_child_default_root_available(demo_a):
  """
  Verifies situations:
    4. Child is default branch while root branch is available.
    8. (root branch?)
  """
  demo_a.handle.git.checkout('-b', 'root_branch')
  demo_b = demo_a.children['gordion_demo_b']
  demo_b.handle.git.checkout('-b', 'root_branch')
  demo_b.handle.branches['develop'].checkout()
  expected = \
    NOMINAL_STATUS.replace(green('test_status'),
                           green('root_branch') + yellow('(untracked)'))
  expected = replace_i(expected,
                       green('develop'),
                       yellow('develop') + yellow('(root_branch?)'), 1)
  root = gordion.Tree(gordion.app.root.gordion_root(demo_a.path))
  assert expected == gordion.app.status.get_status(root)


def test_child_different_root_available(demo_a):
  """
  Verifies situations:
    5. Child is different branch while root branch is available.
  """
  demo_a.handle.git.checkout('-b', 'root_branch')
  demo_b = demo_a.children['gordion_demo_b']
  demo_b.handle.git.checkout('-b', 'root_branch')
  demo_b.handle.git.checkout('-b', 'different_branch')
  expected = \
    NOMINAL_STATUS.replace(green('test_status'),
                           green('root_branch') + yellow('(untracked)'))
  expected = replace_i(expected,
                       green('develop'),
                       yellow('different_branch') + yellow('(root_branch?, untracked)'), 1)
  root = gordion.Tree(gordion.app.root.gordion_root(demo_a.path))
  assert expected == gordion.app.status.get_status(root)


def test_child_detached_root_available(demo_a):
  """
  Verifies situations:
    7. Child is DETACHED while root or default branch is available.
  """
  demo_d = demo_a.children['gordion_demo_b'].children['gordion_demo_d']
  demo_d.handle.git.checkout(demo_d.handle.head.commit)
  expected = replace_i(NOMINAL_STATUS,
                       green('develop'),
                       yellow('DETACHED HEAD') + yellow('(develop?)'), 0)
  root = gordion.Tree(gordion.app.root.gordion_root(demo_a.path))
  assert expected == gordion.app.status.get_status(root)


def test_child_detached_green(demo_a):
  """
  Verifies situations:
    3. Child is DETACHED and root/default branches are not available.
    13. (unsaved)
  """
  # Make a commit to demoC while detached. Now the default branch is not available at this commit,
  # so 'DETACHED HEAD' becomes green.
  demo_d = demo_a.children['gordion_demo_b'].children['gordion_demo_d']
  demo_d.handle.git.checkout(demo_d.handle.head.commit)
  demo_d.handle.index.commit("Empty commit for test_child_detached_green")
  expected = replace_i(NOMINAL_STATUS,
                       green('develop'),
                       green('DETACHED HEAD') + yellow('(unsaved)'), 0)
  expected = expected.replace(green('1e58b64'), red(demo_d.handle.head.commit.hexsha[0:7]))
  root = gordion.Tree(gordion.app.root.gordion_root(demo_a.path))
  assert expected == gordion.app.status.get_status(root)
