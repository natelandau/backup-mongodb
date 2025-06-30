[![Automated Tests](https://github.com/natelandau/backup-mongodb/actions/workflows/automated-tests.yml/badge.svg)](https://github.com/natelandau/backup-mongodb/actions/workflows/automated-tests.yml) [![codecov](https://codecov.io/gh/natelandau/backup-mongodb/branch/main/graph/badge.svg)](https://codecov.io/gh/natelandau/backup-mongodb)

# backup-mongodb

A docker container that creates backups of a MongoDB database at a set schedule. This container is designed to be run as a sidecar to a MongoDB instance.

## Features

-   Backups are GZIP compressed
-   Backups are stored locally, in an AWS S3 bucket, or both
-   Backups are retained according to a configurable retention policy with old backups automatically removed
-   Backups can be restored from a local path or an AWS S3 bucket. **Note: Backups are downloaded to the local path but NOT restored to the MongoDB instance automatically.**

## Configuration

Configuration is managed through environment variables. The following variables are required:

### Required Settings

-   `BACKUP_MONGODB_NAME` - The name of the backup
-   `BACKUP_MONGODB_STORAGE_PATH` - The path to store the backups
-   `BACKUP_MONGODB_STORAGE_LOCATION` - The location to store the backups `local`, `aws`, or `all` (default: `local`)
-   `BACKUP_MONGODB_ACTION` - The action to perform `backup` or `restore` (default: `backup`)

### Restore Option

-   `BACKUP_MONGODB_RESTORE_PATH` - The localpath to save the restored backup to. Required if `BACKUP_MONGODB_ACTION=restore`

### Retention Policies

-   `BACKUP_MONGODB_MAX_BACKUPS` - The maximum number of backups to keep (overrides all other retention policies)
-   `BACKUP_MONGODB_RETENTION_YEARLY` - The number of yearly backups to keep
-   `BACKUP_MONGODB_RETENTION_MONTHLY` - The number of monthly backups to keep
-   `BACKUP_MONGODB_RETENTION_WEEKLY` - The number of weekly backups to keep
-   `BACKUP_MONGODB_RETENTION_DAILY` - The number of daily backups to keep
-   `BACKUP_MONGODB_RETENTION_HOURLY` - The number of hourly backups to keep
-   `BACKUP_MONGODB_RETENTION_MINUTELY` - The number of minutely backups to keep

### Scheduling

-   `BACKUP_MONGODB_CRON` - The cron schedule to run the backup script (Note: This only parses hours and minutes but must include all 5 fields as a single string e.g. `20 11 * * *` or `*\2 * * * *`)
-   `BACKUP_MONGODB_TZ` - The timezone to use for the cron schedule

### Logging

-   `BACKUP_MONGODB_LOG_LEVEL` - The log level to use (default: `INFO`)
-   `BACKUP_MONGODB_LOG_FILE` - The file to write logs to (default: `backup-mongodb.log`)
-   `BACKUP_MONGODB_LOG_PREFIX` - The prefix to use for the log file (default: `blackbook`)

### AWS Storage Backend

-   `BACKUP_MONGODB_AWS_SECRET_KEY` - The AWS secret ke
-   `BACKUP_MONGODB_AWS_S3_BUCKET_NAME` - The AWS S3 bucket name
-   `BACKUP_MONGODB_AWS_S3_BUCKET_PATH` - The AWS S3 bucket path

### MongoDB Settings

-   `BACKUP_MONGODB_MONGO_URI` - The URI to connect to the MongoDB instance
-   `BACKUP_MONGODB_MONGO_DB_NAME` - The name of the database to backup

## Usage

This script is intended to be run as a Docker container. The following command will run the script with the default configuration:

```bash
docker run -d \
    -e BACKUP_MONGODB_NAME="mydb" \
    -e BACKUP_MONGODB_MONGO_URI="mongodb://localhost:27017" \
    -e BACKUP_MONGODB_MONGO_DB_NAME="mydb" \
    -e BACKUP_MONGODB_STORAGE_PATH="/data/backups" \
    -e BACKUP_MONGODB_CRON="0 02 * * *" \
    -e BACKUP_MONGODB_STORAGE_LOCATION="local" \
    -e BACKUP_MONGODB_LOG_FILE="/data/backup-mongodb.log" \
    -e BACKUP_MONGODB_TZ="America/New_York" \
    -v /path/to/data:/data \
    --name backup-mongodb \
    ghcr.io/natelandau/backup-mongodb:latest
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for more information.
