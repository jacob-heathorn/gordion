import yaml


class YamlEditor:
  """
  Encapsulates a gordion.yaml file for reading and writing

  """

  def __init__(self, fullfile: str) -> None:
    with open(fullfile, 'r') as file:
      self.yaml_data = yaml.safe_load(file)

  def write_repository_tag(self, name: str, tag: str):
    self.yaml_data['repositories'][name].tag = tag
