# Setup
```
# Install nix
curl -L https://nixos.org/nix/install | sh
```

For cloning with https
* Generate a new token with access to `Contents`
* When it asks for username, use token as password


# Testing
Just a single test file:
  `tox -e unit -- tests/test_repository.py -s`
  `tox -e unit -- tests/test_tree.py -s`
  `tox -e unit -- tests/test_cache.py -s`
  `tox -e unit -- tests/test_status.py -s`
  `tox -e unit -- tests/test_workspace.py -s`
  `tox -e unit -- tests/test_analogs.py -s`


Lint and type check: `tox -e lint`
Run all tox environments: `tox`

# Debugging
NOTE: Not able to get this working recently
`tox -e unit -- tests/test_repository.py -s --no-cov`

# Install from source
`python3 -m pip install pipx`
`pipx ensurepath`
Change to this directory
`pipx install --force .`
