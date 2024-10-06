import gordion
from .terminal_status import Folder


class NotListedRepositoryFolder(Folder):
  """
  Displays in the repo in RED with (NOT LISTED BY ANY WORKING REPOSITORY)
  """

  def __init__(self, path: str) -> None:
    super().__init__(path)

  @gordion.utils.override(Folder)
  def _get_display_name(self) -> str:
    return gordion.utils.bold_red(
        self.name) + gordion.utils.red(" (NOT LISTED BY ANY WORKING REPOSITORY)")
