"""Script to backup MongoDB database to Amazon S3 and local filesystem."""

import logging
import os
import sys
import threading
from pathlib import Path

from dotenv import dotenv_values
from flask import Flask, Response, jsonify
from loguru import logger

from .utils import Backup, InterceptHandler

app = Flask(__name__)


# Import configuration from environment variables
DIR = Path(__file__).parents[2].absolute()
CONFIG = {
    **dotenv_values(DIR / ".env"),  # load shared variables
    **dotenv_values(DIR / ".env.secrets"),  # load sensitive variables
    **os.environ,  # override loaded values with environment variables
}


# Function to get an environment variable and check if it exists
def get_config_value(var_name: str) -> str:
    """Get an environment variable and check if it exists."""
    var_value = CONFIG.get(var_name, None)
    if var_value is None:
        logger.error(f"Error: Required environment variable '{var_name}' is not set.")
        sys.exit(1)
    return var_value


# Set up logging
logging.getLogger("sh").setLevel(level=CONFIG["SH_LOG_LEVEL"].upper())
for service in ["urllib3", "boto3", "botocore", "s3transfer"]:
    logging.getLogger(service).setLevel(level=CONFIG["AWS_LOG_LEVEL"].upper())

logger.remove()
logger.add(
    sys.stderr,
    level=get_config_value("LOG_LEVEL").upper(),
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>: <level>{message}</level>",
    enqueue=True,
)
logger.add(
    get_config_value("LOG_FILE"),
    level=get_config_value("LOG_LEVEL").upper(),
    rotation="50 MB",
    retention=2,
    compression="zip",
    enqueue=True,
)

# Intercept standard discord.py logs and redirect to Loguru
logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)


#########################################################################
def backup_task() -> None:
    """Perform backup of MongoDB database and clean old backups from disk."""
    backup_engine = Backup(
        backup_dir=Path(get_config_value("BACKUP_DIR")),
        db_name=get_config_value("DB_NAME"),
        mongodb_uri=get_config_value("MONGODB_URI"),
        retention_daily=int(get_config_value("DAILY_RETENTION")),
        retention_weekly=int(get_config_value("WEEKLY_RETENTION")),
        retention_monthly=int(get_config_value("MONTHLY_RETENTION")),
        retention_yearly=int(get_config_value("YEARLY_RETENTION")),
    )
    backup_engine.do_backup()
    backup_engine.clean_old_backups()


@app.route("/start_backup", methods=["POST"])
def start_backup() -> tuple[Response, int]:
    """Start the backup process."""
    try:
        backup_task()
        return (
            jsonify({"status": "success", "message": "Backup process has started."}),
            200,
        )
    except Exception as e:  # noqa: BLE001
        return jsonify({"status": "error", "message": str(e)}), 500


def run_flask_app() -> None:
    """Run the Flask application."""
    app.run(host="0.0.0.0", port=int(get_config_value("PORT")))  # noqa: S104


# Main function
def main() -> None:
    """Main function."""
    logger.info("Starting MongoDB backup application...")

    threading.Thread(target=run_flask_app).start()


if __name__ == "__main__":
    main()
