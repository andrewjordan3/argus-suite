# argus/models/common/base.py
"""
Shared Pydantic Base Models for ARGUS.

This module provides a two-tier base class hierarchy used throughout ARGUS
for both configuration/locale models and statistical analysis result models:

    FrozenModel (base)
        │
        │   - Immutable (frozen=True)
        │   - Strict validation (extra='forbid')
        │   - Default validation at class definition time
        │   - Compact __repr__ for debugging
        │
        ├──▶ Configuration Models
        │       - Nested settings models (ThresholdSettings, AnalysisSettings)
        │       - Any model that doesn't need YAML loading
        │
        ├──▶ Statistical Analysis Models
        │       - Test results (StatisticalTest, ChangePointResult)
        │       - Risk profiles (DriverRiskProfile, TemporalRiskProfile)
        │       - Any model storing computational outputs
        │
        └──▶ RootConfigModel (extends FrozenModel)
                │
                │   - YAML file loading (from_yaml, from_default, etc.)
                │   - YAML serialization (to_yaml_string)
                │   - Default resource path configuration
                │
                └──▶ Root configuration models only

Usage Patterns:

    Configuration Models:
        - Nested/child config models: inherit from FrozenModel
        - Root models (entire YAML files): inherit from RootConfigModel

    Statistical Analysis Models:
        - All analysis result models: inherit from FrozenModel
        - Override __repr__ for domain-specific debugging output
        - Add validators for mathematical constraints (e.g., p-values ∈ [0,1])

Examples:

    Configuration Model:
        >>> class ThresholdSettings(FrozenModel):
        ...     zscore: float
        ...     minimum_count: int

    Statistical Result Model:
        >>> class StatisticalTest(FrozenModel):
        ...     name: str
        ...     p_value: float = Field(default=math.nan)
        ...     is_significant: bool = False
        ...
        ...     @field_validator('p_value')
        ...     @classmethod
        ...     def validate_probability(cls, v: float) -> float:
        ...         if not math.isnan(v) and not (0.0 <= v <= 1.0):
        ...             raise ValueError(f'p-value must be in [0,1], got {v}')
        ...         return v

    Root Configuration Model:
        >>> class PolicyConfig(RootConfigModel):
        ...     _default_resource_path: ClassVar[tuple[str, ...]] = (
        ...         'defaults', 'policy.yaml'
        ...     )
        ...     thresholds: ThresholdSettings
        ...     enabled: bool
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
# Universal base for all ARGUS data models requiring immutability and strict
# validation. Used for both configuration models and statistical result models.
# =============================================================================


class FrozenModel(BaseModel):
    """
    Base class for immutable, strictly-validated Pydantic models.

    This is the foundational base class for all ARGUS models that hold data
    which should not change after creation. It serves two primary use cases:

        1. Configuration Models: Nested settings that compose larger configs
        2. Statistical Analysis Models: Results from computations that should
           be treated as immutable records

    Guarantees:
        - Immutable: Instances cannot be modified after creation (frozen=True).
          For statistical results, this ensures computational outputs remain
          intact. To update values (e.g., after FDR correction), create a
          new instance.
        - Strict: Unknown fields raise ValidationError (extra='forbid').
          Catches typos and schema drift early.
        - Validated: Default values are checked at class definition time
          (validate_default=True). Invalid defaults fail fast during development.

    When to Use FrozenModel:
        - Nested configuration models (fields within larger config structures)
        - Statistical test results (p-values, effect sizes, confidence intervals)
        - Risk assessment profiles (driver scores, temporal patterns)
        - Any computational output that should be immutable
        - Any model that doesn't represent an entire YAML file

    When to Use RootConfigModel Instead:
        - Models representing entire YAML configuration files
        - Models that need from_yaml(), from_default(), or to_yaml_string()

    Customization:
        Subclasses commonly add:
        - Field validators for domain constraints (e.g., probabilities ∈ [0,1])
        - Model validators for cross-field consistency checks
        - Custom __repr__ for domain-specific debugging output

    Examples:
        Configuration model (nested settings):
            >>> class DatabaseSettings(FrozenModel):
            ...     host: str
            ...     port: int = 5432
            ...     max_connections: int = 10

        Statistical result model (with validation):
            >>> class StatisticalTest(FrozenModel):
            ...     name: str
            ...     p_value: float = Field(default=math.nan)
            ...     q_value: float = Field(default=math.nan)
            ...     is_significant: bool = False
            ...
            ...     @field_validator('p_value', 'q_value')
            ...     @classmethod
            ...     def validate_probability(cls, v: float) -> float:
            ...         if not math.isnan(v) and not (0.0 <= v <= 1.0):
            ...             raise ValueError(f'Probability must be in [0,1], got {v}')
            ...         return v
            ...
            ...     def __repr__(self) -> str:
            ...         sig = '✓' if self.is_significant else '✗'
            ...         return f"StatisticalTest('{self.name}', p={self.p_value:.4f}, {sig})"

        Risk profile model:
            >>> class DriverRiskProfile(FrozenModel):
            ...     driver_name: str
            ...     risk_score: float = Field(ge=0.0, le=100.0)
            ...     transaction_count: int = Field(ge=0)
            ...     no_eld_rate: float = Field(ge=0.0, le=1.0)
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
# NOT intended for statistical analysis models (those use FrozenModel directly).
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
