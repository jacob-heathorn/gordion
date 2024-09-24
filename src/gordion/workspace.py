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
        if is_gordion_repository(str(child)):
          return str(current_path)

  # Return the original path parent.
  return str(path.parent)


# TODO comment header, potential rename. Mention must be in a gordion repository.
def find_tree(path):
  current_repo_path = get_repository_root(path)

  # If we are not in a git repository, then we are not in a gordion repository.
  if current_repo_path is None:
    raise gordion.NotAGordionRepositoryError()

  if is_gordion_repository(current_repo_path):
    return gordion.Tree(current_repo_path)
  else:
    raise gordion.NotAGordionRepositoryError()
