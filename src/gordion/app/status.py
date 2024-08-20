import gordion
import os
from typing import List, Optional


def does_tree_list_repository(root: gordion.Tree, repo: gordion.Repository) -> bool:
  """
  Returns true if any of the tree lists the provided repository, identified by the name, url, and
  path. Or if any of the children (with correct tags) list the repository.
  """
  if repo == root:
    return True

  root.yeditor.reload()
  # Check yaml file for this repository
  if root.yeditor.exists():
    for child_name, child_info in root.yeditor.yaml_data['repositories'].items():
      gpath = root.yeditor.read_repository_gpath(child_name)
      child_path = os.path.join(gordion.Store().path, gpath)

      # Check if the child repository exists
      if gordion.Repository._exists(child_path):

        # If the child matches the repo by name, path, and url, then it is in the tree.
        if repo.name == child_name and repo.path == child_path and repo.url == child_info['url']:
          return True

        # Otherwise check the child's children ONLY if the child is the correct tag.
        else:
          child = gordion.Tree(child_path)
          child_target_commit = child._verify_tag(child_info['tag'])
          if child.handle.head.commit == child_target_commit:
            if does_tree_list_repository(child, repo):
              return True

  return False


# TODO duiplicate code
def does_tree_list_repository_with_tag(root: gordion.Tree, repo: gordion.Repository) -> bool:
  """
  Returns true if any of the tree lists the provided repository, identified by the name, url,
  path, and tag. Or if any of the children (with correct tags) list the repository.
  """
  if repo == root:
    return True

  root.yeditor.reload()
  # Check yaml file for this repository
  if root.yeditor.exists():
    for child_name, child_info in root.yeditor.yaml_data['repositories'].items():
      gpath = root.yeditor.read_repository_gpath(child_name)
      child_path = os.path.join(gordion.Store().path, gpath)

      # Check if the child repository exists
      if gordion.Repository._exists(child_path):
        child = gordion.Tree(child_path)
        child_target_commit = child._verify_tag(child_info['tag'])

        # If the child matches the repo by name, path, and url, and tag then return true.
        if (repo.name == child_name and repo.path == child_path and  # noqa: W504
            repo.url == child_info['url'] and repo.handle.head.commit == child_target_commit):
          return True

        # Otherwise check the child's children ONLY if the child is the correct tag.
        else:
          if child.handle.head.commit == child_target_commit:
            if does_tree_list_repository(child, repo):
              return True

  return False


class Folder:
  """
  TODO

  """

  def __init__(self, name) -> None:
    self.name = name
    self.children: List[Folder] = []
    self.parent: Optional[Folder] = None
    self.repo: Optional[gordion.Repository] = None

  def top(self):
    if self.parent:
      return self.parent.top()
    else:
      return self

  def get_symbol_row(self):
    symbols = []
    if self.parent:
      child_type = self.parent.get_child_type(self.name)
      if child_type == "last":
        symbols.insert(0, "└──")
      else:
        symbols.insert(0, "├──")

      current_folder = self.parent
      while current_folder:
        if current_folder.parent:
          parent_child_type = current_folder.parent.get_child_type(current_folder.name)
          if parent_child_type == "last":
            symbols.insert(0, "    ")
          else:
            symbols.insert(0, "│   ")

        current_folder = current_folder.parent

    return symbols

  @staticmethod
  def is_root_branch(repo, root: gordion.Tree) -> bool:
    if not repo.handle.head.is_detached:
      if not root.handle.head.is_detached:
        return repo.handle.active_branch.name == root.handle.active_branch.name

    return False

  @staticmethod
  def is_tracked(repo) -> bool:
    return bool(repo.handle.active_branch.tracking_branch())

  @staticmethod
  def is_correct_tracking_branch(repo) -> bool:
    active_branch = repo.handle.active_branch
    return active_branch.tracking_branch().name == f"origin/{active_branch.name}"

  @staticmethod
  def is_ahead(repo) -> bool:
    active_branch = repo.handle.active_branch
    merge_base = repo.handle.merge_base(active_branch, active_branch.tracking_branch())
    commits_ahead = list(repo.handle.iter_commits(
            f'{merge_base[0].hexsha}..{active_branch.commit.hexsha}'))
    return bool(commits_ahead)

  @staticmethod
  def is_default_branch(repo) -> bool:
    if not repo.handle.head.is_detached:
      return repo.handle.active_branch.name == repo.default_branch_name
    return False

  @staticmethod
  def does_root_branch_have_commit(repo, root):
    if not root.handle.head.is_detached:
      root_branch_name = root.handle.active_branch.name
      return repo._does_local_branch_have_commit(root_branch_name, repo.handle.head.commit)

  @staticmethod
  def get_branch_header(repo, root: gordion.Tree):
    branch_header = ""
    # First print the name of the branch, in green if it is correct, and yellow if it is incorrect
    # or detached.
    branch_suggestion: Optional[str] = None
    branch_header = ""

    # TODO handle other branch, and detached cases.
    if Folder.is_root_branch(repo, root):
      branch_header += gordion.utils.green(repo.handle.active_branch.name)

    elif Folder.is_default_branch(repo):
      if Folder.does_root_branch_have_commit(repo, root):
        branch_suggestion = root.handle.active_branch.name
        branch_header += gordion.utils.yellow(repo.handle.active_branch.name)
      else:
        branch_header += gordion.utils.green(repo.handle.active_branch.name)

    # Orthoganally, append untracked, correct branch suggestion, or ahead if necessary.
    def append_warning(warning: str, addition: str):
      if not warning:
        warning = f"({addition})"
      else:
        warning = warning[0:-2]
        warning += f", {addition})"
      return warning

    # Generate branch warning string
    warning_str = ""
    if branch_suggestion:
      warning_str = append_warning(warning_str, f"{branch_suggestion}?")

    # Other active branch related warnings.
    if not repo.handle.head.is_detached:
      # Warn if branch is untracked.
      if Folder.is_tracked(repo):
        # Warng if it has the incorrect tracking branch name.
        if Folder.is_correct_tracking_branch(repo):
          pass
        else:
          warning_str = append_warning(warning_str, "wrong tracking branch")

        # Warn if branch is ahead.
        if Folder.is_ahead(repo):
          warning_str = append_warning(warning_str, "ahead")
      else:
        warning_str = append_warning(warning_str, "untracked")

    if warning_str:
      branch_header += gordion.utils.yellow(warning_str)

    return branch_header

  def print(self, root: gordion.Tree):
    print(*self.get_symbol_row(), sep='', end='')
    header = gordion.utils.bold_blue(self.name)
    if self.repo:
      # Branch header.
      # TODO branch coloring
      if self.repo.handle.head.is_detached:
        branch_header = "HEAD detached"
      else:
        branch_header = Folder.get_branch_header(self.repo, root)

      # Name branch:tag
      if does_tree_list_repository(root, self.repo):
        header = gordion.utils.bold_green(self.name)
        header += " " + branch_header
        if does_tree_list_repository_with_tag(root, self.repo):
          header += ":" + gordion.utils.green(f"{self.repo.handle.head.commit.hexsha[:7]}")
        else:
          header += ":" + gordion.utils.red(f"{self.repo.handle.head.commit.hexsha[:7]}")
      else:
        header = gordion.utils.bold_red(self.name)
        header += " " + branch_header
        header += ":" + gordion.utils.red(f"{self.repo.handle.head.commit.hexsha[:7]}")

    print(header)

    for child in self.children:
      child.print(root)

  def get_child_type(self, child_name):
    total_children = len(self.children)
    for index, child in enumerate(self.children):
      if child.name == child_name:
        if index == total_children - 1:
          return "last"
        elif index == 0:
          return "first"
        else:
          return "middle"


def print_path_tree(root):
  repos = [root]
  repos.extend(gordion.Store().list_repos())
  repos.sort(key=lambda repo: repo.path)
  root_folder = Folder(root.name)
  root_folder.repo = root

  for repo in repos:
    relpath = os.path.relpath(repo.path, os.path.dirname(root.path))
    parts = relpath.split(os.sep)

    current_folder = root_folder
    for index, part in enumerate(parts):
      if current_folder.name == part:
        continue
      else:
        found_child = False
        for child in current_folder.children:
          if child.name == part:
            current_folder = child
            found_child = True
            break

        if not found_child:
          new_child = Folder(part)
          if index == len(parts) - 1:
            new_child.repo = repo
          new_child.parent = current_folder
          current_folder.children.append(new_child)
          current_folder = new_child

  root_folder.print(root)


def print_status(root):
  print_path_tree(root)
