import os
from gordion.repository import Repository

assert 'TOXTEMPDIR' in os.environ, "you must run these tests using tox"

REPOS_DIR = os.path.join(os.environ['TOXTEMPDIR'], 'repos')
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


def test_exists():

  url = 'dontcare'
  tag = 'dontcare'
  branch = 'dontcare'

  # Repository does not exist yet
  path = os.path.join(REPOS_DIR, 'west_demo_a')
  repo = Repository(path, url, tag, branch)
  assert not repo._exists()

  # A file inside a repository is not an existing repository
  path = os.path.join(SCRIPT_DIR)
  repo = Repository(path, url, tag, branch)
  assert not repo._exists()

  # This file lives in the gordion repository gordion root directory is an existing repository.
  path = os.path.join(SCRIPT_DIR, '..')
  repo = Repository(path, url, tag, branch)
  assert repo._exists()

# TODO make it work with ssh url.
def test_update():
  path = os.path.join(REPOS_DIR, 'west_demo_a')
  url = 'https://github.com/jacob-heathorn/west_demo_a.git'
  tag = '163f847f32fba7307dd94366560d7d55ffe3c144'
  branch = 'develop'

  print("here")
  print(path)

  # import debugpy
  # debugpy.listen(("localhost", 5678))
  # print("Waiting for debugger...")
  # debugpy.wait_for_client()
  # TODO doesnt work in sourc code!


  repo = Repository(path, url, tag, branch)
  assert not repo._exists()
  repo.update()
  assert repo._exists()