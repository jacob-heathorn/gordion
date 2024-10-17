import os
from .folder import Folder
from .repository_folder import RepositoryFolder
from .not_found_repository_folder import NotFoundRepositoryFolder
import gordion
from typing import List, Optional


def set_parent(folder, folders):
  for f in folders:

    if os.path.dirname(folder.path) == f.path:
      f.add_child(folder)


def find_folder_by_path(folders, path) -> Optional[Folder]:
  for folder in folders:
    if folder.path == path:
      return folder
  return None


# def trace_add(tree: gordion.Tree, folders):
#   # Get all listings in the tree.
#     if self.repo.yeditor.exists():
#       for child_name, child_info in self.repo.yeditor.yaml_data['repositories'].items():
#         child_url = child_info['url']
#         child_tag = child_info['tag']


def terminal_status(root: gordion.Tree) -> str:
  """
  Returns a status string indicating the status of each repository in the tree, which looks cute in
  a terminal.
  """

  # Add workspace and root repository folders.
  workspace = gordion.Workspace()
  folders = [Folder(workspace.path)]
  # folders.append(RepositoryFolder(root.repo, root))
  # extend_folders_from_mainline(folders, root, root)

  not_found_listings = []

  # Trace the mainline tree.
  for listing in root.listings(name=None, url=None):
    repo = workspace.get_repository(name=listing.name)
    if repo:
      if gordion.utils.compare_urls(listing.url, repo.url):
        if not any(folder.path == repo.path for folder in folders):
          folders.append(RepositoryFolder(repo, root))
    else:
      not_found_listings.append(listing)

  # DUPLICATES. Find any repository that has a duplicate by name or url. Add to the header. If there
  # is a repo folder for it, mark it duplicate accordingly.
  duplicates: List[gordion.Repository] = []
  for _, repo in workspace.repos().items():
    for _, other in workspace.repos().items():
      if other.path != repo.path:
        # Check for duplicate name
        if other.name == repo.name:
          if not any(duplicate.path == repo.path for duplicate in duplicates):
            duplicates.append(repo)

          folder = find_folder_by_path(repo.path)
          if folder:
            folder.has_duplicate = True

        # Check for duplicate URL
        if gordion.utils.compare_urls(other.url, repo.url):
          if not any(duplicate.path == repo.path for duplicate in duplicates):
            duplicates.append(repo)

          folder = find_folder_by_path(folders, repo.path)
          if folder:
            folder.has_duplicate = True

  # Duplicates header.
  error_header = ""
  if len(duplicates) > 0:
    error_header += gordion.utils.bold_red("Duplicates:\n")
    for duplicate in duplicates:
      error_header += gordion.utils.red(f"* {duplicate.path} ({duplicate.url})\n")
    error_header += "\n"

  # NOT FOUND. List all repositories that were not found, only if they are really not on disk. It
  # could be that they were not found becuase of duplicates, so inore duplicates here.
  not_found_to_show = []
  for listing in not_found_listings:
    # TODO bug here. Not showing repo c
    for duplicate in duplicates:
      if not duplicate.name == listing.name:
        not_found_to_show.append(listing)
        break

  if len(not_found_to_show) > 0:
    error_header += gordion.utils.bold_red("Not Found:\n")
    # TODO share duplicate code?
    for listing in not_found_to_show:
      assert (listing.file)
      error_header += gordion.utils.bold_red(f"* {listing.name}\n")
    error_header += "\n"
    # TODO: LISTED URL INCOHERENCES
    # TODO: LISTED TAG INCOHERENCES

    # for _, repo in workspace.repos().items():
    #   folder = RepositoryFolder(repo, root)
    #   folders.append(folder)

    #   # Check if the folder is listed by mainline or the workspace.
    #   if root.is_listed(repo):
    #     folder.is_listed_by_root = True
    #   else:
    #     if workspace.is_listed(repo):
    #       folder.mute = True
    #       folder.is_listed_by_workspace = True

    #   # Check for duplicate named repositories.
    #   for _, other in workspace.repos().items():
    #     if other.path != repo.path:
    #       if other.name == repo.name:
    #         folder.has_duplicate_name = True
    #         folder.mute = False
    #       if gordion.utils.compare_urls(other.url, repo.url):
    #         folder.has_duplicate_url = True
    #         folder.mute = False

    # # Add not found repository folders
    # root_listings = root.listings(name=None, url=None)
    # for listing in root_listings:
    #   all = workspace.working(name=listing.name, url=None)
    #   all.update(workspace.dependencies(name=listing.name, url=None))
    #   if len(all) == 0:
    #     path = os.path.join(workspace.dependencies_path, listing.name)
    #     if not any(folder.path == path for folder in folders):
    #       # TODO handle situation where non-repo file or folder already exists here. In-fact anywhere
    #       # in dependencies.
    #       folders.append(NotFoundRepositoryFolder(path))

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

  return error_header + folders[0].terminal_status()
