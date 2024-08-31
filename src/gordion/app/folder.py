import gordion
from typing import List, Optional


class Folder:
  """
  TODO

  """

  def __init__(self, name) -> None:
    self.name = name
    self.children: List[Folder] = []
    self.parent: Optional[Folder] = None

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

  def get_status(self) -> str:
    status_string = ''.join(self.get_symbol_row())
    status_string += self.get_display_name()

    for child in self.children:
      status_string += "\n"
      status_string += child.get_status()

    return status_string

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

  def get_display_name(self) -> str:
    return gordion.utils.bold_blue(self.name)
