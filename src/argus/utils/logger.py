# argus/utils/logger.py
"""
Logging configuration for the argus-suite package.

Provides centralized logging setup to ensure consistent log formatting
and output across all modules in the package.
"""

import logging
import sys
from pathlib import Path
from typing import Any, TextIO, cast

from argus.models.user_config.logging import LoggingConfig, LogLevel

__all__: list[str] = ['setup_logger']


def setup_logger(
    config: LoggingConfig,
) -> logging.Logger:
    """
    Set up logging for the argus package.

    This function configures the package-level logger so that all modules
    inherit the same log level and handler configuration. This ensures
    consistent logging throughout the package.

    The function is idempotent - calling it multiple times will completely
    reset and reconfigure the handlers based on the provided arguments.

    Args:
        config: Validated LoggingConfig object.
                - Console logging uses config.console_level
                - File logging is enabled if config.file_path is set

    Returns:
        The package-level logger ('argus') for reference. All module-level
        loggers created with logging.getLogger(__name__) will automatically
        inherit this configuration.

    Example:
        >>> from argus.models.config.logging import LoggingConfig, LogLevel
        >>> from argus.utils.logger import setup_logger
        >>> # Full config (Console + File)
        >>> config = LoggingConfig(
        ...     console_level=LogLevel.INFO,
        ...     file_path='logs/argus.log',
        ...     file_level=LogLevel.DEBUG,
        ... )
        >>> setup_logger(config=config)
    """
    # Get the package-level logger (parent of all module loggers)
    package_logger: logging.Logger = logging.getLogger('argus')

    # Clear existing handlers to allow reconfiguration/idempotency
    # This prevents duplicate logs if setup_logger is called multiple times
    package_logger.handlers.clear()

    # Prevent propagation to root logger to avoid duplicate output
    package_logger.propagate = False

    # Define consistent log format for all handlers
    log_format: logging.Formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)-8s - [%(name)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    # --- 1. Configure Console Handler ---
    # Determine console level
    console_level: LogLevel = config.console_level

    # Use stderr for console output (standard practice for logging)
    console_handler: logging.StreamHandler[TextIO | Any] = logging.StreamHandler(
        sys.stderr
    )
    console_handler.setFormatter(log_format)
    console_handler.setLevel(console_level)
    package_logger.addHandler(console_handler)

    # --- 2. Configure File Handler (Config Only) ---
    if config.file_path is not None:
        # Pydantic validator ensures file_level is set to DEBUG if file_path exists
        # and file_level wasn't explicitly provided
        log_file_path: Path = config.file_path

        # Safe to cast because validator ensures it is not None if file_path is set
        file_level: LogLevel = cast(LogLevel, config.file_level)

        # Ensure parent directory exists
        log_file_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler: logging.FileHandler = logging.FileHandler(
            filename=log_file_path,
            mode='a',  # Append mode
            encoding='utf-8',
        )
        file_handler.setFormatter(log_format)
        file_handler.setLevel(file_level)
        package_logger.addHandler(file_handler)

    # --- 3. Set Package Logger Level ---
    # The logger's level must be the lowest (most verbose) of all its handlers.
    # If the logger is set to INFO, a DEBUG handler will never receive messages.
    effective_level: int = console_level
    if config.file_level is not None:
        effective_level = min(console_level, config.file_level)

    package_logger.setLevel(effective_level)

    # Log setup completion (will appear in console and/or file depending on levels)
    package_logger.info(
        'Logging configured: console_level=%s%s',
        logging.getLevelName(console_level),
        f', file={config.file_path}' if config and config.file_path else '',
    )

    # Return the package logger for reference
    # Module-level loggers (created with logging.getLogger(__name__))
    # will automatically inherit this configuration
    return package_logger
