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
  # Setup
  #
  # Set the object to a known commit on the develop branch.
  tag = 'c9da3e67006cbb03b6810d2e5b8effebb0f0b674'
  branch_name = 'develop'

  # Set the target branch/commit.
  repo_a_session.update(tag, branch_name, force=True)

  yield repo_a_session

  # Cleanup
  #
  # Delete all local branches except develop (can't be deleted) to start fresh.
  repo_a_session.handle.branches['develop'].checkout()
  branches = list(repo_a_session.handle.branches)
  for branch in branches:
    if branch.name != 'develop':
      repo_a_session.handle.delete_head(branch, force=True)

  # Update to our known commit.
  repo_a_session.update(tag, branch_name, force=True)

  # TODO: Should this be done in the force update?
  def cleanup_repo(path):
    if os.path.exists(path):
      print(f"Git clean {path}")
      repo = gordion.Repository(path)
      repo.ensure()
      repo.handle.git.reset('--hard')
      repo.handle.git.clean('-fdx')

  cleanup_repo(repo_a_session.path)
  cleanup_repo(os.path.join(repo_a_session.path, 'gordion', 'gordion_demo_b'))
  cleanup_repo(os.path.join(repo_a_session.path, 'gordion', 'gordion_demo_c'))
  cleanup_repo(os.path.join(repo_a_session.path, 'gordion', 'gordion_demo_d'))


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


def test_duplicate_repo_path_mismatch(repo_a):
  """
  Verifies update will error if the same repository is attempted to be cloned at different paths.
  """

  repo_b = repo_a.children['gordion_demo_b']
  repo_c = repo_a.children['gordion_demo_c']

  with pytest.raises(gordion.UpdateDuplicateRepoPathError) as context:
    repo_a.update("8659bcd4e68ac3e0c0e2f55e6bd03296007a0a47", "test_duplicate_repo_path_mismatch")

  expected = gordion.UpdateDuplicateRepoPathError(repo_c, repo_b)
  assert str(context.value) == str(expected)


def test_non_default_path(repo_a):
  """
  Verifies that a repository can be cloned at a non-default gpath. And that the non-default path can
  be cleaned up if it is moved back.
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

  # Put repository back to default path, verify old path is deleted.
  repo_a.yeditor.yaml_data['repositories']['gordion_demo_b']['path'] = '/gordion_demo_b'
  repo_a.yeditor.save()
  repo_a.update(repo_a.handle.head.commit.hexsha, "develop")
  repo_b = repo_a.children['gordion_demo_b']
  assert repo_b.path == os.path.join(repo_a.path, 'gordion', 'gordion_demo_b')
  assert repo_b.handle.head.commit.hexsha == repo_a.yeditor.read_repository_tag('gordion_demo_b')
  assert not os.path.isdir(os.path.join(repo_a.path, 'gordion', 'heyo'))


def test_unsafe_remove_dirty(repo_a):
  """
  Verifies that an error is generated if the update will attempt to cleanup(remove) a repository
  that has dirty changes.
  """

  # Make the demo_c dirty by adding an empty file.
  repo_c = repo_a.children['gordion_demo_c']
  touchfile = os.path.join(repo_c.path, 'touch.txt')
  with open(touchfile, 'w'):
    pass

  assert repo_c.handle.is_dirty(untracked_files=True)

  with pytest.raises(gordion.UnsafeRemoveDirty) as context:
    repo_a.update('55f619c7af1cdc3ed13487c3aab050b492e655eb', 'test_unsafe_remove_dirty')

  expected = gordion.UnsafeRemoveDirty(repo_c.path)
  assert str(context.value) == str(expected)
