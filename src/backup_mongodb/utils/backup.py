"""Backup MongoDB database."""

from pathlib import Path

import arrow
import inflect
from loguru import logger
from sh import mongodump

p = inflect.engine()


class Backup:
    """A class that manages backups of a mongodb database.

    This class handles operations like determining the backup type (hourly, daily, weekly, monthly, or yearly), creating the backup, and cleaning old backups based on retention policies.

    Attributes:
        retention_daily (int): The retention policy for daily backups.
        retention_weekly (int): The retention policy for weekly backups.
        retention_monthly (int): The retention policy for monthly backups.
        retention_yearly (int): The retention policy for yearly backups.
        backup_dir (Path): The directory where backups are stored.
        db_name (str): The name of the database to backup.
        mongodb_uri (str): The URI of the MongoDB server.

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
        """Create backup directory if it doesn't exist."""
        if not backup_dir.exists():
            logger.info(f"Creating backup directory: {backup_dir}")
            backup_dir.mkdir(parents=True)

        return backup_dir

    @staticmethod
    def type_of_backup() -> str:
        """Determine the type of backup to perform.

        Determine whether the backup type should be "yearly", "monthly", "weekly", or "daily" based on the current date.

        Returns:
            str: The type of backup to perform.
        """
        now = arrow.utcnow()
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
        """Perform backup of MongoDB database."""
        backup_type = self.type_of_backup()
        backup_file = (
            self.backup_dir
            / f"{arrow.utcnow().format('YYYY-MM-DDTHHmmss')}-{backup_type}.acrhive.gz"
        )
        logger.info(f"Backing up database to {backup_file}")
        mongodump(
            "--uri", f"{self.mongodb_uri}/{self.db_name}", f"--archive={backup_file}", "--gzip"
        )

        return backup_file

    def clean_old_backups(self) -> int:
        """Clean up old backups based on retention policies and return the count of deleted files.

        The method proceeds with the following steps:
        1. Scans the backup directory.
        2. Classifies each backup file based on its backup type (daily, weekly, etc.).
        3. Checks each category of backup against its respective retention policy.
        4. Deletes any backups that exceed the retention limit.
        5. Logs each deletion and the total number of deletions.

        Returns:
            int: The number of deleted files.
        """
        logger.debug("BACKUP: Check for old db backups to purge")
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
        for backup_type in backups:
            policy = getattr(self, f"retention_{backup_type}", 2)
            if len(backups[backup_type]) > policy:
                for backup in backups[backup_type][policy:]:
                    logger.debug(f"BACKUP: Delete {backup.name}")
                    backup.unlink()
                    deleted += 1

        if deleted > 0:
            logger.info(f"BACKUP: Delete {deleted} old db {p.plural_noun('backup', deleted)}")

        return deleted
