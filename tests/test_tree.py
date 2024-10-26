# Tests the gordion.Tree interface. A Tree has a gordion.yaml file and recursively manages children.
# In particular, we are interested in testing the behavior of the "diamond" situation:
#
# Repository A lists Repository B and C. B and C both list D.
#
#   A
#  / \
# B   C
#  \ /
#   D

import os
import gordion
import pytest
from tests.conftest import recursive_git_blast


# =================================================================================================
# Fixtures

@pytest.fixture
def tree_a(repository_a):
  """
  This puts the gordion.Tree session object back into a well-known state for each test case.
  """
  # Setup
  #
  # Set the object to a known commit on the develop branch.
  tag = 'c9da3e67006cbb03b6810d2e5b8effebb0f0b674'
  branch_name = 'develop'

  # Set the target branch/commit.
  tree_a = gordion.Tree(repository_a)
  tree_a.update(tag, branch_name, force=True)

  yield tree_a

  # Cleanup.
  recursive_git_blast(tree_a.repo.path)

  # Update to our known commit.
  tree_a.update(tag, branch_name, force=True)


# =================================================================================================
# Tests

def test_same_repo_different_tag(tree_a):
  """
  Verifies update will error if two of the same repository reference have different tags.
  """

  repo_a = tree_a.repo
  repo_b = gordion.Workspace().get_repository('gordion_demo_b')
  repo_d = gordion.Workspace().get_repository('gordion_demo_d')

  # Add a commit to repository D.
  repo_d.handle.git.commit(
      '-m',
      "Empty commit for test_same_demo_different_tag",
      allow_empty=True)

  # Make B point to D's new commit but not C.
  repo_b.yeditor.write_repository_tag('gordion_demo_d', repo_d.handle.head.commit.hexsha)
  repo_b.handle.git.add(os.path.join(repo_b.path, 'gordion.yaml'))
  repo_b.handle.git.commit('-m', "Point to latest D")
  repo_a.yeditor.write_repository_tag('gordion_demo_b', repo_b.handle.head.commit.hexsha)
  repo_a.handle.git.add(os.path.join(repo_a.path, 'gordion.yaml'))
  repo_a.handle.git.commit('-m', "Point to latest B")

  # Now update, it should raise error, tag mismatch.
  with pytest.raises(gordion.UpdateSameRepoDifferentTagError) as context:
    tree_a.update(repo_a.handle.head.commit.hexsha, "develop")

  # Verify the exception.
  listings, _ = tree_a.listings(name=repo_d.name, url=repo_d.url)
  expected = gordion.UpdateSameRepoDifferentTagError(repo_d.path, listings)
  assert str(context.value) == str(expected)


def test_different_name_same_url(tree_a):
  """
  Verifies update will error if a repository with a different name is listed with the same url.
  """

  with pytest.raises(gordion.UpdateDifferentNameSameUrlError) as context:
    tree_a.update("aef5ce0b9c580675178e45f230df3c826f3a7e87", "test_different_name_same_url")

  repo_d = gordion.Workspace().get_repository('gordion_demo_d')
  listings, _ = tree_a.listings(name=None, url=repo_d.url)
  expected = gordion.UpdateDifferentNameSameUrlError('gordion_demo_d_different_name', listings)
  assert str(context.value) == str(expected)


def test_same_name_different_url(tree_a):
  """
  Verifies update will error if a repository with the same name is listed with a different url.
  """

  with pytest.raises(gordion.UpdateSameNameDifferentUrlError) as context:
    tree_a.update('e052034df520cb2c07026a62df1cd0d4d236e7c1', "test_same_name_different_url")

  listings, _ = tree_a.listings(name='gordion_demo_d', url=None)
  expected = gordion.UpdateSameNameDifferentUrlError('gordion_demo_d', listings)
  assert str(context.value) == str(expected)


def test_non_default_path(demo_a):
  """
  Verifies that a repository can be cloned at a non-default gpath. And that the non-default path can
  be cleaned up if it is moved back.
  """

  # Put repo B at in a non-default path, update and verify it exists, and the origional one has been
  # removed.
  demo_a.yeditor.yaml_data['repositories']['gordion_demo_b']['path'] = '/heyo/gordion_demo_b'
  demo_a.yeditor.save()
  demo_a.update(demo_a.handle.head.commit.hexsha, "develop")
  demo_b = demo_a.children['gordion_demo_b']
  assert demo_b.path == os.path.join(demo_a.path, 'gordion', 'heyo', 'gordion_demo_b')
  assert demo_b.handle.head.commit.hexsha == demo_a.yeditor.read_repository_tag('gordion_demo_b')
  assert not os.path.isdir(os.path.join(demo_a.path, 'gordion', 'gordion_demo_b'))

  # Put repository back to default path, verify old path is deleted.
  demo_a.yeditor.yaml_data['repositories']['gordion_demo_b']['path'] = '/gordion_demo_b'
  demo_a.yeditor.save()
  demo_a.update(demo_a.handle.head.commit.hexsha, "develop")
  demo_b = demo_a.children['gordion_demo_b']
  assert demo_b.path == os.path.join(demo_a.path, 'gordion', 'gordion_demo_b')
  assert demo_b.handle.head.commit.hexsha == demo_a.yeditor.read_repository_tag('gordion_demo_b')
  assert not os.path.isdir(os.path.join(demo_a.path, 'gordion', 'heyo'))


def test_unsafe_remove_dirty(demo_a):
  """
  Verifies that an error is generated if the update will attempt to cleanup(remove) a repository
  that has dirty changes.
  """

  # Make the demo_c dirty by adding an empty file.
  demo_c = demo_a.children['gordion_demo_c']
  touchfile = os.path.join(demo_c.path, 'touch.txt')
  with open(touchfile, 'w'):
    pass

  assert demo_c.handle.is_dirty(untracked_files=True)

  with pytest.raises(gordion.UnsafeRemoveDirty) as context:
    demo_a.update('55f619c7af1cdc3ed13487c3aab050b492e655eb', 'test_unsafe_remove_dirty')

  expected = gordion.UnsafeRemoveDirty(demo_c.path)
  assert str(context.value) == str(expected)


def test_unsafe_remove_local_branch_no_tracking_branch(demo_a):
  """
  Verifies that an error is generated if the update attempts to delete a repository that has local
  branches without a remote tracking branch.
  """

  # Checkout a new local branch on repo B.
  demo_b = demo_a.children['gordion_demo_b']
  new_branch = demo_b.handle.create_head("new_branch")
  new_branch.checkout()

  # Remove repo B from Repo A's yaml file.
  del demo_a.yeditor.yaml_data['repositories']['gordion_demo_b']
  demo_a.yeditor.save()

  # Verify update errors because we are deleting the repository and the local branch does not have a
  # tracking branch.
  with pytest.raises(gordion.UnsafeRemoveLocalBranchNoTrackingBranch) as context:
    demo_a.update(demo_a.handle.head.commit.hexsha, "develop")
  expected = gordion.UnsafeRemoveLocalBranchNoTrackingBranch(demo_b.path, "new_branch")
  assert str(context.value) == str(expected)


def test_unsafe_remove_local_branch_ahead(demo_a):
  """
  Verifies that an error is generated if the update attempts to delete a repository that has local
  branches that are ahead of their remote tracking branches.
  """

  # Remove repo B from Repo A's yaml file.
  del demo_a.yeditor.yaml_data['repositories']['gordion_demo_b']
  demo_a.yeditor.save()

  # Now checkout a branch on Repo B that has a remote tracking branch.
  demo_b = demo_a.children['gordion_demo_b']
  demo_b.handle.git.checkout('-b', 'test_unsafe_remove_local_branch_unsaved',
                             'origin/test_unsafe_remove_local_branch_unsaved')
  demo_b.handle.git.commit('-m', "Empty commit for test_unsafe_remove_local_branch_unsaved",
                           allow_empty=True)

  # Verify update errors because we are deleting the repository and the local branch has an unsaved
  # commit.
  with pytest.raises(gordion.UnsafeRemoveLocalBranchAhead) as context:
    demo_a.update(demo_a.handle.head.commit.hexsha, "develop")
  expected = gordion.UnsafeRemoveLocalBranchAhead(demo_b.path,
                                                  "test_unsafe_remove_local_branch_unsaved",
                                                  "origin/test_unsafe_remove_local_branch_unsaved",
                                                  1)
  assert str(context.value) == str(expected)


def test_unsafe_remove_stashes(demo_a):
  """
  Verifies that an error is generated if the update attempts to delete a repository that has
  stashes.
  """

  # Remove repo B from Repo A's yaml file.
  del demo_a.yeditor.yaml_data['repositories']['gordion_demo_b']
  demo_a.yeditor.save()

  # Create a stash on repo B.
  demo_b = demo_a.children['gordion_demo_b']
  file_path = os.path.join(demo_b.path, 'README.md')
  with open(file_path, 'w') as file:
    file.write('test_unsafe_remove_stashes wrote this.\n')
  demo_b.handle.git.stash("save")

  # Verify update errors because we are deleting the repository while it has stashes.
  stashes = demo_b.handle.git.stash("list")
  with pytest.raises(gordion.UnsafeRemoveStashes) as context:
    demo_a.update(demo_a.handle.head.commit.hexsha, "develop")
  expected = gordion.UnsafeRemoveStashes(demo_b.path, stashes)
  assert str(context.value) == str(expected)


def test_name_path_mismatch(demo_a):
  """
  Verifies that an error is generated if the optional path property does not match the repository
  name.
  """
  demo_a.yeditor.yaml_data['repositories']['gordion_demo_b']['path'] = '/subdir/not_gordion_demo_b'
  demo_a.yeditor.save()
  with pytest.raises(gordion.BadRepositoryNamePathMismach) as context:
    demo_a.update(demo_a.handle.head.commit.hexsha, "develop")

  expected = gordion.BadRepositoryNamePathMismach(demo_a.yeditor.fullfile,
                                                  '/subdir/not_gordion_demo_b', 'gordion_demo_b')
  assert str(context.value) == str(expected)


def test_dangling_commit(demo_a):
  """
  Verifies update will error if a child target commit is dangling.
  """

  # Create a dangling commit by committing something, then deleting it. First make an arbitrary
  # change to repo B.
  demo_b = demo_a.children['gordion_demo_b']
  demo_b.handle.git.commit('-m', "Empty commit for test_dangling_commit", allow_empty=True)
  empty_commit = demo_b.handle.head.commit

  # Now delete the commit (checkout HEAD~1).
  demo_b.handle.head.reset('HEAD~1', index=True, working_tree=True)

  # Now add the empty commit to the parent gordion.yaml.
  demo_a.yeditor.write_repository_tag('gordion_demo_b', empty_commit.hexsha)
  demo_a.yeditor.save()

  # Now update should error commit is dangling ehh.
  with pytest.raises(gordion.DanglingCommitError) as context:
    demo_a.update(demo_a.handle.head.commit.hexsha, "develop")

  expected = gordion.DanglingCommitError(demo_b.path, empty_commit.hexsha)
  assert str(context.value) == str(expected)
