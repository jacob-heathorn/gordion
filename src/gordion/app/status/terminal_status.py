import os
from .folder import Folder
from .repository_folder import RepositoryFolder
from .not_found_repository_folder import NotFoundRepositoryFolder
import gordion
from typing import List


def set_parent(folder, folders):
  for f in folders:

    if os.path.dirname(folder.path) == f.path:
      f.add_child(folder)


def terminal_status(root: gordion.Tree) -> str:
  """
  Returns a status string indicating the status of each repository in the tree, which looks cute in
  a terminal.
  """

  # 1) Aggregate a list of all folders, starting with the workspace folder.
  workspace = gordion.Workspace()
  folders = [Folder(workspace.path)]

  listings = root.listings(name=None, url=None)
  for listing in listings:
    repo = workspace.get_repository(listing.name, listing.url)
    if repo:
      if not any(folder.path == repo.path for folder in folders):
        folders.append(RepositoryFolder(repo, root))
    else:
      path = os.path.join(workspace.dependencies_path, listing.name)
      if not any(folder.path == path for folder in folders):
        folders.append(NotFoundRepositoryFolder(path))

  # Add any repo in /dependencies that is not listed by the workspace.
  dependencies = workspace.dependencies(name=None, url=None)
  for key, repo in dependencies.items():
    if not workspace.is_listed(repo):
      if not any(folder.path == repo.path for folder in folders):
        folders.append(RepositoryFolder(repo, root))

  # Also any duplicates.
  for key, repo in workspace.repos().items():
    duplicates = workspace.working(name=None, url=repo.url)
    duplicates.update(workspace.dependencies(name=None, url=repo.url))
    if len(duplicates) > 1:
      for key, duplicate in duplicates.items():
        if not any(folder.path == duplicate.path for folder in folders):
          folders.append(RepositoryFolder(duplicate, root))

  # Add intermediary folders.
  intermediary_folders: List[Folder] = []
  workspace_folder = folders[0]
  for folder in folders[1:]:
    relative_path = os.path.relpath(folder.path, workspace_folder.path)
    relative_path_parts = relative_path.strip(os.sep).split(os.sep)
    current_path = workspace_folder.path

    # Loop over each part of the path
    for part in relative_path_parts:
      current_path = os.path.join(current_path, part)
      # Add new folder if it does not exist
      if not any(folder.path == current_path for folder in folders):
        if not any(folder.path == current_path for folder in intermediary_folders):
          intermediary_folders.append(Folder(current_path))
  folders.extend(intermediary_folders)

  # 2) Alphabetize the list based on path.
  folders = sorted(folders, key=lambda folder: folder.path)

  # 3) Set the heirarchy of folders.
  for folder in folders[1:]:
    set_parent(folder, folders)

  return folders[0].terminal_status()
