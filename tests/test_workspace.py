# Tests the gordion.Workspace

import os
import gordion
import pytest
from conftest import REPOS_DIR
import shutil


# NOTE: We assume this gordion source code repository is cloned without another gordion repostory in
# it's lineage. If there was another gordion repository in it's directory lineage, then it would
# affect the workspace location when running gordion commands from within the test demos
# environment.


def test_path_default(repository_a):
  """
  The default workspace from a gordion repository is the parent directory.
  """
  assert gordion.Workspace.find_root(repository_a.path) == os.path.dirname(repository_a.path)


def test_path_default_non_gordion():
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


@pytest.fixture
def tmp1():
  """
  Creates a tmp1 folder in the REPOS_DIR and then deletes it.
  """
  tmp1 = os.path.join(REPOS_DIR, 'tmp1')
  os.mkdir(tmp1)

  yield tmp1

  shutil.rmtree(tmp1)


def test_path_lineage_arbitrary_folder(tmp1):
  """
  Verifies the path if you are inside a folder in a workspace with a gordion repostiory.
  """
  assert gordion.Workspace.find_root(tmp1) == REPOS_DIR


def test_path_multiple_gordion_lineage(repository_a, tmp1):
  """
  The workspace path will be the parent of the top-most gordion repository in a lineage.
  """
  # Clone gordion_demo_b inside tmp1.
  path = os.path.join(tmp1, 'gordion_demo_b')
  url = 'https://github.com/jacob-heathorn/gordion_demo_b.git'
  gordion.Repository.ensure(path, url)

  # Verify.
  assert gordion.Workspace.find_root(path) == os.path.dirname(repository_a.path)


def test_get_repository(repository_a):
  """
  You can get a repository by name in a workspace.
  """
  ref = gordion.Workspace().get_repository(repository_a.name)
  assert ref.path == repository_a.path
