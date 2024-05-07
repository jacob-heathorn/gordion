class OperationError(Exception):
  """Exception raised for user facing errors that an operation cannot be performed."""
  def __init__(self, message="Operation error."):
      self.message = message
      super().__init__(self.message)

class UpdateError(Exception):
  """Exception raised for user facing errors that an operation cannot be performed."""
  def __init__(self, repo_path, reason, suggestion):
    self.message = f"Cannot update {repo_path} because {reason}. {suggestion}."
    super().__init__(self.message)

class UpdateActiveBranchAheadError(UpdateError):
  """Exception raised for user facing errors that an operation cannot be performed."""
  def __init__(self, repo_path, active_branch, remote_branch, num_commits):
    reason = f"{active_branch} is ahead of {remote_branch} by {num_commits} commit(s). Update would lose these commit(s)"
    suggestion = "Either push the repository or force the update please"
    super().__init__(repo_path, reason, suggestion)
