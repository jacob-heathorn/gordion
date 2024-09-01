import os
from .folder import Folder
from .repository_folder import RepositoryFolder
import gordion


def populate_children(folder, root):
  """
  Populates the children member on the folder object. Maybe better as a method on Folder, but avoids
  a circular dependecy on RepositoryFolder if moved outside the class.
  """
  # Collect list of path folders in this directory (one level deep), and alphabetize it.
  dirs = []
  for dirpath, dirnames, _ in os.walk(folder.path, topdown=True):
    for dirname in dirnames:
      dirs.append(os.path.join(folder.path, dirpath, dirname))
    break  # one level deep
  dirs.sort()

  # Create children.
  for dir in dirs:
    # Create a repository folder if it exists
    if gordion.Repository._exists(dir):
      repo = gordion.Tree(dir)
      child_folder = RepositoryFolder(repo, root)
      folder.add_child(child_folder)

    # Otherwise it's just a regular folder. Recurse into it and add it.
    else:
      child_folder = Folder(dir)
      populate_children(child_folder, root)
      folder.add_child(child_folder)


def terminal_status(root) -> str:
  """
  Returns a status string indicating the status of each repository in the tree, which looks cute in
  a terminal.
  """
  root_folder = RepositoryFolder(root, root)
  gordion_path = os.path.join(root.path, 'gordion')

  if os.path.exists(gordion_path) and os.path.isdir(gordion_path):
    gordion_folder = Folder(gordion_path)
    root_folder.add_child(gordion_folder)
    populate_children(gordion_folder, root)

  return root_folder.terminal_status()
