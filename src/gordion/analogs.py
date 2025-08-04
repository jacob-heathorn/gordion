import gordion
from typing import Dict
from dataclasses import dataclass, field
from typing import Optional


class Analogs:
  """
  Provides git analogs to a gordion repository and it's children.
  """

  @dataclass
  class Node:
    """
    Wraps a repository object and adds necessary fields for git analog operations.
    """
    repo: gordion.Repository
    committed: bool = False
    gordion_updates_message: str = ""
    children: Dict[str, 'Analogs.Node'] = field(default_factory=dict)
    parents: Dict[str, 'Analogs.Node'] = field(default_factory=dict)

  @staticmethod
  def lineage(node: Node) -> Dict[str, 'Analogs.Node']:
    lineage: Dict[str, 'Analogs.Node'] = {}
    for _, parent in node.parents.items():
      lineage[parent.repo.path] = parent
      lineage.update(Analogs.lineage(parent))
    return lineage

  def __init__(self, root: gordion.Repository):
    self.root = Analogs.Node(root)
    self.nodes: Dict[str, Analogs.Node] = {}
    self.trace(root)

  def trace(self, _repo: gordion.Repository):

    # Register this node if necessary.
    node = self.nodes.get(_repo.path)
    if not node:
      node = Analogs.Node(repo=_repo)
      self.nodes[node.repo.path] = node

    # Register it's children.
    if node.repo.yeditor.exists():
      assert node.repo.yeditor.yaml_data
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
                child = Analogs.Node(repo=child_repo)
                self.nodes[child.repo.path] = child

              # Register parent/child relationship.
              node.children[child.repo.path] = child
              child.parents[node.repo.path] = node

              # Recurse.
              self.trace(child.repo)
            else:
              raise gordion.exception.TraceError()
          else:
            raise gordion.exception.TraceError()
        else:
          raise gordion.exception.TraceError()

  def verify_changes_are_branch(self, branch_name: str):
    """
    Raises an error if any repository in the heirarchy has changes, but does not check out the
    provided <branch_name>
    """
    bad_nodes = []
    for _, node in self.nodes.items():
      if node.repo.is_dirty():
        if not node.repo.is_branch(branch_name):
          bad_nodes.append(node.repo)
    if len(bad_nodes) > 0:
      raise gordion.exception.WrongBranchRepositoryDirty(branch_name, bad_nodes)

  def verify_lineage_is_branch(self, branch_name: str):
    """
    Raises an error if any ancestor of a repository with added changes is not the correct branch.
    """

    bad_nodes: Dict[str, gordion.Repository] = {}

    # For each node, if it has staged changes...
    for _, node in self.nodes.items():
      if node.repo.has_staged_changes():
        # Collect all ancestors with the wrong branch.
        for _, ancestor in Analogs.lineage(node).items():
          if not ancestor.repo.is_branch(branch_name):
            bad_nodes[ancestor.repo.path] = ancestor.repo

    if len(bad_nodes) > 0:
      raise gordion.exception.WrongBranchRepositoryLineage(branch_name, list(bad_nodes.values()))

  def verify_lineage_does_not_have_unstaged_gordion_changes(self):
    """
    Raises an error if any ancestor of a repository with staged changes has unstaged changes in it's
    gordion file.
    """

    # An ancestor to a repository with staged changes cannot have unstaged changes in it's gordion
    # file because we will automatically be modifying it and committing it during this command.
    for _, node in self.nodes.items():
      if node.repo.has_staged_changes():
        for _, ancestor in Analogs.lineage(node).items():
          diff = ancestor.repo.handle.git.diff('--', 'gordion.yaml')
          if bool(diff):
            raise gordion.exception.UnstagedGordionChangesInLineage()

  def has_staged_changes(self) -> bool:
    """
    Returns true if any repo in the heirarchy has staged changes.
    """
    for _, node in self.nodes.items():
      if node.repo.has_staged_changes():
        return True
    return False

  def verify_no_cached_repositories(self):
    """
    Raises an error if any repository that would be affected by a commit is in the cache.
    This includes repositories with staged changes and their ancestors.
    """
    workspace = gordion.Workspace()
    cached_repos: Dict[str, gordion.Repository] = {}

    # For each node with staged changes...
    for _, node in self.nodes.items():
      if node.repo.has_staged_changes():
        # Check if the node itself is cached
        if workspace.is_dependency(node.repo.path):
          cached_repos[node.repo.path] = node.repo

        # Check all ancestors for cached repositories
        for _, ancestor in Analogs.lineage(node).items():
          if workspace.is_dependency(ancestor.repo.path):
            cached_repos[ancestor.repo.path] = ancestor.repo

    if len(cached_repos) > 0:
      raise gordion.exception.CommitCachedRepositoriesError(list(cached_repos.values()))

  # =================================================================================================
  # The Analogs

  def add(self, branch_name: str, pathspec: str):
    """
    Analog for: git add
    """

    self.verify_changes_are_branch(branch_name)
    for _, node in self.nodes.items():
      node.repo.add(pathspec)

  def restore(self, pathspec: str, staged: bool):
    """
    Analog for: git restore
    """
    for _, node in self.nodes.items():
      node.repo.restore(pathspec, staged)

  def clean(self, force: bool, dirs: bool, extra: bool):
    """
    Analog for: git clean
    """
    for _, node in self.nodes.items():
      node.repo.clean(force, dirs, extra)

  def commit(self, branch_name: str, header: str):
    """
    Analog for: git commit
    """
    self.verify_no_cached_repositories()
    self.verify_changes_are_branch(branch_name)
    self.verify_lineage_is_branch(branch_name)
    self.verify_lineage_does_not_have_unstaged_gordion_changes()

    while self.has_staged_changes():
      for _, node in self.nodes.items():
        if node.repo.has_staged_changes():
          # Print progress message
          print(f"Committing {node.repo.name}...")

          # Commit this node.
          message = header + "\n"
          message += node.gordion_updates_message
          node.repo.commit(message, node.committed)
          node.committed = True

          # Modify this node's parents' gordion.yaml files and stage the change.
          commit = node.repo.handle.head.commit
          for _, parent in node.parents.items():
            if not parent.repo.yeditor.read_repository_tag(
                    node.repo.name) == commit.hexsha:
              # Update the parent's gordion.yaml file.
              parent.repo.yeditor.write_repository_tag(node.repo.name, commit.hexsha)
              # Add the change.
              parent.repo.add("gordion.yaml")
              parent.gordion_updates_message += f"\n* Bump {node.repo.name} to {commit.hexsha}"

  def push(self, set_upstream: bool, delete: bool, remote: Optional[str], branch: str, force: bool):
    """
    Analog for: git push
    """

    for _, node in self.nodes.items():
      if branch in [branch.name for branch in node.repo.handle.branches]:  # type: ignore
        node.repo.push(set_upstream, delete, remote, branch, force)
