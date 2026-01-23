# argus/formatting/effect_size_mapping.py
"""
Provides a canonical, config-driven mapping between user-facing effect size
display labels and internal snake_case identifiers.

This module enables localization by reading display labels from YAML config
rather than hardcoding English strings. The internal keys remain stable
identifiers used throughout the codebase.

Architecture:
-------------
    YAML Config (localized labels)
           │
           ▼
    EffectSizeConfig (Pydantic validation)
           │
           ▼
    EffectSizeLabelRegistry (bidirectional lookup)
           │
           ▼
    EffectSize Enum (type-safe internal representation)

Usage Example:
--------------
    >>> from config import load_config
    >>> from effect_size_mapping import EffectSize, EffectSizeLabelRegistry
    >>>
    >>> config = load_config("config.yaml")
    >>> registry = EffectSizeLabelRegistry.from_config(config)
    >>>
    >>> # User selects "Cliff's Delta"
    >>> user_selection = "Cliff's Delta"
    >>> effect = registry.from_label(user_selection)
    >>> print(effect.internal_key)  # 'cliffs_delta'
    >>>
    >>> # Generate localized label for display
    >>> print(registry.to_label(EffectSize.COHENS_D))  # "Cohen's d" (or localized)
"""

import logging
from enum import Enum
from typing import Final, Self

from argus.models.locale import (
    StatisticalMethodologyNonParametricCliffsDelta,
    StatisticalMethodologyNonParametricCohensD,
    StatisticalMethodologyNonParametricTests,
)

__all__: list[str] = [
    'EffectSize',
    'EffectSizeLabelRegistry',
]

# Type alias for effect size metric configs that have a .label attribute.
# Used for type narrowing when iterating over config attributes.
EffectSizeMetricConfig = (
    StatisticalMethodologyNonParametricCliffsDelta
    | StatisticalMethodologyNonParametricCohensD
)

# =============================================================================
# Module-Level Logger Configuration
# =============================================================================
logger: logging.Logger = logging.getLogger(__name__)


# =============================================================================
# Effect Size Enumeration
# =============================================================================
class EffectSize(str, Enum):
    """
    Enumeration of supported effect size metrics.

    Inherits from `str` to allow direct string comparison and serialization
    while retaining Enum benefits (identity, exhaustive matching, iteration).

    The Enum values are stable internal keys that never change, regardless
    of localization. Use `EffectSizeLabelRegistry` to convert between
    these internal keys and localized display labels.

    Members
    -------
    CLIFFS_DELTA : str
        Cliff's Delta - a non-parametric effect size measure for ordinal data.

    COHENS_D : str
        Cohen's d - a parametric effect size measuring standardized mean difference.
    """

    CLIFFS_DELTA = 'cliffs_delta'
    COHENS_D = 'cohens_d'

    @property
    def internal_key(self) -> str:
        """
        Return the canonical internal key for this effect size.

        Returns:
            The internal snake_case identifier (e.g., 'cliffs_delta').
        """
        return self.value


# Canonical list of all valid internal keys.
# Used for validation to ensure config provides labels for every key.
_ALL_EFFECT_SIZE_KEYS: Final[tuple[str, ...]] = tuple(
    member.internal_key for member in EffectSize
)


# =============================================================================
# Label Registry: Config-Driven Bidirectional Mapping
# =============================================================================
class EffectSizeLabelRegistry:
    """
    Manages bidirectional mapping between localized labels and EffectSize enums.

    This registry is initialized from configuration, allowing labels to be
    localized without changing any code. The internal keys remain stable
    identifiers used throughout the application.

    Thread Safety:
    --------------
    This class is immutable after construction and safe for concurrent access.

    Attributes
    ----------
    _label_to_enum : dict[str, EffectSize]
        Maps localized display labels to Enum members.

    _enum_to_label : dict[EffectSize, str]
        Maps Enum members to localized display labels.

    _config_section : EffectSizeConfigSection
        Reference to the parsed configuration (for accessing descriptions, etc.)

    Examples
    --------
    >>> registry = EffectSizeLabelRegistry.from_config(config)
    >>> effect = registry.from_label("Cliff's Delta")
    >>> effect
    <EffectSize.CLIFFS_DELTA: 'cliffs_delta'>
    >>> registry.to_label(EffectSize.COHENS_D)
    "Cohen's d"
    """

    __slots__ = ('_config_section', '_enum_to_label', '_label_to_enum')

    def __init__(
        self,
        label_to_enum_mapping: dict[str, EffectSize],
        enum_to_label_mapping: dict[EffectSize, str],
        config_section: StatisticalMethodologyNonParametricTests,
    ) -> None:
        """
        Initialize the registry with pre-built mappings.

        Prefer using the `from_config` factory method instead of direct
        instantiation to ensure proper validation.

        Args:
            label_to_enum_mapping: Forward lookup (label -> enum).
            enum_to_label_mapping: Reverse lookup (enum -> label).
            config_section: The parsed configuration section.
        """
        self._label_to_enum: dict[str, EffectSize] = label_to_enum_mapping
        self._enum_to_label: dict[EffectSize, str] = enum_to_label_mapping
        self._config_section: StatisticalMethodologyNonParametricTests = config_section

        logger.debug(
            'EffectSizeLabelRegistry initialized with %d mappings: %s',
            len(self._label_to_enum),
            list(self._label_to_enum.keys()),
        )

    @classmethod
    def from_config(
        cls, config_section: StatisticalMethodologyNonParametricTests
    ) -> Self:
        """
        Factory method to build the registry from parsed configuration.

        This method validates that the configuration provides labels for
        all known effect size metrics and builds the bidirectional mappings.

        Args:
            config_section: The parsed `StatisticalMethodologyNonParametricTests` from YAML.

        Returns:
            A fully initialized `EffectSizeLabelRegistry`.

        Raises:
            ValueError: If any required effect size key is missing from config,
                or if duplicate labels are detected (which would break lookups).

        Examples
        --------
        >>> from config import load_config
        >>> config = load_config("config.yaml")
        >>> registry = EffectSizeLabelRegistry.from_config(
        ...     config.statistical_methodology.non_parametric_tests
        ... )
        """
        logger.info('Building EffectSizeLabelRegistry from configuration')

        label_to_enum_mapping: dict[str, EffectSize] = {}
        enum_to_label_mapping: dict[EffectSize, str] = {}

        # Track labels to detect duplicates (which would break reverse lookup).
        seen_labels: set[str] = set()

        # Iterate over all known effect size keys and build mappings.
        effect_size_key: str
        for effect_size_key in _ALL_EFFECT_SIZE_KEYS:
            # Retrieve the metric config for this key.
            metric_config: EffectSizeMetricConfig = getattr(
                config_section, effect_size_key
            )
            localized_label: str = metric_config.label

            # Check for duplicate labels (would cause ambiguous lookups).
            if localized_label in seen_labels:
                logger.error(
                    'Duplicate effect size label detected: %r. '
                    'Each effect size must have a unique label.',
                    localized_label,
                )
                raise ValueError(
                    f'Duplicate effect size label: {localized_label!r}. '
                    'Labels must be unique across all effect size metrics.'
                )
            seen_labels.add(localized_label)

            # Convert the internal key to the corresponding Enum member.
            effect_size_enum: EffectSize = EffectSize(effect_size_key)

            # Build both directions of the mapping.
            label_to_enum_mapping[localized_label] = effect_size_enum
            enum_to_label_mapping[effect_size_enum] = localized_label

            logger.debug(
                'Registered mapping: %r <-> %s',
                localized_label,
                effect_size_enum.name,
            )

        # Validate completeness: ensure every Enum member has a mapping.
        missing_enums: set[EffectSize] = set(EffectSize) - set(
            enum_to_label_mapping.keys()
        )
        if missing_enums:
            missing_keys: list[str] = [e.internal_key for e in missing_enums]
            logger.error(
                'Configuration is missing labels for effect sizes: %s',
                missing_keys,
            )
            raise ValueError(
                f'Configuration missing labels for: {missing_keys}. '
                'Ensure all effect size keys have corresponding config entries.'
            )

        logger.info(
            'EffectSizeLabelRegistry built successfully with labels: %s',
            list(label_to_enum_mapping.keys()),
        )

        return cls(
            label_to_enum_mapping=label_to_enum_mapping,
            enum_to_label_mapping=enum_to_label_mapping,
            config_section=config_section,
        )

    def from_label(self, label: str) -> EffectSize:
        """
        Convert a localized display label to the corresponding EffectSize enum.

        This is the primary entry point for user input (UI selections, API
        parameters) into the type-safe internal representation.

        Args:
            label: The localized display label to look up.

        Returns:
            The corresponding `EffectSize` enum member.

        Raises:
            ValueError: If the label is not recognized. The error message
                includes valid options to help users correct their input.

        Examples
        --------
        >>> registry.from_label("Cliff's Delta")
        <EffectSize.CLIFFS_DELTA: 'cliffs_delta'>
        """
        logger.debug('Looking up effect size for label: %r', label)

        effect_size_enum: EffectSize | None = self._label_to_enum.get(label)

        if effect_size_enum is None:
            valid_labels: list[str] = list(self._label_to_enum.keys())
            logger.error(
                'Unrecognized effect size label: %r. Valid labels: %s',
                label,
                valid_labels,
            )
            raise ValueError(
                f'Unrecognized effect size label: {label!r}. '
                f'Valid options: {valid_labels}'
            )

        logger.debug('Resolved label %r -> %s', label, effect_size_enum.name)
        return effect_size_enum

    def to_label(self, effect_size: EffectSize) -> str:
        """
        Get the localized display label for an EffectSize enum.

        Use this when generating user-facing output (UI labels, reports,
        error messages) to ensure proper localization.

        Args:
            effect_size: The enum member to look up.

        Returns:
            The localized display label string.

        Examples
        --------
        >>> registry.to_label(EffectSize.COHENS_D)
        "Cohen's d"
        """
        # Direct dict lookup - all Enum members are guaranteed to have entries
        # due to validation in from_config().
        localized_label: str = self._enum_to_label[effect_size]
        logger.debug('Resolved %s -> label %r', effect_size.name, localized_label)
        return localized_label
