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
    Converts a filesystem path to a cache folder name using URL-safe encoding.
    """
    import urllib.parse
    # Convert to absolute path first
    abs_path = os.path.abspath(path)
    # Use URL encoding which is reversible and filesystem-safe
    # Replace % with _ to avoid issues with some filesystems
    encoded = urllib.parse.quote(abs_path, safe='')
    return encoded.replace('%', '_')

  @staticmethod
  def cache_folder_to_path(cache_folder: str) -> str:
    """
    Converts a cache folder name back to the original filesystem path.
    """
    import urllib.parse
    # Restore % characters
    encoded = cache_folder.replace('_', '%')
    # Decode from URL encoding
    return urllib.parse.unquote(encoded)

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
    Removes workspace cache directories that don't belong to real directories
    containing a gordion repository.
    """
    workspaces_dir = os.path.join(CACHE_DIR, 'workspaces')
    if not os.path.exists(workspaces_dir):
      return

    # List all workspace cache directories
    for cache_folder_name in os.listdir(workspaces_dir):
      workspace_cache_path = os.path.join(workspaces_dir, cache_folder_name)
      if not os.path.isdir(workspace_cache_path):
        continue

      try:
        # Convert cache folder name back to original workspace path
        workspace_path = Cache.cache_folder_to_path(cache_folder_name)
        
        # Check if the workspace path exists and contains a gordion repository
        workspace_has_gordion_repo = False
        if os.path.exists(workspace_path) and os.path.isdir(workspace_path):
          # Look for any subdirectory with gordion.yaml
          for item in os.listdir(workspace_path):
            item_path = os.path.join(workspace_path, item)
            if os.path.isdir(item_path):
              gordion_yaml = os.path.join(item_path, 'gordion.yaml')
              if os.path.exists(gordion_yaml) and os.path.isfile(gordion_yaml):
                workspace_has_gordion_repo = True
                break
        
        # If workspace doesn't exist or has no gordion repository, remove the cache
        if not workspace_has_gordion_repo:
          print(f"Removing orphaned workspace cache: {workspace_cache_path}")
          shutil.rmtree(workspace_cache_path)
      except Exception as e:
        # If we can't decode the cache folder name, it's probably invalid
        print(f"Removing invalid workspace cache: {workspace_cache_path} (error: {e})")
        shutil.rmtree(workspace_cache_path)
