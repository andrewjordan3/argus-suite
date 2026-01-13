# argus/utils/locale_loader.py
"""
Locale configuration loading for ARGUS.

Handles loading localized label/threshold configurations from YAML files,
supporting both package-bundled defaults and user-provided custom locales.
"""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from importlib.resources import as_file, files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

import yaml

from argus.models import ReportConfig

__all__: list[str] = ['load_locale_config']

logger: logging.Logger = logging.getLogger(__name__)

# Package-relative path to the default English locale bundled with ARGUS.
_DEFAULT_LOCALE_PACKAGE: str = 'argus'
_DEFAULT_LOCALE_PATH: tuple[str, ...] = ('locales', 'english.yaml')


@contextmanager
def _open_package_resource(
    package: str,
    resource_path: tuple[str, ...],
) -> Generator[Path, None, None]:
    """
    Context manager to access a package resource as a filesystem path.

    Uses importlib.resources to handle resources that may be inside a zip
    archive (e.g., installed wheel). The `as_file` context manager extracts
    the resource to a temporary location if necessary.

    Args:
        package: The package name containing the resource (e.g., 'argus').
        resource_path: Tuple of path components within the package
            (e.g., ('locales', 'english.yaml')).

    Yields:
        A Path object pointing to the resource file.

    Raises:
        FileNotFoundError: If the resource does not exist within the package.
    """
    resource_traversable: Traversable = files(package).joinpath(*resource_path)

    # as_file() creates a temporary extraction if resource is in a zip/wheel.
    with as_file(resource_traversable) as extracted_path:
        yield Path(extracted_path)


def _load_yaml_file(filepath: Path) -> dict[str, Any]:
    """
    Load and parse a YAML file.

    Args:
        filepath: Path to the YAML file.

    Returns:
        Parsed YAML content as a dictionary.

    Raises:
        FileNotFoundError: If the file does not exist.
        yaml.YAMLError: If the file contains invalid YAML syntax.
    """
    logger.debug('Reading YAML file: %s', filepath)

    with filepath.open(encoding='utf-8') as yaml_file:
        yaml_content: dict[str, Any] | None = yaml.safe_load(yaml_file)

    if not yaml_content:
        logger.error('YAML file is empty or contains only null: %s', filepath)
        raise ValueError(f'Locale configuration file is empty: {filepath}')

    logger.debug(
        'Successfully parsed YAML with %d top-level keys',
        len(yaml_content),
    )
    return yaml_content


def load_locale_config(locale_filepath: str | Path | None = None) -> ReportConfig:
    """
    Load locale configuration from YAML and return a validated Pydantic model.

    Locale files contain localized labels, threshold values, and interpretation
    text used throughout ARGUS reports and UI elements.

    Args:
        locale_filepath: Path to a custom locale YAML file. If None, loads the
            default English locale bundled with the ARGUS package.

    Returns:
        Validated ReportConfig containing all locale settings.

    Raises:
        FileNotFoundError: If the specified or default locale file cannot be found.
        ValueError: If the locale file is empty.
        yaml.YAMLError: If the locale file contains invalid YAML syntax.
        pydantic.ValidationError: If the YAML content fails schema validation.

    Example:
        >>> # Load default English locale
        >>> config = load_locale_config()
        >>>
        >>> # Load custom locale
        >>> config = load_locale_config('/path/to/spanish.yaml')
    """
    if locale_filepath is None:
        logger.info(
            'No locale file specified, loading default: %s:%s',
            _DEFAULT_LOCALE_PACKAGE,
            '/'.join(_DEFAULT_LOCALE_PATH),
        )
        yaml_content: dict[str, Any] = _load_default_locale()
    else:
        locale_path = Path(locale_filepath)
        logger.info('Loading custom locale file: %s', locale_path)
        yaml_content = _load_custom_locale(locale_path)

    # Validate against Pydantic schema for type-safe access throughout ARGUS.
    report_config = ReportConfig(**yaml_content)
    logger.info('Locale configuration loaded and validated successfully')

    return report_config


def _load_default_locale() -> dict[str, Any]:
    """
    Load the default English locale bundled with the ARGUS package.

    Returns:
        Parsed YAML content as a dictionary.

    Raises:
        FileNotFoundError: If the bundled locale resource is missing.
            This indicates a packaging error in pyproject.toml.
    """
    try:
        with _open_package_resource(
            _DEFAULT_LOCALE_PACKAGE,
            _DEFAULT_LOCALE_PATH,
        ) as default_locale_path:
            logger.debug('Default locale extracted to: %s', default_locale_path)
            return _load_yaml_file(default_locale_path)

    except (ModuleNotFoundError, FileNotFoundError) as exc:
        default_resource_display: str = (
            f'{_DEFAULT_LOCALE_PACKAGE}/{"/".join(_DEFAULT_LOCALE_PATH)}'
        )
        logger.error(
            'Default locale resource not found: %s. '
            'Verify package_data is configured correctly in pyproject.toml.',
            default_resource_display,
        )
        raise FileNotFoundError(
            f'Default locale resource not found: {default_resource_display}. '
            'Ensure the locale file is included in package_data.'
        ) from exc


def _load_custom_locale(locale_path: Path) -> dict[str, Any]:
    """
    Load a user-provided custom locale file.

    Args:
        locale_path: Filesystem path to the custom locale YAML file.

    Returns:
        Parsed YAML content as a dictionary.

    Raises:
        FileNotFoundError: If the specified file does not exist.
    """
    if not locale_path.exists():
        logger.error(
            'Custom locale file not found: %s (resolved: %s)',
            locale_path,
            locale_path.resolve(),
        )
        raise FileNotFoundError(f'Locale configuration file not found: {locale_path}')

    return _load_yaml_file(locale_path)
