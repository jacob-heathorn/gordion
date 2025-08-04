# Gordion

The place where the gordian knot was untied.

A multi-repository management tool with a git-like command interface.

## Features

- **Deterministic Dependency Management**: Specify exact commits for reproducible builds
- **Diamond Dependency Resolution**: Automatically resolves version conflicts when multiple repositories depend on a common repository
- **Intuitive Git-like Commands**: Familiar commands like `gor add`, `gor commit`, `gor push` that work across all repositories
- **Smart Workspace Management**: Automatically discovers and manages repositories in your workspace

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

## Key Commands

- `gor -u` - Update/clone all repositories to their specified versions
- `gor status` - Show status across all repositories
- `gor add <pathspec>` - Stage changes in all repositories
- `gor commit -m <message>` - Commit changes and update dependency versions
- `gor push` - Push changes in all repositories
- `gor -f <repo-name>` - Find path to a specific repository

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

## Functional Description

### Workspace Definition
The highest directory in a directory tree containing a gordion repository (one with a gordion.yaml) is a workspace. Every gordion repository under that directory level is part of the workspace. When you clone a new repository there, it becomes par of the workspace automatically.  There cannot exist duplicate repositories (by url or name) in a workspace.  All dependencies in a workspace must agree by tag.

### Workspace context
When you do `gor status`, it only shows you the dependencies for your current root repository.  So in the diamond dependency graph, if you are in repository B and do `gor status`, it will show you status for B and D.

### Cached Repositories
By default, `gor -u` will clone to a cache folder, which is hidden from the status command unless you use `-c`. The idea is that dependencies can be forgotten once they are hardened and working.  For dependencies that you are working on, or important components of your project, you move them to your workspace.

It is not permitted to make changes to repositories in the cache, and `gor -u` will blow them away.

The cache is a little different than a workspace, because it is managed per-repository.  So if you are working in repo A, there is a cache associated with it. If you move to repo B, there is a separate cache associated with it, while repos A and B may share one workspace.  That's because if you work in B and it has a different version of D than B, when you move to C it won't complain because it manages it's own version of D. It's not until you move to A that they need to agree, or if they are in the workspace where D would be shared by B and C.

### Branching
Versioning is stricly controlled by commits, to enforce the reproducible builds requirement, but the tool still tries to checkout branches. If the commit is on the default branch, it will go to that commit on the default branch. If you checkout a different branch from your root working repo, the tool will try to find commits on that branch. If it can't find on those, it will checkout the commit in a detatched HEAD state.


### Add/Commit/Push
If you make changes across multiple repositories in your dependency tree, you can `gor add`, `gor commit`, and `gor push` all of them together. With a caveat, all repos in the tree that will take changes need to be in the workspace not the cache.  The workspace is for repositories your actively developing, the cache is for dependencies you can essentially forget about.


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

Run all tests:
```bash
nox -s tests
```

Run specific test files:
```bash
nox -s tests -- test/test_repository.py -s
nox -s tests -- test/test_tree.py -s
nox -s tests -- test/test_cache.py -s
nox -s tests -- test/test_status.py -s
nox -s tests -- test/test_workspace.py -s
```

## Linting

```bash
nox -s lint
```

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
