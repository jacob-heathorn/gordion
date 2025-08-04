# Gordion

A powerful multi-repository management tool that helps you manage complex dependencies across multiple Git repositories with ease.

## Features

- **Deterministic Dependency Management**: Specify exact commits for reproducible builds
- **Diamond Dependency Resolution**: Automatically resolves version conflicts when multiple repositories depend on a common repository
- **Intuitive Git-like Commands**: Familiar commands like `gor add`, `gor commit`, `gor push` that work across all repositories
- **Smart Workspace Management**: Automatically discovers and manages repositories in your workspace

## Installation

```bash
pip install gordion
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
    tag: main
```

2. Clone and set up your workspace:

```bash
# Clone repositories defined in gordion.yaml
gor -u

# Check status across all repositories
gor status

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
- `gor -w` - Show current workspace path
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

## Development Setup

### Prerequisites

```bash
# Install nix
curl -L https://nixos.org/nix/install | sh
```

### For cloning with HTTPS
* Generate a new token with access to `Contents`
* When it asks for username, use token as password

```bash
git config --global color.ui always
```

### Testing

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

### Linting

```bash
nox -s lint
```

## License

MIT License - see LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.