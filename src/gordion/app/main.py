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
    print(self.name)

    # for 
    # if self.parent:
    #   print(f"{self.get_symbol_row()}{self.name}")
    # else:
    #   print(f"{self.name}")

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


def print_path_tree(paths):
  root_folder_name = paths[0].split(os.sep)[0]
  root = Folder(root_folder_name)

  for path in paths:
    parts = path.split(os.sep)

    current_folder = root
    for part in parts:
      if current_folder == part:
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
          new_child.parent = current_folder
          current_folder.children.append(new_child)
          current_folder = new_child

  root.print()


def aggregate_repositories_map(root):
  repos = {root.path: root}

  # TODO if gordion repo found, don't look at subfolders. In case they have a goridon/ folder too.
  for dirpath, dirnames, _ in os.walk(os.path.join(root.path, 'gordion'), topdown=True):
    for dirname in dirnames:
      full_dirpath = os.path.join(dirpath, dirname)
      if gordion.Repository._exists(full_dirpath):
        repos[full_dirpath] = gordion.Repository(full_dirpath)

  return repos


def print_status(root):
  repos = aggregate_repositories_map(root)
  paths = []
  for key in sorted(repos.keys()):
    paths.append(key)
    # print(f"{key}: {repos[key]}")

  print_path_tree(paths)


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