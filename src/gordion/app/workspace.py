import gordion
import os
import git
from pathlib import Path


def get_repository_root(cwd: str):
  try:
    # Create a Repo object pointing to the current directory
    repo = git.Repo(cwd, search_parent_directories=True)
    # Get the git root directory
    git_root = repo.git.rev_parse("--show-toplevel")
    return git_root
  except Exception:
    return None


def is_gordion_repository(path: str) -> bool:
  if gordion.Repository._exists(path):
    yeditor = gordion.YamlEditor(os.path.join(path, 'gordion.yaml'))
    if yeditor.exists():
      return True

  return False


def does_directory_contain_gordion_repository(path: str):
    # Ensure the path is a directory
  if not os.path.isdir(path):
    return False

  # Loop over each entry in the directory at the given path
  for entry in os.listdir(path):
      # Construct the full path of the entry
    entry_path = os.path.join(path, entry)

    # Check if the entry is a directory and if it is a Gordion repository
    if os.path.isdir(entry_path) and is_gordion_repository(entry_path):
      return True

  # Return False if no Gordion repository is found in the subdirectories
  return False


def find_workspace(path: str) -> str:
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

        if does_directory_contain_gordion_repository(str(child)):
          return str(child)

  # Return the original path parent.
  return str(path.parent)


# TODO comment header, potential rename. Mention must be in a gordion repository.
def workspace_root(path):
  current_repo_path = get_repository_root(path)

  # If we are not in a git repository, then we are not in a gordion repository.
  if current_repo_path is None:
    raise gordion.NotAGordionRepositoryError()

  if is_gordion_repository(current_repo_path):
    return find_workspace(path)
  else:
    raise gordion.NotAGordionRepositoryError()

  # # We are in a git repository.
  # else:
  #   # Find parent gordion folder.
  #   parent_gordion_path = gordion.find_ancestor_dir(current_repo_path, 'gordion')

  #   # If a parent gordion folder does not exist, then we just return the current git repository if
  #   # it is gordion.
  #   if parent_gordion_path is None:
  #     if is_gordion_repository(current_repo_path):
  #       return current_repo_path
  #     else:
  #       raise gordion.NotAGordionRepositoryError()

  #   # A parent gordion folder exists.
  #   else:
  #     # Get the parent git repository containing the parent gordion folder.
  #     parent_root = get_repository_root(parent_gordion_path)

  #     # If the parent git repository is not one level above the /gordion folder, then it is not
  #     # managing it. Just return the current repository if it is gordion.
  #     if parent_root != os.path.dirname(parent_gordion_path):
  #       if is_gordion_repository(current_repo_path):
  #         return current_repo_path
  #       else:
  #         raise gordion.NotAGordionRepositoryError()

  #     # The parent git repository is one level above the parent /gordion folder
  #     else:
  #       # Make sure the parent git repository is a gordion repository. Theoritically, we could just
  #       # be in a gordion folder in a non-gordion git repository. In that case the parent is not
  #       # managing the current repo, so just return the current repo if it is gordion.
  #       if not is_gordion_repository(parent_root):
  #         if is_gordion_repository(current_repo_path):
  #           return current_repo_path
  #         else:
  #           raise gordion.NotAGordionRepositoryError()

  #       # The parent git repository is gordion.
  #       else:
  #         # Check that the parent gordion.yaml file lists the current repo.
  #         parent_yeditor = gordion.YamlEditor(os.path.join(parent_root, 'gordion.yaml'))
  #         assert parent_yeditor.exists()
  #         repo_root_relative = os.path.relpath(current_repo_path, parent_gordion_path)
  #         for name, _ in parent_yeditor.yaml_data['repositories'].items():
  #           if parent_yeditor.read_repository_gpath(name) == repo_root_relative:
  #             return parent_root

  #         # Could not find a parent entry for the current repository. The current repo might be a
  #         # repository that used to be managed by the parent gordion repo, but is not anymore. In
  #         # this case, we generate a unique error to be safely indicate the current repo is
  #         # dangling.
  #         raise gordion.DanglingGordionRepositoryError(current_repo_path, parent_root)
