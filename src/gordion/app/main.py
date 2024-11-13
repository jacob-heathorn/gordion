#!/usr/bin/env python3

import argparse
import gordion
import os
import cProfile
import pstats

PROFILE = False


def main(argv=None):
  if PROFILE:
    profiler = cProfile.Profile()
    profiler.enable()

  parser = argparse.ArgumentParser(description="Process some applications.")
  parser.add_argument('-u', '--update', action='store_true', help='Update the gordion tree')
  parser.add_argument('-w', '--workspace', action='store_true', help='Print the gordion workspace')
  parser.add_argument('-s', '--status', action='store_true', help='Show the gordion status')
  parser.add_argument('-f', '--find', type=str, help='Find full path to repository name')
  args = parser.parse_args()

  try:
    # Initialize workspace.
    workspace = gordion.Workspace()
    workspace.setup(os.getcwd())

    # Update.
    if args.update:
      root = gordion.Tree.find(os.getcwd())
      branch = None
      if not root.repo.handle.head.is_detached:
        branch = root.repo.handle.active_branch.name
      root.update(root.repo.handle.head.commit.hexsha, branch)

    # Print the workspace path.
    if args.workspace:
      print(f"{workspace.path}")

    # Print status.
    if args.status:
      root = gordion.Tree.find(os.getcwd())
      print(gordion.app.status.terminal_status(root))

    # Print the respository path.
    if args.find:
      repo = workspace.get_repository(args.find)
      if repo:
        print(repo.path)

  except Exception as e:
    gordion.utils.print_exception(e=e, trace=True)

  if PROFILE:
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('cumulative')
    stats.print_stats()
