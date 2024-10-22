# Tests the gordion.Workspace

import os
import gordion
import pytest
from tests.conftest import recursive_git_blast
from conftest import REPOS_DIR


# NOTE: We assume this gordion source code repository is cloned without another gordion repostory in
# it's lineage. If there was another gordion repository in it's directory lineage, then it would
# affect the workspace location when running gordion commands from within the test demos
# environment.

def test_path_default(repository_a):
  """
  The default workspace from a gordion repository is the parent directory.
  """
  assert gordion.Workspace.find_root(repository_a.path) == os.path.dirname(repository_a.path)


def test_path_default_non_gordion(forge):
  """
  The default workspace from within a non-gordion repository is still the parent directory.
  """

  gordion_repo_path = gordion.utils.get_repository_root(REPOS_DIR)
  assert gordion.Workspace.find_root(gordion_repo_path) == os.path.dirname(gordion_repo_path)


def test_path_no_gordion_repository():
  """
  If a gordion repository is not found in the path lineage, and you are not inside a non-gordion
  repository either, the workspace is just the input argument path
  """

  # We need a path that is not inside a repostiory to test this. We can use the parent directory of
  # this gordion repository source code.
  gordion_repo_path = gordion.utils.get_repository_root(REPOS_DIR)
  path = os.path.normpath(os.path.join(gordion_repo_path, '..'))
  assert gordion.Workspace.find_root(path) == path
