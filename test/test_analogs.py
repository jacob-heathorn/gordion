# Tests the git analogs of a gordion workspace

import gordion
import pytest
import os


# =================================================================================================
# Tests


def test_trace(tree_a: gordion.Tree):
  """
  Verifies nominal trace behavior.
  """
  analogs = gordion.Analogs(tree_a.repo)
  assert analogs.nodes[gordion.Workspace().get_repository('gordion_demo_a').path] is not None
  assert analogs.nodes[gordion.Workspace().get_repository('gordion_demo_b').path] is not None
  assert analogs.nodes[gordion.Workspace().get_repository('gordion_demo_c').path] is not None
  assert analogs.nodes[gordion.Workspace().get_repository('gordion_demo_d').path] is not None


def test_trace_error(tree_a: gordion.Tree):
  """
  Verifies the analogs object will throw a trace error if we cannot trace the repostiory tree.
  """

  # Checkout a wrong commit on repo_b
  repo_b = gordion.Workspace().get_repository('gordion_demo_b')
  repo_b.handle.head.reset('HEAD~1', index=True, working_tree=True)

  # Verify the analogs object throws trace error.
  with pytest.raises(gordion.exception.TraceError) as context:
    gordion.Analogs(tree_a.repo)
  expected = gordion.exception.TraceError()
  assert str(context.value) == str(expected)


def test_verify_changes_are_branch(tree_a: gordion.Tree):
  """
  verify_changes_are_branch() will throw an error if any dirty repository does not have the correct
  branch checked out.
  """

  repo_b = gordion.Workspace().get_repository('gordion_demo_b')

  # Checkout a new branch on demo_b
  new_branch = repo_b.handle.create_head("new_branch")
  new_branch.checkout()

  # Make the demo_b dirty by adding an empty file.
  touchfile = os.path.join(repo_b.path, 'touch.txt')
  with open(touchfile, 'w'):
    pass
  assert repo_b.is_dirty()

  # Verify error when adding from root.
  analogs = gordion.Analogs(tree_a.repo)
  with pytest.raises(gordion.exception.WrongBranchRepositoryDirty) as context:
    analogs.verify_changes_are_branch(tree_a.repo.get_branch_name())
  expected = gordion.exception.WrongBranchRepositoryDirty(tree_a.repo.get_branch_name(), [repo_b])
  assert str(context.value) == str(expected)


def test_verify_lineage_is_branch(tree_a: gordion.Tree):
  """
  verify_lineage_is_branch() will throw an error if any ancestor repositories of a repository with
  staged changes, does not checkout the correct branch.
  """

  repo_b = gordion.Workspace().get_repository('gordion_demo_b')
  repo_d = gordion.Workspace().get_repository('gordion_demo_d')

  # Checkout a new branch on demo_b
  new_branch = repo_b.handle.create_head("new_branch")
  new_branch.checkout()

  # Make the demo_d dirty by adding an empty file and stage the changes.
  touchfile = os.path.join(repo_d.path, 'touch.txt')
  with open(touchfile, 'w'):
    pass
  repo_d.add(".")
  assert repo_d.has_staged_changes()

  # Verify error when adding from root. A and D are the same branch and D has changes, but
  # committing would require a change to B, which doesn't checkout the same branch. Therefore we
  # expect an error.
  analogs = gordion.Analogs(tree_a.repo)
  with pytest.raises(gordion.exception.WrongBranchRepositoryLineage) as context:
    analogs.verify_lineage_is_branch(tree_a.repo.get_branch_name())
  expected = gordion.exception.WrongBranchRepositoryLineage(tree_a.repo.get_branch_name(), [repo_b])
  assert str(context.value) == str(expected)


def test_verify_lineage_does_not_have_unstaged_gordion_changes(tree_a: gordion.Tree):
  """
  verify_lineage_does_not_have_unstaged_gordion_changes() will throw an error if any ancestor
  repositories of a repository with staged changes has unstaged changes in it's gordion.yaml file.
  """

  repo_a = gordion.Workspace().get_repository('gordion_demo_a')
  repo_b = gordion.Workspace().get_repository('gordion_demo_b')
  repo_d = gordion.Workspace().get_repository('gordion_demo_d')

  # Make demo_d dirty by adding an empty file and stage the changes.
  touchfile = os.path.join(repo_d.path, 'touch.txt')
  with open(touchfile, 'w'):
    pass
  repo_d.add(".")
  assert repo_d.has_staged_changes()

  # Modify demo_a gordion.yaml file by shortening it's demo_b commit hexsha. (same value)
  repo_a.yeditor.write_repository_tag('gordion_demo_b', repo_b.handle.head.commit.hexsha[0:7])
  assert repo_a.is_dirty()

  # Verify error when committing from root.
  analogs = gordion.Analogs(tree_a.repo)
  with pytest.raises(gordion.exception.UnstagedGordionChangesInLineage) as context:
    analogs.verify_lineage_does_not_have_unstaged_gordion_changes()
  expected = gordion.exception.UnstagedGordionChangesInLineage()
  assert str(context.value) == str(expected)


def test_add_restore_clean(tree_a: gordion.Tree):
  """Verifies git add analog"""

  repo_a = tree_a.repo
  repo_d = gordion.Workspace().get_repository('gordion_demo_d')

  # Verify control
  assert repo_a.has_staged_changes() is False
  assert repo_d.has_staged_changes() is False
  assert repo_a.is_dirty() is False
  assert repo_d.is_dirty() is False

  # Add a touchfile to two different repositories.
  touchfile = os.path.join(repo_a.path, 'touch.txt')
  with open(touchfile, 'w'):
    pass
  touchfile = os.path.join(repo_d.path, 'touch.txt')
  with open(touchfile, 'w'):
    pass

  # Gordion add.
  analogs = gordion.Analogs(tree_a.repo)
  analogs.add(repo_a.handle.active_branch.name, ".")

  # Verify files are staged in repos A and D
  assert repo_a.has_staged_changes() is True
  assert repo_d.has_staged_changes() is True

  # Restore staged and verify.
  analogs.restore(".", staged=True)
  assert repo_a.has_staged_changes() is False
  assert repo_d.has_staged_changes() is False
  assert repo_a.is_dirty() is True
  assert repo_d.is_dirty() is True

  # Clean touchfiles.
  analogs.clean(force=True, dirs=True, extra=True)
  assert repo_a.is_dirty() is False
  assert repo_d.is_dirty() is False


def test_commit(tree_a_local: gordion.Tree):
  """Verifies git commit analog"""
  repo_a = tree_a_local.repo
  repo_b = gordion.Workspace().get_repository('gordion_demo_b')
  repo_c = gordion.Workspace().get_repository('gordion_demo_c')
  repo_d = gordion.Workspace().get_repository('gordion_demo_d')

  # Add a touchfile to two different repositories.
  touchfile = os.path.join(repo_d.path, 'touch.txt')
  with open(touchfile, 'w'):
    pass

  # Gordion add.
  analogs = gordion.Analogs(tree_a_local.repo)
  analogs.add(repo_d.handle.active_branch.name, ".")

  # Gordion commit.
  analogs.commit(repo_d.handle.active_branch.name, "test_commit")

  # Verify commit messages.
  assert repo_d.handle.head.commit.message == "test_commit\n"
  b_c_message = f"test_commit\n\n* Bump gordion_demo_d to {repo_d.handle.head.commit.hexsha}\n"
  assert repo_c.handle.head.commit.message == b_c_message
  assert repo_b.handle.head.commit.message == b_c_message
  a_message = f"test_commit\n\n* Bump gordion_demo_c to {repo_c.handle.head.commit.hexsha}\n"
  a_message += f"* Bump gordion_demo_b to {repo_b.handle.head.commit.hexsha}\n"
  assert repo_a.handle.head.commit.message == a_message


def test_push(tree_a: gordion.Tree):
  """Verifies git push analog"""
  repo_a = tree_a.repo
  repo_d = gordion.Workspace().get_repository('gordion_demo_d')

  # Checkout new branch on a and d.
  repo_a.handle.create_head("test_push").checkout()
  repo_d.handle.create_head("test_push").checkout()

  # gor push -u origin test_push.
  analogs = gordion.Analogs(tree_a.repo)
  analogs.push(set_upstream=True, delete=False, remote='origin', branch='test_push', force=False)

  # Verify new remote branches.
  for ref in repo_a.handle.remotes['origin'].refs:
    print(ref.name)
  assert any(ref.name == "origin/test_push" for ref in repo_a.handle.remotes['origin'].refs)
  assert any(ref.name == "origin/test_push" for ref in repo_d.handle.remotes['origin'].refs)

  # gor delete the remote branches.
  analogs.push(set_upstream=False, delete=True, remote='origin', branch='test_push', force=False)
  assert not any(ref.name == "origin/test_push" for ref in repo_a.handle.remotes['origin'].refs)
  assert not any(ref.name == "origin/test_push" for ref in repo_d.handle.remotes['origin'].refs)


def test_commit_fails_with_cached_repositories(tree_a):
  """
  Verifies that commit fails when trying to commit with repositories in the cache.
  """
  # Verify we have cached repositories
  workspace = gordion.Workspace()
  repo_a = workspace.get_repository('gordion_demo_a')
  repo_b = workspace.get_repository('gordion_demo_b')
  repo_c = workspace.get_repository('gordion_demo_c')
  repo_d = workspace.get_repository('gordion_demo_d')
  assert workspace.is_dependency(repo_b.path), "Expected repo_b to be in cache"
  assert workspace.is_dependency(repo_c.path), "Expected repo_c to be in cache"
  assert workspace.is_dependency(repo_d.path), "Expected repo_d to be in cache"

  # Move demo_d from cache to workspace to make changes
  new_path_d = os.path.join(os.path.dirname(repo_a.path), 'gordion_demo_d')
  if not os.path.exists(new_path_d):
    gordion.Repository.safe_move(repo_d.path, new_path_d)
  repo_d = workspace.get_repository('gordion_demo_d')

  # Make a change in demo_d
  test_file = os.path.join(repo_d.path, 'test_commit.txt')
  with open(test_file, 'w') as f:
    f.write('Test content for commit')

  # Stage the change
  repo_d.handle.index.add([test_file])

  # Create analogs from root and try to commit - should fail
  analogs = gordion.Analogs(repo_a)

  with pytest.raises(gordion.exception.CommitCachedRepositoriesError) as exc_info:
    analogs.commit(repo_a.get_branch_name(), 'Test commit')

  # Verify the error message contains the cached repositories in the lineage
  error = exc_info.value
  assert len(error.cached_repos) == 2  # demo_b and demo_c are both in cache and in the lineage
  assert 'gordion_demo_b' in str(error.message)
  assert 'gordion_demo_c' in str(error.message)
  assert 'gordion_demo_d' not in str(error.message)  # demo_d is now in workspace
  assert 'must be cloned to the workspace first' in str(error.message)

  # Clean up - reset the staged file
  repo_d.handle.index.reset(paths=[test_file])
  if os.path.exists(test_file):
    os.remove(test_file)
