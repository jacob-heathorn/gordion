#!/usr/bin/env python3

import argparse
import gordion
import os


def main(argv=None):
  parser = argparse.ArgumentParser(description="Process some applications.")
  parser.add_argument('-u', '--update', action='store_true', help='Update the gordion tree')
  parser.add_argument('-r', '--root', action='store_true', help='Print the gordion root')
  parser.add_argument('-s', '--status', action='store_true', help='Show the gordion status')
  args = parser.parse_args()

  try:
    # Get the root gordion repository path
    root_path = gordion.app.root.gordion_root(os.getcwd())

    # Setup the gordion/ folder store object.
    store = gordion.Store()
    store.setup(root_path)

    # Update.
    if args.update:
      with gordion.utils.pushd(root_path):
        root = gordion.Tree(root_path)
        branch = None
        if not root.handle.head.is_detached:
          branch = root.handle.active_branch.name
        root.update(root.handle.head.commit.hexsha, branch)

    # Print Root.
    if args.root:
      print(f"{root_path}")

    # Print status.
    if args.status:
      with gordion.utils.pushd(root_path):
        root = gordion.Tree(root_path)
        print(gordion.app.status.terminal_status(root))

  except Exception as e:
    gordion.utils.print_exception(e=e, trace=True)


if __name__ == "__main__":
    main()
