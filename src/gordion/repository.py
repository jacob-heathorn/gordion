import os
import subprocess
from gordion.utils import pushd
from pathlib import Path
from git import Repo
import gordion

class Repository:
  """
  Encapsulates a git repository in the gordion context.

  """

  def __init__(self, path: str, url: str, tag: str, branch: str) -> None:
    self.path = Path(path)
    self.url = url
    self.tag = tag
    self.branch = branch

  def update(self) -> None:
    """
    Clones the repository if it does not exist, otherwise updates it to the requested branch:tag

    """

    # Clone if necessary.
    if not self._exists():
      print(self.path.parent)
      with pushd(self.path.parent, create=True):
        # TODO clone with repository name specified in path.
        args = ['git', 'clone', self.url]
        subprocess.check_call(args, stderr=subprocess.STDOUT)

    # TODO: Checkout the branch:tag

    repo = Repo(self.path)
    target_commit = repo.commit(self.tag)

    # Check if branch is constant.
    if repo.active_branch.name == self.branch:
      # Check if commit is constant
      if target_commit == repo.active_branch.commit:
        pass # nothing to do.
      
      # The commit changes.
      else:
        # Fetch remote information
        origin = repo.remotes.origin
        origin.fetch()
        
        # Check if active branch contains the target commit.
        if target_commit in repo.active_branch.commit.traverse():
          self._update_active_branch(repo)
        
        # Active branch does not contain target commit.
        else:
          pass
          # Check if remote branch contains target commit.
          # remote_ref = repo.refs[remote_branch]
    
    # Branch changes.
    else:
      pass

  def _update_active_branch(self, repo: Repo):
    # Resolve the local and remote branch references
    local_branch = repo.heads[self.branch]
    remote_branch_ref = f'origin/{self.branch}'
    remote_branch = repo.remotes['origin'].refs[self.branch]

    # Find the latest common ancestor between the two branches
    merge_base = repo.merge_base(local_branch, remote_branch)

    # Make sure there is a common history.
    if not merge_base:
      # f"No common history between {local_branch_name} and {remote_branch_ref}."
      raise gordion.OperationError("Error, the active branch cannot be updated because it differes from the remote branch. TODO need to..")

    # Compare local commits that are ahead of the merge base but not in the remote branch
    commits_ahead = list(repo.iter_commits(f'{merge_base[0].hexsha}..{local_branch.commit.hexsha}'))

    # Compare remote commits that are ahead of the merge base but not in the local branch
    commits_behind = list(repo.iter_commits(f'{merge_base[0].hexsha}..{remote_branch.commit.hexsha}'))

    # Evaluate comparison results
    if commits_ahead and commits_behind:
      print(f"TODO: {self.branch} and {remote_branch_ref} have diverged with {len(commits_ahead)} local commit(s) ahead and {len(commits_behind)} remote commit(s) behind.")
    elif commits_ahead:
      raise gordion.UpdateActiveBranchAheadError(self.path, self.branch, remote_branch_ref, len(commits_ahead))
    # elif commits_behind:
    #     return f"{local_branch_name} is behind {remote_branch_ref} by {len(commits_behind)} commit(s)."
    # else:
    #     return f"{local_branch_name} and {remote_branch_ref} are up-to-date."
      
  def _exists(self) -> bool:
    # Check directory exists
    if not os.path.isdir(self.path):
      return False

    try:
      # Run the command to determine the root of the repository
      result = subprocess.check_output(
          ["git", "-C", self.path, "rev-parse", "--show-toplevel"],
          stderr=subprocess.DEVNULL
      ).strip().decode('utf-8')

      # Compare the output with self.path to determine if it's the root
      return os.path.abspath(result) == os.path.abspath(self.path)
    except subprocess.CalledProcessError:
        # If the command fails, the directory is not inside a Git repository
        return False
