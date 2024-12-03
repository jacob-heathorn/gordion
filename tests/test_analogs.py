# Tests the git analogs of a gordion workspace

import gordion
import pytest


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


# def test_verify_changes_are_branch(tree_a: gordion.Tree):
#   """
#   Verifies add will raise an error if a repository branch does not match the root branch.
#   """

#   repo_b = gordion.Workspace().get_repository('gordion_demo_b')

#   # Checkout a new branch on demo_b
#   new_branch = repo_b.handle.create_head("new_branch")
#   new_branch.checkout()

#   # Make the demo_b dirty by adding an empty file.
#   touchfile = os.path.join(repo_b.path, 'touch.txt')
#   with open(touchfile, 'w'):
#     pass
#   assert repo_b.is_dirty()

#   # Verify error when adding from root.
#   with pytest.raises(gordion.exception.WrongBranchRepositoryDirty) as context:
#     tree_a.verify_changes_are_branch(tree_a.repo.get_branch_name())
#   expected = gordion.exception.WrongBranchRepositoryDirty(tree_a.repo.get_branch_name(), [repo_b])
#   assert str(context.value) == str(expected)
