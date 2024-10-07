import os
import gordion
from pathlib import Path
from typing import List, Tuple
import shutil


@gordion.utils.singleton
class Workspace:
  """
  Singleton class dedicated to managing the gordion/ folder.
  """

  def __init__(self) -> None:
    self.path = ''
    self.working: List[gordion.Repository] = []
    self.dependencies: List[gordion.Repository] = []

  def setup(self, subpath):
    """
    User must call this function once with a path somewhere inside a workspace.
    """
    self.path = self.find_root(subpath)
    self.dependencies_path = os.path.normpath(os.path.join(self.path, '.dependencies'))
    self.working, self.dependencies = self.discover_repositories()

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
            return os.path.normpath(current_path)

    # Return the original path parent.
    return os.path.normpath(path.parent)

  def is_dependency(self, path: str) -> bool:
    if os.path.commonprefix([self.dependencies_path, path]) == self.dependencies_path:
      return True
    return False

  def get_repositories(self, url: str) -> Tuple[List[gordion.Repository], List[gordion.Repository]]:
    working = []
    dependencies = []
    for repo in self.working:
      if gordion.utils.compare_urls(repo.handle.remotes.origin.url, url):
        working.append(repo)
    for repo in self.dependencies:
      if gordion.utils.compare_urls(repo.handle.remotes.origin.url, url):
        dependencies.append(repo)
    return working, dependencies

  def discover_repositories(self) -> Tuple[List[gordion.Repository], List[gordion.Repository]]:
    """
    Discovers all repository objects in the workspace and caches them in a dictionary.
    """
    working: List[gordion.Repository] = []
    dependencies: List[gordion.Repository] = []

    for dirpath, dirnames, _ in os.walk(self.path, topdown=True):
      # Create a copy of dirnames for iteration to avoid modifying the list while iterating
      for dirname in dirnames[:]:  # [:] creates a shallow copy of the list
        full_dirpath = os.path.join(dirpath, dirname)

        if gordion.Repository._exists(full_dirpath):
          if self.is_dependency(full_dirpath):
            dependencies.append(gordion.Repository(full_dirpath))
          else:
            working.append(gordion.Repository(full_dirpath))
          # Remove the current directory's name from dirnames so os.walk will skip its
          # subdirectories
          dirnames.remove(dirname)

    working = sorted(working, key=lambda repo: repo.path)
    dependencies = sorted(dependencies, key=lambda repo: repo.path)
    return working, dependencies

  def update_repository_cache(self, path: str):
    # If it exists, add it to the repos cache if necessary
    if gordion.Repository._exists(path):
      if self.is_dependency(path):
        if not any(repo.path == path for repo in self.dependencies):
          self.dependencies.append(gordion.Repository(path))
      else:
        if not any(repo.path == path for repo in self.working):
          self.working.append(gordion.Repository(path))
    # If it does not exist, remove it from the cache if necessary
    else:
      self.working = [repo for repo in self.working if repo.path != path]
      self.dependencies = [repo for repo in self.working if repo.path != path]

  def delete_empty_parent_folders(self, path):
    """
    Delete parent folders if they are empty, up until the workspace folder (but not including)
    """
    # Delete parent folders if they are empty, up until the workspace folder (but not including)
    parent_folder = os.path.normpath(os.path.dirname(path))
    while True:
      is_in_workspace = parent_folder.startswith(self.path + os.sep)
      is_empty = not bool(os.listdir(parent_folder))
      if is_in_workspace and is_empty:
        print(f"Deleting empty folder: {parent_folder}")
        shutil.rmtree(parent_folder)
        parent_folder = os.path.normpath(os.path.dirname(parent_folder))
      else:
        break

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
