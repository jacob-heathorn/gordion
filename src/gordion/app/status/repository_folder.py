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

  def is_duplicate(self) -> bool:
    """
    A repository is marked duplicate if one of ...
      a) It is not listed, and there is another repo with the same URL.
      b) It is listed, and it is a dependency among duplicate listed dependencies.
      c) If it is a dependency and one or more working exist.
      d) If it is a working among duplicate working.
    """
    workspace = gordion.Workspace()
    working, dependencies = workspace.get_repositories(name=None, url=self.repo.url)

    # If it is not listed, and there is another repo with this URL.
    if not self.workspace.is_listed(self.repo):
      if len(working + dependencies) > 1:
        return True

    # If it is listed...
    else:
      # If it is a dependency among duplicate listed dependencies.
      if len(working) == 0:
        assert workspace.is_dependency(self.repo.path)
        num_listed_dependencies = 0
        for dependency in dependencies:
          if self.workspace.is_listed(dependency):
            num_listed_dependencies += 1
        print(num_listed_dependencies)
        return num_listed_dependencies > 1
      else:
        # If it is a dependency and one or more working exist.
        if workspace.is_dependency(self.repo.path):
          return True

        # If it is a working among duplicate working.
        else:
          if len(working) > 1:
            return True

  def is_correct_path(self) -> bool:
    if self.workspace.is_dependency(self.repo.path):
      if self.repo.path != os.path.join(self.workspace.dependencies_path, self.repo.name):
        return False
    return True

  def unique_listed_tags(self):
    listings = [listing for listing in self.root_listings if self.repo.url == listing.url]
    unique_tags = set()
    for listing in listings:
      unique_tags.add(self.repo._verify_tag(listing.tag).hexsha)

    return unique_tags

  def is_name_conflicted(self):
    listings = [listing for listing in self.root_listings if self.repo.url == listing.url]
    for listing in listings:
      if listing.name != self.repo.name:
        return True
    return False

  def is_url_conflicted(self):
    listings = [listing for listing in self.root_listings if self.repo.name == listing.name]
    for listing in listings:
      if not gordion.utils.compare_urls(listing.url, self.repo.url):
        return True
    return False

  @gordion.utils.override(Folder)
  def _get_display_name(self) -> str:
    """
    Returns the repository folder name, with branch:commit and warnings in descriptive colors.
    """

    # Aggregate existence errors and return if they have occured
    existence_errors = []
    if self.is_duplicate():
      existence_errors.append("DUPLICATE")
    if not self.is_correct_path():
      existence_errors.append("WRONG PATH")
    if not self.workspace.is_listed(self.repo):
      existence_errors.append("NOT LISTED")

    if existence_errors:
      return gordion.utils.bold_red(
          self.name) + gordion.utils.red(f" ({', '.join(existence_errors)})")

    # Repository name.
    name_header = gordion.utils.bold_green(self.name)

    # Check for conflicted name.
    listing_errors = []
    if self.is_name_conflicted():
      listing_errors.append("CONFLICTED NAME")
      name_header = gordion.utils.bold_red(self.name)

    # Check for conflicting URL.
    if self.is_url_conflicted():
      name_header = gordion.utils.bold_red(self.name)
      listing_errors.append("CONFLICTED URL")

    # Branch header.
    branch_header = self._get_branch_name()
    branch_header = self._color_branch(branch_header)
    branch_suggestion = self._get_branch_suggestion()
    branch_warnings = self._get_branch_warnings(branch_suggestion)
    if branch_warnings:
      branch_header += gordion.utils.yellow(f"({', '.join(branch_warnings)})")

    # Tag header.
    #
    # If any of the tags are incorrect, the commit is incorrect.
    unique_tags = self.unique_listed_tags()
    correct_tag = True
    conflicted_tag = False
    for tag in unique_tags:
      if tag != self.repo.handle.head.commit.hexsha:
        correct_tag = False
    if len(unique_tags) > 1:
      conflicted_tag = True

    tag_header = ""
    if conflicted_tag:
      listing_errors.append("CONFLICTED TAG")
      tag_header = gordion.utils.red(f":{self.repo.handle.head.commit.hexsha[:7]}")
    else:
      if correct_tag:
        tag_header = gordion.utils.green(f":{self.repo.handle.head.commit.hexsha[:7]}")
      else:
        tag_header = gordion.utils.red(f":{self.repo.handle.head.commit.hexsha[:7]}")

    # Append -dirty to hexsha if necessary.
    if self.repo.handle.is_dirty(untracked_files=True):
      tag_header += gordion.utils.yellow("-dirty")

    # Create listing errors header.
    listing_errors_header = ""
    if listing_errors:
      listing_errors_header = gordion.utils.red(f"({', '.join(listing_errors)})")

    # Create display name
    display_name = name_header + " " + branch_header + tag_header
    display_name += " " + listing_errors_header
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

  def _get_branch_warnings(self, branch_suggestion: Optional[str]) -> List[str]:
    warnings: list['str'] = []

    # Generate branch warnings string
    if branch_suggestion:
      warnings.append(f"{branch_suggestion}?")

    # Other active branch related warnings.
    if not self.repo.handle.head.is_detached:
      # Warn if branch is untracked.
      if self._is_tracked():
        # Warng if it has the incorrect tracking branch name.
        if self._is_correct_tracking_branch():
          pass
        else:
          warnings.append("wrong tracking branch")

        # Warn if branch is ahead.
        if self._is_ahead():
          warnings.append("ahead")
      else:
        warnings.append("untracked")

    # Detached
    else:
      if not self._is_detached_head_saved():
        warnings.append("unsaved")

    return warnings

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
