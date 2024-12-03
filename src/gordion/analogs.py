import gordion
from typing import Dict


class Analogs:
  """
  Wraps a tree object and provides git analogs
  """

  def __init__(self, root: gordion.Tree):
    self.root: gordion.Tree = root
    self.nodes: Dict[str, gordion.Tree] = {}
    self.trace(root)

  def trace(self, node: gordion.Tree):
    # Register this node if necessary.
    if not self.nodes.get(node.repo.path):
      self.nodes[node.repo.path] = node

    # Register it's children.
    if node.repo.yeditor.exists():
      assert node.repo.yeditor.yaml_data  # TODO proper error.
      for child_name, child_info in node.repo.yeditor.yaml_data['repositories'].items():
        child_url = child_info['url']
        child_tag = child_info['tag']
        child_repo = gordion.Workspace().get_repository(child_name)

        if child_repo:
          if gordion.utils.compare_urls(child_repo.url, child_url):
            child_listed_commit = child_repo.verify_tag_nothrow(child_tag)
            if child_listed_commit and child_repo.handle.head.commit == child_listed_commit:
              # Get the child if it already exists, otherwise create it.
              child = self.nodes.get(child_repo.path)
              if not child:
                child = gordion.Tree(child_repo)
                self.nodes[child.repo.path] = child

              # Register parent/child relationship.
              node.children1[child.repo.path] = child
              child.parents1[node.repo.path] = node

              # Recurse.
              self.trace(child)
            else:
              raise gordion.exception.TraceError()
          else:
            raise gordion.exception.TraceError()
        else:
          raise gordion.exception.TraceError()

  def verify_changes_are_branch(self, branch_name: str):
    """
    Raises an error if any repository in the tree has changes, but does not check out the provided
    <branch_name>
    """
    bad_nodes = []
    for _, node in self.nodes.items():
      if node.repo.is_dirty():
        if not node.repo.is_branch(branch_name):
          bad_nodes.append(node.repo)
    if len(bad_nodes) > 0:
      raise gordion.exception.WrongBranchRepositoryDirty(branch_name, bad_nodes)

  def add(self, branch_name: str, pathspec: str):
    """
    Analog for: git add <pathspec>
    """

    self.verify_changes_are_branch(branch_name)
    for _, node in self.nodes.items():
      node.repo.add(pathspec)
