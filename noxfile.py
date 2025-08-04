"""Nox configuration for running tests and linting."""
import nox
import os

# Configure nox to use uv
nox.options.default_venv_backend = "uv"


@nox.session
def tests(session):
    """Run the pytest test suite."""
    # Set environment variables for testing
    session.env["TOXTEMPDIR"] = session.create_tmp()
    
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
    # Install the package with its dependencies
    session.install("-e", ".")
    
    # Install lint dependencies
    session.install("flake8", "mypy")
    
    # Run flake8
    session.run(
        "flake8",
        "--config=pyproject.toml",
        "."
    )
    
    # Run mypy
    session.run(
        "mypy",
        "--config-file=pyproject.toml",
        "--package=gordion"
    )
