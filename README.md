# Gordion

The place where the gordian knot was untied.

A multi-repository management tool with a git-like command interface.

## Features

- **Deterministic Dependency Management**: Specify exact commits for reproducible builds across your entire dependency tree
- **Diamond Dependency Resolution**: Forces exact version agreement across dependencies
- **Workspace-Based Development**: Work on multiple repositories together with automatic discovery and shared dependencies
- **Cache System**: Separate stable dependencies from actively developed code with per-repository caching
- **Information Loss Protection**: Safeguards against losing uncommitted changes or unpushed commits during updates
- **Git-like Interface**: Familiar commands (`gor add`, `gor commit`, `gor push`) that operate across all repositories
- **Branch Awareness**: Intelligently follows branches when possible while maintaining commit-based versioning
- **Contextual Operations**: Commands respect your current repository context, showing only relevant dependencies

## Why Gordion?

Gordion solves the "diamond dependency problem" in multi-repository projects:

```
    A
   / \
  B   C
   \ /
    D
```

When repository A depends on B and C, which both depend on D, Gordion ensures all repositories use the same version of D, preventing version conflicts.

### Comparison to Other Tools

- **git submodule**: Creates duplicate repositories in diamond dependencies; Gordion maintains a single version
- **west (Zephyr)**: Requires manifest repo, allows version conflicts; Gordion has contextual manifests and enforces agreement
- **CMake FetchContent**: Build-time only; Gordion manages full development lifecycle with git operations
- **Conan/vcpkg**: Package managers for binaries; Gordion manages source repositories with development workflows
- **Bazel**: Build system with hermetic deps; Solves the diamond dependency problem in a similar way, but now you're stuck using bazel
- **Google Repo**: Requires a manifest repository. Subrepos cannot behave as their own manifest repository. Allows version conflicts.

## Key Commands

- `gor -u` - Update/clone all repositories to their specified versions
- `gor status` - Show status across all repositories
- `gor add <pathspec>` - Stage changes in all repositories
- `gor commit -m <message>` - Commit changes and update dependency versions
- `gor push` - Push changes in all repositories
- `gor -f <repo-name>` - Find path to a specific repository

## Functional Description

### Workspace Definition
The highest directory in a directory tree containing a gordion repository (one with a gordion.yaml) defines a workspace. Every gordion repository under that directory level is part of the workspace. When you clone a new repository there, it automatically becomes part of the workspace. Duplicate repositories (by URL or name) cannot exist within a workspace. All dependencies in a workspace must agree on their tags.

### Workspace Context
When you run `gor status`, it only shows the dependencies for your current root repository. For example, in the diamond dependency graph above, if you are in repository B and run `gor status`, it will show you the status for B and D.

### Cached Repositories
By default, `gor -u` clones to a cache folder, which is hidden from the status command unless you use the `-c` flag. The idea is that stable dependencies can be forgotten once they are hardened and working. For dependencies that you are actively developing or important components of your project, you should move them to your workspace.

Changes to repositories in the cache are not permitted, and `gor -u` will overwrite them.

The cache differs from a workspace because it is managed per-repository. If you are working in repo A, there is a cache associated with it. If you move to repo B, there is a separate cache associated with it, while repos A and B may share one workspace. This means if you work in B and it has a different version of D than C, when you move to C it won't complain because it manages its own version of D. Conflicts only arise when you move to A where they need to agree, or if they are in the workspace where D is automatically shared by B and C.

### Branching
Versioning is strictly controlled by commits to enforce reproducible builds, but the tool still attempts to checkout branches. If the commit is on the default branch, it will checkout that commit on the default branch. If you checkout a different branch from your root working repository, the tool will try to find the commits on that branch. If it can't find them, it will checkout the commit in a detached HEAD state.


### Add/Commit/Push
If you make changes across multiple repositories in your dependency tree, you can run `gor add`, `gor commit`, and `gor push` to manage all of them together. However, all repositories that will receive changes must be in the workspace, not the cache. The workspace is for repositories you're actively developing, while the cache is for dependencies you can essentially forget about.

### Information Loss Protection
`gor -u` guarantees no information can be lost. If the update needs to checkout an earlier commit on a branch, it will only do so if there is already a remote branch that has saved the current commit. If the repository has uncommitted changes that would be lost by the update, the tool will error and notify you rather than proceeding (unless it's a cached dependency). In general, if the tool destroys information during an update that cannot be recovered by conventional git operations, then you've found a bug!

## Installation

```bash
pipx install gordion
```

## Quick Start

1. Create a `gordion.yaml` file in your root repository:

```yaml
repositories:
  my-library:
    url: https://github.com/myorg/my-library.git
    tag: v1.2.3
  my-app:
    url: https://github.com/myorg/my-app.git
    tag: 1234567
```

2. Clone and set up your workspace:

```bash
# Clone repositories defined in gordion.yaml
gor -u

# Check status across all repositories
gor status

# Check status with hidden cache repositories
gor status -c

# Make changes and commit across repos
gor add .
gor commit -m "Update dependencies"
gor push
```


# Development Setup

## Prerequisites

```bash
# Install nix
curl -L https://nixos.org/nix/install | sh
```

## For cloning with HTTPS
* Generate a new token with access to `Contents`
* When it asks for username, use token as password

```bash
git config --global color.ui always
```

## Testing

Nox testing:
```bash
nox -s tests
nox -s lint
nox -s tests -- test/test_repository.py -s
nox -s tests -- test/test_tree.py -s
nox -s tests -- test/test_cache.py -s
nox -s tests -- test/test_status.py -s
nox -s tests -- test/test_workspace.py -s
```

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
