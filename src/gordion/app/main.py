#!/usr/bin/env python3

import argparse
import gordion
import os


def does_tree_list_repository(root: gordion.Tree, repo: gordion.Repository) -> bool:
  """
  Returns true if any of the tree lists the provided repository, identified by the name, url, and
  path. Or if any of the children (with correct tags) list the repository.
  """
  if repo == root:
    return True

  root.yeditor.reload()
  # Check yaml file for this repository
  if root.yeditor.exists():
    for child_name, child_info in root.yeditor.yaml_data['repositories'].items():
      gpath = root.yeditor.read_repository_gpath(child_name)
      child_path = os.path.join(gordion.Store().path, gpath)
      # If the child matches the repo by name, path, and url, then it is in the tree.
      if repo.name == child_name and repo.path == child_path and repo.url == child_info['url']:
        return True

      # Otherwise check the child's children ONLY if the child is the correct tag.
      else:
        if gordion.Repository._exists(child_path):
          child = gordion.Tree(child_path)
          if child.handle.head.commit.hexsha == child_info['tag']:
            if does_tree_list_repository(child, repo):
              return True

  return False


class Folder:
  """
  TODO

  """

  def __init__(self, name) -> None:
    self.name = name
    self.children = []
    self.parent = []
    self.repo = []

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

  def print(self, root: gordion.Tree):
    print(*self.get_symbol_row(), sep='', end='')
    # TODO make utility funcitons. Print bold blue, green, red.
    header = "\033[1;34m" + self.name + "\033[0m"
    if self.repo:
      if does_tree_list_repository(root, self.repo):
        # Brighter: 92m
        header = "\033[1;32m" + self.name + "\033[0m"
      else:
        # Brighter: 91m
        header = '\033[1;31m' + self.name + '\033[0m'

      header += f" {self.repo.handle.active_branch}:{self.repo.handle.head.commit.hexsha}"

    print(header)

    for child in self.children:
      child.print(root)

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


def print_path_tree(root):
  repos = [root]
  repos.extend(gordion.Store().list_repos())
  repos.sort(key=lambda repo: repo.path)
  root_folder = Folder(root.name)
  root_folder.repo = root

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
            new_child.repo = repo
          new_child.parent = current_folder
          current_folder.children.append(new_child)
          current_folder = new_child

  root_folder.print(root)


def print_status(root):
  print_path_tree(root)


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
        print_status(root)

  except Exception as e:
    gordion.utils.print_exception(e=e)


if __name__ == "__main__":
    main()
