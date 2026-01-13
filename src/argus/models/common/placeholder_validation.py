# argus/models/common/placeholder_validation.py
"""
Reusable validation utilities for format strings in locale/policy/config models.

Architecture Overview
=====================
This module provides type annotation factories (FormatStr and FormatStrList) that
ensure format strings contain required named placeholders. Placeholder requirements
are defined centrally in the Placeholders registry (placeholders.py), creating a
single source of truth that ties together:

    1. YAML locale files (contain the actual format strings)
    2. Python models (define structure and validation requirements)
    3. Application code (calls .format(**kwargs) with the placeholder values)

This architecture ensures that:
    - Translators know exactly which placeholders are required
    - All locales (including English) are validated at load time
    - Type checkers see clean types (str or list[str])
    - Changes to placeholder requirements are explicit and traceable

Key Components
==============
FormatStr
    Type annotation for single format strings. Validates that all required
    placeholders from the registry are present in the string.

FormatStrList
    Type annotation for lists of format strings where placeholders are
    distributed across items. Validates that all required placeholders
    appear somewhere in the combined list content.

extract_named_placeholders
    Utility function to parse placeholder names from a format string.
    Handles format specs ({value:.2f}), nested access ({user.name}),
    and the special policy. prefix ({policy.threshold} -> threshold).

Usage Examples
==============
Single format string::

    >>> from argus.models.common.placeholders import Placeholders as P
    >>> from argus.models.common.placeholder_validation import FormatStr
    >>>
    >>> class DataQualityMessages(BaseConfigModel):
    ...     missing_value_item: FormatStr[P.DataQualityMissingValueItem]
    ...     outlier_bounds: FormatStr[P.DataQualityOutlierBounds]

List of format strings::

    >>> from argus.models.common.placeholder_validation import FormatStrList
    >>>
    >>> class DriverAnalysis(BaseConfigModel):
    ...     transaction_items: FormatStrList[P.DriverTransactionItems]
    ...     risk_items: FormatStrList[P.DriverRiskItems]

The Placeholders registry defines what each annotation requires::

    >>> # In placeholders.py
    >>> class Placeholders:
    ...     DataQualityMissingValueItem: Final[frozenset[str]] = frozenset({
    ...         'column',      # str: Column name
    ...         'count',       # int: Number of missing values
    ...         'percentage',  # str: Formatted percentage
    ...     })

Design Decisions
================
Why frozenset for placeholder sets?
    Immutable, hashable, and set operations (difference, intersection) make
    validation logic clean. Order doesn't matter for validation.

Why support tuple and str in FormatStr?
    Convenience for simple cases. FormatStr['name'] and FormatStr['a', 'b']
    work without importing the registry. But FormatStr[P.SomeName] is preferred.

Why warn on extra placeholders instead of failing?
    Locale-specific additions may be intentional. The warning alerts developers
    to potential typos while not blocking valid translations. Users may see
    {placeholder} in output.

Why strip the policy. prefix?
    YAML authors can write {policy.threshold} to indicate the value comes from
    policy configuration. This improves readability for translators while
    keeping the validation simple (just check for 'threshold').
"""

import logging
import string
from collections.abc import Callable
from typing import Annotated, Any, Final

from pydantic import AfterValidator

__all__: list[str] = [
    'FormatStr',
    'FormatStrList',
]

# Module logger - follows project convention of per-module loggers
logger: logging.Logger = logging.getLogger(__name__)

# Namespace prefix stripped during placeholder extraction.
# Allows YAML authors to write {policy.threshold} for clarity while
# validating against just 'threshold'. This convention indicates
# the value is sourced from policy configuration.
_POLICY_PREFIX: Final[str] = 'policy'

# Maximum length of format string to include in warning messages.
# Prevents log spam from very long multi-line strings.
_MAX_VALUE_LENGTH_IN_LOGS: Final[int] = 100


# =============================================================================
# PLACEHOLDER EXTRACTION
# =============================================================================


def extract_named_placeholders(format_string: str) -> frozenset[str]:
    """
    Extract named placeholders from a Python format string.

    Uses Python's `string.Formatter` to properly parse format specifications,
    ensuring that complex format strings like `{value:.2f}` correctly extract
    `value` as the placeholder name (ignoring the format spec).

    Handles several special cases:
        - Format specs: `{amount:.2f}` extracts `amount`
        - Nested access: `{user.name}` extracts `user` (the base kwarg key)
        - Index access: `{items[0]}` extracts `items`
        - Policy prefix: `{policy.threshold}` extracts `threshold`

    The policy prefix stripping allows YAML authors to mark policy-sourced
    values for translator clarity while keeping validation simple.

    Args:
        format_string: A Python format string, e.g., "Avg {value:.2f} for {name}".
            May contain any valid Python format syntax.

    Returns:
        A frozenset of placeholder field names found in the string.
        Returns an empty frozenset if no placeholders are present.

    Raises:
        ValueError: If the format string contains invalid syntax that cannot
            be parsed by Python's string.Formatter.

    Examples:
        Basic placeholders::

            >>> extract_named_placeholders("Hello {name}, you have {count} messages")
            frozenset({'name', 'count'})

        With format specifications::

            >>> extract_named_placeholders("Value: {amount:.2f} ({pct:.1%})")
            frozenset({'amount', 'pct'})

        Policy prefix stripping::

            >>> extract_named_placeholders("Threshold: {policy.threshold}")
            frozenset({'threshold'})

        Nested attribute access (only base name extracted)::

            >>> extract_named_placeholders("User: {user.profile.name}")
            frozenset({'user'})

        No placeholders::

            >>> extract_named_placeholders("Just plain text")
            frozenset()
    """
    formatter = string.Formatter()
    extracted_placeholder_names: set[str] = set()

    try:
        # formatter.parse() yields tuples of:
        # (literal_text, field_name, format_spec, conversion)
        # We only care about field_name for placeholder extraction.
        for (
            _literal_text,
            field_name,
            _format_spec,
            _conversion,
        ) in formatter.parse(format_string):
            if field_name is None:
                # This segment is literal text with no placeholder
                continue

            # Handle policy prefix: {policy.threshold} -> threshold
            # This allows YAML authors to indicate policy-sourced values
            # while keeping the validation simple.
            field_name_without_prefix: str = field_name
            policy_prefix_with_dot: str = f'{_POLICY_PREFIX}.'

            if field_name.startswith(policy_prefix_with_dot):
                field_name_without_prefix = field_name[len(policy_prefix_with_dot) :]

            # Extract base field name from nested access patterns.
            # {user.name} -> user (the kwarg key that must be passed)
            # {items[0]} -> items
            # {stats.mean:.2f} -> stats
            base_field_name: str = (
                field_name_without_prefix.split('.', maxsplit=1)[0]
                .split('[', maxsplit=1)[0]
                .strip()
            )

            if base_field_name:
                extracted_placeholder_names.add(base_field_name)

    except ValueError as format_parsing_error:
        # string.Formatter raises ValueError for malformed format strings
        # e.g., unclosed braces, invalid field names
        logger.debug(
            'Failed to parse format string: %r - %s',
            format_string[:_MAX_VALUE_LENGTH_IN_LOGS],
            format_parsing_error,
        )
        raise ValueError(
            f'Invalid Python format string: {format_parsing_error}'
        ) from format_parsing_error

    return frozenset(extracted_placeholder_names)


# =============================================================================
# INPUT NORMALIZATION
# =============================================================================


def _normalize_placeholder_input(
    placeholders: frozenset[str] | tuple[str, ...] | str,
    *,
    source_class_name: str,
) -> frozenset[str]:
    """
    Normalize placeholder input to a validated frozenset.

    Accepts multiple input formats for developer convenience:
        - frozenset[str]: Preferred, from Placeholders registry
        - tuple[str, ...]: Legacy support, inline definitions
        - str: Single placeholder convenience

    All placeholder names are validated to be valid Python identifiers,
    ensuring they can be used as keyword arguments in .format() calls.

    Args:
        placeholders: The placeholder specification to normalize. Can be:
            - A frozenset of placeholder names (preferred)
            - A tuple of placeholder name strings
            - A single placeholder name string
        source_class_name: Name of the calling class (FormatStr or FormatStrList)
            for error messages.

    Returns:
        A frozenset containing the validated placeholder names.

    Raises:
        TypeError: If placeholders is not a frozenset, tuple, or str.
        ValueError: If placeholders is empty or contains invalid identifiers.

    Examples:
        From registry (preferred)::

            >>> _normalize_placeholder_input(
            ...     frozenset({'column', 'count'}),
            ...     source_class_name='FormatStr'
            ... )
            frozenset({'column', 'count'})

        Single string::

            >>> _normalize_placeholder_input('name', source_class_name='FormatStr')
            frozenset({'name'})

        Tuple of strings::

            >>> _normalize_placeholder_input(
            ...     ('first', 'second'),
            ...     source_class_name='FormatStr'
            ... )
            frozenset({'first', 'second'})
    """
    # Convert input to frozenset based on type
    normalized_placeholders: frozenset[str]

    if isinstance(placeholders, frozenset):
        # Preferred: directly from Placeholders registry
        normalized_placeholders = placeholders

    elif isinstance(placeholders, str):
        # Convenience: single placeholder as string
        normalized_placeholders = frozenset({placeholders})

    else:
        # Legacy support: tuple of placeholder strings
        normalized_placeholders = frozenset(placeholders)

    # Validate non-empty
    if not normalized_placeholders:
        raise ValueError(
            f'{source_class_name} requires at least one placeholder name. '
            f'Use plain `str` or `list[str]` if no placeholders are required.'
        )

    # Validate each placeholder is a valid Python identifier
    # This ensures they can be used as keyword arguments in .format(**kwargs)
    for placeholder_name in normalized_placeholders:
        if not placeholder_name.isidentifier():
            raise ValueError(
                f'Invalid placeholder name: {placeholder_name!r}. '
                f'Placeholder names must be valid Python identifiers '
                f'(letters, digits, underscores; cannot start with digit).'
            )

    logger.debug(
        '%s: Normalized placeholders: {%s}',
        source_class_name,
        ', '.join(sorted(normalized_placeholders)),
    )

    return normalized_placeholders


# =============================================================================
# CORE VALIDATION LOGIC
# =============================================================================


def _validate_placeholders_core(
    format_value: str | list[str],
    required_placeholders: frozenset[str],
) -> None:
    """
    Core validation logic for placeholder checking.

    Validates that all required placeholders exist in the format string(s).
    For lists, validates against the combined content of all items —
    individual item placement doesn't matter, only that all required
    placeholders appear somewhere.

    Logs a warning (but does not fail) if extra placeholders are found.
    This accommodates locale-specific additions while alerting to potential typos.

    Args:
        format_value: Single format string or list of format strings to validate.
        required_placeholders: Set of placeholder names that must be present.

    Raises:
        ValueError: If any required placeholders are missing, or if the
            format string contains invalid syntax.

    Side Effects:
        Logs WARNING if extra (unexpected) placeholders are found.
        Logs DEBUG with validation details.
    """
    # Combine list items for validation - placeholder distribution doesn't matter
    combined_format_string: str
    if isinstance(format_value, list):
        combined_format_string = '\n'.join(format_value)
    else:
        combined_format_string = format_value

    # Extract placeholders from the format string(s)
    # This may raise ValueError for invalid format syntax
    found_placeholders: frozenset[str] = extract_named_placeholders(
        combined_format_string
    )

    # Check for missing required placeholders
    missing_placeholders: frozenset[str] = required_placeholders - found_placeholders

    if missing_placeholders:
        missing_sorted: str = ', '.join(sorted(missing_placeholders))
        found_sorted: str = ', '.join(sorted(found_placeholders)) or '(none)'

        # Truncate value for error message readability
        truncated_value: str = combined_format_string
        if len(truncated_value) > _MAX_VALUE_LENGTH_IN_LOGS:
            truncated_value = truncated_value[:_MAX_VALUE_LENGTH_IN_LOGS] + '...'

        raise ValueError(
            f'Format string is missing required placeholders: {{{missing_sorted}}}. '
            f'Found: {{{found_sorted}}}. '
            f'Value: {truncated_value!r}'
        )

    # Warn about extra placeholders (don't fail - may be intentional)
    extra_placeholders: frozenset[str] = found_placeholders - required_placeholders

    if extra_placeholders:
        extra_sorted: str = ', '.join(sorted(extra_placeholders))
        required_sorted: str = ', '.join(sorted(required_placeholders))

        # Truncate value for log message readability
        truncated_value: str = combined_format_string
        if len(truncated_value) > _MAX_VALUE_LENGTH_IN_LOGS:
            truncated_value = truncated_value[:_MAX_VALUE_LENGTH_IN_LOGS] + '...'

        logger.warning(
            'Format string contains unexpected placeholders: {%s}. '
            'Expected only: {%s}. '
            'This may indicate a typo or locale-specific addition. '
            'Value: %r',
            extra_sorted,
            required_sorted,
            truncated_value,
        )

    logger.debug(
        'Placeholder validation passed. Required: {%s}, Found: {%s}',
        ', '.join(sorted(required_placeholders)),
        ', '.join(sorted(found_placeholders)),
    )


# =============================================================================
# VALIDATOR FACTORIES
# =============================================================================


def _create_str_placeholder_validator(
    required_placeholders: frozenset[str],
) -> Callable[[str], str]:
    """
    Create a Pydantic validator function for single format strings.

    Returns a closure that captures the required placeholders and validates
    any string value against them. Used by FormatStr to create the
    AfterValidator for Pydantic's Annotated type.

    Args:
        required_placeholders: Set of placeholder names that must be present
            in the format string.

    Returns:
        A validator function with signature (str) -> str that:
            - Validates required placeholders are present
            - Warns about extra placeholders
            - Returns the original string unchanged if valid
            - Raises ValueError if validation fails
    """

    def validate_str_placeholders(value: str) -> str:
        """
        Validate that a single format string contains required placeholders.

        Args:
            value: The format string to validate.

        Returns:
            The original string unchanged if validation passes.

        Raises:
            ValueError: If required placeholders are missing or syntax is invalid.
        """
        _validate_placeholders_core(value, required_placeholders)
        return value

    return validate_str_placeholders


def _create_list_placeholder_validator(
    required_placeholders: frozenset[str],
) -> Callable[[list[str]], list[str]]:
    """
    Create a Pydantic validator function for lists of format strings.

    Returns a closure that captures the required placeholders and validates
    a list of strings against them. Placeholders may be distributed across
    list items — only the combined content is validated.

    Args:
        required_placeholders: Set of placeholder names that must be present
            somewhere across all list items combined.

    Returns:
        A validator function with signature (list[str]) -> list[str] that:
            - Validates the list is non-empty
            - Validates required placeholders are present in combined content
            - Warns about extra placeholders
            - Returns the original list unchanged if valid
            - Raises ValueError if validation fails
    """

    def validate_list_placeholders(value: list[str]) -> list[str]:
        """
        Validate that a list of format strings contains required placeholders.

        Placeholders may be distributed across items — individual placement
        doesn't matter. This allows translators to reorder or restructure
        list items while maintaining all required placeholders.

        Args:
            value: List of format strings to validate.

        Returns:
            The original list unchanged if validation passes.

        Raises:
            ValueError: If list is empty, required placeholders are missing,
                or any item contains invalid format syntax.
        """
        if not value:
            required_sorted: str = ', '.join(sorted(required_placeholders))
            raise ValueError(
                f'Format string list cannot be empty. '
                f'Expected placeholders: {{{required_sorted}}}'
            )

        _validate_placeholders_core(value, required_placeholders)
        return value

    return validate_list_placeholders


# =============================================================================
# TYPE ANNOTATION CLASSES
# =============================================================================


class FormatStr:
    """
    Type annotation for strings that must contain required format placeholders.

    Creates a Pydantic-compatible Annotated[str, ...] type that validates
    the string contains all specified placeholder names at model instantiation.
    Properly handles format specifications (e.g., `{value:.3f}` validates as
    having `value`).

    Placeholder requirements should be defined in the central Placeholders
    registry and referenced by name. This ensures:
        - Type checkers see valid identifiers (no red squiggles)
        - Single source of truth for placeholder requirements
        - Self-documenting code via descriptive placeholder set names
        - Translators have clear reference documentation

    The `policy.` prefix in format strings is automatically stripped during
    validation, so `{policy.threshold}` satisfies a requirement for `threshold`.
    This allows YAML authors to mark policy-sourced values for translator clarity.

    Args:
        placeholders: Placeholder specification, one of:
            - frozenset[str]: Preferred, from Placeholders registry
            - tuple[str, ...]: Inline tuple of placeholder names
            - str: Single placeholder name

    Returns:
        An Annotated[str, AfterValidator(...)] type suitable for use
        as a Pydantic model field annotation.

    Raises:
        TypeError: At class definition time if placeholders is not a valid type.
        ValueError: At class definition time if placeholders is empty or
            contains invalid Python identifiers.
        ValueError: At model instantiation time if the format string is missing
            required placeholders or contains invalid format syntax.

    Examples:
        Using Placeholders registry (preferred)::

            >>> from argus.models.common.placeholders import Placeholders as P
            >>>
            >>> class RiskRatioLocale(BaseConfigModel):
            ...     description: FormatStr[P.RiskRatioDescription]
            ...     value: FormatStr[P.RiskRatioValue]
            ...     thresholds: FormatStr[P.RiskRatioThresholds]

        Using inline tuple (legacy support)::

            >>> class SimpleLocale(BaseConfigModel):
            ...     greeting: FormatStr['name', 'title']

        Using single string::

            >>> class MinimalLocale(BaseConfigModel):
            ...     count_message: FormatStr['count']

        Validation at instantiation::

            >>> locale = RiskRatioLocale(
            ...     description="Likelihood at {target_location} vs others.",
            ...     value="RR: {risk_ratio} — {interpretation}",
            ...     thresholds="Substantial > {threshold_substantial}",
            ... )

    Note:
        Static type checkers will see fields annotated with FormatStr[...]
        as `str`, which is correct for downstream usage.
    """

    def __class_getitem__(
        cls,
        placeholders: frozenset[str] | tuple[str, ...] | str,
    ) -> Any:
        """
        Create an Annotated[str, ...] type with placeholder validation.

        This method is called when using FormatStr[...] syntax in type
        annotations. It creates the appropriate Pydantic-compatible type.

        Args:
            placeholders: Placeholder specification (frozenset, tuple, or str).

        Returns:
            Annotated[str, AfterValidator(...)] type for Pydantic validation.

        Raises:
            TypeError: If placeholders is not a valid type.
            ValueError: If placeholders is empty or contains invalid identifiers.
        """
        required_placeholder_set: frozenset[str] = _normalize_placeholder_input(
            placeholders,
            source_class_name='FormatStr',
        )

        placeholder_validator: Callable[[str], str] = _create_str_placeholder_validator(
            required_placeholder_set
        )

        logger.debug(
            'FormatStr: Created validator for placeholders: {%s}',
            ', '.join(sorted(required_placeholder_set)),
        )

        return Annotated[str, AfterValidator(placeholder_validator)]


class FormatStrList:
    """
    Type annotation for lists of format strings with distributed placeholders.

    Creates a Pydantic-compatible Annotated[list[str], ...] type that validates
    the required placeholders appear somewhere across all list items combined.
    Individual item placement doesn't matter — translators may reorder or
    restructure list items as needed for their language.

    This is useful for YAML structures like::

        transaction_items:
          - "• Total Transactions: {transaction_count}"
          - "• Total Cost: {total_cost}"
          - "• Average Cost: {avg_cost}"

    Where the items form a logical unit and all placeholders must be present,
    but the order may vary by locale.

    Placeholder requirements should be defined in the central Placeholders
    registry as a frozenset containing all placeholders that must appear
    across the list.

    Args:
        placeholders: A frozenset of placeholder names from the Placeholders
            registry. All names must appear somewhere across the list items.

    Returns:
        An Annotated[list[str], AfterValidator(...)] type suitable for use
        as a Pydantic model field annotation.

    Raises:
        TypeError: At class definition time if placeholders is not a frozenset.
        ValueError: At class definition time if placeholders is empty.
        ValueError: At model instantiation time if the list is empty, required
            placeholders are missing, or any item has invalid format syntax.

    Examples:
        Registry definition::

            >>> # In placeholders.py
            >>> class Placeholders:
            ...     DriverTransactionItems: Final[frozenset[str]] = frozenset({
            ...         'transaction_count',
            ...         'total_cost',
            ...         'avg_cost',
            ...         'unique_vehicles',
            ...     })

        Model usage::

            >>> from argus.models.common.placeholders import Placeholders as P
            >>>
            >>> class DriverAnalysis(BaseConfigModel):
            ...     transaction_items: FormatStrList[P.DriverTransactionItems]
            ...     risk_items: FormatStrList[P.DriverRiskItems]

        Validation at instantiation::

            >>> locale = DriverAnalysis(
            ...     transaction_items=[
            ...         "• Transactions: {transaction_count}",
            ...         "• Total: {total_cost} | Avg: {avg_cost}",
            ...         "• Vehicles: {unique_vehicles}",
            ...     ],
            ...     risk_items=[...],
            ... )

    Note:
        Static type checkers will see fields annotated with FormatStrList[...]
        as `list[str]`, which is correct for downstream usage.

    Note:
        Unlike FormatStr, FormatStrList only accepts frozenset input.
        This encourages using the Placeholders registry for list definitions,
        which is important since lists typically have more complex placeholder
        requirements that benefit from central documentation.
    """

    def __class_getitem__(
        cls,
        placeholders: frozenset[str],
    ) -> Any:
        """
        Create an Annotated[list[str], ...] type with placeholder validation.

        This method is called when using FormatStrList[...] syntax in type
        annotations. It creates the appropriate Pydantic-compatible type.

        Args:
            placeholders: A frozenset of placeholder names that must appear
                across the list items combined.

        Returns:
            Annotated[list[str], AfterValidator(...)] type for Pydantic validation.

        Raises:
            TypeError: If placeholders is not a frozenset.
            ValueError: If placeholders is empty.
        """
        # Validate all placeholder names are valid identifiers
        required_placeholder_set: frozenset[str] = _normalize_placeholder_input(
            placeholders,
            source_class_name='FormatStrList',
        )

        placeholder_validator: Callable[[list[str]], list[str]] = (
            _create_list_placeholder_validator(required_placeholder_set)
        )

        logger.debug(
            'FormatStrList: Created validator for placeholders: {%s}',
            ', '.join(sorted(required_placeholder_set)),
        )

        return Annotated[list[str], AfterValidator(placeholder_validator)]
