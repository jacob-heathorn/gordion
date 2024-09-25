import os
import gordion
import shutil
from typing import List
from pathlib import Path

# TODO repurpose as workspace?


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
        if (os.path.exists(full_dirpath) and not gordion.utils.is_related_path(full_dirpath,
                                                                               keep_repos)):
          if gordion.Repository._exists(full_dirpath):
            gordion.Repository.safe_delete(full_dirpath, force)

    # Delete everything else that is not related to the gordion paths.
    for dirpath, dirnames, _ in os.walk(self.path, topdown=True):
      for dirname in dirnames:
        full_dirpath = os.path.join(dirpath, dirname)
        if (os.path.exists(full_dirpath) and not gordion.utils.is_related_path(full_dirpath,
                                                                               keep_repos)):
          print(f"Deleting directory: {full_dirpath}")
          assert not gordion.Repository._exists(full_dirpath)  # Removed above.
          shutil.rmtree(full_dirpath)

  def list_repos(self):
    repos = []

    for dirpath, dirnames, _ in os.walk(self.path, topdown=True):
      # Create a copy of dirnames for iteration to avoid modifying the list while iterating
      for dirname in dirnames[:]:  # [:] creates a shallow copy of the list
        full_dirpath = os.path.join(dirpath, dirname)

        if gordion.Repository._exists(full_dirpath):
          repos.append(gordion.Repository(full_dirpath))
          # Remove the current directory's name from dirnames so os.walk will skip its
          # subdirectories
          dirnames.remove(dirname)

    return sorted(repos, key=lambda repo: repo.path)


def find_workspace(path: str) -> str:
  # Convert string path to Path object if necessary
  path = Path(path) if not isinstance(path, Path) else path

  # Iterate through parts of the path from root to the last element
  parts = path.parts
  current_path = Path(parts[0])  # Start with the root

  for part in parts[1:]:
    current_path /= part  # Traverse to the next part in the path

    # Check if the current directory contains a gordion repository.
    for child in current_path.iterdir():
      if child.is_dir() and os.access(str(child), os.R_OK):
        if gordion.Repository.is_gordion(str(child)):
          return str(current_path)

  # Return the original path parent.
  return str(path.parent)
