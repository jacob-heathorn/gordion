import os


# TODO move this to a dedicated singleton.py in utils folder.
def singleton(cls):
  instances = {}

  def get_instance(*args, **kwargs):
    if cls not in instances:
      instances[cls] = cls(*args, **kwargs)
    return instances[cls]
  return get_instance


@singleton
class Store:
  """
  Singleton class dedicated to managing the gordion/ folder.
  """

  def __init__(self) -> None:
    self.path = ''

  def setup(self, path):
    """
    User must call this function once with a path that this store will place the singleton gordion/
    folder.
    """
    self.path = os.path.join(path, 'gordion')

  def print(self):
    assert self.path
    print(f"gordion dir: {self.path}")
