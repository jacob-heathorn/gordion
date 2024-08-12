import os
import unittest
import gordion

assert 'TOXTEMPDIR' in os.environ, "you must run these tests using tox"

REPOS_DIR = os.path.join(os.environ['TOXTEMPDIR'], 'repos')
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


class TestCache(unittest.TestCase):

  def test_repo_details(self):
    url = "https://github.com/username/repository.git"
    host, username, repo_name = gordion.extract_repo_details(url)
    self.assertEqual(host, "github.com")
    self.assertEqual(username, "username")
    self.assertEqual(repo_name, "repository")

    url = "git@github.com:username/repository.git"
    host, username, repo_name = gordion.extract_repo_details(url)
    self.assertEqual(host, "github.com")
    self.assertEqual(username, "username")
    self.assertEqual(repo_name, "repository")
    print(f"host: {host}")

    url = "http://bitbucket.org/username/repository"
    host, username, repo_name = gordion.extract_repo_details(url)
    self.assertEqual(host, "bitbucket.org")
    self.assertEqual(username, "username")
    self.assertEqual(repo_name, "repository")

    url = "ssh://gitlab.com/username/repository.git"
    host, username, repo_name = gordion.extract_repo_details(url)
    self.assertEqual(host, "gitlab.com")
    self.assertEqual(username, "username")
    self.assertEqual(repo_name, "repository")

  def test_mirror(self):
    cache = gordion.Cache()
    cache.clean()
    path, default_branch = cache.ensure_mirror(
      'https://github.com/jacob-heathorn/gordion_demo_a.git')
    self.assertEqual(path, os.path.join(os.environ['HOME'], '.local', 'share', 'gordion',
                                        'mirrors', 'github.com', 'jacob-heathorn',
                                        'gordion_demo_a'))
    self.assertEqual(default_branch, 'develop')
