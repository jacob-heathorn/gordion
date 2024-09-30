import os
from .folder import Folder
from .repository_folder import RepositoryFolder
import gordion
from typing import List


def populate_children(folder, root):
  """
  Populates the children member on the folder object. Maybe better as a method on Folder, but avoids
  a circular dependecy on RepositoryFolder if moved outside the class.
  """
  # Collect list of path folders in this directory (one level deep), and alphabetize it.
  dirs = []
  for dirpath, dirnames, _ in os.walk(folder.path, topdown=True):
    for dirname in dirnames:
      dirs.append(os.path.join(folder.path, dirpath, dirname))
    break  # one level deep
  dirs.sort()

  # Create children.
  for dir in dirs:
    # Create a repository folder if it exists
    if gordion.Repository._exists(dir):
      repo = gordion.Tree(dir)
      child_folder = RepositoryFolder(repo, root)
      folder.add_child(child_folder)

    # Otherwise it's just a regular folder. Recurse into it and add it.
    else:
      child_folder = Folder(dir)
      populate_children(child_folder, root)
      folder.add_child(child_folder)


def set_parent(folder, folders):
  for f in folders:

    if os.path.dirname(folder.path) == f.path:
      f.add_child(folder)


def terminal_status(root) -> str:
  """
  Returns a status string indicating the status of each repository in the tree, which looks cute in
  a terminal.
  """
  # 1) Aggregate a list of all folders, starting with the workspace folder.
  workspace = gordion.Workspace()
  folders = [Folder(workspace.path)]

  # Collect all other Folders of interest.
  #
  # Collect all listed repos from root.
  #
  # TODO handle wrong location, and duplicate repos.
  listings = root.listings(None, None)
  for listing in listings:
    if not any(folder.path == listing.path for folder in folders):
      folders.append(RepositoryFolder(listing.path, listing.url, root))

  # Collect any duplicate repos. TODO.

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
