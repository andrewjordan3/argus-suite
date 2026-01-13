# argus/config/config_loader.py
"""
Configuration Loading Logic.

This module handles the physical retrieval, parsing, and initial validation of
the application configuration. It serves as the bridge between raw YAML files
on the disk and the strictly typed Pydantic models.

Responsibilities:
    1.  File I/O: Safely locating and reading the configuration file.
    2.  Parsing: Converting YAML text into Python dictionaries.
    3.  Validation: Instantiating the `FuelCardForensicsConfig` model to enforce types.
    4.  Error Handling: Capturing low-level I/O or parsing errors and logging
        them with context before raising.
"""

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from argus.models.config.user_config_models import FuelCardForensicsConfig

__all__: list[str] = ['load_config']

logger: logging.Logger = logging.getLogger(__name__)

# Default configuration path relative to project root
DEFAULT_CONFIG_PATH: Path = Path('example_config/config.yaml')


def load_config(config_path: Path | str | None = None) -> FuelCardForensicsConfig:
    """
    Load and validate fuel card forensics configuration from YAML file.

    This function reads the YAML configuration file, parses it, and validates
    all fields using the Pydantic model hierarchy. Detailed validation errors
    are logged and re-raised with context.

    Args:
        config_path: Path to the YAML configuration file (relative or absolute).
                    If None, defaults to 'example_config/config.yaml' relative
                    to the current working directory.

    Returns:
        Validated FuelCardForensicsConfig instance ready for use.

    Raises:
        FileNotFoundError: If config file does not exist at the specified path.
        yaml.YAMLError: If YAML file is malformed or cannot be parsed.
        ValidationError: If configuration fails Pydantic validation.

    Side Effects:
        Logs configuration loading status at INFO level.
        Logs detailed validation errors at ERROR level if validation fails.

    Example:
        >>> config = load_config("config/config.yaml")
        >>> print(config.analysis.target_location_name)
        'Philadelphia Branch'

        >>> # Use default config path
        >>> config = load_config()
    """
    # Use default path if none provided
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
        logger.debug(
            'No config path provided, using default: %s',
            DEFAULT_CONFIG_PATH,
        )
    else:
        config_path = Path(config_path)

    logger.info('Loading configuration from: %s', config_path.resolve())

    # Check file existence
    if not config_path.exists():
        error_message: str = f'Configuration file not found: {config_path.resolve()}'
        logger.error(error_message)
        raise FileNotFoundError(error_message)

    # Parse YAML
    try:
        with config_path.open(encoding='utf-8') as config_file:
            raw_config_data: Any = yaml.safe_load(config_file)
    except yaml.YAMLError as yaml_error:
        error_message = (
            f'Failed to parse YAML configuration from {config_path.resolve()}: '
            f'{yaml_error}'
        )
        logger.error(error_message)
        raise
    except OSError as os_error:
        error_message = (
            f'Failed to read configuration file {config_path.resolve()}: {os_error}'
        )
        logger.error(error_message)
        raise

    # Validate configuration is a dict (YAML can parse to other types)
    if not isinstance(raw_config_data, dict):
        error_message = (
            f'Configuration file {config_path.resolve()} must contain a YAML mapping '
            f'(dictionary), got {type(raw_config_data).__name__}'
        )
        logger.error(error_message)
        raise ValueError(error_message)

    # Validate with Pydantic
    try:
        validated_config = FuelCardForensicsConfig(**raw_config_data)
    except ValidationError as validation_error:
        error_message = (
            f'Configuration validation failed for {config_path.resolve()}:\n'
            f'{validation_error}'
        )
        logger.error(error_message)
        raise

    logger.info(
        'Configuration loaded and validated successfully from: %s',
        config_path.resolve(),
    )

    return validated_config
