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
        """Uploads a specified file to a predefined S3 bucket.

        Attempts to upload a file to an Amazon S3 bucket using the bucket and bucket path
        defined in the instance. Logs the process and returns a boolean indicating success or failure.

        Args:
            file: A `Path` object representing the file to be uploaded.

        Returns:
            A boolean value: True if the file was successfully uploaded, otherwise False.
        """
        logger.debug(f"AWS: Upload {file.name}")
        try:
            self.s3.upload_file(file, self.bucket, f"{self.bucket_path}/{file.name}")
        except ClientError as e:
            logger.error(e)
            return False

        logger.info(f"AWS: Upload {file.name} to S3")
        return True

    def delete_file(self, file: Path | str) -> bool:
        """Deletes a specified file from a predefined S3 bucket.

        Attempts to delete a file from an Amazon S3 bucket. The file can be specified either as a
        string representing the key or a `Path` object. If the key does not start with the predefined
        bucket path, it is prepended automatically.

        Args:
            file: The key of the file to delete or a `Path` object representing the file.

        Returns:
            A boolean value: True if the file was successfully deleted, otherwise False.
        """
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
        """Lists all objects in the S3 bucket that match a given prefix.

        Retrieves a list of all object keys in the configured Amazon S3 bucket that start with the
        specified prefix. This can be used to filter objects within a certain directory or category.

        Args:
            prefix: A string representing the prefix to filter the object keys by.

        Returns:
            A list of strings, each representing an object key that starts with the specified prefix.
        """
        result = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        return [obj["Key"] for obj in result.get("Contents", [])]

    def clean_old_backups(self) -> list[str]:
        """Cleans up old backups from the S3 bucket according to retention policies.

        This method identifies and deletes old backup files from the S3 bucket that exceed specified
        retention limits for daily, weekly, monthly, and yearly backups. It determines which files to
        delete based on the backup type indicated in the file name and the retention policy for each
        backup type.

        Returns:
            A list of strings representing the keys of the backup files that were deleted.
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
