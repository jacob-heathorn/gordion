import os
import gordion
import subprocess
import shutil

CACHE_DIR = os.path.join(os.environ['HOME'], '.gordion')


class Cache:
  """
  Manages the gordion cache.

  """

  def __init__(self) -> None:
    if not os.path.exists(CACHE_DIR):
      os.makedirs(CACHE_DIR)

  def clean(self):
    shutil.rmtree(CACHE_DIR)
    os.makedirs(CACHE_DIR)

  def ensure_mirror(self, url: str) -> str:
    """
    Clones a mirror if it does not already exist

    """

    host, username, repo_name = gordion.extract_repo_details(url)
    local_path = os.path.join(CACHE_DIR, "mirrors", host, username, repo_name)

    # Clone if the mirror does not exist, otherwise fetch
    if not os.path.exists(local_path):
      args = ['git', 'clone', url, local_path]
      subprocess.check_call(args, stderr=subprocess.STDOUT)

    return local_path
