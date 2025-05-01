# type: ignore
"""Test helper utilities."""

import arrow
import pytest
from freezegun import freeze_time

from backup_mongodb.utils import (
    BackupService,
    StorageMethod,
    get_config_value,
    get_current_time,
    get_storage_method,
    parse_cron,
)


def test_backup_type_of_backup(tmp_path):
    """Test BackupService.type_of_backup."""
    backup_svc = BackupService(
        backup_dir=tmp_path / "test",
        db_name="test",
        mongodb_uri="null",
        retention_daily=1,
        retention_weekly=1,
        retention_monthly=1,
        retention_yearly=1,
    )

    # WHEN the time is a weekday except monday
    # THEN return daily
    freezer = freeze_time("Jan 14th, 2023")
    freezer.start()
    assert backup_svc.type_of_backup() == "daily"
    freezer.stop()

    # WHEN the time is a monday
    # THEN return weekly
    freezer = freeze_time("Jan 16th, 2023")
    freezer.start()
    assert backup_svc.type_of_backup() == "weekly"
    freezer.stop()

    # WHEN the time is the first day of the month
    # THEN return monthly
    freezer = freeze_time("Feb 1st, 2023")
    freezer.start()
    assert backup_svc.type_of_backup() == "monthly"
    freezer.stop()

    # WHEN the time is the first day of the year
    # THEN return yearly
    freezer = freeze_time("jan 1st, 2023")
    freezer.start()
    assert backup_svc.type_of_backup() == "yearly"
    freezer.stop()


@freeze_time("2012-01-14 12:00:01")
def test_get_current_time(mocker):
    """Test get_current_time."""
    # WHEN no TZ is set
    # THEN return UTC time
    result = get_current_time()
    expected = arrow.get("2012-01-14 12:00:01")
    assert str(result) == str(expected)

    # WHEN TZ is set
    mocker.patch("backup_mongodb.utils.helpers.get_config_value", return_value="America/New_York")

    # THEN return time in the specified TZ
    result = get_current_time()
    expected = arrow.get("2012-01-14 12:00:01").to("America/New_York")
    assert str(result) == str(expected)


@pytest.mark.parametrize(
    ("schedule", "expected"),
    [
        ("11 0 * * *", ("11", "00", "*", "*", "*")),
        ("0 1 * * 0", ("00", "01", "*", "*", "0")),
        ("0 23 * * *", ("00", "23", "*", "*", "*")),
        ("*/2 0 * * 3", ("*/2", "00", "*", "*", "3")),
        ("*/2", "exception"),
        ("* * * *", "exception"),
        ("* * * * * * * *", ("*", "*", "*", "*", "*")),
    ],
)
def test_parse_cron(schedule, expected):
    """Test parse_cron."""
    if expected == "exception":
        with pytest.raises(SystemExit):
            parse_cron(schedule)
    else:
        assert parse_cron(schedule) == expected


def test_get_config_value():
    """Test get_config_value."""
    with pytest.raises(SystemExit):
        get_config_value("NOT_A_VALUE")

    assert get_config_value("NOT_A_VALUE", pass_none=True) == ""

    assert get_config_value("NOT_A_VALUE", default="test") == "test"

    assert get_config_value("DB_NAME") == "secret"


def test_get_storage_method(mocker):
    """Test get_storage_method."""
    mocker.patch("backup_mongodb.utils.helpers.get_config_value", return_value="NOT_VALID")
    with pytest.raises(SystemExit):
        get_storage_method()

    mocker.patch("backup_mongodb.utils.helpers.get_config_value", return_value="local")
    assert get_storage_method() == StorageMethod.LOCAL

    mocker.patch("backup_mongodb.utils.helpers.get_config_value", return_value="AWS")
    assert get_storage_method() == StorageMethod.AWS
