import os
import re
from typing import Dict, List, Set
import gordion

MODULE_FILE = 'MODULE.bazel'

_BAZEL_DEP = re.compile(r'bazel_dep\(\s*name\s*=\s*"([^"]+)"')


def bazelrc(root: gordion.Tree) -> str:
  """
  Returns bazelrc lines pointing bzlmod at every bazel dependency that is checked out in the
  workspace, so bazel builds against the live checkout instead of fetching the pinned commit.
  """
  checkouts = _workspace_checkouts(root)
  deps: Set[str] = set()
  for repo in [root.repo, *checkouts.values()]:
    deps |= _bazel_deps(repo.path)
  names = sorted(deps & checkouts.keys())
  return "".join(f"common --override_module={name}={checkouts[name].path}\n" for name in names)


def bump_git_override(repo_path: str, module_name: str, commit: str) -> bool:
  """
  Points the git_override for <module_name> in <repo_path>/MODULE.bazel at <commit>. Returns
  whether the file changed.
  """
  module_file = os.path.join(repo_path, MODULE_FILE)
  if not os.path.exists(module_file):
    return False
  with open(module_file) as file:
    before = file.read()
  name = re.escape(module_name)
  pattern = re.compile(
      rf'(git_override\(\s*module_name\s*=\s*"{name}"[^)]*?commit\s*=\s*")[^"]*(")', re.DOTALL)
  after = pattern.sub(rf'\g<1>{commit}\g<2>', before)
  if after == before:
    return False
  with open(module_file, 'w') as file:
    file.write(after)
  return True


def _workspace_checkouts(root: gordion.Tree) -> Dict[str, gordion.Repository]:
  """
  Returns the repositories listed anywhere in the tree that are checked out in the workspace rather
  than the cache. Listings are followed as written, whatever commit each checkout is on.
  """
  workspace = gordion.Workspace()
  checkouts: Dict[str, gordion.Repository] = {}
  visited = {root.repo.name}
  pending = [root.repo]
  while pending:
    for name in _listed_children(pending.pop()):
      repo = workspace.get_repository(name)
      if repo and name not in visited:
        visited.add(name)
        pending.append(repo)
        if not workspace.is_dependency(repo.path):
          checkouts[name] = repo
  return checkouts


def _listed_children(repo: gordion.Repository) -> List[str]:
  if not repo.yeditor.exists():
    return []
  return list(repo.yeditor.yaml_data['repositories'].keys())


def _bazel_deps(repo_path: str) -> Set[str]:
  module_file = os.path.join(repo_path, MODULE_FILE)
  if not os.path.exists(module_file):
    return set()
  with open(module_file) as file:
    return set(_BAZEL_DEP.findall(file.read()))
