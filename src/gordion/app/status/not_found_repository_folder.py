import gordion
from .terminal_status import Folder


class NotFoundRepositoryFolder(Folder):
  """
  Returns the repository folder name in red with (DUPLICATE) annotation.
  """

  def __init__(self, path: str) -> None:
    super().__init__(path)

  @gordion.utils.override(Folder)
  def _get_display_name(self) -> str:
    return gordion.utils.bold_red(self.name) + gordion.utils.red(" (NOT FOUND)")
