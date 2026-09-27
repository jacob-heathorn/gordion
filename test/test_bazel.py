# Tests the bazel integration of a gordion workspace

import gordion
import os


def _write_module(repo: gordion.Repository, deps=(), overrides=()):
  lines = [f'module(name = "{repo.name}", version = "0.0.0")']
  lines += [f'bazel_dep(name = "{dep}", version = "0.0.0")' for dep in deps]
  lines += [
      f'git_override(\n    module_name = "{name}",\n    remote = "r",\n    commit = "{commit}",\n)'
      for name, commit in overrides]
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


def test_bazelrc_skips_cached_dependencies(tree_a: gordion.Tree):
  _write_module(tree_a.repo, deps=['gordion_demo_b', 'gordion_demo_c'])
  assert gordion.bazel.bazelrc(tree_a) == ""


def test_bazelrc_skips_checkouts_that_are_not_bazel_deps(tree_a_local: gordion.Tree):
  _write_module(tree_a_local.repo, deps=['gordion_demo_b'])
  repo_b = gordion.Workspace().get_repository('gordion_demo_b')
  expected = f"common --override_module=gordion_demo_b={repo_b.path}\n"
  assert gordion.bazel.bazelrc(tree_a_local) == expected


def test_bump_git_override(tmp_path):
  module = tmp_path / gordion.bazel.MODULE_FILE
  module.write_text(
      'git_override(\n    module_name = "dep",\n    remote = "r",\n    commit = "old",\n)\n'
      'git_override(module_name = "other", remote = "r", commit = "keep")\n')

  assert gordion.bazel.bump_git_override(str(tmp_path), "dep", "new")
  assert 'commit = "new"' in module.read_text()
  assert 'commit = "keep"' in module.read_text()
  assert not gordion.bazel.bump_git_override(str(tmp_path), "dep", "new")
  assert not gordion.bazel.bump_git_override(str(tmp_path), "missing", "new")
  assert not gordion.bazel.bump_git_override(str(tmp_path / "nowhere"), "dep", "new")


def test_commit_bumps_git_override(tree_a_local: gordion.Tree):
  workspace = gordion.Workspace()
  repo_b = workspace.get_repository('gordion_demo_b')
  repo_d = workspace.get_repository('gordion_demo_d')
  _write_module(repo_b, deps=['gordion_demo_d'],
                overrides=[('gordion_demo_d', repo_d.handle.head.commit.hexsha)])
  with open(os.path.join(repo_d.path, 'touch.txt'), 'w'):
    pass

  branch = repo_d.handle.active_branch.name
  analogs = gordion.Analogs(tree_a_local.repo)
  analogs.add(branch, ".")
  analogs.commit(branch, "test_commit_bumps_git_override")

  committed = repo_b.handle.git.show(f"HEAD:{gordion.bazel.MODULE_FILE}")
  assert f'commit = "{repo_d.handle.head.commit.hexsha}"' in committed
  assert not repo_b.is_dirty()
