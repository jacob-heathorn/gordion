import contextlib
import os
from urllib.parse import urlparse
import traceback


# Context manager for pushd. Example from
# (https://stackoverflow.com/questions/6194499/pushd-through-os-system)
@contextlib.contextmanager
def pushd(dir, create=False):
  """
  Changes the current working directory to `dir` temporarily.

  Parameters
  ----------
  dir : str
      The path to switch to as the new working directory.

  create : bool, optional
      If True, creates the directory if it doesn't exist. Defaults to False.
  """
  previous_dir = os.getcwd()

  if create and not os.path.exists(dir):
    os.makedirs(dir)

  os.chdir(dir)
  try:
    yield
  finally:
    os.chdir(previous_dir)


def extract_repo_details(url):
  """
  Returns the host, username, and repository name from Git repository URL.
  """
  # Handle SSH special case
  if "@" in url and ":" in url:
    # Typical SSH format: user@host:path
    user_host, path = url.split("@", 1)
    host, path = path.split(":", 1)
    username, repo_name = path.split("/", 1)
  else:
    # Parse the URL using urlparse for other schemes
    parsed_url = urlparse(url)
    host = parsed_url.netloc
    path = parsed_url.path.lstrip('/')

    # Remove possible .git suffix
    if path.endswith('.git'):
      path = path[:-4]

    # Split the path into components
    parts = path.split('/')

    # Check if there's at least two parts (username/org and repo name)
    if len(parts) >= 2:
      username = parts[0]
      repo_name = parts[1]
    else:
      raise ValueError("URL path is too short to determine repository details")

  # Ensure the repo name does not contain '.git'
  repo_name = repo_name.rstrip('.git')

  return host, username, repo_name


def is_related_path(directory, paths):
  """
  Returns true if the directory is an exact match, is an ancestor, or is a descendant of one of the
  paths.

  e.g.
    /this/is/a/path

    cases:
      /this/is/a/path -> true (exact match)
      /this/is -> true (ancestor)
      /this/is/a/path/below -> true (descendant)
      /this/is/b -> false (none)
  """

  for path in paths:
    if path.startswith(directory) or directory.startswith(path):
      return True
  return False


def find_ancestor_dir(cwd, target_dir_name):
  """
  Looks for the directory in the direcotires ancestry.
  """
  # Loop to move up the directory tree
  while cwd != os.path.dirname(cwd):  # Continue until the root directory is reached
    parent_dir = os.path.dirname(cwd)
    if os.path.basename(parent_dir) == target_dir_name:
      return parent_dir  # Return the matching ancestor directory
    cwd = parent_dir

  return None  # Return None if no matching ancestor is found


def print_exception(e, trace: bool = False):
  """
  Prints the exception, optionally with a trace.
  """
  formatted_traceback = ''.join(traceback.format_exception(None, e, e.__traceback__))
  RED = '\033[91m'
  RESET = '\033[0m'
  if trace:
    print(f"{formatted_traceback}\n")
  print(f"{RED}{e}{RESET}")


def singleton(cls):
  """
  Decorator to turn a class into a Singleton
  """
  instances = {}

  def get_instance(*args, **kwargs):
    if cls not in instances:
      instances[cls] = cls(*args, **kwargs)
    return instances[cls]
  return get_instance


def bold_red(str):
  return '\033[1;31m' + str + '\033[0m'


def bold_green(str):
  return "\033[1;32m" + str + "\033[0m"


def bold_blue(str):
  return "\033[1;34m" + str + "\033[0m"
