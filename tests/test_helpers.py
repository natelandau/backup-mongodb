# type: ignore
"""Test helper utilities."""


import pytest

from backup_mongodb.utils import parse_cron


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
