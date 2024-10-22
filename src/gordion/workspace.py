import os
import gordion
from pathlib import Path
from typing import Optional, Dict
import shutil


@gordion.utils.singleton
class Workspace:
  """
  Singleton class dedicated to locating and managing the gordion workspace.
  """

  def __init__(self) -> None:
    self.path = ''

  def repos(self) -> Dict[str, gordion.Repository]:
    return gordion.Repository.registry()

  def setup(self, subpath, force=False):
    """
    User must call this function once with a path somewhere inside a workspace.
    """
    if force:
      self.path = subpath
    else:
      self.path = Workspace.find_root(subpath)
    self.dependencies_path = os.path.normpath(os.path.join(self.path, '.dependencies'))
    self.discover_repositories()

  @staticmethod
  def find_root(subpath: str) -> str:
    """
    Finds the workspace given a path inside it.
    """

    # Iterate through parts of the path from root to the last element
    parts = Path(subpath).parts
    current_path = Path(parts[0])  # Start with the root

    for part in parts[1:]:
      current_path /= part  # Traverse to the next part in the path

      # Check if the current directory contains a gordion repository.
      for child in current_path.iterdir():
        if child.is_dir() and os.access(str(child), os.R_OK):
          if gordion.Repository.is_gordion(str(child)):
            return os.path.normpath(current_path)

    # If the given path is a repository, return it's parent.
    print("here1")
    repo_root = gordion.utils.get_repository_root(subpath)
    if repo_root:
      print(f"here2: {repo_root}")
      return os.path.normpath(os.path.dirname(repo_root))

    # Otherwise return the argument itself, which initiallizes a new workspace here.
    print("here3")
    return os.path.normpath(subpath)

  def is_dependency(self, path: str) -> bool:
    if os.path.commonprefix([self.dependencies_path, path]) == self.dependencies_path:
      return True
    return False

  def working(self, name: Optional[str], url: Optional[str]) -> Dict[str, gordion.Repository]:
    return {key: value for key, value in self.repos().items() if not self.is_dependency(
        key) and (not name or name == value.name) and (not url or url == value.url)}

  def dependencies(self, name: Optional[str], url: Optional[str]) -> Dict[str, gordion.Repository]:
    return {key: value for key, value in self.repos().items() if self.is_dependency(
        key) and (not name or name == value.name) and (not url or url == value.url)}

  def get_repository(self, name: str) -> Optional[gordion.Repository]:
    """
    Returns the repository with <name> or None if none or more than one repositories with this name
    exist.
    """

    all = self.working(name=name, url=None)
    all.update(self.dependencies(name=name, url=None))

    if len(all) == 1:
      return next(iter(all.values()))
    else:
      return None

  def discover_repositories(self):
    """
    Discovers all repository objects in the workspace and caches them in a dictionary.
    """

    for dirpath, dirnames, _ in os.walk(self.path, topdown=True):
      # Create a copy of dirnames for iteration to avoid modifying the list while iterating
      for dirname in dirnames[:]:  # [:] creates a shallow copy of the list
        full_dirpath = os.path.join(dirpath, dirname)

        if gordion.Repository.exists(full_dirpath):
          gordion.Repository.register(key=full_dirpath, path=full_dirpath)
          # Remove the current directory's name from dirnames so os.walk will skip its
          # subdirectories
          dirnames.remove(dirname)

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

  def is_listed(self, target: gordion.Repository) -> bool:
    """
    Checks that the repository is listed by name by least one of the working repositories.
    """
    # Working repositories don't need to be listed
    if not self.is_dependency(target.path):
      return True

    for _, repo in self.working(name=None, url=None).items():
      tree = gordion.Tree(repo)
      if tree.is_listed(target):
        return True
    return False

  def trim_repositories(self) -> bool:
    """
    Deletes duplicates and unlisted repositories.
    """
    paths = []
    for _, repo in self.repos().items():
      if self.is_dependency(repo.path):
        if not self.is_listed(repo):
          paths.append(repo.path)
        else:
          expected_path = os.path.join(self.dependencies_path, repo.name)
          if repo.path != expected_path:
            paths.append(repo.path)

    for path in paths:
      gordion.Repository.safe_delete(path)
