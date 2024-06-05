class UpdateError(Exception):
  def __init__(self, repo_path, reason, suggestion):
    self.message = f"Cannot update {repo_path} because {reason}. {suggestion}."
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
  def __init__(self, repo, other_repo):
    reason = (f"The repository({other_repo.handle.remotes.origin.url}) is already cloned at "
              f"{other_repo.path}. You are trying to clone it again to {repo.path}. You cannot "
              f"do this.")
    suggestion = ("You need to make sure all listings of the same repository have the same"
                  "local path in the gordion.yaml file.")
    super().__init__(repo.path, reason, suggestion)

# TODO use "parent" property to get the gordion file that has the mistake.


class UpdateDuplicateRepoTagError(UpdateError):
  def __init__(self, repo, other_repo, tag):
    reason = (f"The repository({other_repo.path}) is already checked out at"
              f"tag({other_repo.handle.head.commit.hexsha}). You are trying to overwrite the"
              f"commit to {tag}.")
    suggestion = ("You need to make sure all listings of the same repository have the same"
                  "tag in the gordion.yaml files.")
    super().__init__(repo.path, reason, suggestion)
