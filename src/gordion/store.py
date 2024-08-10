import gordion


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
    # gordion.app.root.gordion_root(path)
    print("init Store here1")

  def print(self):
    print("here2")
