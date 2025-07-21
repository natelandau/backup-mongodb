"""Entrypoint for the backup-mongodb container."""

import atexit
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from environs import Env, validate
from ezbak import ezbak
from nclutils import (
    ShellCommandFailedError,
    ShellCommandNotFoundError,
    err_console,
    logger,
    run_command,
)

from backup_mongodb.constants import ENVAR_PREFIX, LogLevel, StorageType

env = Env(prefix=ENVAR_PREFIX)
env.read_env(".env.secrets")


@dataclass
class Settings:
    """Settings for the backup-mongodb container."""

    action: str = env.str("ACTION", default="backup")
    log_level: str = env.str(
        "LOG_LEVEL",
        default=LogLevel.INFO.name,
        validate=validate.OneOf(
            [x.name for x in LogLevel],
            error="LOG_LEVEL must be one of: {choices}",
        ),
    )
    log_file: str | None = env.str("LOG_FILE", None)
    name: str | None = env.str("NAME", None)
    storage_location: str = env.str(
        "STORAGE_LOCATION",
        default=StorageType.LOCAL.value,
        validate=validate.OneOf(
            [x.value for x in StorageType],
            error="STORAGE_LOCATION must be one of: {choices}",
        ),
    )
    storage_path: str | None = env.str("STORAGE_PATH", None)
    restore_path: str | None = env.str("RESTORE_PATH", None)
    aws_access_key: str | None = env.str("AWS_ACCESS_KEY", None)
    aws_secret_key: str | None = env.str("AWS_SECRET_KEY", None)
    aws_s3_bucket_name: str | None = env.str("AWS_S3_BUCKET_NAME", None)
    aws_s3_bucket_path: str | None = env.str("AWS_S3_BUCKET_PATH", None)
    max_backups: int | None = env.int("MAX_BACKUPS", None)
    cron: str | None = env.str("CRON", None)
    retention_yearly: int | None = env.int("RETENTION_YEARLY", None)
    retention_monthly: int | None = env.int("RETENTION_MONTHLY", None)
    retention_weekly: int | None = env.int("RETENTION_WEEKLY", None)
    retention_daily: int | None = env.int("RETENTION_DAILY", None)
    retention_hourly: int | None = env.int("RETENTION_HOURLY", None)
    retention_minutely: int | None = env.int("RETENTION_MINUTELY", None)
    mongo_uri: str | None = env.str("MONGO_URI", None)
    mongo_db_name: str | None = env.str("MONGO_DB_NAME", None)

    _tmp_dir: TemporaryDirectory | None = None

    @property
    def tmp_dir(self) -> TemporaryDirectory:
        """Get the temporary directory.

        Returns:
            TemporaryDirectory: The temporary directory.
        """
        if self._tmp_dir is None:
            self._tmp_dir = TemporaryDirectory()
            atexit.register(cleanup_tmp_dir)
        return self._tmp_dir

    def validate(self) -> None:
        """Validate the settings."""
        if not self.name:
            msg = "NAME is required"
            raise ValueError(msg)

        if self.action not in {"backup", "restore"}:
            msg = "ACTION must be one of: 'backup', 'restore'"
            raise ValueError(msg)
        if self.storage_location == StorageType.LOCAL.value and not self.storage_path:
            msg = "STORAGE_PATH is required"
            raise ValueError(msg)
        if self.action == "backup" and not self.mongo_uri:
            msg = "MONGO_URI is required"
            raise ValueError(msg)
        if self.action == "backup" and not self.mongo_db_name:
            msg = "MONGO_DB_NAME is required"
            raise ValueError(msg)
        if self.action == "restore" and not self.restore_path:
            msg = "RESTORE_PATH is required"
            raise ValueError(msg)

    def model_dump(
        self,
    ) -> dict[str, int | str | bool | list[Path | str] | LogLevel | StorageType | None]:
        """Serialize settings to a dictionary representation.

        Converts all settings attributes to a dictionary format for serialization,
        logging, or configuration export purposes.

        Returns:
            dict[str, int | str | bool | list[Path | str] | None]: Dictionary representation of all settings.
        """
        return self.__dict__

    def update(
        self,
        updates: dict[str, str | int | Path | bool | list[Path | str] | LogLevel | StorageType],
    ) -> None:
        """Update settings with provided key-value pairs and reset cached properties.

        Validates that all keys exist as attributes on the settings object before updating. Resets cached properties when their underlying data changes to ensure consistency.

        Args:
            updates (dict[str, str | int | Path | bool | list[Path | str]]): Dictionary of setting keys and their new values.
        """
        for key, value in updates.items():
            try:
                getattr(self, key)
            except AttributeError:
                msg = f"ERROR    | '{key}' does not exist in settings"
                err_console.print(msg)
                sys.exit(1)

            if value is not None:
                setattr(self, key, value)


settings = Settings()


def cleanup_tmp_dir() -> None:
    """Clean up the temporary directory to prevent disk space accumulation.

    Removes the temporary directory created during backup operations to free up disk space and maintain system cleanliness.
    """
    if settings._tmp_dir:  # noqa: SLF001
        settings._tmp_dir.cleanup()  # noqa: SLF001

    # Ensure that this function is only called once even if it is registered multiple times.
    atexit.unregister(cleanup_tmp_dir)


def get_mongo_backup() -> Path:
    """Create a temporary directory for the mongo backup and run mongodump."""
    output_dir = Path(settings.tmp_dir.name)
    if not output_dir.exists():
        output_dir.mkdir(parents=True)

    try:
        run_command(
            "mongodump",
            args=[
                "--uri",
                f"{settings.mongo_uri}",
                "--db",
                f"{settings.mongo_db_name}",
                f"--out={output_dir}",
            ],
        )
    except ShellCommandNotFoundError as e:
        logger.error(f"Error running mongodump: {e}")
        raise
    except ShellCommandFailedError as e:
        logger.error(f"Error running mongodump: {e}")
        raise
    except Exception as e:
        logger.error(f"Error running mongodump: {e}")
        raise e  # noqa: TRY201

    return output_dir


def do_backup(scheduler: BackgroundScheduler | None = None) -> None:
    """Do the backup."""
    backup_dir = (
        get_mongo_backup() / settings.mongo_db_name
        if settings.mongo_db_name
        else get_mongo_backup()
    )

    backupmanager = ezbak(
        name=settings.name,
        source_paths=[backup_dir],
        storage_paths=[settings.storage_path],
        storage_location=settings.storage_location,
        tz=None,
        log_level=settings.log_level,
        log_file=str(settings.log_file) if settings.log_file else None,
        max_backups=settings.max_backups,
        retention_yearly=settings.retention_yearly,
        retention_monthly=settings.retention_monthly,
        retention_weekly=settings.retention_weekly,
        retention_daily=settings.retention_daily,
        retention_hourly=settings.retention_hourly,
        retention_minutely=settings.retention_minutely,
        aws_access_key=settings.aws_access_key,
        aws_secret_key=settings.aws_secret_key,
        aws_s3_bucket_name=settings.aws_s3_bucket_name,
        aws_s3_bucket_path=settings.aws_s3_bucket_path,
    )

    backupmanager.create_backup()
    backupmanager.prune_backups()
    backupmanager.rename_backups()

    if scheduler:  # pragma: no cover
        job = scheduler.get_job(job_id="backup")
        if job and job.next_run_time:
            logger.info(f"Next scheduled run: {job.next_run_time}")

    del backupmanager


def do_restore() -> None:
    """Restore the latest backup."""
    backupmanager = ezbak(
        name=settings.name,
        storage_paths=[settings.storage_path],
        storage_location=settings.storage_location,
        tz=None,
        log_level=settings.log_level,
        log_file=str(settings.log_file) if settings.log_file else None,
        aws_access_key=settings.aws_access_key,
        aws_secret_key=settings.aws_secret_key,
        aws_s3_bucket_name=settings.aws_s3_bucket_name,
        aws_s3_bucket_path=settings.aws_s3_bucket_path,
    )
    backupmanager.restore_backup(destination=settings.restore_path)

    del backupmanager


def main() -> None:
    """Main function for the backup-mongodb container."""
    logger.configure(
        log_level=settings.log_level,
        show_source_reference=False,
        log_file=str(settings.log_file) if settings.log_file else None,
    )

    settings.validate()

    for key, value in settings.model_dump().items():
        if not key.startswith("_") and value is not None:
            logger.debug(f"Config: {key}: {value}")

    logger.info("Starting backup-mongodb container")

    if settings.cron:
        scheduler = BackgroundScheduler()

        job = scheduler.add_job(
            func=do_backup,
            args=[scheduler],
            trigger=CronTrigger.from_crontab(settings.cron),
            jitter=600,
            id="backup",
        )
        logger.info(job)
        scheduler.start()

        if job and job.next_run_time:
            logger.info(f"Next scheduled run: {job.next_run_time}")
        else:
            logger.info("No next scheduled run")

        logger.info("Scheduler started")

        try:
            while scheduler.running:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Exiting...")
            scheduler.shutdown()

    elif settings.action == "restore":
        do_restore()
        logger.info("Restore complete. Exiting.")

    else:
        do_backup()
        logger.info("Backup complete. Exiting.")


if __name__ == "__main__":
    main()
