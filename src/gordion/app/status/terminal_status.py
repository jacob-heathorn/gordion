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


def is_cache_desynced(workspace: gordion.Workspace, root: gordion.Tree) -> bool:
  """
  Check if the cache is out of sync with what's expected.
  """
  # Get all expected repositories from the tree
  expected_listings, _ = root.listings(name=None, url=None)

  for listing in expected_listings:
    # Skip the root repository itself
    if listing.name == root.repo.name:
      continue

    repo = workspace.get_repository(listing.name)

    # Check if repository exists
    if not repo:
      return True

    # Check if it's in the cache (dependency)
    if workspace.is_dependency(repo.path):
      # Check if the commit matches
      try:
        expected_commit = repo.verify_tag(listing.tag)
        if repo.handle.head.commit.hexsha != expected_commit.hexsha:
          return True
      except Exception:
        return True

  return False


def terminal_status(root: gordion.Tree, verbose: bool = False, show_cache: bool = False) -> str:
  """
  Returns a status string indicating the status of each repository in the tree, which looks cute in
  a terminal.

  Args:
    root: The root tree to display status for
    verbose: Whether to show verbose output (git status for each repo)
    show_cache: Whether to show the cache dependencies directory
  """

  # Add workspace and root repository folders.
  workspace = gordion.Workspace()

  # Check if cache is desynced
  cache_desynced = is_cache_desynced(workspace, root)

  # Create workspace folder
  workspace_folder = Folder(workspace.path)
  folders: List[Folder] = [workspace_folder]

  # If show_cache is enabled, also create the dependencies cache folder
  if show_cache and os.path.exists(workspace.dependencies_path):
    cache_folder = Folder(workspace.dependencies_path)
    folders.append(cache_folder)

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

  # DIRTY CACHED REPOSITORIES. Find any cached repository that has uncommitted changes.
  dirty_cached_repos: List[gordion.Repository] = []
  for _, repo in workspace.repos().items():
    if workspace.is_dependency(repo.path) and repo.handle.is_dirty(untracked_files=True):
      dirty_cached_repos.append(repo)

  # Duplicates header.
  error_header = ""
  if len(duplicates) > 0:
    error_header += gordion.utils.bold_red("\nDuplicates:\n")
    for duplicate in duplicates:
      error_header += gordion.utils.red(f"* {duplicate.path} ({duplicate.url})\n")

  # Dirty cached repositories header.
  if len(dirty_cached_repos) > 0:
    error_header += gordion.utils.bold_red("\nDirty Cached Repositories:\n")
    error_header += gordion.utils.red("(Changes not allowed in cached repositories!)\n")
    for repo in dirty_cached_repos:
      error_header += gordion.utils.red(f"* {repo.path}\n")

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

  # Filter out folders that are in the dependencies cache (unless show_cache is enabled)
  display_folders: List[Folder] = []
  if show_cache:
    # When show_cache is enabled, include all folders (including cache dependencies)
    display_folders = folders.copy()
  else:
    # Normal mode: only include folders within the workspace path
    for folder in folders:  # type: ignore[assignment]
      if folder.path.startswith(workspace.path):
        display_folders.append(folder)

  # Add intermediary folders for display folders only
  intermediary_folders: List[Folder] = []
  # Find root folders (folders without a parent in the list)
  root_folders = []
  for folder in display_folders:  # type: ignore[assignment]
    is_root = True
    for other in display_folders:  # type: ignore[assignment]
      if folder != other and folder.path.startswith(other.path + os.sep):
        is_root = False
        break
    if is_root:
      root_folders.append(folder)

  # For each non-root folder, add intermediary folders between it and its root
  for folder in display_folders:  # type: ignore[assignment]
    if folder not in root_folders:
      # Find the root folder for this folder
      root_folder = None
      for root in root_folders:  # type: ignore[assignment]
        if folder.path.startswith(root.path + os.sep):  # type: ignore[attr-defined]
          root_folder = root
          break

      if root_folder:
        relative_path = os.path.relpath(folder.path, root_folder.path)  # type: ignore[attr-defined]
        relative_path_parts = relative_path.strip(os.sep).split(os.sep)
        current_path = root_folder.path  # type: ignore[attr-defined]

        # Loop over each part of the path
        for part in relative_path_parts:
          current_path = os.path.join(current_path, part)
          # Add new folder if it does not exist
          if not any(f.path == current_path for f in display_folders):
            if not any(f.path == current_path for f in intermediary_folders):
              intermediary_folders.append(Folder(current_path))
  display_folders.extend(intermediary_folders)

  # 2) Alphabetize the list based on path.
  display_folders = sorted(display_folders, key=lambda folder: folder.path)

  # 3) Set the heirarchy of folders.
  for folder in display_folders[1:]:  # type: ignore[assignment]
    set_parent(folder, display_folders)

  if error_header:
    error_header += "\n"

  # Build the complete status from all root folders
  status_parts = []

  # If show_cache is enabled, show cache folder first if it exists
  if show_cache:
    for folder in display_folders:  # type: ignore[assignment]
      if folder.path == workspace.dependencies_path:
        status_parts.append(folder.terminal_status())
        break

  # Find and show the workspace folder
  workspace_folder_found = False
  for folder in display_folders:  # type: ignore[assignment]
    if folder.path == workspace.path:
      workspace_status = folder.terminal_status()

      # If cache is desynced or there are dirty cached repositories, append the message
      if cache_desynced or len(dirty_cached_repos) > 0:
        lines = workspace_status.splitlines()
        if lines:
          # Append the red (out of sync) message to the first line
          lines[0] += gordion.utils.red("  (out of sync)")
          workspace_status = "\n".join(lines)

      status_parts.append(workspace_status)
      workspace_folder_found = True
      break

  # If workspace folder not found, fall back to first folder
  if not workspace_folder_found and display_folders:
    status_parts.append(display_folders[0].terminal_status())

  # Join all parts with newlines
  full_status = "\n".join(status_parts) if status_parts else ""

  return error_header + full_status
