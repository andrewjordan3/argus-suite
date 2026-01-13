# argus/utils/resources.py
"""Resource loading utilities for bundled default files."""

from importlib.resources import files
from pathlib import Path

from argus.models.policy import PolicyConfig

__all__: list[str] = [
    'load_locale_yaml_text',
    'load_policy',
    'load_policy_yaml_text',
]


def load_locale_yaml_text(user_path: Path | None = None) -> str:
    """
    Load locale YAML text, falling back to the bundled default.

    Args:
        user_path: User-specified locale file path, or None for default.

    Returns:
        YAML content as a string.

    Raises:
        OSError: If a user_path is provided but cannot be read.
    """
    if user_path is not None:
        return user_path.read_text(encoding='utf-8')
    return (files('argus.locales') / 'english.yaml').read_text(encoding='utf-8')


def load_policy_yaml_text(user_path: Path | None = None) -> str:
    """
    Load policy YAML text, falling back to the bundled default.

    Args:
        user_path: User-specified policy file path, or None for default.

    Returns:
        YAML content as a string.

    Raises:
        OSError: If a user_path is provided but cannot be read.
    """
    if user_path is not None:
        return user_path.read_text(encoding='utf-8')
    return (files('argus.defaults') / 'policy.yaml').read_text(encoding='utf-8')


def load_policy(user_path: Path | None = None) -> PolicyConfig:
    """
    Load and validate policy configuration, falling back to bundled default.

    Args:
        user_path: User-specified policy file path, or None for default.

    Returns:
        Validated PolicyConfig instance.

    Raises:
        OSError: If a user_path is provided but cannot be read.
        ValidationError: If the YAML content fails validation.
    """
    yaml_text: str = load_policy_yaml_text(user_path)
    return PolicyConfig.from_yaml_text(yaml_text)
