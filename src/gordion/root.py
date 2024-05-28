import yaml


class Root:
  """
  Manages a root gordion tree.

  """

  def __init__(self, yaml_fullfile: str) -> None:
    self.yaml_fullfile = yaml_fullfile
    self.parse_yaml()

  def parse_yaml(self):
    # Open the YAML file and load the data
    with open(self.yaml_fullfile, 'r') as file:
      self.yaml_data = yaml.safe_load(file)

    # Print the loaded data or process it as needed
    for repo_name, repo_info in self.yaml_data['repositories'].items():
      print(f"Repository Name: {repo_name}")
      print(f"URL: {repo_info['url']}")
      print(f"Tag: {repo_info['tag']}")
      print()  # Add a newline for readability between entries
