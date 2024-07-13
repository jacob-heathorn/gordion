class UpdateError(Exception):
  def __init__(self, target, reason, suggestion):
    self.message = (f"Cannot update {target.name}.\n"
                    f"system path: {target.path}\n"
                    f"listed path: {target._listed_path()}\n"
                    f"reason: {reason}\n"
                    f"suggestion: {suggestion}")
    super().__init__(self.message)


class UpdateLocalBranchAheadError(UpdateError):
  def __init__(self, target, local_branch, remote_branch, num_commits):
    reason = (f"{local_branch} is {num_commits} commit(s) ahead of {remote_branch}. "
              f"Update would lose one or more of these commit(s).")
    suggestion = "Push or remove the commits please."
    super().__init__(target, reason, suggestion)


class UpdateNoTrackingBranchError(UpdateError):
  def __init__(self, target, local_branch):
    reason = f"{local_branch} does not have a tracking branch, so commits will be lost."
    suggestion = f"Create a remote tracking branch (git push -u origin {local_branch})"
    super().__init__(target, reason, suggestion)


class UpdateWrongTrackingBranchError(UpdateError):
  def __init__(self, target, local_branch, remote_branch):
    reason = (f"{local_branch} does not track origin/{local_branch}. Instead, it tracks\n\t\t"
              f"{remote_branch}. This is unexpected and can cause problems.")
    suggestion = f"fix it: git push -u origin {local_branch}. Maybe delete incorrect remote branch?"
    super().__init__(target, reason, suggestion)


class UpdateDetachedHeadNotSavedError(UpdateError):
  def __init__(self, target):
    tab = " " * 8
    reason = (f"The repository is in a detached HEAD state. This is fine except the HEAD is\n{tab}"
              f"a commit that is not saved in a local ore remote branch. This indicates\n{tab}"
              f"that you have made local commits while in the detached HEAD state, which is\n{tab}"
              f"fine but we want to make sure you save those changes.")
    suggestion = "Checkout a new local branch to save the current head state."
    super().__init__(target, reason, suggestion)


class UpdateRepoIsDirtyError(UpdateError):
  def __init__(self, target):
    reason = ("The repository is dirty and you are trying to move the HEAD commit.")
    suggestion = "Save or restore the uncommitted changes."
    super().__init__(target, reason, suggestion)


class UpdateDuplicateRepoPathError(UpdateError):
  def __init__(self, target, other):
    tab = " " * 8
    reason = (f"The repository({other.url}) is already cloned at\n{tab}"
              f"{other.path}.\n{tab}"
              f"You are trying to clone it again to\n{tab}"
              f"{target.path}.\n{tab}"
              "You cannot do this.")
    tab = " " * 12
    suggestion = (f"You need to make sure all listings of the same repository have the same\n{tab}"
                  "local path in the gordion.yaml file.")
    super().__init__(target, reason, suggestion)


class UpdateDuplicateRepoTagError(UpdateError):
  def __init__(self, target, target_tag, other, other_tag):
    reason = (f"Gordion repository tag mismatch!\n\t"
              f"{target._listed_path()}:{target_tag}\n\t"
              f"{other._listed_path()}:{other_tag}")
    suggestion = ("The tags need to match. I guess that's kinda the whole point of this thing.")
    super().__init__(target, reason, suggestion)


class UnsafeRemoveDirty(Exception):
  def __init__(self, path):
    self.message = (f"Cannot remove repository:\n"
                    f"{path}\n"
                    f"because it is dirty")
    super().__init__(self.message)


class NotAGordionRepositoryError(Exception):
  def __init__(self):
    self.message = "You are not in a gordion repository!"
    super().__init__(self.message)


class DanglingGordionRepositoryError(Exception):
  def __init__(self, current_repo_path, disconnected_parent_path):
    self.message = (f"You are in repository<{current_repo_path}>.\n"
                    f"There is a parent gordion repository{disconnected_parent_path}> but it does\n"
                    f"not list this repository. This repository appears to be dangling, and should be deleted.")
    super().__init__(self.message)