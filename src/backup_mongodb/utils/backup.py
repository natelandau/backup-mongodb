"""Backup MongoDB database."""

from pathlib import Path

import inflect
import sh
from loguru import logger
from sh import mongodump

from backup_mongodb.utils.helpers import get_current_time

p = inflect.engine()


class BackupService:
    """Manages backups and retention of MongoDB database backups.

    This class handles the creation and management of backups for a specified MongoDB database,
    implementing retention policies for backups taken at different intervals (daily, weekly,
    monthly, yearly). It supports operations to perform backups, clean old backups based on
    retention policies, and determine the type of backup needed based on the date.
    """

    def __init__(
        self,
        backup_dir: Path,
        db_name: str,
        mongodb_uri: str,
        retention_daily: int,
        retention_weekly: int,
        retention_monthly: int,
        retention_yearly: int,
    ):
        self.backup_dir = self._create_backup_dir(backup_dir)
        self.db_name = db_name
        self.mongodb_uri = mongodb_uri.rstrip("/")
        self.retention_daily = retention_daily
        self.retention_weekly = retention_weekly
        self.retention_monthly = retention_monthly
        self.retention_yearly = retention_yearly

    @staticmethod
    def _create_backup_dir(backup_dir: Path) -> Path:
        """Ensures the specified backup directory exists, creating it if not.

        Args:
            backup_dir: The directory where backups will be stored.

        Returns:
            The same Path object passed as input, after ensuring the directory exists.
        """
        if not backup_dir.exists():
            logger.info(f"LOCAL: Create backup directory: {backup_dir}")
            backup_dir.mkdir(parents=True)

        return backup_dir

    @staticmethod
    def type_of_backup() -> str:
        """Determines the backup type based on the current date.

        Evaluates the current date to decide whether the backup should be classified as yearly,
        monthly, weekly, or daily.

        Returns:
            A string representing the backup type ('yearly', 'monthly', 'weekly', 'daily').
        """
        now = get_current_time()
        today = now.format("YYYY-MM-DD")
        yearly = now.span("year")[0].format("YYYY-MM-DD")
        monthly = now.span("month")[0].format("YYYY-MM-DD")

        if today == yearly:
            return "yearly"
        if today == monthly:
            return "monthly"
        if now.weekday() == 0:  # Monday is denoted by 0
            return "weekly"

        return "daily"

    def do_backup(self) -> Path:
        """Performs a backup of the MongoDB database.

        Executes a backup operation, saving the MongoDB database to a gzip-compressed archive file.
        The file is named based on the current date and the determined backup type.

        Returns:
            A Path object representing the file where the backup was saved.
        """
        backup_type = self.type_of_backup()
        now = get_current_time()
        backup_file = (
            self.backup_dir / f"{now.format('YYYY-MM-DDTHHmmss')}-{backup_type}.acrhive.gz"
        )
        logger.debug(f"TRACE: Running mongodump with {backup_file}")

        try:
            mongodump(
                f"--uri={self.mongodb_uri}/{self.db_name}", f"--archive={backup_file}", "--gzip"
            )
        except sh.ErrorReturnCode as e:
            logger.error(f"Error running mongodump: {e}")
            raise e  # noqa: TRY201

        logger.info(f"LOCAL: Create backup {backup_file}")
        return backup_file

    def clean_old_backups(self) -> list[Path]:
        """Cleans up old database backups exceeding retention policies.

        Iterates over the backup files stored in the backup directory, organizing them by type
        (daily, weekly, monthly, yearly), and deletes files exceeding the retention count set for each
        type. It logs the action taken for each deleted backup.

        Returns:
            A list of Path objects representing the backup files that were deleted.
        """
        logger.debug("LOCAL: Check for old db backups to purge")
        deleted = 0
        backups: dict[str, list[Path]] = {
            "daily": [],
            "weekly": [],
            "monthly": [],
            "yearly": [],
        }

        # Build the dictionary of backups
        for file in sorted(self.backup_dir.iterdir(), key=lambda x: x.name, reverse=True):
            for backup_type in backups:
                if backup_type in file.name:
                    backups[backup_type].append(file)

        # Now delete the old backups
        deleted_files = []
        for backup_type in backups:
            policy = getattr(self, f"retention_{backup_type}", 2)
            if len(backups[backup_type]) > policy:
                for backup in backups[backup_type][policy:]:
                    logger.debug(f"LOCAL: Delete {backup.name}")
                    deleted_files.append(backup)
                    backup.unlink()
                    deleted += 1

        if deleted > 0:
            logger.info(f"LOCAL: Delete {deleted} old db {p.plural_noun('backup', deleted)}")

        return deleted_files
