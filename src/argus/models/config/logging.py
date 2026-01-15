# argus/models/config/logging.py
"""
Logging configuration module for the ARGUS system.
"""

from pathlib import Path
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from argus.models.common import FrozenModel

__all__: list[str] = ['LoggingConfig']

# =============================================================================
# LOGGING TYPE DEFINITIONS
# =============================================================================

# Valid logging level names recognized by Python's logging module.
# Using Literal rather than an Enum because these map directly to stdlib names.
LogLevelName = Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

# Numeric equivalents of log level names for validation purposes.
# These are the only valid integer values accepted when specifying log levels.
LOG_LEVEL_VALUES: frozenset[int] = frozenset({10, 20, 30, 40, 50})

# Mapping from level name to numeric value, avoiding import of logging module
# in the model layer to maintain separation of concerns.
LOG_LEVEL_NAME_TO_INT: dict[LogLevelName, int] = {
    'DEBUG': 10,
    'INFO': 20,
    'WARNING': 30,
    'ERROR': 40,
    'CRITICAL': 50,
}

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
        Levels can be specified as names ('DEBUG', 'INFO', etc.) or as
        their numeric equivalents (10, 20, etc.). String names are
        preferred for readability in YAML configuration files.

    Attributes:
        file_path: Path to log file. None disables file logging.
            Extension .log is appended automatically if missing.
        console_level: Minimum log level for console (stderr) output.
        file_level: Minimum log level for file output. Defaults to DEBUG if file_path is provided.
    """

    file_path: Path | None = Field(
        default=None,
        description='Log file path (.log extension auto-added). None disables file logging.',
    )

    console_level: LogLevelName | int = Field(
        default='INFO',
        description="Console log level: 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', or int",
    )

    file_level: LogLevelName | int | None = Field(
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

        # Convert to Path immediately to leverage safe filesystem methods
        path: Path = Path(path_value)

        # Tilde characters (~) must be expanded to the full user home
        # directory to ensure the path is valid for filesystem operations
        path = path.expanduser()

        # The .log extension is enforced for consistency.
        # Logic appends the extension if missing, preserving existing
        # extensions (e.g., 'data.txt' becomes 'data.txt.log')
        if path.suffix.lower() != '.log':
            path = path.with_name(f'{path.name}.log')

        if not path.is_absolute():
            # Convert relative paths to absolute paths based on
            # the current working directory
            path = Path.cwd() / path

        # Resolution anchors the path to the filesystem immediately
        # to prevent ambiguity if the working directory changes later
        return path.resolve(strict=False)

    @field_validator('console_level', 'file_level', mode='before')
    @classmethod
    def normalize_log_level_case(
        cls,
        level_value: str | int | None,
    ) -> str | int | None:
        """
        Normalize string log levels to uppercase for case-insensitive config.

        Allows users to specify 'debug', 'Debug', or 'DEBUG' in YAML and have
        all variants work correctly.

        Args:
            level_value: Log level as string, integer, or None.

        Returns:
            Uppercase string if input was string, otherwise unchanged.
        """
        if isinstance(level_value, str):
            return level_value.upper()
        return level_value

    @field_validator('console_level', 'file_level', mode='after')
    @classmethod
    def validate_numeric_log_level(
        cls,
        level_value: LogLevelName | int | None,
    ) -> LogLevelName | int | None:
        """
        Validate numeric log levels are standard Python logging values.

        Args:
            level_value: Log level as name string, integer, or None.

        Returns:
            The validated log level.

        Raises:
            ValueError: If numeric level is not a standard logging value.
        """
        if level_value is None or isinstance(level_value, str):
            return level_value

        # Integer level must be a standard Python logging level
        if level_value not in LOG_LEVEL_VALUES:
            raise ValueError(
                f'Numeric log level must be one of {sorted(LOG_LEVEL_VALUES)}, '
                f'got: {level_value}'
            )

        return level_value

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
            # Sensible default: capture everything to file for debugging
            self.file_level = 'DEBUG'

        if has_file_level and not has_file_path:
            raise ValueError(
                'file_level is specified but file_path is missing. '
                'Provide file_path to enable file logging, or remove file_level.'
            )

        return self

    def get_console_level_int(self) -> int:
        """
        Convert console_level to numeric value for logging module.

        Returns:
            Integer logging level (10=DEBUG through 50=CRITICAL).
        """
        if isinstance(self.console_level, int):
            return self.console_level
        return LOG_LEVEL_NAME_TO_INT[self.console_level]

    def get_file_level_int(self) -> int | None:
        """
        Convert file_level to numeric value for logging module.

        Returns:
            Integer logging level, or None if file logging is disabled.
        """
        if self.file_level is None:
            return None
        if isinstance(self.file_level, int):
            return self.file_level
        return LOG_LEVEL_NAME_TO_INT[self.file_level]
