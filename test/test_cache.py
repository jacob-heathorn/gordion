import os
# import re
from urllib.parse import urlparse
import unittest
import gordion

assert 'TOXTEMPDIR' in os.environ, "you must run these tests using tox"

REPOS_DIR = os.path.join(os.environ['TOXTEMPDIR'], 'repos')
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


def extract_repo_details(url):
  # Parse the URL using urlparse to handle various schemes and netloc
  parsed_url = urlparse(url)
  path = parsed_url.path

  # Remove leading slash and possible .git suffix
  if path.startswith('/'):
    path = path[1:]
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

  return parsed_url.netloc, username, repo_name


# Example usage:
urls = [
    "https://github.com/username/repository.git",
    "git@github.com:username/repository.git",
    "http://bitbucket.org/username/repository",
    "ssh://gitlab.com/username/repository.git"
]

for url in urls:
  host, username, repo_name = extract_repo_details(url)
  print(f"URL: {url}\nHost: {host}\nUsername: {username}\nRepository Name: {repo_name}\n")


class TestCache(unittest.TestCase):

  def test_exists(self):
    for url in urls:
      host, username, repo_name = extract_repo_details(url)
      print(f"URL: {url}\nHost: {host}\nUsername: {username}\nRepository Name: {repo_name}\n")
