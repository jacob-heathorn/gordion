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

  # # Main parser setup
  # parser = argparse.ArgumentParser(prog='gordion', description="Manage gordion tasks")
  # parser.add_argument(
  #     '-s',
  #     '--silent',
  #     action='store_true',
  #     help='Run in silent mode',
  #     dest='global_silent')

  # # Setting up subparsers for specific commands under 'gordion'
  # subparsers = parser.add_subparsers(dest='command', help='Available commands')

  # # 'status' command subparser
  # parser_status = subparsers.add_parser('status', help='Show the gordion status')
  # parser_status.add_argument('-s', '--show', action='store_true',
  #                            help='Display detailed status information')

  # # 'clean' command subparser
  # parser_clean = subparsers.add_parser('clean', help='Clean gordion environment')

  # # Parse the arguments
  # args = parser.parse_args()

  # # Process based on the input
  # if args.global_silent:
  #   print("Global silent mode activated")

  # if args.command == 'status':
  #   print("status")
  # elif args.command == 'clean':
  #   print("clean")

  # return 0

  parser = argparse.ArgumentParser(prog='gordion', description="Gordion user commands")
  parser.add_argument('-u', '--update', action='store_true', help='Update the gordion tree')
  parser.add_argument('-w', '--workspace', action='store_true', help='Print the gordion workspace')
  # parser.add_argument('-s', '--status', action='store_true', help='Show the gordion status')
  parser.add_argument('-f', '--find', type=str, help='Find full path to repository name')
  parser.add_argument('-e', '--expand', type=str, help='Expand gordion env variables in a file')
  parser.add_argument('-o', '--output', type=str, help='Output file after expansion')
  parser.add_argument('-a', '--add', action='store_true', help='git add in all repositories')

  subparsers = parser.add_subparsers(dest='command', help='Git analog commands')
  parser_status = subparsers.add_parser('status', help='Show the gordion status')
  parser_status.add_argument('-v', '--verbose', action='store_true', help='verbose')

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
    if args.command == 'status':
      root = gordion.Tree.find(os.getcwd())
      print(gordion.app.status.terminal_status(root, args.verbose))

    # Print the respository path.
    if args.find:
      repo = workspace.get_repository_or_throw(args.find)
      print(repo.path)

    # Expand file.
    if args.expand:
      gordion.app.expand(args.expand, args.output)

    if args.add:
      root = gordion.Tree.find(os.getcwd())
      root.add()

  except Exception as e:
    gordion.utils.print_exception(e=e, trace=False)
    sys.exit(1)

  if PROFILE:
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('cumulative')
    stats.print_stats()
