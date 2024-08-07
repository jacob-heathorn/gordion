class UpdateError(Exception):
  def __init__(self, target, reason, suggestion):
    self.message = (f"Cannot update repository<{target.name}>.\n"
                    f"listed path: <{target._listed_path()}>\n"
                    f"system path: <{target.path}>\n"
                    f"{reason}. {suggestion}.")
    super().__init__(self.message)


class UpdateLocalBranchAheadError(UpdateError):
  def __init__(self, target, local_branch, remote_branch, num_commits):
    reason = (f"{local_branch} is {num_commits} commit(s) ahead of {remote_branch}. "
              f"Update would lose one or more of these commit(s)")
    suggestion = "Push or remove the commits please"
    super().__init__(target, reason, suggestion)


class UpdateNoTrackingBranchError(UpdateError):
  def __init__(self, target, local_branch):
    reason = f"{local_branch} does not have a tracking branch, so commits will be lost"
    suggestion = f"Create a remote tracking branch (git push -u origin {local_branch})"
    super().__init__(target, reason, suggestion)


class UpdateWrongTrackingBranchError(UpdateError):
  def __init__(self, target, local_branch, remote_branch):
    reason = (f"{local_branch} does not track origin/{local_branch}. Instead, it tracks "
              f"{remote_branch}. This is unexpected and can cause problems")
    suggestion = f"fix it: git push -u origin {local_branch}. Maybe delete incorrect remote branch?"
    super().__init__(target, reason, suggestion)


class UpdateDetachedHeadNotSavedError(UpdateError):
  def __init__(self, target):
    reason = (f"The repository<{target.name}> is in a detached HEAD state. This is fine except "
              f"the HEAD is a commit that is not saved in a local or remote branch. This "
              f"indicates that you have made local commits while in the detached HEAD state, "
              f"which is fine but we want to make sure you save those changes")
    suggestion = "Checkout a new local branch to save the current head state"
    super().__init__(target, reason, suggestion)


class UpdateRepoIsDirtyError(UpdateError):
  def __init__(self, target):
    reason = ("The repository is dirty and you are trying to move the HEAD commit")
    suggestion = "Save or restore the uncommitted changes"
    super().__init__(target, reason, suggestion)


class UpdateDuplicateRepoPathError(UpdateError):
  def __init__(self, target, other):
    reason = (f"The repository({other.url}) is already cloned at {other.path}. You are trying to "
              f"clone it again to {target.path}. You cannot do this")
    suggestion = ("You need to make sure all listings of the same repository have the same "
                  "local path in the gordion.yaml file")
    super().__init__(target, reason, suggestion)


class UpdateDuplicateRepoTagError(UpdateError):
  def __init__(self, target, target_tag, other, other_tag):
    reason = (f"Gordion repository tag mismatch!\n"
              f"{target._listed_path()}:{target_tag}\n"
              f"{other._listed_path()}:{other_tag}\n")
    suggestion = ("The tags need to match. I guess that's kinda the whole point of this thing")
    super().__init__(target, reason, suggestion)


class UnsafeRemoveDirty(Exception):
  def __init__(self, path):
    self.message = (
      f"Cannot remove repository<{path}> because it is dirty."
    )
    super().__init__(self.message)


class UnsafeRemoveLocalBranchAhead(Exception):
  def __init__(self, path, local_branch, tracking_branch, num_commits_ahead):
    self.message = (
      f"Cannot remove repository<{path}> because it has local branch<{local_branch}> that is "
      f"{num_commits_ahead} commit(s) ahead of tracking branch<{tracking_branch}>."
    )
    super().__init__(self.message)


class UnsafeRemoveLocalBranchNoTrackingBranch(Exception):
  def __init__(self, path, local_branch):
    self.message = (
      f"Cannot remove repository<{path}> because it has local branch<{local_branch}> that does "
      f"not have a tracking branch."
    )
    super().__init__(self.message)


class UnsafeRemoveStashes(Exception):
  def __init__(self, path, stashes):
    self.message = (
      f"Cannot remove repository<{path}> because it has the following stashes that would be lost:\n"
      f"{stashes}."
    )
    super().__init__(self.message)


class NotAGordionRepositoryError(Exception):
  def __init__(self):
    self.message = (
      "You are not in a gordion repository!"
    )
    super().__init__(self.message)


class DanglingGordionRepositoryError(Exception):
  def __init__(self, current_repo_path, disconnected_parent_path):
    self.message = (
      f"You are in repository<{current_repo_path}>. There is a parent gordion "
      f"repository<{disconnected_parent_path}> but it does not list this repository. Therefore "
      f"this repository appears to be dangling and should be deleted."
    )
    super().__init__(self.message)


class BadRepositoryNamePathMismach(Exception):
  def __init__(self, file, path, name):
    self.message = (
      f"File<{file}> lists repository name<{name}> but the path is <{path}>. The name needs to"
      f" match the base directory name of the path."
    )
    super().__init__(self.message)


class UpdateDifferentRepoSamePathError(UpdateError):
  def __init__(self, target, other):
    reason = (f"The repository<{other.url}> is already cloned<{other.path}>."
              f" You are trying to clone <{target.url}> to the same path."
              " You cannot do this")
    suggestion = "You need to make sure repositories have unique paths in the gordion.yaml files"
    super().__init__(target, reason, suggestion)


class DanglingCommitError(UpdateError):
  def __init__(self, target, target_tag):
    reason = (f"Commit<{target_tag}> is dangling (does not belong to a branch)")
    suggestion = ("Update the commit tag in the parent gordion.yaml")
    super().__init__(target, reason, suggestion)
