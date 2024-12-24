import gordion
from typing import List, Optional
import os


class Folder:
  """
  Provedes a way to display the directory tree, with control over the "display name" for each
  folder. A folder displays blue, akin to how the `tree` command displays in Unix-based terminals.
  Another class can inherit and override _get_display_name() to modify it.

  """

  def __init__(self, path) -> None:
    self.path = path
    self.name = os.path.basename(path)
    self.children: List[Folder] = []
    self.parent: Optional[Folder] = None

  def terminal_status(self) -> str:
    """
    Returns a string of the Folder tree from this folder downward.
    """
    status_string = ""

    symbol_row = ''.join(self._get_symbol_row())
    status_string = symbol_row
    status_string += self._get_display_name()

    git_status = self._get_git_status()
    if git_status:
      symbol_row = symbol_row.replace("├──", "│  ")
      symbol_row = symbol_row.replace("└──", "   ")
      for line in git_status.splitlines():
        status_string += "\n" + symbol_row + line
      status_string += "\n" + symbol_row

    for child in self.children:
      child_status = child.terminal_status()
      if child_status:
        status_string += "\n" + child_status

    return status_string

  def add_child(self, child):
    child.parent = self
    self.children.append(child)

  def _get_symbol_row(self):
    symbols: List[str] = []
    if self.parent:
      if self.parent._is_last_child(self.name):
        symbols.insert(0, "└──")
      else:
        symbols.insert(0, "├──")

      current_folder = self.parent
      while current_folder:
        if current_folder.parent:
          if current_folder.parent._is_last_child(current_folder.name):
            symbols.insert(0, "    ")
          else:
            symbols.insert(0, "│   ")

        current_folder = current_folder.parent  # type: ignore[assignment]

    return symbols

  def _is_last_child(self, child_name) -> bool:
    total_children = len(self.children)
    for index, child in enumerate(self.children):
      if child.name == child_name:
        return index == total_children - 1
    return False

  def _get_display_name(self) -> str:
    return gordion.utils.bold_blue(self.name)

  def _get_git_status(self) -> str:
    return ""
