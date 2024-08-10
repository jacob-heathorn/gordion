import os
import gordion
import shutil
from typing import List


@gordion.utils.singleton
class Store:
  """
  Singleton class dedicated to managing the gordion/ folder.
  """

  def __init__(self) -> None:
    self.path = ''

  def setup(self, root_repository_path):
    """
    User must call this function once with the root gordion repository path, where we will store the
    gordion/ folder managed by this class.
    """
    self.path = os.path.join(root_repository_path, 'gordion')

  def trim_repos(self, keep_repos: List[str], force: bool = False):
    """
    Removes repositories that are not listed in the keep_repos argument.
    """
    assert self.path

    # Delete git repositories.
    for dirpath, dirnames, _ in os.walk(self.path, topdown=True):
      for dirname in dirnames:
        full_dirpath = os.path.join(dirpath, dirname)
        if (os.path.exists(full_dirpath) and not gordion.is_related_path(full_dirpath,
                                                                         keep_repos)):
          if gordion.Repository._exists(full_dirpath):
            gordion.Repository.safe_delete(full_dirpath, force)

    # Delete everything else that is not related to the gordion paths.
    for dirpath, dirnames, _ in os.walk(self.path, topdown=True):
      for dirname in dirnames:
        full_dirpath = os.path.join(dirpath, dirname)
        if (os.path.exists(full_dirpath) and not gordion.is_related_path(full_dirpath,
                                                                         keep_repos)):
          print(f"Deleting directory: {full_dirpath}")
          assert not gordion.Repository._exists(full_dirpath)  # Removed above.
          shutil.rmtree(full_dirpath)
