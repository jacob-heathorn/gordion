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
