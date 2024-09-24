#!/usr/bin/env python3

import argparse
import gordion
import os


def main(argv=None):
  parser = argparse.ArgumentParser(description="Process some applications.")
  parser.add_argument('-u', '--update', action='store_true', help='Update the gordion tree')
  parser.add_argument('-w', '--workspace', action='store_true', help='Print the gordion workspace')
  parser.add_argument('-s', '--status', action='store_true', help='Show the gordion status')
  args = parser.parse_args()

  try:
    # Get the root gordion repository path.
    workspace = gordion.app.workspace.workspace_root(os.getcwd())

    # Update.
    if args.update:
      with gordion.utils.pushd(workspace):
        root = gordion.Tree(workspace)
        branch = None
        if not root.handle.head.is_detached:
          branch = root.handle.active_branch.name
        root.update(root.handle.head.commit.hexsha, branch)

    # Print the workspace path.
    if args.workspace:
      print(f"{workspace}")

    # Print status.
    if args.status:
      with gordion.utils.pushd(workspace):
        root = gordion.Tree(workspace)
        print(gordion.app.status.terminal_status(root))

  except Exception as e:
    gordion.utils.print_exception(e=e, trace=True)


if __name__ == "__main__":
  main()
