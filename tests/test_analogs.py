# Tests the git analogs of a gordion workspace

import os
import gordion
import pytest


# =================================================================================================
# Tests

def test_add_child_wrong_branch(tree_a: gordion.Tree):
  """
  Verifies add will raise an error if a repository branch does not match the root branch.
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
  with pytest.raises(gordion.exception.WrongBranchRepositoryDirty) as context:
    tree_a.add(tree_a.repo.handle.active_branch.name, ".")
  expected = gordion.exception.WrongBranchRepositoryDirty(tree_a.repo.get_branch_name(), [repo_b])
  assert str(context.value) == str(expected)
