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

# =================================================================================================
# Fixtures

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


@pytest.fixture
def mock_dependencies():
  """
  Creates a .dependencies folder in the REPOS_DIR and then deletes it.
  """
  mock_dependencies = os.path.join(REPOS_DIR, '.dependencies')
  os.mkdir(mock_dependencies)

  yield mock_dependencies

  # shutil.rmtree(mock_dependencies, ignore_errors=True)
  # gordion.Workspace().discover_repositories()


# =================================================================================================
# Tests

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


def test_trim_repositories_duplicate(repository_a, mock_dependencies):
  """
  If a dependency is a duplicate of a working, it is trimmed.
  """
  duplicate_path = os.path.join(mock_dependencies, repository_a.name)
  shutil.copytree(repository_a.path, duplicate_path)
  gordion.Repository.register(key=duplicate_path, path=duplicate_path)
  assert gordion.Repository.exists(duplicate_path)
  gordion.Workspace().trim_repositories()
  print(duplicate_path)
  assert not gordion.Repository.exists(duplicate_path)


def test_trim_repositories_wrong_path(repository_a, mock_dependencies):
  """
  If a dependency is in the wrong location it is trimmed.
  """
  subdir = os.path.join(mock_dependencies, 'subdir')
  os.mkdir(subdir)
  repo_b_wrong_path = os.path.join(subdir, 'gordion_demo_b')
  gordion.Repository.clone(repo_b_wrong_path,
                           'https://github.com/jacob-heathorn/gordion_demo_b.git')
  assert gordion.Repository.exists(repo_b_wrong_path)
  gordion.Workspace().trim_repositories()
  assert not gordion.Repository.exists(repo_b_wrong_path)

# TODO here, need a to be complete, move to test_tree? Or move fixture here. Actually just move
# tree_a fixture? and share it here.


def test_trim_repositories_not_listed(repository_a, mock_dependencies):
  """
  If a dependency is not listed, then it is trimmed.
  """
  not_listed_path = os.path.join(mock_dependencies, 'forge')
  gordion.Repository.clone(not_listed_path, 'https://github.com/jacob-heathorn/forge.git')
  assert gordion.Repository.exists(not_listed_path)
  gordion.Workspace().trim_repositories()
  assert not gordion.Repository.exists(not_listed_path)


def test_unify_dependencies(repository_a, mock_dependencies, tmp1):
  """
  If the workspace root moves, there could be a dangling .dependencies folder left at the old
  workspace root. If it is inside the new workspace root, it will be merged.
  """
  # Clone demo_b inside a dangling dependencies folder.
  dangling_dependencies = os.path.join(tmp1, '.dependencies')
  repo_b_path = os.path.join(dangling_dependencies, 'gordion_demo_b')
  gordion.Repository.clone(repo_b_path, 'https://github.com/jacob-heathorn/gordion_demo_b.git')

  # Verify paths before and after unify().
  moved_path = os.path.join(mock_dependencies, 'gordion_demo_b')
  assert gordion.Repository.exists(repo_b_path)
  assert not gordion.Repository.exists(moved_path)
  gordion.Workspace().unify_dependencies()
  assert not gordion.Repository.exists(repo_b_path)
  assert gordion.Repository.exists(moved_path)
  assert not os.path.exists(dangling_dependencies)
