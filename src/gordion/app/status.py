from __future__ import annotations
import os
from .folder import Folder
from .repository_folder import RepositoryFolder


def get_path_tree(root) -> str:
  root_folder = RepositoryFolder(root, root)
  gordion_path = os.path.join(root.path, 'gordion')

  if os.path.exists(gordion_path) and os.path.isdir(gordion_path):
    gordion_folder = Folder(gordion_path)
    root_folder.add_child(gordion_folder)
    gordion_folder.discover_children(root)

  return root_folder.get_status()


def get_status(root) -> str:
  return get_path_tree(root)
