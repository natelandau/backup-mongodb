"""Test the entrypoint."""

import shutil
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import time_machine

from backup_mongodb.entrypoint import main, settings

UTC = ZoneInfo("UTC")
frozen_time = datetime(2025, 6, 9, tzinfo=UTC)
frozen_time_str = frozen_time.strftime("%Y%m%dT%H%M%S")
fixture_archive_path = Path(__file__).parent / "fixtures" / "archive.tgz"


def test_require_action() -> None:
    """Test the main function."""
    settings.update({"name": "pytest", "log_level": "TRACE"})

    with pytest.raises(ValueError, match="ACTION must be one of:"):
        main()


def test_require_name() -> None:
    """Test the main function."""
    settings.update({"action": "backup", "log_level": "TRACE"})
    with pytest.raises(ValueError, match="NAME is required"):
        main()


def test_require_storage_path() -> None:
    """Test the main function."""
    settings.update(
        {"action": "backup", "log_level": "TRACE", "name": "pytest", "storage_location": "local"}
    )
    with pytest.raises(ValueError, match="STORAGE_PATH is required"):
        main()


def test_require_restore_path() -> None:
    """Test the main function."""
    settings.update(
        {
            "action": "restore",
            "log_level": "TRACE",
            "name": "pytest",
            "storage_location": "local",
            "storage_path": "/some/path/pytest",
        }
    )
    with pytest.raises(ValueError, match="RESTORE_PATH is required"):
        main()


def test_require_mongo_uri() -> None:
    """Test the main function."""
    settings.update({"action": "backup", "log_level": "TRACE", "name": "pytest"})
    with pytest.raises(ValueError, match="MONGO_URI is required"):
        main()


def test_require_mongo_db_name() -> None:
    """Test the main function."""
    settings.update(
        {
            "action": "backup",
            "log_level": "TRACE",
            "name": "pytest",
            "mongo_uri": "mongodb://localhost:27017",
        }
    )
    with pytest.raises(ValueError, match="MONGO_DB_NAME is required"):
        main()


@time_machine.travel(frozen_time, tick=False)
def test_backup(mocker, tmp_path, clean_stderr, debug) -> None:
    """Test the main function."""
    storage_path = tmp_path / "storage"
    storage_path.mkdir(parents=True)
    mocker.patch("backup_mongodb.entrypoint.run_command", return_value=True)

    settings.update(
        {
            "action": "backup",
            "log_level": "TRACE",
            "name": "pytest",
            "mongo_uri": "NULL",
            "mongo_db_name": "NULL",
            "storage_location": "local",
            "storage_path": storage_path,
        }
    )
    main()
    output = clean_stderr()
    debug(output)

    assert len(list(storage_path.glob("*"))) == 1
    assert Path(storage_path / f"pytest-{frozen_time_str}-yearly.tgz").exists()
    assert "Starting backup-mongodb container" in output
    assert "Run ezbak for 'pytest'" in output
    assert "Backup complete. Exiting." in output


@pytest.mark.skip("singleton settings in ezbak prevent this from running")
def test_restore(mocker, tmp_path, clean_stderr, debug) -> None:
    """Test the main function."""
    storage_path = tmp_path / "storage"
    restore_path = tmp_path / "restore"
    storage_path.mkdir(parents=True, exist_ok=True)
    restore_path.mkdir(parents=True, exist_ok=True)

    shutil.copy(fixture_archive_path, storage_path / f"pytest-{frozen_time_str}-yearly.tgz")

    settings.update(
        {
            "action": "restore",
            "log_level": "TRACE",
            "name": "pytest",
            "mongo_uri": "NULL",
            "mongo_db_name": "NULL",
            "storage_location": "local",
            "storage_path": storage_path,
            "restore_path": restore_path,
        }
    )
    main()
    output = clean_stderr()
    debug(output)
    debug(restore_path)

    assert len(list(restore_path.glob("*"))) == 1
    assert Path(restore_path / "src" / "baz.txt").exists()
    assert "Starting backup-mongodb container" in output
    assert "Run ezbak for 'pytest'" in output
    assert "Restore complete. Exiting." in output
