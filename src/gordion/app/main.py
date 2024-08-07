#!/usr/bin/env python3

import argparse
import gordion
import os


# def list_repository_paths(root):
#   # Initialize the list with the current root path
#   paths = [root.path]

#   # Recursively gather paths from child directories
#   for child in root.children:
#     paths.extend(list_repository_paths(child))

#   return paths


def aggregate_repositories_map(root):
  repos = {root.path: root}

  for dirpath, dirnames, _ in os.walk(os.path.join(root.path, 'gordion'), topdown=True):
    for dirname in dirnames:
      full_dirpath = os.path.join(dirpath, dirname)
      if gordion.Repository._exists(full_dirpath):
        repos[full_dirpath] = gordion.Repository(full_dirpath)

  return repos


def print_status(root):
  repos = aggregate_repositories_map(root)
  for key in sorted(repos.keys()):
    print(f"{key}: {repos[key]}")


def main(argv=None):
  parser = argparse.ArgumentParser(description="Process some applications.")
  parser.add_argument('-u', '--update', action='store_true', help='Update the gordion tree')
  parser.add_argument('-r', '--root', action='store_true', help='Print the gordion root')
  parser.add_argument('-s', '--status', action='store_true', help='Show the gordion status')
  args = parser.parse_args()

  try:
    if args.update:
      root_path = gordion.app.root.gordion_root()
      with gordion.utils.pushd(root_path):
        root = gordion.Repository(root_path)
        branch = None
        if not root.handle.head.is_detached:
          branch = root.handle.active_branch.name
        root.update(root.handle.head.commit.hexsha, branch)

    if args.root:
      print(f"{gordion.app.root.gordion_root()}")

    if args.status:
      root_path = gordion.app.root.gordion_root()
      with gordion.utils.pushd(root_path):
        root = gordion.Repository(root_path)
        print_status(root)
        # repository_paths = list_repository_paths(root)
        # for repository_path in repository_paths:
        #   print(repository_path)
        # # print("└──")

  except Exception as e:
    gordion.utils.print_exception(e)


if __name__ == "__main__":
    main()
