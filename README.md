TODO

tox -- test/test_repository.py -s --no-cov

# Testing
Just a single test file: `tox -e unit -- tests/test_single.py -s`
Lint and type check: `tox -e lint`
Run all tox environments: `tox`

# Debugging
TODO: finish
`tox -e unit -- tests/test_repository.py -s --no-cov`

# Install from source
`python3 -m pip install pipx`
`pipx ensurepath`
Change to this directory
`pipx install --force .`
