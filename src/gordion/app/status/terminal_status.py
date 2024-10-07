import os
from .folder import Folder
from .repository_folder import RepositoryFolder
from .duplicate_repository_folder import DuplicateRepositoryFolder
from .not_listed_repository_folder import NotListedRepositoryFolder
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

  # For each repository in the .dependencies/. Decide if it is listed or not by a working repo, and
  # if it is at the correct location.
  for dependency in workspace.dependencies:
    folders.append(RepositoryFolder(dependency, root))

    # if dependency.path != os.path.join(workspace.dependencies_path, dependency.name):
    #   folders.append(WrongPathRepositoryFolder(dependency.path))
    # else:

    #   # If it is listed by root, then we want to show status for it.

    #   # For all listings with this name, make sure the listing has the correct url.
    #   dependency_folder = RepositoryFolder(dependency, root)

    #   listings = root.listings(name=dependency.name, url=None)
    #   for listing in listings:
    #     if gordion.utils.compare_urls(listing.url, dependency.name):
    #       if not any(folder.path == repo.path for folder in folders):
    #         folders.append(RepositoryFolder(dependency, root))
    #     else:

    #   if len(listings) > 0:
    #     folders.append(RepositoryFolder(dependency, root))

    #   # If it is not listed by root or any workspace folder, we want to show that it should
    #   # not exist.
    #   #
    #   # TODO handle wrong name here?
    #   for repo in workspace.working:
    #     if gordion.Repository.is_gordion(repo.path):
    #       tree = gordion.Tree(repo.path)
    #       listings = tree.listings(target_url=dependency.url)
    #       if len(listings) == 0:
    #         folders.append(NotListedRepositoryFolder(dependency.path))

  # TODO: Aggregate repositories that are listed by root, but not found in the workspace.

  # # Collect all other Folders of interest.
  # #
  # # Collect all listed repos from root.
  # #
  # listings = root.listings(target_url=None)
  # for listing in listings:
  #   if not any(folder.path == listing.path for folder in folders):
  #     folders.append(RepositoryFolder(listing.path, listing.url, root))

  # # Collect repositories that exist at the wrong path.
  # for repo in workspace.repos:
  #   # If this folder isn't aggregated yet.
  #   if not any(folder.path == repo.path for folder in folders):
  #     # If a listing matches the url
  #     for listing in listings:
  #       if gordion.utils.compare_urls(repo.handle.remotes.origin.url, listing.url):
  #         folders.append(WrongPathRepositoryFolder(repo.path))
  #         break

  # TODO: Collect any pure duplicate repos.
  # for repo in workspace.repos:
  #   # If this folder isn't aggregated yet.
  #   if not any(folder.path == repo.path for folder in folders):
  #     for other_repo in workspace.repos:
  #       if other_repo.path != repo.path:
  #         if gordion.utils.compare_urls(repo.handle.remotes.origin.url,
  #                                       other_repo.handle.remotes.origin.url):
  #           folders.append(DuplicateRepositoryFolder(repo.path))

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
