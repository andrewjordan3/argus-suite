# argus/models/user_config/logging.py
"""
Logging configuration module for the ARGUS system.
"""

from enum import IntEnum
from pathlib import Path
from typing import Self

from pydantic import Field, field_validator, model_validator

from argus.models.common import FrozenModel

__all__: list[str] = [
    'LogLevel',
    'LoggingConfig',
]


# =============================================================================
# LOGGING TYPE DEFINITIONS
# =============================================================================


class LogLevel(IntEnum):
    """
    Standard Python logging levels as an enumeration.

    Using IntEnum provides several benefits:
        - Single source of truth for level names and numeric values
        - Values match Python's logging module exactly (10, 20, 30, 40, 50)
        - Built-in ordering: LogLevel.DEBUG < LogLevel.INFO
        - Pydantic accepts both string names ('DEBUG') and integers (10)
        - Iterable: for level in LogLevel

    The numeric values are intentionally spaced by 10 to match stdlib logging,
    which allows custom intermediate levels if ever needed (though not
    recommended for ARGUS).

    Example:
        >>> LogLevel.DEBUG
        <LogLevel.DEBUG: 10>
        >>> LogLevel.DEBUG < LogLevel.INFO
        True
        >>> LogLevel['WARNING']
        <LogLevel.WARNING: 30>
        >>> LogLevel(40)
        <LogLevel.ERROR: 40>
    """

    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================


class LoggingConfig(FrozenModel):
    """
    Configuration for application logging output.

    Supports dual-destination logging: console (always enabled) and optional
    file output. Console output is typically set to INFO for operational
    visibility, while file output captures DEBUG-level detail for debugging.

    File Logging:
        File logging is enabled by providing a file_path. The file_level
        defaults to DEBUG if not specified, capturing maximum detail.
        Parent directories are created automatically by the logging setup.

    Level Specification:
        Levels can be specified as enum members, string names ('DEBUG', 'INFO',
        etc.), or numeric equivalents (10, 20, etc.). String names are
        preferred for readability in YAML configuration files. All formats
        are accepted and normalized to LogLevel enum members.

    Attributes:
        file_path: Path to log file. None disables file logging.
            Extension .log is appended automatically if missing.
        console_level: Minimum log level for console (stderr) output.
        file_level: Minimum log level for file output. Defaults to DEBUG
            if file_path is provided.

    Example:
        >>> config = LoggingConfig(
        ...     console_level='INFO',  # String name works
        ...     file_path='logs/argus.log',
        ...     file_level=LogLevel.DEBUG,  # Enum member works
        ... )
        >>> config.console_level
        <LogLevel.INFO: 20>
    """

    file_path: Path | None = Field(
        default=None,
        description='Log file path (.log extension auto-added). None disables file logging.',
    )

    console_level: LogLevel = Field(
        default=LogLevel.INFO,
        description='Console log level: DEBUG, INFO, WARNING, ERROR, or CRITICAL',
    )

    file_level: LogLevel | None = Field(
        default=None,
        description='File log level. Defaults to DEBUG when file_path is provided.',
    )

    @field_validator('file_path', mode='before')
    @classmethod
    def normalize_log_file_path(cls, path_value: str | Path | None) -> Path | None:
        """
        Normalize path and ensure .log extension.

        Args:
            path_value: Path to log file, or None to disable file logging.

        Returns:
            Normalized Path with .log extension, or None.
        """
        if path_value is None:
            return None

        path: Path = Path(path_value)
        path = path.expanduser()

        if path.suffix.lower() != '.log':
            path = path.with_name(f'{path.name}.log')

        if not path.is_absolute():
            path = Path.cwd() / path

        return path.resolve(strict=False)

    @field_validator('console_level', 'file_level', mode='before')
    @classmethod
    def normalize_log_level(
        cls,
        level_value: str | int | LogLevel | None,
    ) -> LogLevel | None:
        """
        Normalize log level input to LogLevel enum member.

        Accepts multiple input formats for YAML/config flexibility:
            - String names: 'DEBUG', 'debug', 'Debug' (case-insensitive)
            - Integer values: 10, 20, 30, 40, 50
            - LogLevel members: LogLevel.DEBUG
            - None (for optional file_level)

        Args:
            level_value: Log level in any accepted format.

        Returns:
            LogLevel enum member, or None if input was None.

        Raises:
            ValueError: If string name or integer value is not valid.
        """
        if level_value is None:
            return None

        if isinstance(level_value, LogLevel):
            return level_value

        if isinstance(level_value, str):
            normalized_name: str = level_value.upper()
            try:
                return LogLevel[normalized_name]
            except KeyError:
                valid_names: list[str] = [level.name for level in LogLevel]
                raise ValueError(
                    f"Invalid log level name '{level_value}'. "
                    f'Valid names: {valid_names}'
                ) from None

        try:
            return LogLevel(level_value)
        except ValueError:
            valid_values: list[int] = [level.value for level in LogLevel]
            raise ValueError(
                f'Invalid log level value {level_value}. Valid values: {valid_values}'
            ) from None

    @model_validator(mode='after')
    def ensure_file_logging_configuration_consistency(self) -> Self:
        """
        Ensure file_path and file_level are consistently configured.

        If file_path is provided without file_level, defaults to DEBUG.
        If file_level is provided without file_path, raises an error since
        there's nowhere to write the logs.

        Returns:
            The validated model with consistent file logging settings.

        Raises:
            ValueError: If file_level is set but file_path is missing.
        """
        has_file_path: bool = self.file_path is not None
        has_file_level: bool = self.file_level is not None

        if has_file_path and not has_file_level:
            # Use object.__setattr__ because model is frozen
            object.__setattr__(self, 'file_level', LogLevel.DEBUG)

        if has_file_level and not has_file_path:
            raise ValueError(
                'file_level is specified but file_path is missing. '
                'Provide file_path to enable file logging, or remove file_level.'
            )

        return self
