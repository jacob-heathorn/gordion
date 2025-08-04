# Setup
```
# Install nix
curl -L https://nixos.org/nix/install | sh
```

For cloning with https
* Generate a new token with access to `Contents`
* When it asks for username, use token as password

`git config --global color.ui always`


# Testing
Just a single test file:
  `nox -s tests -- test/test_repository.py -s`
  `nox -s tests -- test/test_tree.py -s`
  `nox -s tests -- test/test_cache.py -s`
  `nox -s tests -- test/test_status.py -s`
  `nox -s tests -- test/test_workspace.py -s`
  `nox -s tests -- test/test_analogs.py -s`


Lint and type check: `nox -s lint`
Run all tests and lint: `nox`


# Install from source
```bash
# Ensure pipx is installed
python3 -m pip install pipx
pipx ensurepath

# Change to this directory
pipx install --force .
```
