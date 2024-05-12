class UpdateError(Exception):
  def __init__(self, repo_path, reason, suggestion):
    self.message = f"Cannot update {repo_path} because {reason}. {suggestion}."
    super().__init__(self.message)


class UpdateActiveBranchAheadError(UpdateError):
  def __init__(self, repo_path, active_branch, remote_branch, num_commits):
    reason = (f"{active_branch} is ahead of {remote_branch} by {num_commits} commit(s)."
              f"Update would lose these commit(s)")
    suggestion = "Either push the repository or force the update please"
    super().__init__(repo_path, reason, suggestion)
