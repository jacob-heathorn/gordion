import yaml


class YamlEditor:
  """
  Encapsulates a gordion.yaml file for reading and writing

  """

  def __init__(self, fullfile: str) -> None:
    self.fullfile = fullfile
    with open(self.fullfile, 'r') as file:
      self.yaml_data = yaml.safe_load(file)

  def write_repository_tag(self, name: str, tag: str):
    # Check if the repository exists
    if name in self.yaml_data['repositories']:
      # Update the tag for the specified repository
      self.yaml_data['repositories'][name]['tag'] = tag
      self.save()
    else:
      # Handle the case where the repository doesn't exist
      raise ValueError(f"Repository '{name}' not found in YAML data.")

  def save(self):
    # Write the modified data back to the YAML file
    with open(self.fullfile, 'w') as file:
      yaml.dump(self.yaml_data, file)
