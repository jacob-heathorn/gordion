import os
import subprocess
from gordion.utils import pushd
from pathlib import Path
from git import Repo
import gordion

CACHE_DIR = os.path.join(os.environ['HOME'], '.gordion')


class Cache:
  """
  Manages the gordion cache.

  """

  def __init__() -> None:
    if not os.path.exists(CACHE_DIR):
      os.makedirs(CACHE_DIR)

  def get_mirror_path(url: str) -> None:
    """
    Returns a path in the cache

    """

    pass
