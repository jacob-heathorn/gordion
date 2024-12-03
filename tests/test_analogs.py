# Tests the git analogs of a gordion workspace

import gordion
import pytest
import os


# =================================================================================================
# Tests


def test_trace(tree_a):
  """
  Verifies nominal trace behavior.
  """
  analogs = gordion.Analogs(tree_a)
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
    gordion.Analogs(tree_a)
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
  analogs = gordion.Analogs(tree_a)
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
  analogs = gordion.Analogs(tree_a)
  with pytest.raises(gordion.exception.WrongBranchRepositoryLineage) as context:
    analogs.verify_lineage_is_branch(tree_a.repo.get_branch_name())
  expected = gordion.exception.WrongBranchRepositoryLineage(tree_a.repo.get_branch_name(), [repo_b])
  assert str(context.value) == str(expected)
