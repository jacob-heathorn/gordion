import gordion
from .terminal_status import Folder


class DuplicateRepositoryFolder(Folder):
  """
  Inherits from Folder, to override _get_display_name so that a Folder that "isa"
  repository can print information about the repository in pretty colors.
  """

  def __init__(self, path: str) -> None:
    super().__init__(path)

  @gordion.utils.override(Folder)
  def _get_display_name(self) -> str:
    """
    Returns the repository folder name in red with (DUPLICATE) annotation.
    """

    return gordion.utils.bold_red(self.name) + gordion.utils.red(" (DUPLICATE)")
