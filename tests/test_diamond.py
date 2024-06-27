import os
import gordion
import pytest

assert 'TOXTEMPDIR' in os.environ, "you must run these tests using tox"

REPOS_DIR = os.path.join(os.environ['TOXTEMPDIR'], 'repos')
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture(scope="session")
def repo_a_session():
  """
  Creates the repo_a object only once for the lifetime of this session. This is important so the
  "fetch_once" doesn't fetch every test case, which saves time.
  """
  path = os.path.join(REPOS_DIR, 'gordion_demo_a')
  url = 'https://github.com/jacob-heathorn/gordion_demo_a.git'

  # Create the repo object and ensure it.
  repo = gordion.Repository(path)
  repo.ensure(url)

  yield repo


@pytest.fixture
def repo_a(repo_a_session):
  """
  This puts the repo_a object back into a well-known state for each test case.
  """

  # Clear uncommitted changes.
  repo_a_session.handle.git.reset('--hard')
  repo_a_session.handle.git.clean('-fdx')

  # Delete all local branches except develop (can't be deleted) to start fresh.
  repo_a_session.handle.branches['develop'].checkout()
  branches = list(repo_a_session.handle.branches)
  for branch in branches:
    if branch.name != 'develop':
      repo_a_session.handle.delete_head(branch, force=True)

  # Set the object to a known commit on the develop branch.
  tag = 'c9da3e67006cbb03b6810d2e5b8effebb0f0b674'
  branch_name = 'develop'

  # Set the target branch/commit
  repo_a_session.update(tag, branch_name, force=True)
  assert repo_a_session.handle.head.commit.hexsha == tag
  assert repo_a_session.handle.active_branch.name == branch_name

  yield repo_a_session


def test_tag_mismatch(repo_a):
  """
  Verifies update will error if two of the same repository reference have different tags.
  """

  # Add a commit to repository D.
  repo_d = repo_a.children['gordion_demo_b'].children['gordion_demo_d']
  repo_d.handle.git.commit('-m', "Empty commit for test_tag_mismatch", allow_empty=True)

  # Make B point to D's new commit but not C.
  repo_b = repo_a.children['gordion_demo_b']
  repo_b.yeditor.write_repository_tag('gordion_demo_d', repo_d.handle.head.commit.hexsha)
  repo_b.handle.git.add(os.path.join(repo_b.path, 'gordion.yaml'))
  repo_b.handle.git.commit('-m', "Point to latest D")
  repo_a.yeditor.write_repository_tag('gordion_demo_b', repo_b.handle.head.commit.hexsha)
  repo_a.handle.git.add(os.path.join(repo_a.path, 'gordion.yaml'))
  repo_a.handle.git.commit('-m', "Point to latest B")

  # Save some information before the update.
  b_ref_d = repo_a.children['gordion_demo_b'].children['gordion_demo_d']
  b_ref_d_tag = repo_a.children['gordion_demo_b'].yeditor.read_repository_tag('gordion_demo_d')
  c_ref_d = repo_a.children['gordion_demo_c'].children['gordion_demo_d']
  c_ref_d_tag = repo_a.children['gordion_demo_c'].yeditor.read_repository_tag('gordion_demo_d')

  # Now update, it should raise error, tag mismatch.
  with pytest.raises(gordion.UpdateDuplicateRepoTagError) as context:
    repo_a.update(repo_a.handle.head.commit.hexsha, "develop")

  # Verify the exception.
  expected = gordion.UpdateDuplicateRepoTagError(c_ref_d, c_ref_d_tag,
                                                 b_ref_d, b_ref_d_tag)
  assert str(context.value) == str(expected)


def test_path_mismatch(repo_a):
  """
  Verifies update will error if two repositories are attempted to be cloned at different paths.
  """
  # TODO
  pass


def test_non_default_path_1(repo_a):
  """
  TODO
  """

  # Put repo B at in a non-default path, update and verify it exists, and the origional one has been
  # removed.
  repo_a.yeditor.yaml_data['repositories']['gordion_demo_b']['path'] = '/heyo/gordion_demo_b'
  repo_a.yeditor.save()
  repo_a.update(repo_a.handle.head.commit.hexsha, "develop")
  repo_b = repo_a.children['gordion_demo_b']
  assert repo_b.path == os.path.join(repo_a.path, 'gordion', 'heyo', 'gordion_demo_b')
  assert repo_b.handle.head.commit.hexsha == repo_a.yeditor.read_repository_tag('gordion_demo_b')
  assert not os.path.isdir(os.path.join(repo_a.path, 'gordion', 'gordion_demo_b'))
  # TODO careful about deleting old repository, make sure it doesn't have stashes, or local commits
  # that are lost.

  # TODO error if name differs from path basedir.
  # Name doesn't have to be unique but gpath does.
  # gpath is dirived from name + path in yaml.

  # Put repository back to default path, verify old path is deleted.
  repo_a.yeditor.yaml_data['repositories']['gordion_demo_b']['path'] = '/gordion_demo_b'
  repo_a.yeditor.save()
  repo_a.update(repo_a.handle.head.commit.hexsha, "develop")
  repo_b = repo_a.children['gordion_demo_b']
  assert repo_b.path == os.path.join(repo_a.path, 'gordion', 'gordion_demo_b')
  assert repo_b.handle.head.commit.hexsha == repo_a.yeditor.read_repository_tag('gordion_demo_b')
  assert not os.path.isdir(os.path.join(repo_a.path, 'gordion', 'heyo'))
