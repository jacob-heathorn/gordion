import contextlib
import os
from urllib.parse import urlparse
import traceback
import re
import git
import sys

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


def compare_urls(url_a, url_b):
  """
  Returns true if the the two urls identify the same repository.
  """
  host_a, username_a, repo_name_a = extract_repo_details(url_a)
  host_b, username_b, repo_name_b = extract_repo_details(url_b)
  return host_a == host_b and username_a == username_b and repo_name_a == repo_name_b


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
    print(f"{formatted_traceback}\n", file=sys.stderr)
  print(f"{RED}{e}{RESET}", file=sys.stderr)


def singleton(cls):
  """
  Decorator to turn a class into a Singleton
  """
  instances = {}
  import functools

  @functools.wraps(cls)  # This helps in preserving the original class's metadata
  def get_instance(*args, **kwargs):
    if cls not in instances:
      instances[cls] = cls(*args, **kwargs)
    return instances[cls]

  # Copy static methods and other attributes to the get_instance function
  for attr in dir(cls):
    if not hasattr(get_instance, attr):
      try:
        setattr(get_instance, attr, getattr(cls, attr))
      except TypeError:
        pass  # Skip setting attributes that cause TypeError

  return get_instance


def registry(cls):
  """
  A decorator that adds registry functionality to a class.
  """
  cls.registry_ = {}

  @classmethod  # type: ignore[misc]
  def register(cls, key, obj):
    cls.registry_[key] = obj

  @classmethod  # type: ignore[misc]
  def unregister(cls, key):
    if key in cls.registry_:
      del cls.registry_[key]

  @classmethod  # type: ignore[misc]
  def registry(cls):
    return cls.registry_

  @classmethod  # type: ignore[misc]
  def reset_registry(cls):
    cls.registry_ = {}

  # Attach the method to the class
  cls.register = register
  cls.unregister = unregister
  cls.registry = registry
  cls.reset_registry = reset_registry

  return cls


def override(interface_class):
  def overrider(method):
    assert (method.__name__ in dir(interface_class)), \
        f"Error: {method.__name__} does not override any method in {interface_class.__name__}"
    return method
  return overrider


def red(str):
  return '\033[31m' + str + '\033[m'


def bold_red(str):
  return '\033[1;31m' + str + '\033[m'


def green(str):
  return "\033[32m" + str + "\033[m"


def bold_green(str):
  return "\033[1;32m" + str + "\033[m"


def bold_blue(str):
  return "\033[1;34m" + str + "\033[m"


def yellow(str):
  return '\033[93m' + str + "\033[m"


def hyperlink(link, text):
  return f"\033]8;;{link}\033\\{text}\033]8;;\033\\"


def filelink(link, text):
  return f"\033]8;;file://{link}\033\\{text}\033]8;;\033\\"


def replace_i(text, old, new, occurrence_i):
  """
  Replaces 'old' with 'new' at the 'occurrence_i' instance index in 'text'.

  Parameters:
  - text (str): The original string.
  - old (str): The substring to replace.
  - new (str): The substring to use as replacement.
  - occurrence (int): The specific occurrence to replace (0-based index).

  Returns:
  - str: The modified string with the specified occurrence replaced.
  """
  # Find all the start positions of 'old' in 'text'
  matches = list(re.finditer(re.escape(old), text))
  if len(matches) < (occurrence_i + 1):
    return text  # Return the original if there are less occurrences than required

  # Get the specific match
  specific_match = matches[occurrence_i]
  start, end = specific_match.start(), specific_match.end()

  # Replace only the specified occurrence
  return text[:start] + new + text[end:]


def get_repository_root(path: str):
  """
  Returns the root of a git repository.
  """
  try:
    # Create a Repo object pointing to the current directory
    repo = git.Repo(path, search_parent_directories=True)
    # Get the git root directory
    git_root = repo.git.rev_parse("--show-toplevel")
    return git_root
  except Exception:
    return None
