"""Nox configuration for running tests and linting."""
import nox
import os
from pathlib import Path

# Configure nox to use uv
nox.options.default_venv_backend = "uv"

# Set default sessions (exclude build and publish)
nox.options.sessions = ["tests", "lint"]


@nox.session
def tests(session):
    """Run the pytest test suite."""

    # Pass through SSH_AUTH_SOCK if available
    if "SSH_AUTH_SOCK" in os.environ:
        session.env["SSH_AUTH_SOCK"] = os.environ["SSH_AUTH_SOCK"]

    # Install the package with its dependencies
    session.install("-e", ".")

    # Install test dependencies
    session.install("pytest", "pytest-cov", "debugpy")

    # Run pytest with coverage
    session.run(
        "pytest",
        "--cov=gordion",
        "-o", "cache_dir=.pycache",
        "test",
        *session.posargs,
    )


@nox.session
def lint(session):
    """Run flake8 and mypy linting."""
    # Set PYTHONPATH for mypy to find the package
    session.env["PYTHONPATH"] = "src"

    # Install the package with its dependencies
    session.install("-e", ".")

    # Install lint dependencies
    session.install("flake8", "mypy")

    # Run flake8 with configuration
    session.run(
        "flake8",
        "--ignore=E126",
        "--exclude=.nox,build,.pycache,.nox",
        "--max-line-length=100",
        "--indent-size=2",
        "."
    )

    # Run mypy with configuration
    session.run(
        "mypy",
        "--ignore-missing-imports",
        "--check-untyped-defs",
        "--cache-dir=.pycache",
        "--package=gordion"
    )


@nox.session
def build(session):
    """Build the package for distribution."""
    import shutil
    
    # Clean previous builds
    if os.path.exists("dist"):
        shutil.rmtree("dist")
    # Clean egg-info directories
    for path in Path("src").glob("*.egg-info"):
        if path.exists():
            shutil.rmtree(path)
    
    # Install build tools
    session.install("build", "twine")
    
    # Build the package
    session.run("python", "-m", "build")
    
    # Check the package
    session.run("twine", "check", "--strict", "dist/*", success_codes=[0, 1])
    session.log("Note: 'license-file' warning can be ignored - it's a hatchling metadata field")
    
    # List the built files
    session.log("Built packages:")
    for file in sorted(os.listdir("dist")):
        session.log(f"  - {file}")


@nox.session
def publish(session):
    """Publish the package to PyPI."""
    import sys
    
    # Run tests first
    session.log("Running tests...")
    session.notify("tests")
    
    # Run lint
    session.log("Running lint...")
    session.notify("lint")
    
    # Build the package
    session.log("Building package...")
    session.notify("build")
    
    # Check if we're publishing to test PyPI
    test_pypi = "--test" in session.posargs
    
    # Install twine if needed
    session.install("twine")
    
    # Publish
    if test_pypi:
        session.log("Publishing to TestPyPI...")
        session.run(
            "twine", "upload", "--repository", "testpypi", "dist/*",
            external=True
        )
        session.log("\nPublished to TestPyPI!")
        session.log("Test installation with:")
        session.log("  pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ gordion")
    else:
        # Confirm before publishing to real PyPI
        session.log("\n⚠️  About to publish to PyPI (production)!")
        response = input("Are you sure? (yes/no): ")
        if response.lower() != "yes":
            session.error("Publishing cancelled.")
        
        session.log("Publishing to PyPI...")
        session.run(
            "twine", "upload", "dist/*",
            external=True
        )
        session.log("\n✨ Published to PyPI!")
        session.log("Install with: pip install gordion")
