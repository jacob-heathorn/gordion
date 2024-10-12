import os
import gordion
from pathlib import Path
from typing import Optional, Dict
import shutil


@gordion.utils.singleton
class Workspace:
  """
  Singleton class dedicated to managing the gordion/ folder.
  """

  def __init__(self) -> None:
    self.path = ''

  def repos(self) -> Dict[str, gordion.Repository]:
    return gordion.Repository.registry()

  def setup(self, subpath):
    """
    User must call this function once with a path somewhere inside a workspace.
    """
    self.path = self.find_root(subpath)
    self.dependencies_path = os.path.normpath(os.path.join(self.path, '.dependencies'))
    self.discover_repositories()

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

  def working(self, name: Optional[str], url: Optional[str]) -> Dict[str, gordion.Repository]:
    return {key: value for key, value in self.repos().items() if not self.is_dependency(
        key) and (not name or name == value.name) and (not url or url == value.url)}

  def dependencies(self, name: Optional[str], url: Optional[str]) -> Dict[str, gordion.Repository]:
    return {key: value for key, value in self.repos().items() if self.is_dependency(
        key) and (not name or name == value.name) and (not url or url == value.url)}

  def get_repository(self, name: str, url: str) -> Optional[gordion.Repository]:
    """
    Provides a deterministic way to select a tree by name and url from a workspace that could
    have duplicates or misnamed repositories.
    """

    # Define a helper function
    def get_correctly_named_or_none(
            repos: Dict[str, gordion.Repository], name: str) -> Optional[gordion.Repository]:
      correctly_named = []
      for _, repo in repos.items():
        if repo.name == name:
          correctly_named.append(repo)
      if len(correctly_named) == 1:
        return correctly_named[0]
      else:
        # Cannot decide which working is the correct repo, return None.
        return None

    # First handle situation where there are no working repositories with this url.
    working = self.working(name=None, url=url)
    if len(working) == 0:
      dependencies = self.dependencies(name=None, url=url)
      if len(dependencies) == 0:
        return None

      # If there is exactly one dependency repository with this url, we select it even if it has the
      # wrong name. Although status will tell you it has the wrong name.
      elif len(dependencies) == 1:
        return next(iter(dependencies.values()))

      # If there is more than one dependency repository, but only one has the correct name, we
      # select it. NOTE: it might be at the wrong path in the /dependencies folder.
      else:
        return get_correctly_named_or_none(dependencies, name)

    # If there is exactly one working repository with this url, we select it even if it has the
    # wrong name. Although status will tell you it has the wrong name.
    elif working == 1:
      return next(iter(working.values()))

    # If there is more than one working repository. But only one has the
    # correct name, select that one.
    else:
      return get_correctly_named_or_none(working, name)

  def discover_repositories(self):
    """
    Discovers all repository objects in the workspace and caches them in a dictionary.
    """

    for dirpath, dirnames, _ in os.walk(self.path, topdown=True):
      # Create a copy of dirnames for iteration to avoid modifying the list while iterating
      for dirname in dirnames[:]:  # [:] creates a shallow copy of the list
        full_dirpath = os.path.join(dirpath, dirname)

        if gordion.Repository._exists(full_dirpath):
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
    Checks that the repository is listed by name and url by at least one of the working
    repositories.
    """
    # Working repositories don't need to be listed
    if not self.is_dependency(target.path):
      return True

    for key, repo in self.working(name=None, url=None).items():
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
      if self.is_duplicate(repo) or not self.is_listed(repo):
        paths.append(repo.path)
    for path in paths:
      gordion.Repository.safe_delete(path)

  def is_duplicate(self, target: gordion.Repository) -> bool:
    """
    A repository is marked duplicate if one of ...
      a) It is not listed, and there is another repo with the same URL.
      b) It is listed, and it is a dependency among duplicate listed dependencies.
      c) If it is a dependency and one or more working exist.
      d) If it is a working among duplicate working.
    """
    working = self.working(name=None, url=target.url)
    dependencies = self.dependencies(name=None, url=target.url)
    all = working.copy()
    all.update(dependencies)

    # If it is not listed, and there is another repo with this URL.
    if not self.is_listed(target):
      if len(all) > 1:
        return True

    # If it is listed...
    else:
      # If it is a dependency among duplicate listed dependencies.
      if len(working) == 0:
        assert self.is_dependency(target.path)
        num_listed_dependencies = 0
        for _, dependency in dependencies.items():
          if self.is_listed(dependency):
            num_listed_dependencies += 1
        return num_listed_dependencies > 1
      else:
        # If it is a dependency and one or more working exist.
        if self.is_dependency(target.path):
          return True

        # If it is a working among duplicate working.
        else:
          if len(working) > 1:
            return True

  def has_duplicate(self, target: gordion.Repository) -> bool:
    all = self.working(name=None, url=target.url)
    all.update(self.dependencies(name=None, url=target.url))
    if len(all) > 1:
      return True
    return False
