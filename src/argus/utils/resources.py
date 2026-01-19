# argus/utils/resources.py
"""
Utility functions for loading configuration resources. This includes locale settings,
policy definitions, and user-specific configurations. Each function handles loading
from a specified file path or falling back to default bundled resources when applicable.
"""

from pathlib import Path

from argus.models.config import UserConfig
from argus.models.locale import LocaleConfig
from argus.models.policy import PolicyConfig

__all__: list[str] = [
    'load_locale_yaml',
    'load_policy_yaml',
    'load_user_config',
]


def load_locale_yaml(file_path: Path | None = None) -> LocaleConfig:
    """
    Load locale YAML text, falling back to the bundled default.

    Args:
        file_path: User-specified locale file path, or None for default.

    Returns:
        Validated LocaleConfig instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        IsADirectoryError: If the path points to a directory, not a file.
        PermissionError: If the file cannot be read due to permissions.
        yaml.YAMLError: If the YAML syntax is invalid.
        ValueError: If the YAML file is empty.
        TypeError: If the YAML root is not a dictionary.
    """
    if file_path is not None:
        return LocaleConfig.from_yaml(file_path)
    return LocaleConfig.from_default()


def load_policy_yaml(file_path: Path | None = None) -> PolicyConfig:
    """
    Load policy YAML text, falling back to the bundled default.

    Args:
        file_path: User-specified policy file path, or None for default.

    Returns:
        Validated PolicyConfig instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        IsADirectoryError: If the path points to a directory, not a file.
        PermissionError: If the file cannot be read due to permissions.
        yaml.YAMLError: If the YAML syntax is invalid.
        ValueError: If the YAML file is empty.
        TypeError: If the YAML root is not a dictionary.
    """
    if file_path is not None:
        return PolicyConfig.from_yaml(file_path)
    return PolicyConfig.from_default()


def load_user_config(file_path: Path) -> UserConfig:
    """
    Load and validate user configuration from a YAML file. The user must
    provide the path to the configuration file. A default configuration is
    not allowed because user-specific settings are required.

    Args:
        file_path: User-specified configuration file path.

    Returns:
        Validated UserConfig instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        IsADirectoryError: If the path points to a directory, not a file.
        PermissionError: If the file cannot be read due to permissions.
        yaml.YAMLError: If the YAML syntax is invalid.
        ValueError: If the YAML file is empty.
        TypeError: If the YAML root is not a dictionary.
    """
    return UserConfig.from_yaml(file_path)
