import contextlib
import os

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
