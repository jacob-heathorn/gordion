import os
import gordion


def test_repo_details():
  url = "https://github.com/username/repository.git"
  host, username, repo_name = gordion.extract_repo_details(url)
  assert host == "github.com"
  assert username == "username"
  assert repo_name == "repository"

  url = "git@github.com:username/repository.git"
  host, username, repo_name = gordion.extract_repo_details(url)
  assert host == "github.com"
  assert username == "username"
  assert repo_name == "repository"

  url = "http://bitbucket.org/username/repository"
  host, username, repo_name = gordion.extract_repo_details(url)
  assert host == "bitbucket.org"
  assert username == "username"
  assert repo_name == "repository"

  url = "ssh://gitlab.com/username/repository.git"
  host, username, repo_name = gordion.extract_repo_details(url)
  assert host == "gitlab.com"
  assert username == "username"
  assert repo_name == "repository"


def test_mirror():
  cache = gordion.Cache()
  # NOTE: Don't clean the cache because it's breaking other tests.
  # cache.clean()
  path, default_branch = cache.ensure_mirror(
      'https://github.com/jacob-heathorn/gordion_demo_a.git')
  assert path == os.path.join(os.path.expanduser('~'), '.local', 'share', 'gordion',
                              'mirrors', 'github.com', 'jacob-heathorn',
                              'gordion_demo_a')
  assert default_branch == 'develop'


def test_trim_orphaned_cache():
  """
  Test that cache.trim() removes orphaned dependency caches.
  """
  cache = gordion.Cache()
  dependencies_dir = os.path.join(gordion.cache.CACHE_DIR, 'dependencies')

  # Create a fake orphaned cache directory
  orphaned_cache = os.path.join(dependencies_dir, 'fake_orphaned_dependency_12345')
  os.makedirs(orphaned_cache, exist_ok=True)

  # Create a test file in the orphaned cache
  test_file = os.path.join(orphaned_cache, 'test.txt')
  with open(test_file, 'w') as f:
    f.write('test')

  assert os.path.exists(orphaned_cache)

  # Run trim - it should remove the orphaned cache
  cache.trim()

  # Verify the orphaned cache was removed
  assert not os.path.exists(orphaned_cache)


def test_trim_keeps_valid_cache(repository_a):
  """
  Test that cache.trim() keeps dependency caches that belong to valid repositories.
  """
  # Get current workspace and its cache
  workspace = gordion.Workspace()

  # The workspace cache should exist after setup
  assert os.path.exists(workspace.dependencies_path)

  # Create a dummy file in the cache to ensure it's not empty
  dummy_file = os.path.join(workspace.dependencies_path, 'dummy.txt')
  with open(dummy_file, 'w') as f:
    f.write('keep me')

  # Run trim
  cache = gordion.Cache()
  cache.trim()

  # The valid workspace cache should still exist
  assert os.path.exists(workspace.dependencies_path)

  # Clean up
  if os.path.exists(dummy_file):
    os.remove(dummy_file)
