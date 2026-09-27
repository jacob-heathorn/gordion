import os
import re
from typing import Dict, List, Set
import gordion

MODULE_FILE = 'MODULE.bazel'

_BAZEL_DEP = re.compile(r'bazel_dep\(\s*name\s*=\s*"([^"]+)"')


def bazelrc(root: gordion.Tree) -> str:
  """
  Returns bazelrc lines pointing bzlmod at every gordion-managed bazel dependency in the tree, so
  gordion.yaml is the only place a dependency's version lives.
  """
  repos = _tree_repositories(root)
  deps: Set[str] = set()
  for repo in [root.repo, *repos.values()]:
    deps |= _bazel_deps(repo.path)
  names = sorted(deps & repos.keys())
  return "".join(f"common --override_module={name}={repos[name].path}\n" for name in names)


def _tree_repositories(root: gordion.Tree) -> Dict[str, gordion.Repository]:
  """
  Returns every repository listed in the tree, following listings as written whatever commit each
  checkout is on. A listed repository that is not on disk needs `gor -u` first.
  """
  workspace = gordion.Workspace()
  repos: Dict[str, gordion.Repository] = {}
  pending = [root.repo]
  while pending:
    for name in _listed_children(pending.pop()):
      if name in repos or name == root.repo.name:
        continue
      repo = workspace.get_repository(name)
      if repo is None:
        raise gordion.exception.RepositoryNotFoundError(name)
      repos[name] = repo
      pending.append(repo)
  return repos


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
