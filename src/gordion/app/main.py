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
    if repo.yeditor is not None:
      return True

  return False


def gordion_root(cwd: str):
  repo_root = get_repository_root(os.getcwd())
  #print(f"repo_root: {repo_root}")

  if repo_root is None:
    if is_gordion_repository(repo_root):
      return repo_root
    else:
      raise gordion.NotAGordionRepositoryError(cwd)
  else:
    # Find parent gordion folder
    parent_gordion_path = gordion.find_ancestor_dir(repo_root, 'gordion')
    if parent_gordion_path is None:
      if is_gordion_repository(repo_root):
        return repo_root
      else:
        raise gordion.NotAGordionRepositoryError(cwd)
    else:
      #print(f"parent_gordion_path: {parent_gordion_path}")
      # Check that the parent gordion folder is in a repository whose root is one level above.
      parent_root = get_repository_root(parent_gordion_path)
      if parent_root != os.path.dirname(parent_gordion_path):
        # TODO verify repo_root is a gordion repo (i.e has gordion.yaml)
        return repo_root
      else:
        # Check that the parent yaml file lists the original repo_root
        repo_root_relative = os.path.relpath(repo_root, parent_gordion_path)
        parent = gordion.Repository(parent_root)
        if parent.yeditor is not None:
          for name, entry in parent.yeditor.yaml_data['repositories'].items():
            #print(f"name: {name}")
            #print(f"entry gpath: {parent.yeditor.read_repository_gpath(name)}, repo_root_relative: {repo_root_relative}")
            if parent.yeditor.read_repository_gpath(name) == repo_root_relative:
              #print("Found parent entry")
              return parent.path


def main(argv=None):
  parser = argparse.ArgumentParser(description="Process some applications.")
  parser.add_argument('-u', '--update', action='store_true', help='Update the gordion tree')
  parser.add_argument('-r', '--root', action='store_true', help='Print the gordion root')
  args = parser.parse_args()

  if args.update:
    pass

  if args.root:
    cwd = os.getcwd()
    print(f"{gordion_root(cwd)}")


if __name__ == "__main__":
    main()
