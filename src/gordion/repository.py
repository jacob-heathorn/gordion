import os


class Repository:
  """
  Encapsulates a git repository in the gordion context.

  """

  def __init__(self, path: os.path, url: str, tag: str, branch: str) -> None:
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

    return True

  
  def _is_git_repository(self) -> bool:
    """
    Checks if the given the path is a git repository

    """
    # Construct the expected path to the `.git` folder
    git_dir = os.path.join(self.path, ".git")
    
    # Check if the `.git` directory exists and is a directory itself
    return os.path.isdir(git_dir)


        # args = [LINK_SERVER, "flash", "--no-boot", "MIMXRT1176xxxxx:MIMXRT1170-EVK", "load", application]
        # subprocess.check_call(args)
