# argus/models/common/base.py
"""
Shared Pydantic Base Models for ARGUS.

This module provides a two-tier base class hierarchy for ARGUS configuration
and locale models:

    FrozenModel (base)
        │
        │   - Immutable (frozen=True)
        │   - Strict validation (extra='forbid')
        │   - Compact __repr__ for debugging
        │
        └──▶ RootConfigModel (extends FrozenModel)
                │
                │   - YAML file loading (from_yaml, from_default, etc.)
                │   - YAML serialization (to_yaml_string)
                │   - Default resource path configuration
                │
                └──▶ Your 3 root config models

Usage Pattern:
    - Nested/child models: inherit from FrozenModel
    - Root models (representing entire YAML files): inherit from RootConfigModel

Example:
    >>> # Nested model - just needs validation and immutability
    >>> class ThresholdSettings(FrozenModel):
    ...     zscore: float
    ...     minimum_count: int
    ...
    >>> # Root model - represents an entire YAML file
    >>> class PolicyConfig(RootConfigModel):
    ...     _default_resource_path: ClassVar[tuple[str, ...]] = (
    ...         'defaults', 'policy.yaml'
    ...     )
    ...     thresholds: ThresholdSettings  # nested model
    ...     enabled: bool
    ...
    >>> # Load the root model (nested models are validated automatically)
    >>> policy = PolicyConfig.from_yaml('~/.argus/policy.yaml')
"""

import logging
from pathlib import Path
from typing import Any, ClassVar, Self

import yaml
from pydantic import BaseModel, ConfigDict
from pydantic.fields import FieldInfo

from argus.utils.yaml_loader import (
    DEFAULT_RESOURCE_PACKAGE,
    load_yaml_from_package_resource,
    load_yaml_from_path,
    parse_yaml_to_dict,
)

__all__: list[str] = [
    'FrozenModel',
    'RootConfigModel',
]

logger: logging.Logger = logging.getLogger(__name__)

# Maximum string length shown in __repr__ output.
# Prevents console spam from large locale strings during debugging.
_REPR_MAX_STRING_LENGTH: int = 50


# =============================================================================
# Base Model: FrozenModel
# =============================================================================
# Use this for nested/child models that are part of a larger configuration.
# Provides immutability, strict validation, and compact repr—nothing more.
# =============================================================================


class FrozenModel(BaseModel):
    """
    Base class for immutable, strictly-validated Pydantic models.

    Use this as the base class for nested configuration models—the building
    blocks that compose larger root configurations. This class provides the
    core guarantees all ARGUS config models need, without YAML loading logic
    that only makes sense for root-level models.

    Guarantees:
        - Immutable: Instances cannot be modified after creation (frozen=True)
        - Strict: Unknown fields raise ValidationError (extra='forbid')
        - Validated: Default values are checked at class definition time

    When to Use:
        - Nested models that are fields within larger models
        - Any model that doesn't represent an entire YAML file
        - Models that will be instantiated by Pydantic during parent validation

    When to Use RootConfigModel Instead:
        - Models representing entire YAML configuration files
        - Models that need from_yaml(), from_default(), or to_yaml_string()

    Example:
        >>> class DatabaseSettings(FrozenModel):
        ...     host: str
        ...     port: int = 5432
        ...     max_connections: int = 10
        ...
        >>> class ServerSettings(FrozenModel):
        ...     bind_address: str = '0.0.0.0'
        ...     workers: int = 4
        ...
        >>> # These are used as fields in a root model:
        >>> class AppConfig(RootConfigModel):
        ...     database: DatabaseSettings
        ...     server: ServerSettings
    """

    model_config = ConfigDict(
        extra='forbid',
        frozen=True,
        validate_default=True,
    )

    @classmethod
    def get_field_definitions(cls) -> dict[str, FieldInfo]:
        """
        Access model field definitions via the class, not the instance.

        Pydantic V2 deprecated accessing `model_fields` on instances.
        This classmethod provides a clean, future-proof interface that
        works identically whether called on the class or an instance.

        Returns:
            Dictionary mapping field names to their FieldInfo metadata.

        Example:
            >>> # Both of these work identically:
            >>> MyConfig.get_field_definitions()
            >>> my_config_instance.get_field_definitions()
        """
        return cls.model_fields

    def __repr__(self) -> str:
        """
        Return a compact string representation for debugging.

        Truncates long strings and summarizes nested models to prevent
        console spam when inspecting large configuration objects.

        Returns:
            Compact representation suitable for logging and REPL use.

        Example:
            >>> repr(settings)
            "DatabaseSettings(host='localhost', port=5432, max_connections=10)"
        """
        field_representations: list[str] = []

        for field_name in self.__class__.model_fields:
            field_value: Any = getattr(self, field_name)
            compact_representation: str = _format_value_for_repr(field_value)
            field_representations.append(f'{field_name}={compact_representation}')

        return f'{self.__class__.__name__}({", ".join(field_representations)})'


# =============================================================================
# Root Model: RootConfigModel
# =============================================================================
# Use this for top-level models that represent entire YAML configuration files.
# Adds YAML loading and serialization capabilities to FrozenModel.
# =============================================================================


class RootConfigModel(FrozenModel):
    """
    Base class for root-level configuration models representing YAML files.

    Extends FrozenModel with YAML loading and serialization capabilities.
    Use this as the base class for models that represent entire configuration
    files, not for nested models within those files.

    Class Attributes (Override in Subclasses):
        _default_resource_package: Package containing bundled defaults.
            Defaults to 'argus'. Rarely needs overriding.
        _default_resource_path: Path tuple to the default YAML file within
            the package. Set to None (default) if no bundled default exists.
            MUST be set to enable from_default().

    Loading Methods:
        from_yaml: Load from filesystem path (user-provided config)
        from_yaml_string: Load from string (useful for testing)
        from_package_resource: Load from arbitrary package resource
        from_default: Load bundled default (requires _default_resource_path)

    Serialization:
        to_yaml_string: Convert model to YAML (debugging, generating templates)

    Inheritance:
        RootConfigModel extends FrozenModel, so root models get all the same
        guarantees (immutability, strict validation) plus YAML capabilities.

    Example:
        >>> class PolicyConfig(RootConfigModel):
        ...     '''Root model for policy.yaml configuration file.'''
        ...
        ...     _default_resource_path: ClassVar[tuple[str, ...]] = (
        ...         'defaults', 'policy.yaml'
        ...     )
        ...
        ...     # Nested models (these inherit from FrozenModel)
        ...     thresholds: ThresholdSettings
        ...     analysis: AnalysisSettings
        ...
        ...     # Simple fields
        ...     enabled: bool = True
        ...
        >>> # Three ways to load:
        >>> config = PolicyConfig.from_yaml('~/.argus/policy.yaml')
        >>> config = PolicyConfig.from_default()
        >>> config = PolicyConfig.from_yaml_string('enabled: false\\n...')
    """

    # -------------------------------------------------------------------------
    # Class-Level Default Resource Configuration
    # -------------------------------------------------------------------------
    # These ClassVar attributes configure bundled default loading.
    # Subclasses override _default_resource_path to enable from_default().
    # -------------------------------------------------------------------------

    _default_resource_package: ClassVar[str] = DEFAULT_RESOURCE_PACKAGE
    _default_resource_path: ClassVar[tuple[str, ...] | None] = None

    # -------------------------------------------------------------------------
    # Class Methods: YAML Loading
    # -------------------------------------------------------------------------

    @classmethod
    def from_yaml(cls, file_path: str | Path) -> Self:
        """
        Load and validate a model instance from a filesystem YAML file.

        Use this method for user-provided configuration files. For bundled
        defaults, use from_default() instead.

        Args:
            file_path: Path to the YAML file. Accepts string or Path.
                Tilde (~) is expanded automatically.

        Returns:
            Validated, immutable model instance.

        Raises:
            FileNotFoundError: If the file does not exist.
            PermissionError: If the file cannot be read.
            yaml.YAMLError: If YAML syntax is invalid.
            ValueError: If the YAML file is empty or an empty dictionary.
            TypeError: If YAML root is not a dictionary.
            pydantic.ValidationError: If data fails schema validation.

        Example:
            >>> policy = PolicyConfig.from_yaml('~/.argus/policy.yaml')
        """
        logger.debug('Loading %s from filesystem', cls.__name__)

        parsed_data: dict[str, Any] = load_yaml_from_path(file_path)
        validated_instance: Self = cls.model_validate(parsed_data)

        logger.info('Successfully loaded %s from filesystem', cls.__name__)

        return validated_instance

    @classmethod
    def from_yaml_string(cls, yaml_content: str) -> Self:
        """
        Load and validate a model instance from a YAML string.

        Primarily useful for testing, where embedding YAML in test code
        is more convenient than creating temporary files.

        Args:
            yaml_content: YAML-formatted string. Leading/trailing whitespace
                is acceptable (common with triple-quoted strings).

        Returns:
            Validated, immutable model instance.

        Raises:
            yaml.YAMLError: If YAML syntax is invalid.
            ValueError: If the YAML string is empty or an empty dictionary.
            TypeError: If YAML root is not a dictionary.
            pydantic.ValidationError: If data fails schema validation.

        Example:
            >>> config = PolicyConfig.from_yaml_string('''
            ...     thresholds:
            ...         zscore: 3.0
            ...     enabled: true
            ... ''')
        """
        source_description: str = f'{cls.__name__} YAML string'

        logger.debug('Loading %s from YAML string', cls.__name__)

        parsed_data: dict[str, Any] = parse_yaml_to_dict(
            yaml_source=yaml_content,
            source_description=source_description,
        )
        validated_instance: Self = cls.model_validate(parsed_data)

        logger.debug('Successfully loaded %s from YAML string', cls.__name__)

        return validated_instance

    @classmethod
    def from_package_resource(
        cls,
        resource_path: tuple[str, ...],
        package: str | None = None,
    ) -> Self:
        """
        Load and validate a model from a package-bundled YAML resource.

        This method accesses YAML files distributed as part of a Python
        package. It's the foundation for from_default(), but can also be
        used directly for non-default package resources.

        Args:
            resource_path: Tuple of path components within the package.
                Example: ('locales', 'pt_BR', 'messages.yaml')
            package: Package containing the resource. If None, uses the
                class's _default_resource_package (defaults to 'argus').

        Returns:
            Validated, immutable model instance.

        Raises:
            FileNotFoundError: If the resource path doesn't exist.
            yaml.YAMLError: If YAML syntax is invalid.
            ValueError: If the YAML file is empty or an empty dictionary.
            TypeError: If YAML root is not a dictionary.
            pydantic.ValidationError: If data fails schema validation.

        Example:
            >>> locale = LocaleConfig.from_package_resource(
            ...     resource_path=('locales', 'pt_BR', 'messages.yaml'),
            ... )
        """
        effective_package: str = package or cls._default_resource_package

        logger.debug(
            "Loading %s from package resource in '%s'",
            cls.__name__,
            effective_package,
        )

        parsed_data: dict[str, Any] = load_yaml_from_package_resource(
            resource_path=resource_path,
            package=effective_package,
        )
        validated_instance: Self = cls.model_validate(parsed_data)

        logger.info(
            'Successfully loaded %s from package resource',
            cls.__name__,
        )

        return validated_instance

    @classmethod
    def from_default(cls) -> Self:
        """
        Load the bundled default configuration for this model type.

        Convenience method that loads from the path specified by the
        class's _default_resource_path attribute. Subclasses MUST define
        this attribute to use from_default().

        Returns:
            Validated, immutable model instance from bundled defaults.

        Raises:
            NotImplementedError: If subclass hasn't defined _default_resource_path.
            FileNotFoundError: If the default resource doesn't exist (packaging bug).
            yaml.YAMLError: If default YAML has syntax errors.
            pydantic.ValidationError: If default data is invalid.

        Example:
            >>> # Subclass must define the default path:
            >>> class PolicyConfig(RootConfigModel):
            ...     _default_resource_path: ClassVar[tuple[str, ...]] = (
            ...         'defaults', 'policy.yaml'
            ...     )
            ...
            >>> default_policy = PolicyConfig.from_default()

        Note:
            NotImplementedError means this model has no bundled default.
            Some models (e.g., user-specific configs) intentionally lack
            defaults and must be provided explicitly.
        """
        if cls._default_resource_path is None:
            error_message: str = (
                f'{cls.__name__} does not define _default_resource_path. '
                f'Either set this ClassVar to enable from_default(), or '
                f'use from_yaml() with an explicit file path.'
            )
            logger.error(error_message)
            raise NotImplementedError(error_message)

        logger.debug('Loading default %s', cls.__name__)

        return cls.from_package_resource(
            resource_path=cls._default_resource_path,
            package=cls._default_resource_package,
        )

    # -------------------------------------------------------------------------
    # Instance Methods: Serialization
    # -------------------------------------------------------------------------

    def to_yaml_string(self) -> str:
        """
        Serialize the model to a YAML-formatted string.

        Useful for debugging, logging active configuration at startup,
        or generating reference/template YAML files.

        Returns:
            Human-readable YAML string with block style formatting.

        Example:
            >>> print(config.to_yaml_string())
            thresholds:
                zscore: 3.0
                minimum_count: 10
            enabled: true
        """
        return yaml.dump(
            self.model_dump(),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=100,
        )


# -----------------------------------------------------------------------------
# Private Helper Functions
# -----------------------------------------------------------------------------


def _format_value_for_repr(value: object) -> str:
    """
    Create a compact string representation of a value for __repr__ output.

    Handles nested models, long strings, and collections to prevent
    console spam during debugging sessions.

    Args:
        value: Any value to format compactly.

    Returns:
        Compact string suitable for inclusion in __repr__ output.
    """
    formatted_output: str

    match value:
        # Nested config models: show class name and field count only.
        case FrozenModel():
            field_count: int = len(value.__class__.model_fields)
            formatted_output = f'{value.__class__.__name__}({field_count} fields)'

        # Long strings: truncate with ellipsis.
        case str() if len(value) > _REPR_MAX_STRING_LENGTH:
            truncated: str = value[:_REPR_MAX_STRING_LENGTH]
            formatted_output = f'{truncated!r}...'

        # Short strings: show with quotes.
        case str():
            formatted_output = repr(value)

        # Non-empty lists: show type of first item and count.
        case list() if value:
            first_type: str = type(value[0]).__name__
            formatted_output = f'[{first_type}, ...] ({len(value)} items)'

        # Empty lists.
        case list():
            formatted_output = '[]'

        # Dictionaries: show key count only.
        case dict():
            formatted_output = f'{{...}} ({len(value)} keys)'

        # Fallback: default repr.
        case _:
            formatted_output = repr(value)

    return formatted_output
