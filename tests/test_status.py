# Verifies the gordion -s behavior

import gordion
from gordion.utils import green, bold_green, bold_blue, red, bold_red, yellow
from gordion.utils import replace_i
import pytest


# =================================================================================================
# Fixtures

@pytest.fixture
def tree_a(tree_a):
  """
  This puts tree_a session object back into a well-known state for each test case.
  """
  # Setup
  #
  # Set the object to a known commit and branch.
  tag = '082abea'
  branch_name = 'test_status'

  # Set the target branch/commit.
  tree_a.update(tag, branch_name, force=True)

  yield tree_a

  print("here1")


# =================================================================================================
# Nominal status test

NOMINAL_STATUS = \
    f"""{bold_blue('repos')}
├──{bold_blue('.dependencies')}
│   ├──{bold_green('gordion_demo_b')} {green('develop')}{green(':fe4fd4d')}
│   ├──{bold_green('gordion_demo_c')} {green('develop')}{green(':1a8f7fe')}
│   └──{bold_green('gordion_demo_d')} {green('develop')}{green(':c516fff')}
└──{bold_green('gordion_demo_a*')} {green('test_status')}{green(':082abea')}"""


def test_nominal_status(tree_a):
  """
  Verifies the nominal status string (all green).
  """
  assert NOMINAL_STATUS == gordion.app.status.terminal_status(tree_a)


# =================================================================================================
# Tests for commit status

def test_wrong_commit(tree_a):
  """
  Verifies the commit will appear RED if it does not match the parent gordion.yaml file.
  """

  # In demoC, checkout HEAD~1
  # repo_c = gordion.Workspace().get_repository('gordion_demo_c')
  # repo_c.handle.head.reset('HEAD~1', index=True, working_tree=True)

  # # Get the expected status string.
  # demo_c_new_commit = repo_c.handle.head.commit.hexsha[:7]
  # expected = NOMINAL_STATUS.replace(green(':1a8f7fe'), red(f":{demo_c_new_commit}"))
  # assert expected == gordion.app.status.terminal_status(tree_a)

  # TODO remove
  # print("\n\n")
  # print(expected)
  # print("\n\n")
  # print(gordion.app.status.terminal_status(tree_a))


def test_child_mismatch(demo_a):
  """
  Verifies the following commit appendages:
    -mismatch
    -dirty
  """
  # Change demoB's listing of demoD to HEAD~1
  demo_b = demo_a.children['gordion_demo_b']
  demo_d = demo_b.children['gordion_demo_d']
  dminus1 = demo_d.handle.head.commit.parents[0]
  demo_b.yeditor.write_repository_tag('gordion_demo_d', dminus1.hexsha)
  demo_b.yeditor.save()

  # Verify.
  expected = NOMINAL_STATUS.replace(green('c516fff'), red('c516fff-mismatch'))
  expected = expected.replace(green('fe4fd4d'), green('fe4fd4d') + yellow('-dirty'))
  root = gordion.Tree(gordion.app.root.gordion_root(demo_a.path))
  assert expected == gordion.app.status.terminal_status(root)


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
  expected = expected.replace(green('4d95f11'),
                              green(demo_a.handle.head.commit.hexsha[0:7]))
  root = gordion.Tree(gordion.app.root.gordion_root(demo_a.path))
  assert expected == gordion.app.status.terminal_status(root)


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
  assert expected == gordion.app.status.terminal_status(root)


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
  assert expected == gordion.app.status.terminal_status(root)


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
  assert expected == gordion.app.status.terminal_status(root)


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
  assert expected == gordion.app.status.terminal_status(root)


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
  assert expected == gordion.app.status.terminal_status(root)


def test_child_detached_green(demo_a):
  """
  Verifies situations:
    3. Child is DETACHED and root/default branches are not available.
    13. (unsaved)
  """
  # Make a commit to demoC while detached. The default branch is not available at this commit,
  # so 'DETACHED HEAD' is green.
  demo_d = demo_a.children['gordion_demo_b'].children['gordion_demo_d']
  demo_d.handle.git.checkout(demo_d.handle.head.commit)
  demo_d.handle.index.commit("Empty commit for test_child_detached_green")
  expected = replace_i(NOMINAL_STATUS,
                       green('develop'),
                       green('DETACHED HEAD') + yellow('(unsaved)'), 0)
  expected = expected.replace(green('c516fff'), red(demo_d.handle.head.commit.hexsha[0:7]))
  root = gordion.Tree(gordion.app.root.gordion_root(demo_a.path))
  assert expected == gordion.app.status.terminal_status(root)
