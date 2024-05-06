import os
import subprocess


class Repository:
  """
  Encapsulates a git repository in the gordion context.

  """

  def __init__(self, path: str, url: str, tag: str, branch: str) -> None:
    self.path = path
    self.url = url
    self.tag = tag
    self.branch = branch

  def update(self) -> None:
    """
    Clones the repository if it does not exist, otherwise updates it to the requested branch:tag

    """

    if self._is_git_repository():
      print("yay")

  def _is_git_repository(self) -> bool:
    if not os.path.isdir(self.path):
      return False

    try:
      # Run `git rev-parse` to verify the directory is a Git repository
      subprocess.check_call(
          ["git", "-C", self.path, "rev-parse", "--is-inside-work-tree"],
          stdout=subprocess.DEVNULL,
          stderr=subprocess.DEVNULL
      )
      return True
    except subprocess.CalledProcessError:
      # If `git rev-parse` fails, it's not a valid Git repository
      return False
