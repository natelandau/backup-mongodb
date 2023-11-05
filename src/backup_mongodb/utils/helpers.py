"""Helper functions for backup_mongodb."""

import re
import sys

from loguru import logger


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
