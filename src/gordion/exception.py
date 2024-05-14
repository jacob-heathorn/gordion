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


class TargetBranchDoesNotContainTag(UpdateError):
  def __init__(self, repo):
    reason = (f"{repo.target_branch_name} does not contain {repo.target_tag}.")
    suggestion = f"Ensure the tag exists in either the remote or local {repo.target_branch_name}"
    super().__init__(repo.path, reason, suggestion)
