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
  repo_c = gordion.Workspace().get_repository('gordion_demo_c')
  repo_c.handle.head.reset('HEAD~1', index=True, working_tree=True)

  # Get the expected status string.
  demo_c_new_commit = repo_c.handle.head.commit.hexsha[:7]
  expected = NOMINAL_STATUS.replace(green(':1a8f7fe'), red(f":{demo_c_new_commit}"))
  assert expected == gordion.app.status.terminal_status(tree_a)


def test_child_mismatch(tree_a):
  """
  Verifies (TAG INCOHERENCE)
  """
  # Change demoB's listing of demoD to HEAD~1
  repo_b = gordion.Workspace().get_repository('gordion_demo_b')
  repo_d = gordion.Workspace().get_repository('gordion_demo_d')
  dminus1 = repo_d.handle.head.commit.parents[0]
  repo_b.yeditor.write_repository_tag('gordion_demo_d', dminus1.hexsha)
  repo_b.yeditor.save()

  # Verify.
  expected = NOMINAL_STATUS.replace(green(':c516fff'),
                                    red(':c516fff') + " " + red('(TAG INCOHERENCE)'))
  expected = expected.replace(green(':fe4fd4d'), green(':fe4fd4d') + yellow('-dirty'))

  expected_header = bold_red("\nTag Incoherences:\n")
  repo_b_listings, _ = tree_a.listings(name='gordion_demo_d', url=None)
  for listing in repo_b_listings:
    listing_str = gordion.Tree.list_tag(listing)
    expected_header += red(listing_str + "\n")
  expected = expected_header + "\n" + expected

  assert expected == gordion.app.status.terminal_status(tree_a)


def test_conflicted(tree_a):
  """
  Verifies NAME_CONFLICTED, URL_CONFLICTED, and NOT_FOUND.
  """
  # Change demoC's listing of "gordion_demo_d"s URL to "gordion_demo_b"s URL.
  repo_c = gordion.Workspace().get_repository('gordion_demo_c')
  b_url = tree_a.repo.yeditor.yaml_data['repositories']['gordion_demo_b']['url']
  repo_c.yeditor.yaml_data['repositories']['gordion_demo_d']['url'] = b_url
  repo_c.yeditor.save()

  # Verify.
  # demoC commit is dirty.
  c_commit = repo_c.handle.head.commit.hexsha
  expected = NOMINAL_STATUS.replace(green(':' + c_commit[0:7]),
                                    green(':' + c_commit[0:7]) + yellow("-dirty"))
  # demoB is NAME_CONFLICTED. There are two listings that have demoB's URL, but they have different
  # names.
  repo_b = gordion.Workspace().get_repository('gordion_demo_b')
  b_commit = repo_b.handle.head.commit.hexsha
  expected = expected.replace(green(':' + b_commit[0:7]),
                              green(':' + b_commit[0:7]) + " " + red("(NAME CONFLICTED)"))
  # demoD is URL_CONFLICTED. There are two listings of demoD, with different URLs.
  repo_d = gordion.Workspace().get_repository('gordion_demo_d')
  d_commit = repo_d.handle.head.commit.hexsha
  expected = expected.replace(green(':' + d_commit[0:7]),
                              green(':' + d_commit[0:7]) + " " + red("(URL CONFLICTED)"))

  # The not found listing will be the demoD listing with demoBs url.
  expected_header = bold_red("\nNot Found:\n")
  not_found_listings, _ = tree_a.listings(name='gordion_demo_d', url=b_url)
  assert len(not_found_listings) == 1
  listing_str = gordion.Tree.list_url(not_found_listings[0])
  expected_header += red(listing_str + "\n")

  # The URL Incoherences (all demoD, and demoB listings)
  expected_header += bold_red("\nURL Incoherences:\n")
  repo_d_listings, _ = tree_a.listings(name='gordion_demo_d', url=None)
  repo_b_listings, _ = tree_a.listings(name='gordion_demo_b', url=None)
  all_incoherences = []
  all_incoherences.extend(repo_d_listings)
  all_incoherences.extend(repo_b_listings)
  all_incoherences.sort(key=lambda listing: listing.name)
  for listing in all_incoherences:
    listing_str = gordion.Tree.list_url(listing)
    expected_header += red(listing_str + "\n")
  expected = expected_header + "\n" + expected
  assert expected == gordion.app.status.terminal_status(tree_a)


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


def test_branch_ahead(tree_a):
  """
  Verifies situations:
    10. (ahead)
    2. Child branch is default branch, while root branch is not available.
       (All children are default branch, and still green)
  """
  original_tag = green(":" + tree_a.repo.handle.head.commit.hexsha[0:7])
  tree_a.repo.handle.index.commit("Empty commit for test_branch_ahead")
  expected = NOMINAL_STATUS.replace(green('test_status'),
                                    green('test_status') + yellow('(ahead)'))
  expected = expected.replace(original_tag,
                              green(":" + tree_a.repo.handle.head.commit.hexsha[0:7]))

  assert expected == gordion.app.status.terminal_status(tree_a)


def test_wrong_tracking_branch(tree_a):
  """
  Verifies situations:
    6. Child is different branch while default branch is available.
    9. (default branch?)
    11. (wrong tracking branch)
  """
  repo_d = gordion.Workspace().get_repository('gordion_demo_d')
  repo_d.handle.git.checkout('-b', 'different_branch')
  repo_d.handle.active_branch.set_tracking_branch(repo_d.handle.remotes['origin'].refs['develop'])
  expected = replace_i(NOMINAL_STATUS,
                       green('develop'),
                       yellow('different_branch') + yellow('(develop?, wrong tracking branch)'), 2)

  assert expected == gordion.app.status.terminal_status(tree_a)


def test_child_branch_is_root_branch(tree_a):
  """
  Verifies situations:
    12. (untracked)
    1. Child same as root branch.
  """
  tree_a.repo.handle.git.checkout('-b', 'root_branch')
  repo_b = gordion.Workspace().get_repository('gordion_demo_b')
  repo_b.handle.git.checkout('-b', 'root_branch')
  expected = NOMINAL_STATUS.replace(green('test_status'),
                                    green('root_branch') + yellow('(untracked)'))
  expected = replace_i(expected,
                       green('develop'),
                       green('root_branch') + yellow('(untracked)'), 0)

  assert expected == gordion.app.status.terminal_status(tree_a)


def test_child_default_root_available(tree_a):
  """
  Verifies situations:
    4. Child is default branch while root branch is available.
    8. (root branch?)
  """
  tree_a.repo.handle.git.checkout('-b', 'root_branch')
  repo_b = gordion.Workspace().get_repository('gordion_demo_b')
  repo_b.handle.git.checkout('-b', 'root_branch')
  repo_b.handle.branches['develop'].checkout()
  expected = NOMINAL_STATUS.replace(green('test_status'),
                                    green('root_branch') + yellow('(untracked)'))
  expected = replace_i(expected,
                       green('develop'),
                       yellow('develop') + yellow('(root_branch?)'), 0)
  assert expected == gordion.app.status.terminal_status(tree_a)


def test_child_different_root_available(tree_a):
  """
  Verifies situations:
    5. Child is different branch while root branch is available.
  """
  tree_a.repo.handle.git.checkout('-b', 'root_branch')
  repo_b = gordion.Workspace().get_repository('gordion_demo_b')
  repo_b.handle.git.checkout('-b', 'root_branch')
  repo_b.handle.git.checkout('-b', 'different_branch')
  expected = NOMINAL_STATUS.replace(green('test_status'),
                                    green('root_branch') + yellow('(untracked)'))
  expected = replace_i(expected,
                       green('develop'),
                       yellow('different_branch') + yellow('(root_branch?, untracked)'), 0)
  assert expected == gordion.app.status.terminal_status(tree_a)


def test_child_detached_root_available(tree_a):
  """
  Verifies situations:
    7. Child is DETACHED while root or default branch is available.
  """
  repo_d = gordion.Workspace().get_repository('gordion_demo_d')
  repo_d.handle.git.checkout(repo_d.handle.head.commit)
  expected = replace_i(NOMINAL_STATUS,
                       green('develop'),
                       yellow('DETACHED HEAD') + yellow('(develop?)'), 2)
  assert expected == gordion.app.status.terminal_status(tree_a)


def test_child_detached_green(tree_a):
  """
  Verifies situations:
    3. Child is DETACHED and root/default branches are not available.
    13. (unsaved)
  """
  # Make a commit to demoC while detached. The default branch is not available at this commit,
  # so 'DETACHED HEAD' is green.
  repo_d = gordion.Workspace().get_repository('gordion_demo_d')
  original_commit = repo_d.handle.head.commit.hexsha
  repo_d.handle.git.checkout(repo_d.handle.head.commit)
  repo_d.handle.index.commit("Empty commit for test_child_detached_green")
  expected = replace_i(NOMINAL_STATUS,
                       green('develop'),
                       green('DETACHED HEAD') + yellow('(unsaved)'), 2)
  expected = expected.replace(green(':' + original_commit[0:7]),
                              red(':' + repo_d.handle.head.commit.hexsha[0:7]))
  assert expected == gordion.app.status.terminal_status(tree_a)
