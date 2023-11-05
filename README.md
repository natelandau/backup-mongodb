[![Automated Tests](https://github.com/natelandau/backup-mongodb/actions/workflows/automated-tests.yml/badge.svg)](https://github.com/natelandau/backup-mongodb/actions/workflows/automated-tests.yml) [![codecov](https://codecov.io/gh/natelandau/backup-mongodb/branch/main/graph/badge.svg)](https://codecov.io/gh/natelandau/backup-mongodb)

# backup-mongodb

Backup MongoDB databases

A script that creates backups of a MongoDB databases at a set schedule.

## Configuration

Configuration is managed through environment variables. The following variables are required:

-   `MONGO_URI` - The URI to connect to the MongoDB instance
-   `MONGO_DB` - The name of the database to backup
-   `BACKUP_DIR` - The directory to store the backups
-   `CRON_SCHEDULE` - The cron schedule to run the backup script (Note: This only parses hours and minutes but must include all 5 fields as a single string e.g. `20 11 * * *` or `*\2 * * * *`)
-   `DAILY_RETENTION` - The number of daily backups to keep (default: 7)
-   `WEEKLY_RETENTION` - The number of weekly backups to keep (default: 4)
-   `MONTHLY_RETENTION` - The number of monthly backups to keep (default: 12)
-   `YEARLY_RETENTION` - The number of yearly backups to keep (default: 2)
-   `PORT` - The port to connect to the MongoDB instance (default: `8080`)
-   `LOG_FILE` - The file to write logs to (default: `backup-mongodb.log`)
-   `LOG_LEVEL` - The log level to use (default: `INFO`)

The script will perform a backup at the time specified by `CRON_SCHEDULE` and will remove old backups according to the retention policy. You can create a backup on demand by sending a `POST` request to the `/start_backup` endpoint.

## Usage

This script is intended to be run as a Docker container. The following command will run the script with the default configuration:

```bash
docker run -d \
    -e MONGO_URI="mongodb://localhost:27017" \
    -e MONGO_DB="mydb" \
    -e BACKUP_DIR="/data/backups" \
    -e CRON_SCHEDULE="0 02 * * *" \
    -e LOG_FILE="/data/backup-mongodb.log" \
    -v /path/to/data:/data \
    -p 8080:8080 \
    --name backup-mongodb \
    ghcr.io/natelandau/backup-mongodb:latest
```

## Contributing

## Setup: Once per project

There are two ways to contribute to this project.

### 1. Local development

1. Install Python 3.11 and [Poetry](https://python-poetry.org)
2. Clone this repository. `git clone https://github.com/natelandau/backup-mongodb`
3. Install the Poetry environment with `poetry install`.
4. Activate your Poetry environment with `poetry shell`.
5. Install the pre-commit hooks with `pre-commit install --install-hooks`.

## Developing

-   This project follows the [Conventional Commits](https://www.conventionalcommits.org/) standard to automate [Semantic Versioning](https://semver.org/) and [Keep A Changelog](https://keepachangelog.com/) with [Commitizen](https://github.com/commitizen-tools/commitizen).
    -   When you're ready to commit changes run `cz c`
-   Run `poe` from within the development environment to print a list of [Poe the Poet](https://github.com/nat-n/poethepoet) tasks available to run on this project. Common commands:
    -   `poe lint` runs all linters
    -   `poe test` runs all tests with Pytest
-   Run `poetry add {package}` from within the development environment to install a run time dependency and add it to `pyproject.toml` and `poetry.lock`.
-   Run `poetry remove {package}` from within the development environment to uninstall a run time dependency and remove it from `pyproject.toml` and `poetry.lock`.
-   Run `poetry update` from within the development environment to upgrade all dependencies to the latest versions allowed by `pyproject.toml`.
