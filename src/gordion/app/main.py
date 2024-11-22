#!/usr/bin/env python3

import argparse
import gordion
import os
import cProfile
import pstats
import sys

PROFILE = False


def main(argv=None):
  if PROFILE:
    profiler = cProfile.Profile()
    profiler.enable()

  # Base parser
  parser = argparse.ArgumentParser(prog='gordion', description="Gordion user commands")
  parser.add_argument('-u', '--update', action='store_true', help='Update the gordion tree')
  parser.add_argument('-w', '--workspace', action='store_true', help='Print the gordion workspace')
  parser.add_argument('-f', '--find', type=str, help='Find full path to repository name')
  parser.add_argument('-e', '--expand', type=str, help='Expand gordion env variables in a file')
  parser.add_argument('-o', '--output', type=str, help='Output file after expansion')
  parser.add_argument('-a', '--add', action='store_true', help='git add in all repositories')

  # Status parser
  subparsers = parser.add_subparsers(dest='command', help='Git analog commands')
  parser_status = subparsers.add_parser('status', help='Show the gordion status')
  parser_status.add_argument('-v', '--verbose', action='store_true', help='verbose')

  # Clean parser
  parser_clean = subparsers.add_parser('clean', help='Git clean in all repositories')
  parser_clean.add_argument('-f', '--force', action='store_true',
                            help='Force the clean by removing all untracked files')
  parser_clean.add_argument(
      '-d',
      '--dirs',
      action='store_true',
      help='Remove untracked directories in addition to untracked files')
  parser_clean.add_argument(
      '-x',
      '--extra',
      action='store_true',
      help='Remove only files ignored by git, excluding those specified by .gitignore')

  # Add parser
  parser_add = subparsers.add_parser('add', help='Git add <pathspec> in all repositories')
  parser_add.add_argument('pathspec', nargs='+', help='Pathspec to add to staging')

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

    # Print the respository path.
    if args.find:
      repo = workspace.get_repository_or_throw(args.find)
      print(repo.path)

    # Expand file.
    if args.expand:
      gordion.app.expand(args.expand, args.output)

    # Git Analogs
    #
    if args.command == 'status':
      root = gordion.Tree.find(os.getcwd())
      print(gordion.app.status.terminal_status(root, args.verbose))

    if args.command == 'clean':
      root = gordion.Tree.find(os.getcwd())
      root.clean(args.force, args.dirs, args.extra)

    # TODO use pthspec
    if args.command == 'add':
      root = gordion.Tree.find(os.getcwd())
      branch_name = None
      if root.repo.handle.active_branch:
        branch_name = root.repo.handle.active_branch.name
      root.add(branch_name)

  except Exception as e:
    gordion.utils.print_exception(e=e, trace=False)
    sys.exit(1)

  if PROFILE:
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('cumulative')
    stats.print_stats()
