import os
from .folder import Folder
from .repository_folder import RepositoryFolder
import gordion
from typing import List, Optional, Tuple


def set_parent(folder, folders):
  for f in folders:

    if os.path.dirname(folder.path) == f.path:
      f.add_child(folder)


def find_folder_by_path(folders, path) -> Optional[Folder]:
  for folder in folders:
    if folder.path == path:
      return folder
  return None


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
  tag_incoherent_listings_tuples: List[Tuple[gordion.Tree.Listing, Optional[str]]] = []

  # Trace the mainline tree.
  root_listings = root.listings(name=None, url=None)
  for listing in root_listings:
    repo = workspace.get_repository(name=listing.name)
    if repo:
      if gordion.utils.compare_urls(listing.url, repo.url):
        if not any(folder.path == repo.path for folder in folders):
          folder = RepositoryFolder(repo, root)
          folders.append(folder)

          ####

          folder_listings = [listing for listing in root_listings if repo.name == listing.name]
          folder_listings = [
              listing for listing in folder_listings if gordion.utils.compare_urls(
                  repo.url, listing.url)]

          folder_good_tag_listings = []
          folder_bad_tag_listings = []
          unique_good_tags = set()
          for folder_listing in folder_listings:
            try:
              commit = repo._verify_tag(folder_listing.tag)
              folder_good_tag_listings.append(folder_listing)
              unique_good_tags.add(commit.hexsha)
            except Exception:
              folder_bad_tag_listings.append(listing)

          if len(unique_good_tags) > 1 or len(folder_bad_tag_listings) > 0:
            folder.incoherent_tag = True
            for al in folder_good_tag_listings:
              at = (al, repo._verify_tag(al.tag).hexsha)
              tag_incoherent_listings_tuples.append(at)
            for al in folder_bad_tag_listings:
              tag_incoherent_listings_tuples.append((al, None))
          else:
            tag = list(unique_good_tags)[0]
            if tag == repo.handle.head.commit.hexsha:
              folder.correct_tag = True

          ####
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

          folder = find_folder_by_path(folders, repo.path)
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
    error_header += gordion.utils.bold_red("\nDuplicates:\n")
    for duplicate in duplicates:
      error_header += gordion.utils.red(f"* {duplicate.path} ({duplicate.url})\n")

  # NOT FOUND. List all repositories that were not found by the root trace.
  if len(not_found_listings) > 0:
    error_header += gordion.utils.bold_red("\nNot Found:\n")
    for listing in not_found_listings:
      listing_str = f"* {gordion.utils.filelink(listing.file, listing.file)} : {listing.name} : "
      listing_str += f"{gordion.utils.hyperlink(listing.url, listing.url)}\n"
      error_header += gordion.utils.red(listing_str)

  # URL INCOHERENCES.
  all_conflicted = []
  for listing in root_listings:
    url_conflicted = [other for other in root_listings if other.name ==
                      listing.name and other.url != listing.url]
    name_conflicted = [other for other in root_listings if other.name !=
                       listing.name and other.url == listing.url]
    all_conflicted.extend(url_conflicted)
    all_conflicted.extend(name_conflicted)

  if len(all_conflicted):
    error_header += gordion.utils.bold_red("\nURL Incoherences:\n")
    for listing in all_conflicted:
      listing_str = "* "
      if listing.file:
        listing_str += f"{gordion.utils.filelink(listing.file, listing.file)} : {listing.name} : "
      else:
        listing_str += f"{listing.name}* : "
      listing_str += f"{gordion.utils.hyperlink(listing.url, listing.url)}\n"
      error_header += gordion.utils.red(listing_str)

  # TAG INCOHERENCES
  if len(tag_incoherent_listings_tuples) > 0:
    error_header += gordion.utils.bold_red("\nTag Incoherences:\n")
    for tuple in tag_incoherent_listings_tuples:
      listing = tuple[0]
      resolved_tag = tuple[1]
      listing_str = "* "
      if listing.file:
        partial_path = os.path.join(
            os.path.basename(
                os.path.dirname(
                    listing.file)), os.path.basename(
                listing.file))
        listing_str += f"{gordion.utils.filelink(listing.file, partial_path)} : {listing.name} : "
      else:
        listing_str += f"{listing.name}* : "
      if resolved_tag:
        listing_str += f"{resolved_tag}\n"
      else:
        listing_str += f"{listing.tag} (BAD TAG)\n"
      error_header += gordion.utils.red(listing_str)

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

  if error_header:
    error_header += "\n"

  return error_header + folders[0].terminal_status()
