import os


class UpdateError(Exception):
  def __init__(self, target_path, reason, suggestion):
    self.message = (f"Cannot update repository<{target_path}>. "
                    f"{reason}. {suggestion}.")
    super().__init__(self.message)


class UpdateLocalBranchAheadError(UpdateError):
  def __init__(self, target_path, local_branch, remote_branch, num_commits):
    reason = (f"{local_branch} is {num_commits} commit(s) ahead of {remote_branch}. "
              f"Update would lose one or more of these commit(s)")
    suggestion = "Push or remove the commits please"
    super().__init__(target_path, reason, suggestion)


class UpdateTargetPathExistsError(UpdateError):
  def __init__(self, target_path):
    reason = f"{target_path} already exists but is not a repository"
    suggestion = f"Manually delete {target_path}"
    super().__init__(target_path, reason, suggestion)


class UpdateMultipleRepositoriesAlreadyExistsError(UpdateError):
  def __init__(self, target_path, other_repos):
    reason = f"Multiple repositories with url<{other_repos[0].url}> already exist:"
    for _, other_repo in other_repos.items():
      reason += f"\n * {other_repo.path}"
    suggestion = "\nDelete duplicate repositories"
    super().__init__(target_path, reason, suggestion)


class UpdateWorkingRepositoryWrongUrlError(UpdateError):
  def __init__(self, path, current_url, correct_url):
    reason = (f"The working repository name<{os.path.basename(path)}> has the wrong "
              f"url<{current_url}>")
    suggestion = f"Manually delete it and re-clone it with <{correct_url}>"
    super().__init__(path, reason, suggestion)


class UpdateNoTrackingBranchError(UpdateError):
  def __init__(self, target_path, local_branch):
    reason = f"{local_branch} does not have a tracking branch, so commits will be lost"
    suggestion = f"Create a remote tracking branch (git push -u origin {local_branch})"
    super().__init__(target_path, reason, suggestion)


class UpdateWrongTrackingBranchError(UpdateError):
  def __init__(self, target_path, local_branch, remote_branch):
    reason = (f"{local_branch} does not track origin/{local_branch}. Instead, it tracks "
              f"{remote_branch}. This is unexpected and can cause problems")
    suggestion = f"fix it: git push -u origin {local_branch}. Maybe delete incorrect remote branch?"
    super().__init__(target_path, reason, suggestion)


class UpdateDetachedHeadNotSavedError(UpdateError):
  def __init__(self, target_path):
    reason = (f"The repository<{os.path.basename(target_path)}> is in a detached HEAD state. "
              f"This is fine except the HEAD is a commit that is not saved in a local or remote "
              f"branch. This indicates that you have made local commits while in the detached "
              f"HEAD state, which is fine but we want to make sure you save those changes")
    suggestion = "Checkout a new local branch to save the current head state"
    super().__init__(target_path, reason, suggestion)


class UpdateRepoIsDirtyError(UpdateError):
  def __init__(self, target_path):
    reason = ("The repository is dirty and you are trying to move the HEAD commit")
    suggestion = "Save or restore the uncommitted changes"
    super().__init__(target_path, reason, suggestion)


class UpdateDifferentRepoSamePathError(UpdateError):
  def __init__(self, target_path, listings):
    reason = f"Different repositories are attempted to be cloned at the same path<{target_path}>!"
    for listing in listings:
      reason += f"\nRepository<{listing.url}>"
    suggestion = "\nYou need to make sure repositories have unique paths in the gordion.yaml files"
    super().__init__(target_path, reason, suggestion)


class UpdateSameRepoDifferentPathError(UpdateError):
  def __init__(self, target_path, listings):
    reason = "The same repository is attempted to be cloned at different paths!"
    for listing in listings:
      reason += f"\nRepository<{listing.url}> at path<{listing.path}>"
    suggestion = ("\nMake sure all listings of the same repository have the same "
                  "local path in the gordion.yaml file")
    super().__init__(target_path, reason, suggestion)


class UpdateSameRepoDifferentTagError(UpdateError):
  def __init__(self, target_path, listings):
    reason = "Gordion repository tag mismatch!"
    for listing in listings:
      reason += f"\n{listing.file} : {listing.name} : {listing.tag}"
    suggestion = ("\nThe tags need to identify the same commit pleaaaaase")
    super().__init__(target_path, reason, suggestion)


class UpdateSameNameDifferentUrlError(UpdateError):
  def __init__(self, target_path, listings):
    reason = "Gordion repository url mismatch!"
    for listing in listings:
      reason += f"\n{listing.file} : {listing.name} : {listing.url}"
    suggestion = ("\nThe urls need to point to the same repository ehh")
    super().__init__(target_path, reason, suggestion)


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


class DanglingCommitError(UpdateError):
  def __init__(self, target_path, target_tag):
    reason = (f"Commit<{target_tag}> is dangling (does not belong to a branch)")
    suggestion = ("Update the commit tag in the parent gordion.yaml")
    super().__init__(target_path, reason, suggestion)
