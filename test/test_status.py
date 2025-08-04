# Verifies the gordion -s behavior

import gordion
from gordion.utils import green, bold_green, bold_blue, red, bold_red, yellow
from gordion.utils import replace_i
import pytest
from test.conftest import REPOS_DIR
import os
import shutil


# =================================================================================================
# Fixtures

@pytest.fixture
def tree_a_local(tree_a_local):
  """
  This puts tree_a session object back into a well-known state for each test case.
  """
  # Setup
  #
  # Set the object to a known commit and branch.
  tag = '082abea'
  branch_name = 'test_status'

  # Set the target branch/commit.
  tree_a_local.update(tag, branch_name, force=True)

  yield tree_a_local


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


@pytest.fixture
def tmp1():
  """
  Creates a tmp1 folder in the REPOS_DIR and then deletes it.
  """
  tmp1 = os.path.join(REPOS_DIR, 'tmp1')
  os.mkdir(tmp1)

  yield tmp1

  shutil.rmtree(tmp1, ignore_errors=True)
  gordion.Workspace().discover_repositories()


# =================================================================================================
# Nominal status test

NOMINAL_STATUS = \
    f"""{bold_blue('repos')}
├──{bold_green('gordion_demo_a*')} {green('test_status')}{green(':082abea')}
├──{bold_green('gordion_demo_b')} {green('develop')}{green(':fe4fd4d')}
├──{bold_green('gordion_demo_c')} {green('develop')}{green(':1a8f7fe')}
└──{bold_green('gordion_demo_d')} {green('develop')}{green(':c516fff')}"""


def test_nominal_status(tree_a_local):
  """
  Verifies the nominal status string (all green).
  """
  assert NOMINAL_STATUS == gordion.app.status.terminal_status(tree_a_local)


# =================================================================================================
# Tests for commit status

def test_wrong_commit(tree_a_local):
  """
  Verifies the commit will appear RED if it does not match the parent gordion.yaml file.
  """

  # In demoC, checkout HEAD~1
  repo_c = gordion.Workspace().get_repository('gordion_demo_c')
  repo_c.handle.head.reset('HEAD~1', index=True, working_tree=True)

  # Get the expected status string.
  demo_c_new_commit = repo_c.handle.head.commit.hexsha[:7]
  expected = NOMINAL_STATUS.replace(green(':1a8f7fe'), red(f":{demo_c_new_commit}"))
  assert expected == gordion.app.status.terminal_status(tree_a_local)


def test_child_mismatch(tree_a_local):
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
  b_commit = repo_b.handle.head.commit.hexsha
  expected = NOMINAL_STATUS.replace(green(f':{b_commit[0:7]}'),
                                    green(f':{b_commit[0:7]}') + f"\n│   {red('M')} gordion.yaml\n│  ")
  d_commit = repo_d.handle.head.commit.hexsha
  expected = expected.replace(green(f':{d_commit[0:7]}'),
                              red(f':{d_commit[0:7]}') + " " + red('(TAG INCOHERENCE)'))
  b_commit = repo_b.handle.head.commit.hexsha
  expected = expected.replace(green(f':{b_commit[0:7]}'),
                              green(f':{b_commit[0:7]}') + yellow('-dirty'))

  expected_header = bold_red("\nTag Incoherences:\n")
  repo_b_listings, _ = tree_a_local.listings(name='gordion_demo_d', url=None)
  for listing in repo_b_listings:
    listing_str = gordion.Tree.format_listing_tag(listing)
    expected_header += red(listing_str + "\n")
  expected = expected_header + "\n" + expected

  assert expected == gordion.app.status.terminal_status(tree_a_local)


def test_conflicted(tree_a_local):
  """
  Verifies NAME_CONFLICTED, URL_CONFLICTED, and NOT_FOUND.
  """
  # Change demoC's listing of "gordion_demo_d"s URL to "gordion_demo_b"s URL.
  repo_c = gordion.Workspace().get_repository('gordion_demo_c')
  b_url = tree_a_local.repo.yeditor.yaml_data['repositories']['gordion_demo_b']['url']
  repo_c.yeditor.yaml_data['repositories']['gordion_demo_d']['url'] = b_url
  repo_c.yeditor.save()

  # Verify.
  # demoC commit is dirty.
  c_commit = repo_c.handle.head.commit.hexsha
  expected = NOMINAL_STATUS.replace(green(f':{c_commit[0:7]}'),
                                    green(f':{c_commit[0:7]}') +
                                    yellow("-dirty") + f"\n│   {red('M')} gordion.yaml\n│  ")
  # demoB is NAME_CONFLICTED. There are two listings that have demoB's URL, but they have different
  # names.
  repo_b = gordion.Workspace().get_repository('gordion_demo_b')
  b_commit = repo_b.handle.head.commit.hexsha
  expected = expected.replace(green(f':{b_commit[0:7]}'),
                              green(f':{b_commit[0:7]}') + " " + red("(NAME CONFLICTED)"))
  # demoD is URL_CONFLICTED. There are two listings of demoD, with different URLs.
  repo_d = gordion.Workspace().get_repository('gordion_demo_d')
  d_commit = repo_d.handle.head.commit.hexsha
  expected = expected.replace(green(f':{d_commit[0:7]}'),
                              green(f':{d_commit[0:7]}') + " " + red("(URL CONFLICTED)"))

  # The Not Found will be the demoD listing with demoBs url.
  expected_header = bold_red("\nNot Found:\n")
  not_found_listings, _ = tree_a_local.listings(name='gordion_demo_d', url=b_url)
  assert len(not_found_listings) == 1
  listing_str = gordion.Tree.format_listing_url(not_found_listings[0])
  expected_header += red(listing_str + "\n")

  # The URL Incoherences (all demoD, and demoB listings)
  expected_header += bold_red("\nURL Incoherences:\n")
  repo_d_listings, _ = tree_a_local.listings(name='gordion_demo_d', url=None)
  repo_b_listings, _ = tree_a_local.listings(name='gordion_demo_b', url=None)
  all_incoherences = []
  all_incoherences.extend(repo_d_listings)
  all_incoherences.extend(repo_b_listings)
  all_incoherences.sort(key=lambda listing: listing.name)
  for listing in all_incoherences:
    listing_str = gordion.Tree.format_listing_url(listing)
    expected_header += red(listing_str + "\n")
  expected = expected_header + "\n" + expected
  assert expected == gordion.app.status.terminal_status(tree_a_local)


def test_duplicate(tree_a_local, tmp1):
  """
  Verifies HAS_DUPLICATE
  """
  # Make a duplicate in the ./dependencies/tmp1 directory.
  repo_b = gordion.Workspace().get_repository('gordion_demo_b')
  duplicate_path = os.path.join(tmp1, 'gordion_demo_x')
  shutil.copytree(repo_b.path, duplicate_path)
  duplciate = gordion.Repository(duplicate_path)

  # repo B becomes red and shows HAS_DUPLICATE.
  expected = NOMINAL_STATUS.replace(bold_green('gordion_demo_b'), bold_red('gordion_demo_b'))
  b_commit = repo_b.handle.head.commit.hexsha
  expected = expected.replace(green(f':{b_commit[0:7]}'),
                              green(f':{b_commit[0:7]}') + " " + red("(HAS DUPLICATE)"))

  # Duplicates header.
  expected_header = bold_red("\nDuplicates:\n")
  expected_header += red(f"* {repo_b.path} ({repo_b.url})\n")
  expected_header += red(f"* {duplciate.path} ({duplciate.url})\n")
  expected = expected_header + "\n" + expected
  assert expected == gordion.app.status.terminal_status(tree_a_local)


# flake8: noqa
EXPECTED_WRONG_PATH_STATUS = \
    f"""{bold_blue('repos')}
├──{bold_green('gordion_demo_a*')} {green('test_status')}{green(':082abea')}
├──{bold_green('gordion_demo_c')} {green('develop')}{green(':1a8f7fe')}
├──{bold_green('gordion_demo_d')} {green('develop')}{green(':c516fff')}
└──{bold_blue('tmp1')}
    └──{bold_green('gordion_demo_b')} {green('develop')}{green(':fe4fd4d')}"""


def test_wrong_path(tree_a_local, tmp1):
  """
  Verifies WRONG_PATH
  """
  # Make a duplicate in the ./dependencies/tmp1 directory and delete demo_b
  repo_b = gordion.Workspace().get_repository('gordion_demo_b')
  wrong_path = os.path.join(tmp1, 'gordion_demo_b')
  shutil.copytree(repo_b.path, wrong_path)
  gordion.Repository(wrong_path)
  gordion.Repository.safe_delete(repo_b.path)

  # Verify
  assert EXPECTED_WRONG_PATH_STATUS == gordion.app.status.terminal_status(tree_a_local)

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


def test_branch_ahead(tree_a_local):
  """
  Verifies situations:
    10. (ahead)
    2. Child branch is default branch, while root branch is not available.
       (All children are default branch, and still green)
  """
  original_tag = green(f':{tree_a_local.repo.handle.head.commit.hexsha[0:7]}')
  tree_a_local.repo.handle.index.commit("Empty commit for test_branch_ahead")
  expected = NOMINAL_STATUS.replace(green('test_status'),
                                    green('test_status') + yellow('(ahead)'))
  expected = expected.replace(original_tag,
                              green(f':{tree_a_local.repo.handle.head.commit.hexsha[0:7]}'))

  assert expected == gordion.app.status.terminal_status(tree_a_local)


def test_wrong_tracking_branch(tree_a_local):
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

  assert expected == gordion.app.status.terminal_status(tree_a_local)


def test_child_branch_is_root_branch(tree_a_local):
  """
  Verifies situations:
    12. (untracked)
    1. Child same as root branch.
  """
  tree_a_local.repo.handle.git.checkout('-b', 'root_branch')
  repo_b = gordion.Workspace().get_repository('gordion_demo_b')
  repo_b.handle.git.checkout('-b', 'root_branch')
  expected = NOMINAL_STATUS.replace(green('test_status'),
                                    green('root_branch') + yellow('(untracked)'))
  expected = replace_i(expected,
                       green('develop'),
                       green('root_branch') + yellow('(untracked)'), 0)

  assert expected == gordion.app.status.terminal_status(tree_a_local)


def test_child_default_root_available(tree_a_local):
  """
  Verifies situations:
    4. Child is default branch while root branch is available.
    8. (root branch?)
  """
  tree_a_local.repo.handle.git.checkout('-b', 'root_branch')
  repo_b = gordion.Workspace().get_repository('gordion_demo_b')
  repo_b.handle.git.checkout('-b', 'root_branch')
  repo_b.handle.branches['develop'].checkout()
  expected = NOMINAL_STATUS.replace(green('test_status'),
                                    green('root_branch') + yellow('(untracked)'))
  expected = replace_i(expected,
                       green('develop'),
                       yellow('develop') + yellow('(root_branch?)'), 0)
  assert expected == gordion.app.status.terminal_status(tree_a_local)


def test_child_different_root_available(tree_a_local):
  """
  Verifies situations:
    5. Child is different branch while root branch is available.
  """
  tree_a_local.repo.handle.git.checkout('-b', 'root_branch')
  repo_b = gordion.Workspace().get_repository('gordion_demo_b')
  repo_b.handle.git.checkout('-b', 'root_branch')
  repo_b.handle.git.checkout('-b', 'different_branch')
  expected = NOMINAL_STATUS.replace(green('test_status'),
                                    green('root_branch') + yellow('(untracked)'))
  expected = replace_i(expected,
                       green('develop'),
                       yellow('different_branch') + yellow('(root_branch?, untracked)'), 0)
  assert expected == gordion.app.status.terminal_status(tree_a_local)


def test_child_detached_root_available(tree_a_local):
  """
  Verifies situations:
    7. Child is DETACHED while root or default branch is available.
  """
  repo_d = gordion.Workspace().get_repository('gordion_demo_d')
  repo_d.handle.git.checkout(repo_d.handle.head.commit)
  expected = replace_i(NOMINAL_STATUS,
                       green('develop'),
                       yellow('DETACHED HEAD') + yellow('(develop?)'), 2)
  assert expected == gordion.app.status.terminal_status(tree_a_local)


def test_child_detached_green(tree_a_local):
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
  assert expected == gordion.app.status.terminal_status(tree_a_local)


def test_cache_out_of_sync_missing_repo(tree_a):
  """
  Verifies that (out of sync) appears when a repository is missing from cache.
  """
  # Delete a dependency repository from the cache
  workspace = gordion.Workspace()
  repo_b = workspace.get_repository('gordion_demo_b')
  assert workspace.is_dependency(repo_b.path), f"Expected {repo_b.path} to be in cache"
  
  # Use safe_delete to properly remove the repository
  gordion.Repository.safe_delete(repo_b.path, force=True)
  
  # The status should show (out of sync) next to repos folder
  status = gordion.app.status.terminal_status(tree_a)
  
  # Verify the Not Found error is shown
  assert bold_red("\nNot Found:\n") in status
  assert "gordion_demo_b" in status
  
  # Verify (out of sync) appears next to the workspace folder
  assert red("  (out of sync)") in status
  # Find the line with the workspace folder - it may not be the first line due to errors
  lines = status.splitlines()
  workspace_line = None
  for line in lines:
    if bold_blue('repos') in line:
      workspace_line = line
      break
  assert workspace_line is not None, "Could not find workspace folder line"
  assert red("  (out of sync)") in workspace_line


def test_cache_out_of_sync_wrong_commit(tree_a):
  """
  Verifies that (out of sync) appears when a cache repository has wrong commit.
  """
  # Change a dependency repository to wrong commit
  workspace = gordion.Workspace()
  repo_b = workspace.get_repository('gordion_demo_b')
  assert workspace.is_dependency(repo_b.path), f"Expected {repo_b.path} to be in cache"
  
  # Checkout a different commit
  repo_b.handle.head.reset('HEAD~1', index=True, working_tree=True)
  
  # The status should show (out of sync) next to repos folder
  status = gordion.app.status.terminal_status(tree_a)
  assert red("  (out of sync)") in status


def test_dirty_cached_repository(tree_a):
  """
  Verifies that an error is shown when a cached repository has uncommitted changes.
  """
  # Make changes in a cached repository
  workspace = gordion.Workspace()
  repo_b = workspace.get_repository('gordion_demo_b')
  assert workspace.is_dependency(repo_b.path), f"Expected {repo_b.path} to be in cache"
  
  # Create a new file to make the repository dirty
  test_file = os.path.join(repo_b.path, 'test_dirty.txt')
  with open(test_file, 'w') as f:
    f.write('This should not be allowed in cached repositories!')
  
  # The status should show the dirty cached repository error
  status = gordion.app.status.terminal_status(tree_a)
  
  # Verify the error header and message are shown
  assert bold_red("\nDirty Cached Repositories:\n") in status
  assert red("(Changes not allowed in cached repositories!)\n") in status
  assert red(f"* {repo_b.path}\n") in status
  
  # Verify (out of sync) appears next to the workspace folder
  assert red("  (out of sync)") in status
  # Find the line with the workspace folder - it should be after the error header
  lines = status.splitlines()
  workspace_line = None
  for line in lines:
    if bold_blue('repos') in line:
      workspace_line = line
      break
  assert workspace_line is not None, "Could not find workspace folder line"
  assert red("  (out of sync)") in workspace_line
  
  # Clean up
  os.remove(test_file)


def test_status_show_cache_flag(tree_a):
  """
  Verifies that the --cache (-c) flag shows the dependencies cache directory.
  """
  workspace = gordion.Workspace()
  
  # Regular status (without cache flag)
  regular_status = gordion.app.status.terminal_status(tree_a, verbose=False, show_cache=False)
  
  # Status with cache flag
  cache_status = gordion.app.status.terminal_status(tree_a, verbose=False, show_cache=True)
  
  # The cache status should be longer (includes cache directory)
  assert len(cache_status) > len(regular_status)
  
  # The cache status should contain the encoded cache directory name
  # The cache directory appears as a base64 encoded name in the output
  # The encoding is based on the root repository path, not the workspace path
  import base64
  root_repo_path = workspace.root_repository.path
  encoded_name = base64.b64encode(root_repo_path.encode()).decode().replace('/', '').rstrip('=')
  assert encoded_name in cache_status
  
  # The regular status should NOT contain the encoded cache directory
  assert encoded_name not in regular_status
  
  # Verify cached repositories appear when cache flag is set
  repo_b = workspace.get_repository('gordion_demo_b')
  if workspace.is_dependency(repo_b.path):
    assert repo_b.name in cache_status
    # In regular status, cached repos should not appear
    assert repo_b.path not in regular_status


