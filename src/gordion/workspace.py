import os
import gordion
from pathlib import Path
from typing import List


@gordion.utils.singleton
class Workspace:
  """
  Singleton class dedicated to managing the gordion/ folder.
  """

  def __init__(self) -> None:
    self.path = ''
    self.repos = []

  def setup(self, subpath):
    """
    User must call this function once with a path somewhere inside a workspace.
    """
    self.path = self.find_root(subpath)
    self.repos = self.discover_repositories()

  def find_root(self, path: str) -> str:
    """
    Finds the workspace given a path inside it.
    """
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

  def get_repositories_by_url(self, url: str) -> List[gordion.Repository]:
    found = []
    for repo in self.repos:
      if gordion.utils.compare_urls(repo.handle.remotes.origin.url, url):
        found.append(repo)
    return found

  def discover_repositories(self) -> List[gordion.Repository]:
    """
    Discovers all repository objects in the workspace and caches them in a dictionary.
    """
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

  def update_repository_cache(self, path: str):
    # If it exists, add it to the repos cache if necessary
    if gordion.Repository._exists(path):
      if not any(repo.path == path for repo in self.repos):
        self.repos.append(gordion.Repository(path))
    # If it does not exist, remove it from the cache if necessary
    else:
      self.repos = [repo for repo in self.repos if repo.path != path]

    # def trim_repos(self, keep_repos: List[str], force: bool = False):
    #   """
    #   Removes repositories that are not listed in the keep_repos argument.
    #   """
    #   assert self.path

    #   # Delete git repositories.
    #   for dirpath, dirnames, _ in os.walk(self.path, topdown=True):
    #     for dirname in dirnames:
    #       full_dirpath = os.path.join(dirpath, dirname)
    #       if (os.path.exists(full_dirpath) and not gordion.utils.is_related_path(full_dirpath,
    #                                                                              keep_repos)):
    #         if gordion.Repository._exists(full_dirpath):
    #           gordion.Repository.safe_delete(full_dirpath, force)

    #   # Delete everything else that is not related to the gordion paths.
    #   for dirpath, dirnames, _ in os.walk(self.path, topdown=True):
    #     for dirname in dirnames:
    #       full_dirpath = os.path.join(dirpath, dirname)
    #       if (os.path.exists(full_dirpath) and not gordion.utils.is_related_path(full_dirpath,
    #                                                                              keep_repos)):
    #         print(f"Deleting directory: {full_dirpath}")
    #         assert not gordion.Repository._exists(full_dirpath)  # Removed above.
    #         shutil.rmtree(full_dirpath)

    # def list_repos(self):
    #   repos = []

    #   for dirpath, dirnames, _ in os.walk(self.path, topdown=True):
    #     # Create a copy of dirnames for iteration to avoid modifying the list while iterating
    #     for dirname in dirnames[:]:  # [:] creates a shallow copy of the list
    #       full_dirpath = os.path.join(dirpath, dirname)

    #       if gordion.Repository._exists(full_dirpath):
    #         repos.append(gordion.Repository(full_dirpath))
    #         # Remove the current directory's name from dirnames so os.walk will skip its
    #         # subdirectories
    #         dirnames.remove(dirname)

    #   return sorted(repos, key=lambda repo: repo.path)
