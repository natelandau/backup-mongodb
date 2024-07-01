"""Script to backup MongoDB database to Amazon S3 and local filesystem."""

import sys
import threading
import time
from pathlib import Path

import inflect
import schedule
from flask import Flask, Response, jsonify
from loguru import logger

from .__version__ import __version__
from .utils import (
    AWSService,
    BackupService,
    StorageMethod,
    get_config_value,
    get_storage_method,
    parse_cron,
    test_db_connection,
)

p = inflect.engine()
app = Flask(__name__)


# Set up logging
logger.remove()
logger.add(
    sys.stderr,
    level=get_config_value("LOG_LEVEL").upper(),
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>: <level>{message}</level>"
    if get_config_value("LOG_LEVEL").upper() == "DEBUG"
    else "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    enqueue=True,
)
logger.add(
    get_config_value("LOG_FILE"),
    level=get_config_value("LOG_LEVEL").upper(),
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
    rotation="50 MB",
    retention=2,
    compression="zip",
    enqueue=True,
)


def setup_schedule(
    minute: str,
    hour: str,
    day_of_month: str,  # noqa: ARG001
    month: str,  # noqa: ARG001
    day_of_week: str,  # noqa: ARG001
) -> None:
    """Configures the backup task based on a cron-like schedule.

    Sets up the scheduling for backups based on simplified cron expressions provided for the time
    and frequency of the backup. Supports scheduling at specific minutes past the hour, every
    certain number of hours or minutes, and at specific times of day.

    Args:
        minute: A string representing the minute part of the schedule. Can be a specific minute
                ('0' to '59'), '*', or an interval ('*/15').
        hour: A string representing the hour part of the schedule. Can be a specific hour ('0' to
              '23'), '*', or an interval ('*/3').
        day_of_month: Currently unused, placeholder for future expansion.
        month: Currently unused, placeholder for future expansion.
        day_of_week: Currently unused, placeholder for future expansion.

    Note:
        - This function currently handles only parts of the cron syntax, specifically time-based
          scheduling (minute and hour fields).
        - The `day_of_month`, `month`, and `day_of_week` parameters are placeholders for potential
          future enhancements to allow more complex scheduling.
    """
    # TODO: work with days, months, etc.

    if minute.startswith("*/"):
        logger.info(
            f"SCHEDULE: Every {minute.split('/')[1]} {p.plural_noun('minute', minute.split('/')[1])}"
        )
        interval_minutes = int(minute.split("/")[1])
        schedule.every(interval_minutes).minutes.do(process_backups)

    elif hour.startswith("*/"):
        logger.info(
            f"SCHEDULE: Every {hour.split('/')[1]} {p.plural_noun('hour', hour.split('/')[1])}"
        )
        interval_hours = int(hour.split("/")[1])
        schedule.every(interval_hours).hours.do(process_backups)

    elif hour == "*" and minute != "*":
        # If the hour field is '*', run the task every hour at the specified minute
        logger.info(f"SCHEDULE: Every hour at minute {minute}")
        schedule.every().hour.at(f":{minute}").do(process_backups)

    elif hour != "*":
        if minute.startswith("*"):
            minute = "00"
        # Otherwise, run the task at the specified hour and minute
        logger.info(f"SCHEDULE: Every day at {hour}:{minute}")
        schedule.every().day.at(f"{hour}:{minute}").do(process_backups)


def process_backups() -> None:
    """Executes the backup and cleanup processes for MongoDB based on the configuration.

    Validates the database connection before proceeding with the backup operation. Retrieves and
    parses necessary configuration values, initializes the appropriate services (local and/or AWS),
    and executes the backup process. This includes creating a new backup, cleaning up old backups
    according to the specified retention policies, and, if configured, uploading the backup to AWS
    S3 and cleaning up old backups in S3 as well.

    Note:
        - The decision to clean up local backups and handle AWS operations depends on the
          configured storage method (local, AWS, or both).
        - If the storage method is set to AWS only, the local backup file is removed after
          successful upload to S3.
    """
    # Confirm the database is available
    if not test_db_connection():
        logger.error("DB: Connection failed, not performing backup")
        return

    # Retrieve configuration values only once and convert to correct types
    config_values: dict[str, int | str | Path] = {
        "backup_dir": Path(get_config_value("BACKUP_DIR")),
        "db_name": get_config_value("DB_NAME"),
        "mongodb_uri": get_config_value("MONGODB_URI"),
        "retention_daily": int(get_config_value("DAILY_RETENTION")),
        "retention_weekly": int(get_config_value("WEEKLY_RETENTION")),
        "retention_monthly": int(get_config_value("MONTHLY_RETENTION")),
        "retention_yearly": int(get_config_value("YEARLY_RETENTION")),
    }

    # Initialize the backup service
    backup_svc = BackupService(**config_values)  # type: ignore [arg-type]

    # Determine the storage method
    storage_location = get_storage_method()

    aws_svc = None
    if storage_location in {StorageMethod.AWS, StorageMethod.BOTH}:
        aws_config = {
            "access_key": get_config_value("AWS_ACCESS_KEY_ID"),
            "secret_key": get_config_value("AWS_SECRET_ACCESS_KEY"),
            "bucket_name": get_config_value("AWS_S3_BUCKET_NAME"),
            "bucket_path": get_config_value("AWS_S3_BUCKET_PATH"),
            # AWS service uses the same retention policies
            **{k: v for k, v in config_values.items() if k.startswith("retention_")},
        }
        aws_svc = AWSService(**aws_config)  # type: ignore [arg-type]

    # Perform the backup and handle storage options
    new_backup = backup_svc.do_backup()

    # Determine whether to clean up local backups
    should_clean_local = storage_location in {StorageMethod.LOCAL, StorageMethod.BOTH}
    should_handle_aws = storage_location in {StorageMethod.AWS, StorageMethod.BOTH}

    if should_clean_local:
        backup_svc.clean_old_backups()

    if should_handle_aws and aws_svc:
        aws_svc.upload_file(new_backup)
        aws_svc.clean_old_backups()

        if storage_location == StorageMethod.AWS:
            # If the backup shouldn't be retained locally, remove it after upload
            new_backup.unlink()
            logger.debug(f"Deleted temporary local backup file {new_backup.name}")


@app.route("/start_backup", methods=["POST"])
def start_backup() -> tuple[Response, int]:
    """Handles a request to initiate the backup process via a POST method.

    This endpoint logs the receipt of the request, initiates the backup process, and responds with
    a success message and a 200 status code if the process starts successfully. In case of an
    exception, it responds with an error message and a 500 status code.

    Returns:
        A tuple containing a Flask `Response` object with a JSON body indicating the outcome
        (success or error) of the request, and an HTTP status code (200 for success, 500 for error).
    """
    try:
        logger.info("API: Received request to start backup process")
        process_backups()
        return (
            jsonify({"status": "success", "message": "Backup process has started."}),
            200,
        )
    except Exception as e:  # noqa: BLE001
        return jsonify({"status": "error", "message": str(e)}), 500


def run_flask_app() -> None:
    """Starts the Flask application server.

    Launches the Flask web server with configurations specified for the host and port. The port
    is retrieved from the application's configuration. Host is set to allow connections from any
    IP address, facilitating running in a containerized or networked environment.

    Note:
        This function should be called to start the Flask application only; it does not return.
    """
    app.run(host="0.0.0.0", port=int(get_config_value("PORT")))  # noqa: S104


# Main function
def main() -> None:
    """Orchestrates the MongoDB backup process according to a schedule and configuration.

    This function initializes the backup process by determining the storage method and parsing the
    schedule from configuration. It sets up a Flask application in a separate thread for any
    operational commands and continuously checks for scheduled tasks to execute.

    Note:
        - The storage method is determined from the configuration and can be local, AWS, or both.
        - The backup schedule is defined in the configuration in a cron-like format.
        - A Flask application runs in a background thread to possibly handle operational commands.
    """
    logger.info(f"Starting MongoDB backup v{__version__}")
    storage_location = get_storage_method()
    logger.info(f"Storage method: {storage_location.name}")

    minute, hour, day_of_month, month, day_of_week = parse_cron(get_config_value("CRON_SCHEDULE"))
    setup_schedule(minute, hour, day_of_month, month, day_of_week)

    threading.Thread(target=run_flask_app).start()

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
