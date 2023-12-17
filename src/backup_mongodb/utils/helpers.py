"""Helper functions for backup_mongodb."""

import os
import re
import sys
from enum import Enum
from pathlib import Path

import arrow
from arrow import Arrow
from dotenv import dotenv_values
from loguru import logger

DIR = Path(__file__).parents[3].absolute()
CONFIG = {
    **dotenv_values(DIR / ".env"),  # load shared variables
    **dotenv_values(DIR / ".env.secrets"),  # load sensitive variables
    **os.environ,  # override loaded values with environment variables
}


# Function to get an environment variable and check if it exists
def get_config_value(var_name: str, default: str | None = None, pass_none: bool = False) -> str:
    """Get an environment variable and check if it exists.

    Args:
        var_name (str): The name of the environment variable.
        default (str, optional): The default value to use if the environment variable is not set. Defaults to None.
        pass_none (bool, optional): Whether to pass None if the environment variable is not set. Defaults to False.

    Returns:
        str: The value of the environment variable

    """
    var_value = CONFIG.get(var_name)
    if var_value is None:
        if default:
            return default

        if pass_none:
            return None

        logger.error(f"Error: Required environment variable '{var_name}' is not set.")
        sys.exit(1)

    return var_value.lstrip('"').rstrip('"')


def parse_cron(schedule: str) -> tuple[str, str, str, str, str]:
    """Parse cron schedule and return the schedule parts."""
    parse_cron_schedule = re.compile(r"(\S+)\s(\S+)\s(\S+)\s(\S+)\s(\S+)")
    try:
        minute, hour, day_of_month, month, day_of_week = parse_cron_schedule.match(
            schedule
        ).groups()
    except AttributeError:
        logger.error("Invalid cron schedule format. Expected 5 space-separated parts.")
        sys.exit(1)

    if re.match(r"^\d$", minute):
        minute = f"0{minute}"

    if re.match(r"^\d$", hour):
        hour = f"0{hour}"

    return minute, hour, day_of_month, month, day_of_week


class StorageMethod(Enum):
    """Enum for storage method."""

    LOCAL = 0
    AWS = 1
    BOTH = 2


def get_storage_method() -> StorageMethod:
    """Get the storage method."""
    user_storage_method = get_config_value("STORAGE_LOCATION").upper()

    if user_storage_method in StorageMethod.__members__:
        return StorageMethod[user_storage_method]

    logger.error("Error: Invalid storage method selected.")
    sys.exit(1)


def get_current_time() -> Arrow:
    """Get the time string.

    This function returns the current time in the timezone specified by the TZ environment variable if it is set. If not, it returns the current time in UTC.
    """
    utc = arrow.utcnow()

    if get_config_value("TZ", pass_none=True):
        return utc.to(get_config_value("TZ"))

    return utc
