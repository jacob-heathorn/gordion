# Publishing to PyPI

## Prerequisites

1. **Create PyPI Account**
   - Register at https://pypi.org/account/register/
   - Verify your email

2. **Create API Token**
   - Go to https://pypi.org/manage/account/token/
   - Create a token with "Entire account" scope
   - Save it securely

## Publishing Steps

We have nox sessions to automate the publishing process:

```bash
# Build only (builds the package)
nox -s build

# Publish to PyPI
nox -s publish-pypi
```

The `publish-pypi` session will:
1. Run all tests
2. Run lint checks
3. Build the package
4. Upload to PyPI (with confirmation prompt for production)
