import gordion
from typing import List, Optional
import os


class Folder:
  """
  TODO

  """

  def __init__(self, path) -> None:
    self.path = path
    self.name = os.path.basename(path)
    self.children: List[Folder] = []
    self.parent: Optional[Folder] = None

  def add_child(self, child):
    child.parent = self
    self.children.append(child)

  def get_symbol_row(self):
    symbols = []
    if self.parent:
      if self.parent.is_last_child(self.name):
        symbols.insert(0, "└──")
      else:
        symbols.insert(0, "├──")

      current_folder = self.parent
      while current_folder:
        if current_folder.parent:
          if current_folder.parent.is_last_child(current_folder.name):
            symbols.insert(0, "    ")
          else:
            symbols.insert(0, "│   ")

        current_folder = current_folder.parent

    return symbols

  def get_status(self) -> str:
    status_string = ''.join(self.get_symbol_row())
    status_string += self.get_display_name()

    for child in self.children:
      status_string += "\n"
      status_string += child.get_status()

    return status_string

  def is_last_child(self, child_name) -> bool:
    total_children = len(self.children)
    for index, child in enumerate(self.children):
      if child.name == child_name:
        return index == total_children - 1
    return False

  def get_display_name(self) -> str:
    return gordion.utils.bold_blue(self.name)
