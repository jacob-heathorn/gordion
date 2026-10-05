# Tests the bazel integration of a gordion workspace

import gordion
import os


def _write_module(repo: gordion.Repository, deps=()):
  lines = [f'module(name = "{repo.name}", version = "0.0.0")']
  lines += [f'bazel_dep(name = "{dep}", version = "0.0.0")' for dep in deps]
  with open(os.path.join(repo.path, gordion.bazel.MODULE_FILE), 'w') as file:
    file.write("\n".join(lines) + "\n")


def test_bazelrc_overrides_workspace_checkouts(tree_a_local: gordion.Tree):
  workspace = gordion.Workspace()
  repo_b = workspace.get_repository('gordion_demo_b')
  repo_c = workspace.get_repository('gordion_demo_c')
  repo_d = workspace.get_repository('gordion_demo_d')
  _write_module(tree_a_local.repo, deps=['gordion_demo_b', 'gordion_demo_c'])
  _write_module(repo_b, deps=['gordion_demo_d'])
  _write_module(repo_c, deps=['gordion_demo_d'])
  _write_module(repo_d)

  expected = "".join(
      f"common --override_module={repo.name}={repo.path}\n" for repo in [repo_b, repo_c, repo_d])
  assert gordion.bazel.bazelrc(tree_a_local) == expected


def test_bazelrc_overrides_cached_dependencies(tree_a: gordion.Tree):
  workspace = gordion.Workspace()
  repo_b = workspace.get_repository('gordion_demo_b')
  repo_c = workspace.get_repository('gordion_demo_c')
  _write_module(tree_a.repo, deps=['gordion_demo_b', 'gordion_demo_c'])

  expected = "".join(
      f"common --override_module={repo.name}={repo.path}\n" for repo in [repo_b, repo_c])
  assert gordion.bazel.bazelrc(tree_a) == expected


def test_bazelrc_skips_checkouts_that_are_not_bazel_deps(tree_a_local: gordion.Tree):
  _write_module(tree_a_local.repo, deps=['gordion_demo_b'])
  repo_b = gordion.Workspace().get_repository('gordion_demo_b')
  expected = f"common --override_module=gordion_demo_b={repo_b.path}\n"
  assert gordion.bazel.bazelrc(tree_a_local) == expected
