"""Shared fixtures for testing."""

import contextlib
import os

import pytest
from nclutils.pytest_fixtures import clean_stderr, debug  # noqa: F401

from backup_mongodb.entrypoint import settings


@pytest.fixture(autouse=True)
def reset_settings() -> None:
    """Reset the settings singleton."""
    with contextlib.suppress(FileNotFoundError, OSError):
        if settings._tmp_dir is not None:
            settings._tmp_dir.cleanup()
            settings._tmp_dir = None

    for key in settings.__dict__:
        if not key.startswith("_"):
            setattr(settings, key, None)


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Mock environment variables for testing."""
    for k in os.environ:
        if k.startswith("EZBAK_"):
            monkeypatch.delenv(k, raising=False)
        if k.startswith("BACKUP_MONGODB_"):
            monkeypatch.delenv(k, raising=False)
