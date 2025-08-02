import os
from .folder import Folder
from .repository_folder import RepositoryFolder
import gordion
from typing import List, Optional


def set_parent(folder, folders):
  for f in folders:

    if os.path.dirname(folder.path) == f.path:
      f.add_child(folder)


def find_folder_by_path(folders: List[Folder], path: str) -> Optional[Folder]:
  for folder in folders:
    if folder.path == path:
      return folder
  return None


def get_tag_incoherent_listings(folder, root_listings) -> List[gordion.Tree.Listing]:
  repo = folder.repo
  listings = [listing for listing in root_listings if repo.name == listing.name]
  listings = [listing for listing in listings if gordion.utils.compare_urls(repo.url, listing.url)]

  unique_good_tags = set()
  for listing in listings:
    commit = repo.verify_tag_nothrow(listing.tag)
    if commit:
      unique_good_tags.add(commit.hexsha)
    else:
      folder.incoherent_tag = True

  if len(unique_good_tags) > 1:
    folder.incoherent_tag = True
  else:
    if len(unique_good_tags) > 0:
      if repo.handle.head.commit.hexsha == list(unique_good_tags)[0]:
        folder.correct_tag = True

  if folder.incoherent_tag:
    return listings

  return []


def terminal_status(root: gordion.Tree, verbose: bool = False) -> str:
  """
  Returns a status string indicating the status of each repository in the tree, which looks cute in
  a terminal.
  """

  # Add workspace and root repository folders.
  workspace = gordion.Workspace()
  folders: List[Folder] = [Folder(workspace.path)]

  # Trace the mainline tree.
  not_found_listings = []
  all_tag_incoherent_listings: List[gordion.Tree.Listing] = []
  root_listings, _ = root.listings(name=None, url=None)
  for listing in root_listings:
    repo = workspace.get_repository(name=listing.name)
    if repo:
      if gordion.utils.compare_urls(listing.url, repo.url):
        if not any(folder.path == repo.path for folder in folders):
          folder = RepositoryFolder(repo, root, verbose)
          folders.append(folder)
          tag_incoherent_listings = get_tag_incoherent_listings(folder, root_listings)
          all_tag_incoherent_listings.extend(tag_incoherent_listings)
      else:
        not_found_listings.append(listing)
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

          folder = find_folder_by_path(folders, repo.path)  # type: ignore[assignment]
          if folder:
            folder.has_duplicate = True

        # Check for duplicate URL
        if gordion.utils.compare_urls(other.url, repo.url):
          if not any(duplicate.path == repo.path for duplicate in duplicates):
            duplicates.append(repo)

          folder = find_folder_by_path(folders, repo.path)  # type: ignore[assignment]
          if folder:
            folder.has_duplicate = True

  # Duplicates header.
  error_header = ""
  if len(duplicates) > 0:
    error_header += gordion.utils.bold_red("\nDuplicates:\n")
    for duplicate in duplicates:
      error_header += gordion.utils.red(f"* {duplicate.path} ({duplicate.url})\n")

  # NOT FOUND. List all repositories that were not found by the root trace.
  if len(not_found_listings) > 0:
    error_header += gordion.utils.bold_red("\nNot Found:\n")
    for listing in not_found_listings:
      listing_str = gordion.Tree.format_listing_url(listing)
      error_header += gordion.utils.red(listing_str + "\n")

  # URL INCOHERENCES.
  all_incoherences = []
  for listing in root_listings:
    url_incoherences = [listing for other in root_listings if other.name ==  # noqa: W504
                        listing.name and other.url != listing.url]
    name_incoherences = [listing for other in root_listings if other.name !=  # noqa: W504
                         listing.name and other.url == listing.url]
    # Combine the two lists.
    incoherences = url_incoherences.copy()
    incoherences.extend(name_incoherences)

    # Add to all_conflicted, checking for duplicates.
    for nc in incoherences:
      if nc not in all_incoherences:
        all_incoherences.append(nc)

  if len(all_incoherences) > 0:
    all_incoherences.sort(key=lambda listing: listing.name)
    error_header += gordion.utils.bold_red("\nURL Incoherences:\n")
    for listing in all_incoherences:
      listing_str = gordion.Tree.format_listing_url(listing)
      error_header += gordion.utils.red(listing_str + "\n")

  # TAG INCOHERENCES
  if len(all_tag_incoherent_listings) > 0:
    error_header += gordion.utils.bold_red("\nTag Incoherences:\n")
    for listing in all_tag_incoherent_listings:
      listing_str = gordion.Tree.format_listing_tag(listing)
      error_header += gordion.utils.red(listing_str + "\n")

  # Filter out folders that are in the dependencies cache
  display_folders: List[Folder] = []
  for folder in folders:  # type: ignore[assignment]
    # Only include folders that are within the workspace path
    if folder.path.startswith(workspace.path):
      display_folders.append(folder)

  # Add intermediary folders for display folders only
  intermediary_folders: List[Folder] = []
  workspace_folder: Folder = display_folders[0]
  for folder in display_folders[1:]:  # type: ignore[assignment]
    relative_path = os.path.relpath(folder.path, workspace_folder.path)
    relative_path_parts = relative_path.strip(os.sep).split(os.sep)
    current_path = workspace_folder.path

    # Loop over each part of the path
    for part in relative_path_parts:
      current_path = os.path.join(current_path, part)
      # Add new folder if it does not exist
      if not any(folder.path == current_path for folder in display_folders):
        if not any(folder.path == current_path for folder in intermediary_folders):
          intermediary_folders.append(Folder(current_path))
  display_folders.extend(intermediary_folders)

  # 2) Alphabetize the list based on path.
  display_folders = sorted(display_folders, key=lambda folder: folder.path)

  # 3) Set the heirarchy of folders.
  for folder in display_folders[1:]:  # type: ignore[assignment]
    set_parent(folder, display_folders)

  if error_header:
    error_header += "\n"

  return error_header + display_folders[0].terminal_status()
