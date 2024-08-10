# TODO can I move this? or import it?
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
    print("init Store here1")
