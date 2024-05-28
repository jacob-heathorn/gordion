import yaml
import gordion
import os
from git import Repo


class Root:
  """
  Manages a root gordion tree.

  """

  def __init__(self, yaml_fullfile: str) -> None:
    self.yaml_fullfile = yaml_fullfile
    self.gordion_dir = os.path.join(os.path.dirname(yaml_fullfile), 'gordion')
    self.yaml_data = []
    self.parse_yaml()
    self.repositories = {}

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

  def update(self):
    # Create root repository
    root = self.create_root_repository()
    root_name = os.path.basename(root.path)  # TODO need a unique identifier for a repository.
    self.repositories[root_name] = root

    # Create and update children repositories
    for repo_name, repo_info in self.yaml_data['repositories'].items():
      # TODO: allow non-default path
      path = os.path.join(self.gordion_dir, repo_name)
      url = repo_info['url']
      tag = repo_info['tag']
      branch = root.target_branch_name

      self.repositories[repo_name] = gordion.Repository(path, url, tag, branch)
      # self.repositories[repo_name].update()

  def create_root_repository(self) -> gordion.Repository:
    root_path = os.path.dirname(self.yaml_fullfile)
    root_repo = Repo(root_path)
    root_url = ''  # won't be used
    root_tag = root_repo.head.commit.hexsha
    root_branch = []
    if not root_repo.head.is_detached:
      root_branch = root_repo.active_branch.name

    return gordion.Repository(root_path, root_url, root_tag, root_branch)
