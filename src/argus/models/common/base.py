# argus/models/common/base.py
"""
Shared Pydantic base models for ARGUS.

These models centralize Pydantic configuration so individual models stay
clean and consistent.

Notes:
- `frozen=True` makes models effectively immutable (assignment prohibited).
- `extra='forbid'` prevents unknown keys in configuration files.
"""

import logging
from pathlib import Path
from typing import Any, Self

import yaml
from pydantic import BaseModel, ConfigDict

__all__: list[str] = [
    'BaseConfigModel',
]

logger: logging.Logger = logging.getLogger(__name__)

# Maximum length for string field values in __repr__ output.
# Prevents console spam from large locale strings.
_REPR_MAX_STR_LENGTH: int = 50


class BaseConfigModel(BaseModel):
    """
    Base class for configuration and locale models.

    Provides common configuration and utility methods for all ARGUS
    config/locale models. Designed for immutable value objects loaded
    from YAML files.

    Configuration:
        - Disallows unknown fields (`extra='forbid'`) - catches YAML typos
        - Prevents mutation after creation (`frozen=True`) - config is immutable
        - Validates default values (`validate_default=True`) - catches bad defaults

    Class Methods:
        from_yaml: Load model from a YAML file path
        from_yaml_string: Load model from a YAML string (useful for testing)

    Methods:
        to_yaml_string: Serialize model back to YAML (useful for debugging)

    Raises:
        pydantic.ValidationError: If input data does not conform to the schema.
    """

    model_config = ConfigDict(
        extra='forbid',
        frozen=True,
        validate_default=True,
    )

    @classmethod
    def from_yaml(cls, file_path: str | Path) -> Self:
        """
        Load and validate a model instance from a YAML file.

        Args:
            file_path: Path to the YAML file. Can be string or Path object.

        Returns:
            Validated model instance.

        Raises:
            FileNotFoundError: If the file does not exist.
            yaml.YAMLError: If the file contains invalid YAML syntax.
            pydantic.ValidationError: If the data fails model validation.

        Example:
            >>> english = MessagesLocale.from_yaml('locales/en_US/messages.yaml')
        """
        file_path = Path(file_path)

        logger.debug('Loading %s from %s', cls.__name__, file_path)

        yaml_content: str = file_path.read_text(encoding='utf-8')
        parsed_data: dict[str, Any] = yaml.safe_load(yaml_content)

        instance: Self = cls.model_validate(parsed_data)

        logger.debug('Successfully loaded %s from %s', cls.__name__, file_path)

        return instance

    @classmethod
    def from_yaml_string(cls, yaml_content: str) -> Self:
        """
        Load and validate a model instance from a YAML string.

        Useful for testing or when YAML content is embedded/generated.

        Args:
            yaml_content: YAML-formatted string.

        Returns:
            Validated model instance.

        Raises:
            yaml.YAMLError: If the string contains invalid YAML syntax.
            pydantic.ValidationError: If the data fails model validation.

        Example:
            >>> locale = MessagesLocale.from_yaml_string('''
            ...     messages:
            ...       greeting: "Hello {name}"
            ... ''')
        """
        parsed_data: dict[str, Any] = yaml.safe_load(yaml_content)

        return cls.model_validate(parsed_data)

    def to_yaml_string(self) -> str:
        """
        Serialize the model to a YAML-formatted string.

        Useful for debugging, logging, or generating reference YAML.
        Uses block style for readability.

        Returns:
            YAML-formatted string representation of the model.

        Example:
            >>> print(locale.to_yaml_string())
            messages:
              greeting: Hello {name}
        """
        return yaml.dump(
            self.model_dump(),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=100,
        )

    def __repr__(self) -> str:
        """
        Return a compact string representation for debugging.

        Truncates long string values to prevent console spam when
        inspecting large locale models. Shows class name and field
        count for nested models.

        Returns:
            Compact string representation.

        Example:
            >>> repr(locale)
            "MessagesLocale(messages=DataQualityMessages(4 fields), ...)"
        """
        field_reprs: list[str] = []

        for field_name in self.__class__.model_fields:
            field_value: Any = getattr(self, field_name)
            field_reprs.append(f'{field_name}={_compact_repr(field_value)}')

        return f'{self.__class__.__name__}({", ".join(field_reprs)})'


def _compact_repr(value: object) -> str:
    """
    Create a compact representation of a value for __repr__ output.

    Handles nested models, long strings, and collections gracefully
    to prevent console spam.

    Args:
        value: Any value to represent.

    Returns:
        Compact string representation.
    """
    compact_value: str

    match value:
        case BaseConfigModel():
            field_count: int = len(value.__class__.model_fields)
            compact_value = f'{value.__class__.__name__}({field_count} fields)'

        # Use guards (if condition) to handle long strings separately
        case str() if len(value) > _REPR_MAX_STR_LENGTH:
            compact_value = f'{value[:_REPR_MAX_STR_LENGTH]!r}...'

        case str():
            compact_value = repr(value)

        # Use implicit truthiness of lists to detect non-empty lists
        case list() if value:
            first_item_type: str = type(value[0]).__name__
            compact_value = f'[{first_item_type}, ...] ({len(value)} items)'

        case list():
            compact_value = '[]'

        case dict():
            compact_value = f'{{...}} ({len(value)} keys)'

        case _:
            compact_value = repr(value)

    return compact_value
