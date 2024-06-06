import os


class UpdateError(Exception):
  def __init__(self, repo_path, reason, suggestion):
    self.message = f"Cannot update {repo_path}.\nreason: {reason}\nsuggestion: {suggestion}"
    super().__init__(self.message)


class UpdateLocalBranchAheadError(UpdateError):
  def __init__(self, repo_path, local_branch, remote_branch, num_commits):
    reason = (f"{local_branch} has {num_commits} commit(s) ahead of {remote_branch}. "
              f"Update would lose these commit(s)")
    suggestion = "Either push the commits or force the update please"
    super().__init__(repo_path, reason, suggestion)


class UpdateNoTrackingBranchError(UpdateError):
  def __init__(self, repo_path, local_branch):
    reason = f"{local_branch} does not have a tracking branch, so commits will be lost."
    suggestion = f"Create a remote tracking branch (git push -u origin {local_branch})"
    super().__init__(repo_path, reason, suggestion)


class UpdateWrongTrackingBranchError(UpdateError):
  def __init__(self, repo_path, local_branch, remote_branch):
    reason = (f"{local_branch} does not track origin/{local_branch}. Instead, it tracks"
              "{remote_branch}. This is unexpected and can cause problems.")
    suggestion = f"fix it: git push -u origin {local_branch}. Maybe delete incorrect remote branch?"
    super().__init__(repo_path, reason, suggestion)


class UpdateDetachedHeadNotSavedError(UpdateError):
  def __init__(self, repo_path):
    reason = ("The repository is an a detached HEAD state. This is fine except the HEAD is a commit"
              "that is not saved in a local ore remote branch. This indicates that you have made"
              "local commits while in the detached HEAD state, which is fine but we want to"
              "make sure you save those changes.")
    suggestion = "Checkout a new local branch to save the current head state."
    super().__init__(repo_path, reason, suggestion)


class UpdateRepoIsDirtyError(UpdateError):
  def __init__(self, repo_path):
    reason = ("The repository is dirty and you are trying to move the HEAD commit.")
    suggestion = "Save or restore the uncommitted changes."
    super().__init__(repo_path, reason, suggestion)


class UpdateDuplicateRepoPathError(UpdateError):
  def __init__(self, path, other_repo):
    reason = (f"The repository({other_repo.url}) is already cloned at "
              f"{other_repo.path}. You are trying to clone it again to {path}. You cannot "
              f"do this.")
    suggestion = ("You need to make sure all listings of the same repository have the same "
                  "local path in the gordion.yaml file.")
    super().__init__(path, reason, suggestion)

# TODO use "parent" property to get the gordion file that has the mistake.


class UpdateDuplicateRepoTagError(UpdateError):
  def __init__(self, path, yaml_listing, other_repo):

    other_yaml_listing = other_repo.parent_listing
    if not other_yaml_listing:
      root_name = os.path.basename(other_repo.path)
      other_yaml_listing = f"{root_name}:{other_repo.handle.head.commit.hexsha}"
    reason = (
        f"Gordion repository mismatch!\n\t{yaml_listing}\n\t{other_yaml_listing}")
    suggestion = ("These need to match.")
    super().__init__(path, reason, suggestion)
