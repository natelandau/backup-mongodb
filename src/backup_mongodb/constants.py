"""Constants for the backup-mongodb container."""

from enum import Enum

__version__ = "1.1.0"
ENVAR_PREFIX = "BACKUP_MONGODB_"


class LogLevel(Enum):
    """Log level."""

    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class StorageType(Enum):
    """Storage location."""

    LOCAL = "local"
    AWS = "aws"
    ALL = "all"
