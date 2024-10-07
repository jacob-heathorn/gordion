import gordion
from typing import Optional, List
import os
from .terminal_status import Folder


class RepositoryFolder(Folder):
  """
  Inherits from Folder, to override _get_display_name so that a Folder that "isa"
  repository can print information about the repository in pretty colors.
  """

  def __init__(self, repo: gordion.Repository, root: gordion.Tree) -> None:
    super().__init__(repo.path)
    self.repo = repo
    self.root: gordion.Tree = root
    self.root_listings = self.root.listings(name=None, url=None)
    self.workspace = gordion.Workspace()
    self.existence_error_string = ""

  def check_duplicate(self):
    all_repos = self.workspace.working + self.workspace.dependencies
    for repo in all_repos:
      if repo.path != self.repo.path:
        if gordion.utils.compare_urls(repo.url, self.repo.url):
          self.append_existence_error("DUPLICATE")
          return

  def check_path(self):
    if self.workspace.is_dependency(self.repo.path):
      if self.repo.path != os.path.join(self.workspace.dependencies_path, self.repo.name):
        self.append_existence_error("WRONG_PATH")

  def check_is_listed(self):
    """
    Checks that the repository is listed by name and url by at least one of the working
    repositories.
    """
    # Working repositories don't need to be listed
    if not self.workspace.is_dependency(self.repo.path):
      return

    listed = False
    for repo in self.workspace.working:
      if gordion.Repository.is_gordion(repo.path):
        tree = gordion.Tree(repo.path)
        listings = tree.listings(name=self.repo.name, url=self.repo.url)
        if len(listings) > 0:
          listed = True
          break
    if not listed:
      self.append_existence_error("NOT LISTED")

  def append_existence_error(self, error: str):
    if not self.existence_error_string:
      self.existence_error_string = f"({error})"
    else:
      self.existence_error_string = self.existence_error_string[0:-1]
      self.existence_error_string += f", {error})"

  @gordion.utils.override(Folder)
  def _get_display_name(self) -> str:
    """
    Returns the repository folder name, with branch:commit and warnings in descriptive colors.
    """

    # Aggregate existence errors and return if they have occured
    self.check_duplicate()
    self.check_path()
    self.check_is_listed()
    if self.existence_error_string:
      return gordion.utils.bold_red(
          self.name) + gordion.utils.red(f" {self.existence_error_string}")

    # Get all the listings of this repo in the tree and check for yaml listing discrepencies.
    listings = self.root.listings(self.name, self.repo.url)
    is_repository_listed = False
    correct_tag = True
    mismatch = False
    unique_tags = set()
    for listing in listings:
      unique_tags.add(self.repo._verify_tag(listing.tag).hexsha)

    if len(unique_tags) > 0:
      is_repository_listed = True

    # If any of the tags are incorrect, the commit is incorrect.
    for tag in unique_tags:
      if tag != self.repo.handle.head.commit.hexsha:
        correct_tag = False

    if len(unique_tags) > 1:
      mismatch = True

    # Branch header.
    branch_header = self._get_branch_name()
    branch_suggestion = None
    if is_repository_listed:
      branch_header = self._color_branch(branch_header)
      branch_suggestion = self._get_branch_suggestion()

    branch_header += self._get_branch_warnings(branch_suggestion)

    # Name branch:tag
    if is_repository_listed:
      display_name = gordion.utils.bold_green(self.name)
      display_name += " " + branch_header

      if mismatch > 0:
        display_name += ":" + gordion.utils.red(
            f"{self.repo.handle.head.commit.hexsha[:7]}-mismatch")
      else:
        if correct_tag:
          display_name += ":" + gordion.utils.green(f"{self.repo.handle.head.commit.hexsha[:7]}")
        else:
          display_name += ":" + gordion.utils.red(f"{self.repo.handle.head.commit.hexsha[:7]}")
    else:
      display_name = gordion.utils.bold_red(self.name)
      display_name += " " + branch_header
      display_name += ":" + self.repo.handle.head.commit.hexsha[:7]

    # Append -dirty to hexsha if necessary.
    if self.repo.handle.is_dirty(untracked_files=True):
      display_name += gordion.utils.yellow("-dirty")

    return display_name

  def _get_branch_name(self):
    if self.repo.handle.head.is_detached:
      return "DETACHED HEAD"
    else:
      return self.repo.handle.active_branch.name

  def _color_branch(self, branch_name: str):
    # Case1: Root branch is checked out.
    if self._is_root_branch():
      return gordion.utils.green(branch_name)

    # Case2: Default branch is checked out.
    elif self._is_default_branch():
      if self._does_root_branch_have_commit():
        return gordion.utils.yellow(branch_name)
      else:
        return gordion.utils.green(branch_name)

    # Case3: Other branch is checked out.
    elif self._is_other_branch():
      return gordion.utils.yellow(branch_name)

    # Case4: DETATCHED
    elif self.repo.handle.head.is_detached:
      if self._does_root_branch_have_commit():
        return gordion.utils.yellow(branch_name)
      elif self._does_default_branch_have_commit():
        return gordion.utils.yellow(branch_name)
      else:
        return gordion.utils.green(branch_name)

  def _get_branch_suggestion(self):
    branch_suggestion: Optional[str] = None

    # Case1: Root branch is checked out.
    if self._is_root_branch():
      pass

    # Case2: Default branch is checked out.
    elif self._is_default_branch():
      if self._does_root_branch_have_commit():
        branch_suggestion = self.root.handle.active_branch.name

    # Case3: Other branch is checked out.
    elif self._is_other_branch():
      if self._does_root_branch_have_commit():
        branch_suggestion = self.root.handle.active_branch.name
      elif self._does_default_branch_have_commit():
        branch_suggestion = self.repo.default_branch_name

    # Case4: DETATCHED
    elif self.repo.handle.head.is_detached:
      if self._does_root_branch_have_commit():
        branch_suggestion = self.root.handle.active_branch.name
      elif self._does_default_branch_have_commit():
        branch_suggestion = self.repo.default_branch_name

    return branch_suggestion

  def _is_other_branch(self) -> bool:
    if not self.repo.handle.head.is_detached:
      return not self._is_default_branch() and not self._is_root_branch()
    return False

  def _does_root_branch_have_commit(self):
    if not self.root.handle.head.is_detached:
      root_branch_name = self.root.handle.active_branch.name
      return self.repo._does_local_branch_have_commit(root_branch_name,
                                                      self.repo.handle.head.commit)

  def _does_default_branch_have_commit(self):
    return self.repo._does_local_branch_have_commit(self.repo.default_branch_name,
                                                    self.repo.handle.head.commit)

  def _is_detached_head_saved(self) -> bool:
    # Check if the local HEAD commit is the tip of any local or remote branch.
    head_commit = self.repo.handle.head.commit

    # Check local branches.
    local_branches = [branch for branch in self.repo.handle.branches  # type: ignore
                      if head_commit.hexsha == branch.commit.hexsha or  # noqa: W504
                      head_commit.hexsha in  # noqa: W504
                      [commit.hexsha for commit in branch.commit.iter_parents()]]

    # If not found in local, check remote branches.
    if not local_branches:
      remote_branches = [branch for branch in self.repo.handle.remotes.origin.refs
                         if head_commit.hexsha == branch.commit.hexsha or  # noqa: W504
                         head_commit.hexsha in
                         [commit.hexsha for commit in branch.commit.iter_parents()]]
      return bool(remote_branches)

    return bool(local_branches)

  def _get_branch_warnings(self, branch_suggestion: Optional[str]):
    # Generate warnings
    def append_warning(warning: str, addition: str):
      if not warning:
        warning = f"({addition})"
      else:
        warning = warning[0:-1]
        warning += f", {addition})"
      return warning

    # Generate branch warnings string
    warning_str = ""
    if branch_suggestion:
      warning_str = append_warning(warning_str, f"{branch_suggestion}?")

    # Other active branch related warnings.
    if not self.repo.handle.head.is_detached:
      # Warn if branch is untracked.
      if self._is_tracked():
        # Warng if it has the incorrect tracking branch name.
        if self._is_correct_tracking_branch():
          pass
        else:
          warning_str = append_warning(warning_str, "wrong tracking branch")

        # Warn if branch is ahead.
        if self._is_ahead():
          warning_str = append_warning(warning_str, "ahead")
      else:
        warning_str = append_warning(warning_str, "untracked")

    # Detached
    else:
      if not self._is_detached_head_saved():
        warning_str = append_warning(warning_str, "unsaved")

    if warning_str:
      return gordion.utils.yellow(warning_str)
    else:
      return ''

  def _is_root_branch(self) -> bool:
    if not self.repo.handle.head.is_detached:
      if not self.root.handle.head.is_detached:
        return self.repo.handle.active_branch.name == self.root.handle.active_branch.name

    return False

  def _is_tracked(self) -> bool:
    return bool(self.repo.handle.active_branch.tracking_branch())

  def _is_correct_tracking_branch(self) -> bool:
    active_branch = self.repo.handle.active_branch
    return active_branch.tracking_branch().name == f"origin/{active_branch.name}"  # type: ignore

  def _is_ahead(self) -> bool:
    active_branch = self.repo.handle.active_branch
    merge_base = self.repo.handle.merge_base(active_branch, active_branch.tracking_branch())
    commits_ahead = list(self.repo.handle.iter_commits(
            f'{merge_base[0].hexsha}..{active_branch.commit.hexsha}'))
    return bool(commits_ahead)

  def _is_default_branch(self) -> bool:
    if not self.repo.handle.head.is_detached:
      return self.repo.handle.active_branch.name == self.repo.default_branch_name
    return False
