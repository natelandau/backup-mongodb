# type: ignore
"""Test helper utilities."""


import pytest

from backup_mongodb.utils import StorageMethod, get_config_value, get_storage_method, parse_cron


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
