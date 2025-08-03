import os
import gordion
import subprocess
import shutil
import git

CACHE_DIR = os.path.join(os.path.expanduser('~'), '.local', 'share', 'gordion')


class Cache:
  """
  Manages the gordion cache.

  """

  def __init__(self) -> None:
    if not os.path.exists(CACHE_DIR):
      os.makedirs(CACHE_DIR)

  @staticmethod
  def path_to_cache_folder(path: str) -> str:
    """
    Converts a filesystem path to a cache folder name using base64 encoding.
    """
    import base64
    # Convert to absolute path first
    abs_path = os.path.abspath(path)
    # Use base64 encoding which is reversible and filesystem-safe
    # Replace / with _ to make it filesystem safe
    encoded = base64.urlsafe_b64encode(abs_path.encode('utf-8')).decode('ascii')
    return encoded.rstrip('=')  # Remove padding

  @staticmethod
  def cache_folder_to_path(cache_folder: str) -> str:
    """
    Converts a cache folder name back to the original filesystem path.
    """
    import base64
    # Add back padding if needed
    padding = 4 - (len(cache_folder) % 4)
    if padding != 4:
      cache_folder += '=' * padding
    # Decode from base64
    decoded = base64.urlsafe_b64decode(cache_folder.encode('ascii'))
    return decoded.decode('utf-8')

  def clean(self):
    shutil.rmtree(CACHE_DIR)
    os.makedirs(CACHE_DIR)

  def ensure_mirror(self, url: str) -> tuple[str, str]:
    """
    Clones a mirror if it does not already exist. Returns the path and default branch name.

    """

    host, username, repo_name = gordion.extract_repo_details(url)
    local_path = os.path.join(CACHE_DIR, "mirrors", host, username, repo_name)

    # Clone if the mirror does not exist
    if not os.path.exists(local_path):
      args = ['git', 'clone', '--mirror', url, local_path]
      subprocess.check_call(args, stderr=subprocess.STDOUT)

    # Get the default branch
    mirror = git.Repo(local_path)
    default_branch_name = mirror.active_branch.name

    return local_path, default_branch_name

  def trim(self):
    """
    Removes dependency cache directories that don't belong to real directories
    containing a gordion repository.
    """
    dependencies_dir = os.path.join(CACHE_DIR, 'dependencies')
    if not os.path.exists(dependencies_dir):
      return

    # List all dependency cache directories
    for cache_folder_name in os.listdir(dependencies_dir):
      dependency_cache_path = os.path.join(dependencies_dir, cache_folder_name)
      if not os.path.isdir(dependency_cache_path):
        continue

      try:
        # Convert cache folder name back to original repository path
        repository_path = Cache.cache_folder_to_path(cache_folder_name)

        # Check if the repository path exists and is a gordion repository
        repo_exists = os.path.exists(repository_path)
        is_gordion = gordion.Repository.is_gordion(repository_path) if repo_exists else False
        if not repo_exists or not is_gordion:
          print(f"Removing orphaned dependency cache: {dependency_cache_path}")
          shutil.rmtree(dependency_cache_path)
      except Exception as e:
        # If we can't decode the cache folder name, it's probably invalid
        print(f"Removing invalid dependency cache: {dependency_cache_path} (error: {e})")
        shutil.rmtree(dependency_cache_path)
