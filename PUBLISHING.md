# Publishing to PyPI

## Prerequisites

1. **Create PyPI Account**
   - Register at https://pypi.org/account/register/
   - Verify your email

2. **Create API Token**
   - Go to https://pypi.org/manage/account/token/
   - Create a token with "Entire account" scope
   - Save it securely

3. **Install Build Tools**
   ```bash
   pip install build twine
   ```

4. **Configure Authentication** (choose one):
   
   Option A: Create `~/.pypirc`:
   ```ini
   [distutils]
   index-servers =
       pypi
       testpypi

   [pypi]
   username = __token__
   password = pypi-your-token-here

   [testpypi]
   username = __token__
   password = pypi-your-test-token-here
   ```
   
   Option B: Use environment variable:
   ```bash
   export TWINE_USERNAME=__token__
   export TWINE_PASSWORD=pypi-your-token-here
   ```

## Publishing Steps

### Using Nox (Recommended)

We have nox sessions to automate the publishing process:

```bash
# Build only (builds the package)
nox -s build

# Publish to TestPyPI (for testing)
nox -s publish-pypi -- --test

# Publish to PyPI (production)
nox -s publish-pypi
```

The `publish-pypi` session will:
1. Run all tests
2. Run lint checks
3. Build the package
4. Upload to PyPI (with confirmation prompt for production)

### Manual Steps

If you prefer to do it manually:

#### 1. Run Tests and Lint
```bash
nox -s tests
nox -s lint
```

#### 2. Update Version
Edit `pyproject.toml` and update the version number:
```toml
version = "1.0.1"  # Increment as needed
```

#### 3. Build the Package
```bash
nox -s build
```

#### 4. Test with TestPyPI (Optional but Recommended)
```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ gordion
```

#### 5. Upload to PyPI
```bash
twine upload dist/*
```

### 7. Verify Installation
```bash
pip install gordion
```

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):
- MAJOR.MINOR.PATCH (e.g., 1.0.0)
- MAJOR: Breaking changes
- MINOR: New features (backwards compatible)
- PATCH: Bug fixes

## Checklist Before Publishing

- [ ] All tests pass (`nox -s tests`)
- [ ] Code passes lint (`nox -s lint`)
- [ ] Version number updated in `pyproject.toml`
- [ ] README.md is up to date
- [ ] LICENSE file is correct
- [ ] Commit all changes
- [ ] Create git tag: `git tag v1.0.0 && git push --tags`

## Troubleshooting

**Package name already taken**: The name "gordion" must be unique on PyPI. If it's taken, you'll need to choose a different name in `pyproject.toml`.

**Authentication failed**: Make sure you're using `__token__` as username and your full token (including `pypi-` prefix) as password.

**Missing dependencies**: Ensure all runtime dependencies are listed in `pyproject.toml` under `dependencies`.