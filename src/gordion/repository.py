import os
import subprocess
from gordion.utils import pushd
from pathlib import Path


class Repository:
  """
  Encapsulates a git repository in the gordion context.

  """

  def __init__(self, path: str, url: str, tag: str, branch: str) -> None:
    self.path = Path(path)
    self.url = url
    self.tag = tag
    self.branch = branch

  def update(self) -> None:
    """
    Clones the repository if it does not exist, otherwise updates it to the requested branch:tag

    """

    if not self._exists():
      print(self.path.parent)
      with pushd(self.path.parent, create=True):
        args = ['git', 'clone', self.url]
        subprocess.check_call(args, stderr=subprocess.STDOUT)

  def _exists(self) -> bool:
    # Check directory exists
    if not os.path.isdir(self.path):
      return False

    try:
      # Run the command to determine the root of the repository
      result = subprocess.check_output(
          ["git", "-C", self.path, "rev-parse", "--show-toplevel"],
          stderr=subprocess.DEVNULL
      ).strip().decode('utf-8')

      # Compare the output with self.path to determine if it's the root
      return os.path.abspath(result) == os.path.abspath(self.path)
    except subprocess.CalledProcessError:
        # If the command fails, the directory is not inside a Git repository
        return False
