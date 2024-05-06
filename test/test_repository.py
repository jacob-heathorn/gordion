import os
from gordion.repository import Repository

assert 'TOXTEMPDIR' in os.environ, "you must run these tests using tox"

REPOS_PATH = os.path.join(os.environ['TOXTEMPDIR'], 'repos')


def test_repository():

    # # White box test for git parsing behavior.
    # assert gv(b'git version 2.25.1\n') == (2, 25, 1)
    # assert gv(b'git version 2.28.0.windows.1\n') == (2, 28, 0)
    # assert gv(b'git version 2.24.3 (Apple Git-128)\n') == (2, 24, 3)
    # assert gv(b'git version 2.29.GIT\n') == (2, 29)
    # assert gv(b'not a git version') is None

  repo = Repository(path=REPOS_PATH, url='git@github.com:jacob-heathorn/west_demo_a.git',
                    tag='1c518ee74d9c619321fea12e90c7a721dfddb0ee', branch='develop')

  assert repo.update()
