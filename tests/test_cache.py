import os
import gordion

assert 'TOXTEMPDIR' in os.environ, "you must run these tests using tox"

REPOS_DIR = os.path.join(os.environ['TOXTEMPDIR'], 'repos')
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


def test_repo_details():
  url = "https://github.com/username/repository.git"
  host, username, repo_name = gordion.extract_repo_details(url)
  assert host == "github.com"
  assert username == "username"
  assert repo_name == "repository"

  url = "git@github.com:username/repository.git"
  host, username, repo_name = gordion.extract_repo_details(url)
  assert host == "github.com"
  assert username == "username"
  assert repo_name == "repository"

  url = "http://bitbucket.org/username/repository"
  host, username, repo_name = gordion.extract_repo_details(url)
  assert host == "bitbucket.org"
  assert username == "username"
  assert repo_name == "repository"

  url = "ssh://gitlab.com/username/repository.git"
  host, username, repo_name = gordion.extract_repo_details(url)
  assert host == "gitlab.com"
  assert username == "username"
  assert repo_name == "repository"


def test_mirror():
  cache = gordion.Cache()
  # NOTE: Don't clean the cache because it's breaking other tests.
  # cache.clean()
  path, default_branch = cache.ensure_mirror(
      'https://github.com/jacob-heathorn/gordion_demo_a.git')
  assert path == os.path.join(os.environ['HOME'], '.local', 'share', 'gordion',
                              'mirrors', 'github.com', 'jacob-heathorn',
                              'gordion_demo_a')
  assert default_branch == 'develop'
