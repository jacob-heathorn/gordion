#!/usr/bin/env python3

import argparse
import gordion
import os
import git


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
    repo = gordion.Repository(path)
    if repo.yeditor.exists():
      return True

  return False


def gordion_root(cwd: str):
  current_repo_path = get_repository_root(os.getcwd())

  # If we are not in a git repository, then we are not in a gordion repository.
  if current_repo_path is None:
    raise gordion.NotAGordionRepositoryError()

  # We are in a git repository.
  else:
    # Find parent gordion folder.
    parent_gordion_path = gordion.find_ancestor_dir(current_repo_path, 'gordion')

    # If a parent gordion folder does not exist, then we just return the current git repository if
    # it is gordion.
    if parent_gordion_path is None:
      if is_gordion_repository(current_repo_path):
        return current_repo_path
      else:
        raise gordion.NotAGordionRepositoryError()

    # A parent gordion folder exists.
    else:
      # Get the parent git repository containing the parent gordion folder.
      parent_root = get_repository_root(parent_gordion_path)

      # If the parent git repository is not one level above the /gordion folder, then it is not
      # managing it. Just return the current repository if it is gordion.
      if parent_root != os.path.dirname(parent_gordion_path):
        if is_gordion_repository(current_repo_path):
          return current_repo_path
        else:
          raise gordion.NotAGordionRepositoryError()

      # The parent git repository is one level above the parent /gordion folder
      else:
        # Make sure the parent git repository is a gordion repository. Theoritically, we could just
        # be in a gordion folder in a non-gordion git repository. In that case the parent is not
        # managing the current repo, so just return the current repo if it is gordion.
        if not is_gordion_repository(parent_root):
          if is_gordion_repository(current_repo_path):
            return current_repo_path
          else:
            raise gordion.NotAGordionRepositoryError()

        # The parent git repository is gordion.
        else:
          # Check that the parent gordion.yaml file lists the current repo.
          parent = gordion.Repository(parent_root)
          assert parent.yeditor.exists()
          repo_root_relative = os.path.relpath(current_repo_path, parent_gordion_path)
          for name, _ in parent.yeditor.yaml_data['repositories'].items():
            if parent.yeditor.read_repository_gpath(name) == repo_root_relative:
              return parent.path

          # Could not find a parent entry for the current repository. The current repo might be a
          # repository that used to be managed by the parent gordion repo, but is not anymore. In
          # this case, we generate a unique error to be safely indicate the current repo is
          # dangling.
          raise gordion.DanglingGordionRepositoryError(current_repo_path, parent.path)


def main(argv=None):
  parser = argparse.ArgumentParser(description="Process some applications.")
  parser.add_argument('-u', '--update', action='store_true', help='Update the gordion tree')
  parser.add_argument('-r', '--root', action='store_true', help='Print the gordion root')
  args = parser.parse_args()

  if args.update:
    pass

  if args.root:
    cwd = os.getcwd()
    try:
      print(f"{gordion_root(cwd)}")
    except Exception as e:
      gordion.utils.print_exception(e)


if __name__ == "__main__":
    main()
