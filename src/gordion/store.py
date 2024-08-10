import gordion
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

  def __init__(self, path) -> None:
    self.gordion_dir = os.path.join(gordion.app.root.gordion_root(path), 'gordion')
    print("init Store here1")

  def print(self):
    print(f"gordion dir: {self.gordion_dir}")
