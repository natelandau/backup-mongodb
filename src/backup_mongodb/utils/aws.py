"""Class to interact with AWS S3."""

import re
from pathlib import Path

import boto3
import inflect
from botocore.config import Config
from botocore.exceptions import ClientError
from loguru import logger

p = inflect.engine()


class AWSService:
    """Class for interacting with AWS services."""

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        bucket_path: str,
        retention_daily: int,
        retention_weekly: int,
        retention_monthly: int,
        retention_yearly: int,
    ) -> None:
        """Initialize the AWS Service class with credentials.

        Args:
            access_key (str): AWS access key ID.
            secret_key (str): AWS secret access key.
            bucket_name (str): Name of the S3 bucket to use.
            bucket_path (str): Path to the S3 bucket to use.
            retention_daily (int): Retention policy for daily backups.
            retention_weekly (int): Retention policy for weekly backups.
            retention_monthly (int): Retention policy for monthly backups.
            retention_yearly (int): Retention policy for yearly backups.
        """
        self.aws_access_key_id = access_key
        self.aws_secret_access_key = secret_key
        self.bucket_name = bucket_name
        self.bucket_path = bucket_path
        self.retention_daily = retention_daily
        self.retention_weekly = retention_weekly
        self.retention_monthly = retention_monthly
        self.retention_yearly = retention_yearly

        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            config=Config(retries={"max_attempts": 10, "mode": "standard"}),
        )
        self.bucket = self.bucket_name
        self.location = self.s3.get_bucket_location(Bucket=self.bucket)  # Ex. us-east-1

    def upload_file(self, file: Path) -> bool:
        """Upload a file to an S3 bucket."""
        logger.debug(f"AWS: Upload {file.name}")
        try:
            self.s3.upload_file(file, self.bucket, f"{self.bucket_path}/{file.name}")
        except ClientError as e:
            logger.error(e)
            return False

        logger.info(f"AWS: Upload {file.name} to S3")
        return True

    def delete_file(self, file: Path | str) -> bool:
        """Delete a file from an S3 bucket."""
        if isinstance(file, Path):
            file = file.name

        if not re.match(rf"^{self.bucket_path}", file):
            file = f"{self.bucket_path}/{file}"  # type: ignore [unreachable]

        logger.debug(f"AWS: Delete {file}")
        try:
            self.s3.delete_object(Bucket=self.bucket, Key=f"{file}")
        except ClientError as e:
            logger.error(e)
            return False

        return True

    def list_objects(self, prefix: str) -> list[str]:
        """List all objects in the S3 bucket with a given prefix.

        Use the S3 bucket's object filter method to find all objects that have keys starting with the given prefix. Return these keys as a list of strings.

        Args:
            prefix (str): The prefix to filter object keys by.

        Returns:
            list[str]: A list of object keys that start with the given prefix.
        """
        result = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        return [obj["Key"] for obj in result.get("Contents", [])]

    def clean_old_backups(self) -> list[str]:
        """Clean up old backups based on retention policies.

        The method proceeds with the following steps:
        1. Scans the backup directory.
        2. Classifies each backup file based on its backup type (daily, weekly, etc.).
        3. Checks each category of backup against its respective retention policy.
        4. Deletes any backups that exceed the retention limit.
        5. Logs each deletion and the total number of deletions.

        Returns:
            list[Path]: A list of the deleted backup files.
        """
        logger.debug("AWS: Check for old db backups to purge")
        deleted = 0
        backups: dict[str, list[str]] = {
            "daily": [],
            "weekly": [],
            "monthly": [],
            "yearly": [],
        }

        # Build the dictionary of backups
        for file in sorted(self.list_objects(self.bucket_path), reverse=True):
            for backup_type in backups:
                if backup_type in file:
                    backups[backup_type].append(file)

        # Now delete the old backups
        deleted_files = []
        for backup_type in backups:
            policy = getattr(self, f"retention_{backup_type}", 4)
            if len(backups[backup_type]) > policy:
                for backup in backups[backup_type][policy:]:
                    deleted_files.append(backup)
                    self.delete_file(backup)
                    deleted += 1

        if deleted > 0:
            logger.info(f"AWS: Delete {deleted} old db {p.plural_noun('backup', deleted)}")

        return deleted_files
