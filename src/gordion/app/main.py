#!/usr/bin/env python3

import argparse
import gordion
import os


class Folder:
  """
  TODO

  """

  def __init__(self, name) -> None:
    self.name = name
    self.children = []
    self.parent = []
    self.header = []

  def top(self):
    if self.parent:
      return self.parent.top()
    else:
      return self

  def get_symbol_row(self):
    symbols = []
    if self.parent:
      child_type = self.parent.get_child_type(self.name)
      if child_type == "last":
        symbols.insert(0, "└──")
      else:
        symbols.insert(0, "├──")

      current_folder = self.parent
      while current_folder:
        if current_folder.parent:
          parent_child_type = current_folder.parent.get_child_type(current_folder.name)
          if parent_child_type == "last":
            symbols.insert(0, "    ")
          else:
            symbols.insert(0, "│   ")

        current_folder = current_folder.parent

    return symbols

  def print(self):
    print(*self.get_symbol_row(), sep='', end='')
    if self.header:
      print(f"{self.name} {self.header}")
    else:
      print(self.name)

    for child in self.children:
      child.print()

  def get_child_type(self, child_name):
    total_children = len(self.children)
    for index, child in enumerate(self.children):
      if child.name == child_name:
        if index == total_children - 1:
          return "last"
        elif index == 0:
          return "first"
        else:
          return "middle"


def list_repositories(root):
  repos = [root]

  for dirpath, dirnames, _ in os.walk(os.path.join(root.path, 'gordion'), topdown=True):
    # Create a copy of dirnames for iteration to avoid modifying the list while iterating
    for dirname in dirnames[:]:  # [:] creates a shallow copy of the list
      full_dirpath = os.path.join(dirpath, dirname)

      if gordion.Repository._exists(full_dirpath):
        repos.append(gordion.Repository(full_dirpath))
        # Remove the current directory's name from dirnames so os.walk will skip its subdirectories
        dirnames.remove(dirname)

  return sorted(repos, key=lambda repo: repo.name)


def print_path_tree(root):
  repos = list_repositories(root)
  root_folder = Folder(root.name)
  root_folder.header = f"{root.handle.active_branch}:{root.handle.head.commit.hexsha}"

  for repo in repos:
    relpath = os.path.relpath(repo.path, os.path.dirname(root.path))
    parts = relpath.split(os.sep)

    current_folder = root_folder
    for index, part in enumerate(parts):
      if current_folder.name == part:
        continue
      else:
        found_child = False
        for child in current_folder.children:
          if child.name == part:
            current_folder = child
            found_child = True
            break

        if not found_child:
          new_child = Folder(part)
          if index == len(parts) - 1:
            new_child.header = f"{repo.handle.active_branch}:{repo.handle.head.commit.hexsha}"
          new_child.parent = current_folder
          current_folder.children.append(new_child)
          current_folder = new_child

  root_folder.print()


def print_status(root):
  print_path_tree(root)


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

  except Exception as e:
    gordion.utils.print_exception(e=e, trace=True)


if __name__ == "__main__":
    main()


# def print_path_tree(paths):
#     def print_part(part, indent, is_last):
#       """ Helper function to print a line with appropriate prefix """
#       # Choose the right prefix based on whether the item is the last in the section
#       prefix = '└── ' if is_last else '├── '
#       # Print with indentation and prefix
#       print('    ' * indent + prefix + part)

#     # Store depth and last index seen at each depth
#     last_indices = {}

#     previous_parts = []

#     for path in paths:
#       parts = path.split(os.sep)
#       max_depth = len(parts) - 1

#       # Update last indices for all seen parts
#       for depth, part in enumerate(parts):
#         last_indices[depth] = parts[depth:]

#       common_prefix_length = len(os.path.commonprefix([previous_parts if previous_parts else [], parts]))

#       # Determine the range of new parts to print
#       new_parts_range = range(common_prefix_length, len(parts))

#       # Print each new part of the path
#       for i in new_parts_range:
#           # Determine if this is the last part to print for this depth
#           is_last = i == max_depth or parts[i] != last_indices[i][0]
#           print_part(parts[i], i, is_last)

#       previous_parts = parts