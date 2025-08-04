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
  parser.add_argument('--force', action='store_true', help='Update the gordion tree')

  # Status parser
  subparsers = parser.add_subparsers(dest='command', help='Git analog commands')
  parser_status = subparsers.add_parser('status', help='Show the gordion status')
  parser_status.add_argument('-v', '--verbose', action='store_true', help='verbose')
  parser_status.add_argument('-c', '--cache', action='store_true',
                             help='show cache dependencies directory')

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

  # Restore parser
  parser_restore = subparsers.add_parser(
      'restore', help='Git restore <pathspec> in all repositories')
  parser_restore.add_argument('-S', '--staged', action='store_true', help='Restore staged changes')
  parser_restore.add_argument('pathspec', nargs='+', help='Pathspec to add to staging')

  # Commit parser
  parser_commit = subparsers.add_parser('commit', help='Git commit in all repositories')
  parser_commit.add_argument('-m', '--message', type=str, required=True, help='<message>')

  # Push parser
  parser_push = subparsers.add_parser('push', help='Git push in all repositories')
  parser_push.add_argument(
      '-u', '--set-upstream',
      action='store_true',
      help='Set upstream branch'
  )
  parser_push.add_argument(
      '-d', '--delete',
      action='store_true',
      help='delete refs'
  )
  parser_push.add_argument(
      'remote',
      type=str,
      nargs='?',  # Makes this argument optional
      help='The name of the remote (e.g., origin)'
  )
  parser_push.add_argument(
      'branch',
      type=str,
      nargs='?',  # Makes this argument optional
      help='The name of the branch to push'
  )
  parser_push.add_argument('-f', '--force', action='store_true', help='force updates')

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
      root.update(root.repo.handle.head.commit.hexsha, branch, force=False)

    # Print the workspace path.
    if args.workspace:
      print(f"{workspace.path}")

    # Print the respository path.
    if args.find:
      repo = workspace.get_repository_or_throw(args.find)
      print(repo.path)

    # Git Analogs
    #
    # Status
    if args.command == 'status':
      root = gordion.Tree.find(os.getcwd())
      print(gordion.app.status.terminal_status(root, args.verbose, args.cache))

    # Clean
    if args.command == 'clean':
      root = gordion.Tree.find(os.getcwd())
      gordion.Analogs(root.repo).clean(args.force, args.dirs, args.extra)

    # Add
    if args.command == 'add':
      root = gordion.Tree.find(os.getcwd())
      branch_name = root.repo.get_branch_name_or_throw()
      gordion.Analogs(root.repo).add(branch_name, args.pathspec)

    # Restore
    if args.command == 'restore':
      root = gordion.Tree.find(os.getcwd())
      gordion.Analogs(root.repo).restore(args.pathspec, args.staged)

    # Commit
    if args.command == 'commit':
      root = gordion.Tree.find(os.getcwd())
      branch_name = root.repo.get_branch_name_or_throw()
      gordion.Analogs(root.repo).commit(branch_name, args.message)

    # Push
    if args.command == 'push':
      root = gordion.Tree.find(os.getcwd())
      if not args.branch:
        args.branch = root.repo.get_branch_name_or_throw()
      gordion.Analogs(
          root.repo).push(
          args.set_upstream,
          args.delete,
          args.remote,
          args.branch,
          args.force)

  except Exception as e:
    gordion.utils.print_exception(e=e, trace=False)
    sys.exit(1)

  if PROFILE:
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats('cumulative')
    stats.print_stats()
