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


# =================================================================================================
# Tests

def test_same_repo_different_tag(tree_a: gordion.Tree):
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


def test_unsafe_remove_local_branch_no_tracking_branch(tree_a):
  """
  Verifies that an error is generated if the update attempts to delete a repository that has local
  branches without a remote tracking branch.
  """

  # Checkout a new local branch on repo B.
  repo_b = gordion.Workspace().get_repository('gordion_demo_b')
  new_branch = repo_b.handle.create_head("new_branch")
  new_branch.checkout()

  # Remove repo B from Repo A's yaml file.
  del tree_a.repo.yeditor.yaml_data['repositories']['gordion_demo_b']
  tree_a.repo.yeditor.save()

  # Verify update errors because we are deleting the repository and the local branch does not have a
  # tracking branch.
  with pytest.raises(gordion.UnsafeRemoveLocalBranchNoTrackingBranch) as context:
    tree_a.update(tree_a.repo.handle.head.commit.hexsha, "develop")
  expected = gordion.UnsafeRemoveLocalBranchNoTrackingBranch(repo_b.path, "new_branch")
  assert str(context.value) == str(expected)


def test_unsafe_remove_local_branch_ahead(tree_a):
  """
  Verifies that an error is generated if the update attempts to delete a repository that has local
  branches that are ahead of their remote tracking branches.
  """

  # Remove repo B from Repo A's yaml file.
  del tree_a.repo.yeditor.yaml_data['repositories']['gordion_demo_b']
  tree_a.repo.yeditor.save()

  # Now checkout a branch on Repo B that has a remote tracking branch.
  repo_b = gordion.Workspace().get_repository('gordion_demo_b')
  repo_b.handle.git.checkout('-b', 'test_unsafe_remove_local_branch_unsaved',
                             'origin/test_unsafe_remove_local_branch_unsaved')
  repo_b.handle.git.commit('-m', "Empty commit for test_unsafe_remove_local_branch_unsaved",
                           allow_empty=True)

  # Verify update errors because we are deleting the repository and the local branch has an unsaved
  # commit.
  with pytest.raises(gordion.UnsafeRemoveLocalBranchAhead) as context:
    tree_a.update(tree_a.repo.handle.head.commit.hexsha, "develop")
  expected = gordion.UnsafeRemoveLocalBranchAhead(repo_b.path,
                                                  "test_unsafe_remove_local_branch_unsaved",
                                                  "origin/test_unsafe_remove_local_branch_unsaved",
                                                  1)
  assert str(context.value) == str(expected)


def test_unsafe_remove_stashes(tree_a):
  """
  Verifies that an error is generated if the update attempts to delete a repository that has
  stashes.
  """

  # Remove repo B from Repo A's yaml file.
  del tree_a.repo.yeditor.yaml_data['repositories']['gordion_demo_b']
  tree_a.repo.yeditor.save()

  # Create a stash on repo B.
  repo_b = gordion.Workspace().get_repository('gordion_demo_b')
  file_path = os.path.join(repo_b.path, 'README.md')
  with open(file_path, 'w') as file:
    file.write('test_unsafe_remove_stashes wrote this.\n')
  repo_b.handle.git.stash("save")

  # Verify update errors because we are deleting the repository while it has stashes.
  stashes = repo_b.handle.git.stash("list")
  with pytest.raises(gordion.UnsafeRemoveStashes) as context:
    tree_a.update(tree_a.repo.handle.head.commit.hexsha, "develop")
  expected = gordion.UnsafeRemoveStashes(repo_b.path, stashes)
  assert str(context.value) == str(expected)


def test_dangling_commit(tree_a):
  """
  Verifies update will error if a child target commit is dangling.
  """

  # Create a dangling commit by committing something, then deleting it. First make an arbitrary
  # change to repo B.
  repo_b = gordion.Workspace().get_repository('gordion_demo_b')
  repo_b.handle.git.commit('-m', "Empty commit for test_dangling_commit", allow_empty=True)
  empty_commit = repo_b.handle.head.commit

  # Now delete the commit (checkout HEAD~1).
  repo_b.handle.head.reset('HEAD~1', index=True, working_tree=True)

  # Now add the empty commit to the parent gordion.yaml.
  tree_a.repo.yeditor.write_repository_tag('gordion_demo_b', empty_commit.hexsha)
  tree_a.repo.yeditor.save()

  # Now update should error commit is dangling ehh.
  with pytest.raises(gordion.DanglingCommitError) as context:
    tree_a.update(tree_a.repo.handle.head.commit.hexsha, "develop")

  expected = gordion.DanglingCommitError(repo_b.path, empty_commit.hexsha)
  assert str(context.value) == str(expected)


def test_tree_update_cleans_dirty_cached_repos(tree_a):
    """
    Verifies that tree.update() cleans dirty cached repositories.
    """
    # Get a cached repository
    workspace = gordion.Workspace()
    repo_b = workspace.get_repository('gordion_demo_b')
    assert workspace.is_dependency(repo_b.path), f"Expected {repo_b.path} to be in cache"

    # Make it dirty by adding an untracked file
    test_file = os.path.join(repo_b.path, 'test_dirty.txt')
    with open(test_file, 'w') as f:
        f.write('This should be cleaned!')

    # Also modify an existing file
    readme_path = os.path.join(repo_b.path, 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'a') as f:
            f.write('\n# Modified content')

    # Verify the repository is dirty
    assert repo_b.handle.is_dirty(untracked_files=True)
    assert os.path.exists(test_file)

    # Update the tree - this should clean the dirty cached repository
    tree_a.update('082abea', 'test_status', force=True)

    # Verify the repository is now clean
    assert not repo_b.handle.is_dirty(untracked_files=True)
    assert not os.path.exists(test_file)
