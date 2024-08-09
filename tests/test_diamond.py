import os
import gordion
import pytest
from tests.conftest import recursive_git_blast


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

  # Cleanup.
  recursive_git_blast(repo_a_session.path)

  # Update to our known commit.
  repo_a_session.update(tag, branch_name, force=True)


def test_same_repo_different_tag(repo_a):
  """
  Verifies update will error if two of the same repository reference have different tags.
  """

  # Add a commit to repository D.
  repo_d = repo_a.children['gordion_demo_b'].children['gordion_demo_d']
  repo_d.handle.git.commit('-m', "Empty commit for test_same_repo_different_tag", allow_empty=True)

  # Make B point to D's new commit but not C.
  repo_b = repo_a.children['gordion_demo_b']
  repo_b.yeditor.write_repository_tag('gordion_demo_d', repo_d.handle.head.commit.hexsha)
  repo_b.handle.git.add(os.path.join(repo_b.path, 'gordion.yaml'))
  repo_b.handle.git.commit('-m', "Point to latest D")
  repo_a.yeditor.write_repository_tag('gordion_demo_b', repo_b.handle.head.commit.hexsha)
  repo_a.handle.git.add(os.path.join(repo_a.path, 'gordion.yaml'))
  repo_a.handle.git.commit('-m', "Point to latest B")

  # Save some information before the update.
  b_ref_d = repo_a.children['gordion_demo_b'].children['gordion_demo_d']
  b_ref_d_tag = repo_a.children['gordion_demo_b'].yeditor.read_repository_tag('gordion_demo_d')
  c_ref_d = repo_a.children['gordion_demo_c'].children['gordion_demo_d']
  c_ref_d_tag = repo_a.children['gordion_demo_c'].yeditor.read_repository_tag('gordion_demo_d')

  # Now update, it should raise error, tag mismatch.
  with pytest.raises(gordion.UpdateSameRepoDifferentTagError) as context:
    repo_a.update(repo_a.handle.head.commit.hexsha, "develop")

  # Verify the exception.
  expected = gordion.UpdateSameRepoDifferentTagError(c_ref_d.path, c_ref_d._listed_path(),
                                                     c_ref_d_tag, b_ref_d._listed_path(),
                                                     b_ref_d_tag)
  assert str(context.value) == str(expected)


def test_same_repo_different_path(repo_a):
  """
  Verifies update will error if the same repository is attempted to be cloned at different paths.
  """

  repo_b = repo_a.children['gordion_demo_b']
  repo_c = repo_a.children['gordion_demo_c']

  with pytest.raises(gordion.UpdateSameRepoDifferentPathError) as context:
    repo_a.update("8659bcd4e68ac3e0c0e2f55e6bd03296007a0a47", "test_duplicate_repo_path_mismatch")

  expected = gordion.UpdateSameRepoDifferentPathError(repo_c.path, repo_b.path, repo_b.url)
  assert str(context.value) == str(expected)


def test_different_repo_same_path(repo_a):
  """
  Verifies that an error is generated if a different repository is attempted to be cloned to the
  same gordion path.
  """

  with pytest.raises(gordion.UpdateDifferentRepoSamePathError) as context:
    repo_a.update('92d294df03a6bbf7ef43b60a0255adca08671328', "test_different_repo_same_path")

  repo_b = repo_a.children['gordion_demo_b']

  target_path = os.path.join(repo_a.path, 'gordion', 'gordion_demo_b')
  target_url = 'https://github.com/jacob-heathorn/gordion_demo_d.git'
  expected = gordion.UpdateDifferentRepoSamePathError(target_path, target_url, repo_b.path,
                                                      repo_b.url)
  assert str(context.value) == str(expected)


def test_non_default_path(repo_a):
  """
  Verifies that a repository can be cloned at a non-default gpath. And that the non-default path can
  be cleaned up if it is moved back.
  """

  # Put repo B at in a non-default path, update and verify it exists, and the origional one has been
  # removed.
  repo_a.yeditor.yaml_data['repositories']['gordion_demo_b']['path'] = '/heyo/gordion_demo_b'
  repo_a.yeditor.save()
  repo_a.update(repo_a.handle.head.commit.hexsha, "develop")
  repo_b = repo_a.children['gordion_demo_b']
  assert repo_b.path == os.path.join(repo_a.path, 'gordion', 'heyo', 'gordion_demo_b')
  assert repo_b.handle.head.commit.hexsha == repo_a.yeditor.read_repository_tag('gordion_demo_b')
  assert not os.path.isdir(os.path.join(repo_a.path, 'gordion', 'gordion_demo_b'))

  # Put repository back to default path, verify old path is deleted.
  repo_a.yeditor.yaml_data['repositories']['gordion_demo_b']['path'] = '/gordion_demo_b'
  repo_a.yeditor.save()
  repo_a.update(repo_a.handle.head.commit.hexsha, "develop")
  repo_b = repo_a.children['gordion_demo_b']
  assert repo_b.path == os.path.join(repo_a.path, 'gordion', 'gordion_demo_b')
  assert repo_b.handle.head.commit.hexsha == repo_a.yeditor.read_repository_tag('gordion_demo_b')
  assert not os.path.isdir(os.path.join(repo_a.path, 'gordion', 'heyo'))


def test_unsafe_remove_dirty(repo_a):
  """
  Verifies that an error is generated if the update will attempt to cleanup(remove) a repository
  that has dirty changes.
  """

  # Make the demo_c dirty by adding an empty file.
  repo_c = repo_a.children['gordion_demo_c']
  touchfile = os.path.join(repo_c.path, 'touch.txt')
  with open(touchfile, 'w'):
    pass

  assert repo_c.handle.is_dirty(untracked_files=True)

  with pytest.raises(gordion.UnsafeRemoveDirty) as context:
    repo_a.update('55f619c7af1cdc3ed13487c3aab050b492e655eb', 'test_unsafe_remove_dirty')

  expected = gordion.UnsafeRemoveDirty(repo_c.path)
  assert str(context.value) == str(expected)


def test_unsafe_remove_local_branch_no_tracking_branch(repo_a):
  """
  Verifies that an error is generated if the update attempts to delete a repository that has local
  branches without a remote tracking branch.
  """

  # Checkout a new local branch on repo B.
  repo_b = repo_a.children['gordion_demo_b']
  new_branch = repo_b.handle.create_head("new_branch")
  new_branch.checkout()

  # Remove repo B from Repo A's yaml file.
  del repo_a.yeditor.yaml_data['repositories']['gordion_demo_b']
  repo_a.yeditor.save()

  # Verify update errors because we are deleting the repository and the local branch does not have a
  # tracking branch.
  with pytest.raises(gordion.UnsafeRemoveLocalBranchNoTrackingBranch) as context:
    repo_a.update(repo_a.handle.head.commit.hexsha, "develop")
  expected = gordion.UnsafeRemoveLocalBranchNoTrackingBranch(repo_b.path, "new_branch")
  assert str(context.value) == str(expected)


def test_unsafe_remove_local_branch_ahead(repo_a):
  """
  Verifies that an error is generated if the update attempts to delete a repository that has local
  branches that are ahead of their remote tracking branches.
  """

  # Remove repo B from Repo A's yaml file.
  del repo_a.yeditor.yaml_data['repositories']['gordion_demo_b']
  repo_a.yeditor.save()

  # Now checkout a branch on Repo B that has a remote tracking branch.
  repo_b = repo_a.children['gordion_demo_b']
  repo_b.handle.git.checkout('-b', 'test_unsafe_remove_local_branch_unsaved',
                             'origin/test_unsafe_remove_local_branch_unsaved')
  repo_b.handle.git.commit('-m', "Empty commit for test_unsafe_remove_local_branch_unsaved",
                           allow_empty=True)

  # Verify update errors because we are deleting the repository and the local branch has an unsaved
  # commit.
  with pytest.raises(gordion.UnsafeRemoveLocalBranchAhead) as context:
    repo_a.update(repo_a.handle.head.commit.hexsha, "develop")
  expected = gordion.UnsafeRemoveLocalBranchAhead(repo_b.path,
                                                  "test_unsafe_remove_local_branch_unsaved",
                                                  "origin/test_unsafe_remove_local_branch_unsaved",
                                                  1)
  assert str(context.value) == str(expected)


def test_unsafe_remove_stashes(repo_a):
  """
  Verifies that an error is generated if the update attempts to delete a repository that has
  stashes.
  """

  # Remove repo B from Repo A's yaml file.
  del repo_a.yeditor.yaml_data['repositories']['gordion_demo_b']
  repo_a.yeditor.save()

  # Create a stash on repo B.
  repo_b = repo_a.children['gordion_demo_b']
  file_path = os.path.join(repo_b.path, 'README.md')
  with open(file_path, 'w') as file:
    file.write('test_unsafe_remove_stashes wrote this.\n')
  repo_b.handle.git.stash("save")

  # Verify update errors because we are deleting the repository while it has stashes.
  stashes = repo_b.handle.git.stash("list")
  with pytest.raises(gordion.UnsafeRemoveStashes) as context:
    repo_a.update(repo_a.handle.head.commit.hexsha, "develop")
  expected = gordion.UnsafeRemoveStashes(repo_b.path, stashes)
  assert str(context.value) == str(expected)


def test_name_path_mismatch(repo_a):
  """
  Verifies that an error is generated if the optional path property does not match the repository
  name.
  """
  repo_a.yeditor.yaml_data['repositories']['gordion_demo_b']['path'] = '/subdir/not_gordion_demo_b'
  repo_a.yeditor.save()
  with pytest.raises(gordion.BadRepositoryNamePathMismach) as context:
    repo_a.update(repo_a.handle.head.commit.hexsha, "develop")

  expected = gordion.BadRepositoryNamePathMismach(repo_a.yeditor.fullfile,
                                                  '/subdir/not_gordion_demo_b', 'gordion_demo_b')
  assert str(context.value) == str(expected)


def test_dangling_commit(repo_a):
  """
  Verifies update will error if a child target commit is dangling.
  """

  # Create a dangling commit by committing something, then deleting it. First make an arbitrary
  # change to repo B.
  repo_b = repo_a.children['gordion_demo_b']
  repo_b.handle.git.commit('-m', "Empty commit for test_dangling_commit", allow_empty=True)
  empty_commit = repo_b.handle.head.commit

  # Now delete the commit (checkout HEAD~1).
  repo_b.handle.head.reset('HEAD~1', index=True, working_tree=True)

  # Now add the empty commit to the parent gordion.yaml.
  repo_a.yeditor.write_repository_tag('gordion_demo_b', empty_commit.hexsha)
  repo_a.yeditor.save()

  # Now update should error commit is dangling ehh.
  with pytest.raises(gordion.DanglingCommitError) as context:
    repo_a.update(repo_a.handle.head.commit.hexsha, "develop")

  expected = gordion.DanglingCommitError(repo_b.path, empty_commit.hexsha)
  assert str(context.value) == str(expected)
