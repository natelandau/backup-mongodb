"""Helper functions for backup_mongodb."""

import os
import re
import sys
from enum import Enum
from pathlib import Path

import arrow
import pymongo
from arrow import Arrow
from dotenv import dotenv_values
from loguru import logger

DIR = Path(__file__).parents[3].absolute()
CONFIG = {
    **dotenv_values(DIR / ".env"),  # load shared variables
    **dotenv_values(DIR / ".env.secrets"),  # load sensitive variables
    **os.environ,  # override loaded values with environment variables
}


def test_db_connection() -> bool:
    """Tests the MongoDB connection.

    Attempts to connect to the MongoDB database using a URI from the application's configuration,
    with a timeout for server selection. Logs the outcome of the attempt.

    Returns:
        True if the connection is successful, False if a timeout error occurs.
    """
    logger.debug("DB: Testing connection...")
    mongo_uri = get_config_value("MONGODB_URI")

    try:
        client: pymongo.MongoClient = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=1800)
        client.server_info()
        logger.debug("DB: Connection successful")
    except pymongo.errors.ServerSelectionTimeoutError:
        return False
    else:
        return True


# Function to get an environment variable and check if it exists
def get_config_value(var_name: str, default: str | None = None, pass_none: bool = False) -> str:  # noqa: FBT001, FBT002
    """Retrieves the value of an environment or configuration variable.

    Looks up a configuration value by name, with options for default values and handling missing
    values. Exits the program if the variable is required but not set and no default is provided.

    Args:
        var_name: The name of the variable to retrieve.
        default: A default value to return if the variable is not set. If None and `pass_none` is
                 False, the program exits.
        pass_none: If True, returns None instead of exiting when the variable is not set and no
                   default is provided.

    Returns:
        The value of the variable, or the default value if the variable is not set.

    Raises:
        SystemExit: If the variable is not set, no default is provided, and `pass_none` is False.
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
    """Parses a cron schedule string into its components.

    Validates and decomposes a cron schedule into its five components: minute, hour, day of the
    month, month, and day of the week.

    Args:
        schedule: A cron schedule string.

    Returns:
        A tuple containing the minute, hour, day of the month, month, and day of the week components
        of the schedule.

    Raises:
        SystemExit: If the schedule does not match the expected format.
    """
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
    """Determines the storage method based on configuration.

    Reads the storage method from the application's configuration and validates it against the
    available options. Supports local, AWS, and both as valid storage methods.

    Returns:
        An enum member indicating the configured storage method.

    Raises:
        SystemExit: If the configured storage method is invalid.
    """
    user_storage_method = get_config_value("STORAGE_LOCATION").upper()

    if user_storage_method in StorageMethod.__members__:
        return StorageMethod[user_storage_method]

    logger.error("Error: Invalid storage method selected.")
    sys.exit(1)


def get_current_time() -> Arrow:
    """Retrieves the current time, optionally adjusted to a specific timezone.

    Returns the current time as an Arrow object. If a timezone is specified in the application's
    configuration, adjusts the time to that timezone; otherwise, uses UTC.

    Returns:
        The current time as an Arrow object, possibly adjusted for timezone.
    """
    utc = arrow.utcnow()

    if get_config_value("TZ", pass_none=True):
        return utc.to(get_config_value("TZ"))

    return utc
