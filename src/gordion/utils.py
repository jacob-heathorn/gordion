import contextlib
import os
from urllib.parse import urlparse


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
