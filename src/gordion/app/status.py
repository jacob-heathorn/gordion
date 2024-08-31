from __future__ import annotations
import gordion
import os
from .folder import Folder
from .repository_folder import RepositoryFolder


def get_path_tree(root) -> str:
  status_string = ''
  repos = [root]
  repos.extend(gordion.Store().list_repos())
  repos.sort(key=lambda repo: repo.path)
  root_folder = RepositoryFolder(root, root)
  root_folder.repo = root

  for repo in repos:
    relpath = os.path.relpath(repo.path, os.path.dirname(root.path))
    parts = relpath.split(os.sep)

    current_folder: Folder = root_folder
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
          if index == len(parts) - 1:
            assert repo.name == part
            new_child: Folder = RepositoryFolder(repo, root)
          else:
            new_child = Folder(part)
          new_child.parent = current_folder
          current_folder.children.append(new_child)
          current_folder = new_child

  status_string += root_folder.get_status()
  return status_string


def get_status(root) -> str:
  return get_path_tree(root)
