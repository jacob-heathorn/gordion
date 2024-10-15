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


# def extend_folders_from_mainline(folders, tree, root) -> List[Folder]:
#   workspace = gordion.Workspace()
#   if tree.repo.yeditor.exists():
#     for child_name, child_info in tree.repo.yeditor.yaml_data['repositories'].items():
#       child_url = child_info['url']
#       child_tag = child_info['tag']

#       working = workspace.working(name=child_name, url=None)
#       dependencies = workspace.dependencies(name=child_name, url=None)

#       if len(working) == 0:
#         if len(dependencies) == 0:
#           # TODO if there is already a repo or file here, handle these situations, otherwise just
#           # display NOT_FOUND.
#           path = os.path.join(workspace.dependencies_path, child_name)
#           if not any(folder.path == path for folder in folders):
#             folders.append(NotFoundRepositoryFolder(path))
#         elif len(dependencies) == 1:
#           child_repo = next(iter(dependencies.values()))
#           is_wrong_url = gordion.utils.compare_urls(child_repo.url, child_url)

#           # Create the repository folder if not yet created.
#           if not any(folder.path == path for folder in folders):
#             folders.append(RepositoryFolder(child_repo, root))
#           folder = find_folder_by_path(folders, child_repo.path)

#           # Mark WRONG_URL if necessary.
#           folder.is_wrong_url = is_wrong_url

#       # Add child repository folder if we found it.
#       if child_repo:
#         # Create a new repository folder if it is not already existing.
#         if not any(folder.path == child_repo.path for folder in folders):
#           folders.append(RepositoryFolder(child_repo, root))

#         # Mark WRONG_NAME if necessary.
#         folder = find_folder_by_path(folders, child_repo.path)
#         if child_name != child_repo.name:
#           folder.wrong_name = True

#         # Mark HAS_DUPLICATE if necessary.
#         for _, workspace_repo in workspace.repos().items():
#           if workspace_repo.path != child_repo.path:
#             if gordion.utils.compare_urls(workspace_repo.url, child_repo.url):
#               folder.has_duplicate = True

#         # Recurse into the child repository if it has the correct commit.
#         child_listed_commit = child_repo._verify_tag(child_tag)
#         if child_repo.handle.head.commit == child_listed_commit:
#           child_tree = gordion.Tree(child_repo)
#           extend_folders_from_mainline(folders, child_tree, root)

#       # Otherwise add a NOT_FOUND repository folder.
#       else:
#         # TODO if there is already a repo or file here, handle these situations, otherwise just
#         # display NOT_FOUND.
#         path = os.path.join(workspace.dependencies_path, child_name)
#         if not any(folder.path == path for folder in folders):
#           folders.append(NotFoundRepositoryFolder(path))


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

  for _, repo in workspace.repos().items():
    folder = RepositoryFolder(repo, root)
    folders.append(folder)

    # Check if the folder is listed by mainline or the workspace.
    if root.is_listed(repo):
      folder.is_listed_by_root = True
    else:
      if workspace.is_listed(repo):
        folder.mute = True
        folder.is_listed_by_workspace = True

    # Check for duplicate named repositories.
    for _, other in workspace.repos().items():
      if other.path != repo.path:
        if other.name == repo.name:
          folder.has_duplicate_name = True
          folder.mute = False
        if gordion.utils.compare_urls(other.url, repo.url):
          folder.has_duplicate_url = True
          folder.mute = False

  # Add not found repository folders
  root_listings = root.listings(name=None, url=None)
  for listing in root_listings:
    all = workspace.working(name=listing.name, url=None)
    all.update(workspace.dependencies(name=listing.name, url=None))
    if len(all) == 0:
      path = os.path.join(workspace.dependencies_path, listing.name)
      if not any(folder.path == path for folder in folders):
        # TODO handle situation where non-repo file or folder already exists here. In-fact anywhere
        # in dependencies.
        folders.append(NotFoundRepositoryFolder(path))

    # # Add dependency folders
    # dependencies = workspace.dependencies(name=None, url=None)
    # root_listings = root.listings(name=None, url=None)
    # for _, dependency in dependencies.items():
    #   named_listings = [listing for listing in root_listings if listing.name == dependency.name]
    #   if len(named_listings) == 1:
    #     folders.append(RepositoryFolder(dependency, root))
    #   else:
    #     assert len(named_listings) > 1

    #   if root.

    # listings = root.listings(name=None, url=None)
    # for listing in listings:
    #   repo = workspace.get_repository(name=listing.name)
    #   if repo:
    #     if not any(folder.path == repo.path for folder in folders):
    #       folders.append(RepositoryFolder(repo, root))
    #   else:
    #     path = os.path.join(workspace.dependencies_path, listing.name)
    #     if not any(folder.path == path for folder in folders):
    #       folders.append(NotFoundRepositoryFolder(path))

    # # Add any repo in /dependencies that is not listed by the workspace.
    # dependencies = workspace.dependencies(name=None, url=None)
    # for key, repo in dependencies.items():
    #   if not workspace.is_listed(repo):
    #     if not any(folder.path == repo.path for folder in folders):
    #       folders.append(RepositoryFolder(repo, root))

    # # Also any duplicates.
    # for key, repo in workspace.repos().items():
    #   duplicates = workspace.working(name=None, url=repo.url)
    #   duplicates.update(workspace.dependencies(name=None, url=repo.url))
    #   if len(duplicates) > 1:
    #     for key, duplicate in duplicates.items():
    #       if not any(folder.path == duplicate.path for folder in folders):
    #         folders.append(RepositoryFolder(duplicate, root))

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
