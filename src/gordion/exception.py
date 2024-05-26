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
    reason = (f"{local_branch} does not track origin/{local_branch}. Instead, it tracks {remote_branch}.",
              "This is unexpected and can cause problems.")
    suggestion = f"fix it: git push -u origin {local_branch}. Maybe delete incorrect remote branch?"
    super().__init__(repo_path, reason, suggestion)
