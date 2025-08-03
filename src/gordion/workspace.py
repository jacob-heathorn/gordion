import os
import gordion
from pathlib import Path
from typing import Optional, Dict, Tuple
import shutil


@gordion.utils.singleton
class Workspace:
  """
  Singleton class dedicated to locating and managing the gordion workspace.
  """

  def __init__(self) -> None:
    self.path = ''
    self.root_repository: Optional[gordion.Repository] = None

  def repos(self) -> Dict[str, gordion.Repository]:
    return gordion.Repository.registry()  # type: ignore[attr-defined]

  def setup(self, subpath):
    """
    User must call this function once with a path somewhere inside a gordion repository.
    """
    # Check if the path is inside a gordion repository
    repo_root = gordion.utils.get_repository_root(subpath)
    if not repo_root:
      raise Exception(f"Path '{subpath}' is not inside a git repository")

    if not gordion.Repository.is_gordion(repo_root):
      raise Exception(
          f"Path '{subpath}' is not inside a gordion repository (no gordion.yaml found)"
      )
    self.path = Workspace.find_root(subpath)

    # Store the root repository first
    self.root_repository = gordion.Repository(repo_root)

    # Create a sanitized identifier for cache directory based on root repository
    repository_id = gordion.Cache.path_to_cache_folder(self.root_repository.path)
    cache_base = os.path.join(gordion.cache.CACHE_DIR, 'dependencies')
    self.dependencies_path = os.path.normpath(os.path.join(cache_base, repository_id))

    # Create the cache directory if it doesn't exist
    if not os.path.exists(self.dependencies_path):
      os.makedirs(self.dependencies_path, exist_ok=True)

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
    repo_root = gordion.utils.get_repository_root(subpath)
    if repo_root:
      return os.path.normpath(os.path.dirname(repo_root))

    # Otherwise return the argument itself, which initiallizes a new workspace here.
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

  def get_repository_or_throw(self, name: str) -> gordion.Repository:
    """
    Returns the repository with <name> or throws an error if it does not exist.
    """

    repo = self.get_repository(name)
    if repo:
      return repo
    else:
      raise Exception(f"Could not find repository<{name}>!")

  def discover_repositories(self):
    """
    Discovers all repository objects in the workspace and caches them in a dictionary.
    """
    # Track which paths we've seen during discovery
    discovered_paths = set()

    # Get current registry to track what needs to be removed
    current_registry = gordion.Repository.registry().copy()  # type: ignore[attr-defined]

    # Discover repositories in both workspace and dependencies cache
    paths_to_walk = [self.path]
    if os.path.exists(self.dependencies_path):
      paths_to_walk.append(self.dependencies_path)

    for base_path in paths_to_walk:
      for dirpath, dirnames, _ in os.walk(base_path, topdown=True):
        # Create a copy of dirnames for iteration to avoid modifying the list while iterating
        for dirname in dirnames[:]:  # [:] creates a shallow copy of the list
          full_dirpath = os.path.join(dirpath, dirname)

          if gordion.Repository.exists(full_dirpath):
            normalized_path = os.path.normpath(full_dirpath)
            discovered_paths.add(normalized_path)

            # Only create new instance if not already in registry
            if normalized_path not in current_registry:
              gordion.Repository(full_dirpath)

            # Remove the current directory's name from dirnames so os.walk will skip its
            # subdirectories
            dirnames.remove(dirname)

    # Remove repositories that no longer exist on disk
    for path in current_registry:
      if path not in discovered_paths:
        gordion.Repository.unregister(path)  # type: ignore[attr-defined]

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

  def is_listed(self, target: gordion.Repository) -> Tuple[bool, bool]:
    """
    Checks that the repository is listed by name by least one of the working repositories.
    """
    complete = True
    is_listed = False

    # Working repositories don't need to be listed
    if not self.is_dependency(target.path):
      is_listed = True

    for _, repo in self.working(name=None, url=None).items():
      tree = gordion.Tree(repo)
      is_listed_here, complete = tree.is_listed(target)
      if is_listed_here:
        is_listed = True

    return is_listed, complete

  def trim_repositories(self):
    """
    Deletes duplicates and unlisted repositories.
    """
    paths = set()
    for _, repo in self.repos().items():
      if self.is_dependency(repo.path):
        # If it is not listed, remove it.
        is_listed, complete = self.is_listed(repo)
        if not is_listed and complete:
          paths.add(repo.path)

        # If it is a duplicate of a working.
        for _, other in self.repos().items():
          if not self.is_dependency(other.path):
            if other.path != repo.path and gordion.utils.compare_urls(other.url, repo.url):
              paths.add(repo.path)

        # If it is not at the expected path remove it.
        expected_path = os.path.join(self.dependencies_path, repo.name)
        if repo.path != expected_path:
          paths.add(repo.path)

    for path in paths:
      gordion.Repository.safe_delete(path)
