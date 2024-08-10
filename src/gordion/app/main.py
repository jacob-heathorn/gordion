#!/usr/bin/env python3

import argparse
import gordion
import os


def main(argv=None):
  parser = argparse.ArgumentParser(description="Process some applications.")
  parser.add_argument('-u', '--update', action='store_true', help='Update the gordion tree')
  parser.add_argument('-r', '--root', action='store_true', help='Print the gordion root')
  args = parser.parse_args()

  try:
    # Get the root gordion repository path
    root_path = gordion.app.root.gordion_root(os.getcwd())

    # Setup the gordion/ folder store object.
    store = gordion.Store()
    store.setup(root_path)

    # Update
    if args.update:
      with gordion.utils.pushd(root_path):
        root = gordion.Tree(root_path)
        branch = None
        if not root.handle.head.is_detached:
          branch = root.handle.active_branch.name
        root.update(root.handle.head.commit.hexsha, branch)

    # Return root
    if args.root:
      print(f"{root_path}")

  except Exception as e:
    gordion.utils.print_exception(e)


if __name__ == "__main__":
    main()
