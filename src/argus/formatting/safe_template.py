# argus/formatting/safe_template.py
"""
A safe and robust string template formatter. It enhances Python's built-in
`string.Formatter` to provide:
    1. Graceful handling of missing keys by inserting a "{MISSING:key}" marker
       instead of raising a KeyError.
    2. Intelligent coercion of string values to numeric types when the format
       specification requires numeric input (e.g., "{value:.2f}"). This allows
       strings like "1,200" or "95%" to be formatted as numbers without error.
    3. Clear error markers "{VALUE_FORMAT_ERROR:...}" when a value cannot be
       coerced to a numeric type.

Example usage:
    template = "Amount: {amount:.2f}, Rate: {rate:.1%}, Name: {name}"
    result = safe_format_template(
        template,
        amount="1,234.56",
        rate="95%",
        name="Sample"
    )
    # result -> "Amount: 1234.56, Rate: 95.0%, Name: Sample"
"""

import logging
import re
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from string import Formatter
from typing import Any, Literal

from argus.utils import is_missing_like

__all__: list[str] = ['safe_format_template']

# Set up the logger for this module.
logger: logging.Logger = logging.getLogger(__name__)

# A tuple of types that are considered "already numeric" and do not
# need any string-to-number coercion.
# Decimal is included as it's a valid high-precision numeric type.
# _NUMERIC_TYPES: tuple[type[int], type[float], type[Decimal]] = (int, float, Decimal)
numeric_types = int | float | Decimal

# These are the Python format-mini-language type codes that
# exclusively apply to numeric types.
_NUMERIC_TYPE_CODES: tuple[
    Literal['f'],
    Literal['F'],
    Literal['e'],
    Literal['E'],
    Literal['g'],
    Literal['G'],
    Literal['%'],
    Literal['d'],
    Literal['n'],
    Literal['b'],
    Literal['o'],
    Literal['x'],
    Literal['X'],
] = ('f', 'F', 'e', 'E', 'g', 'G', '%', 'd', 'n', 'b', 'o', 'x', 'X')

# Regex to extract only the parts that make sense for strings:
# [fill][align][sign][#][0][width][grouping][.precision][type]
# For strings, we will keep only fill+align+width.
_FORMAT_RE: re.Pattern[str] = re.compile(
    r"""
    (?P<fill>.)?(?P<align>[<>=^])?    # fill + align
    (?P<sign>[+\- ])?                # sign (numeric)
    (?P<alt>\#)?                     # alternate form (numeric)
    (?P<zero>0)?                     # zero padding (numeric)
    (?P<width>\d+)?                  # width
    (?P<group>[,_])?                 # grouping options (numeric)
    (?P<prec>\.\d+)?                 # precision (numeric type or max chars for 's')
    (?P<type>[bcdeEfFgGnosxX%])?     # type code
    """,
    re.VERBOSE,
)


class SafeFormatter(Formatter):
    """
    Formatter that:
      - Marks missing keys as {MISSING:name} instead of raising.
      - If a numeric spec is applied to a non-numeric/missing-like value,
        falls back to string formatting while preserving alignment/width.
    """

    def get_value(
        self, key: str | int, args: Sequence[Any], kwargs: Mapping[str, Any]
    ) -> Any:
        """
        Overrides the base method to fetch a value without raising KeyError.

        Args:
            key: The key (either an integer index for args or string for kwargs)
                 being requested by the format string.
            args: The positional arguments passed to .format().
            kwargs: The keyword arguments passed to .format().

        Returns:
            The corresponding value if found, or a descriptive error string
            if a KeyError occurs.
        """
        try:
            # Attempt to retrieve the value using the standard mechanism.
            return super().get_value(key, args, kwargs)
        except KeyError:
            # The key was not found in args or kwargs.
            logger.warning('Missing template variable: %r', key)
            # Return a machine-readable, descriptive marker.
            # The double-braces '{{' and '}}' are escaped to produce
            # literal '{' and '}' in the final string.
            return f'{{MISSING:{key}}}'

    def format_field(self, value: Any, format_spec: str) -> str:
        """
        Overrides the base method to format a single field, adding a fallback
        for numeric format specs applied to non-numeric string values.

        If a ValueError occurs (e.g., trying to apply a numeric format spec
        like '.2f' to a non-numeric string like 'N/A'), this will:
        1. Log a warning.
        2. Fall back to formatting the value as a plain string, but
           *attempts to preserve* any alignment/width from the original spec.
        """
        # If the value is "missing-like", always treat it as plain text.
        if is_missing_like(value) and _format_spec_requires_numeric(format_spec):
            safe_spec: str = _string_only_format_spec(format_spec)
            # Format the "missing" value (e.g., "N/A", "None") using the safe spec
            return super().format_field(str(value), safe_spec)

        try:
            # Normal path: let Python handle it.
            return super().format_field(value, format_spec)
        except ValueError as e:
            # Typical case: numeric spec applied to a string (e.g., 'N/A') or other non-numeric.
            wants_numeric: bool = _format_spec_requires_numeric(format_spec)
            if wants_numeric:
                logger.warning(
                    'Numeric format %r failed for value %r; '
                    'falling back to string (align/width preserved). Error: %s',
                    format_spec,
                    value,
                    e,
                )
                # Rebuild a spec that is valid for strings.
                safe_spec = _string_only_format_spec(format_spec)
                try:
                    return super().format_field(str(value), safe_spec)
                except ValueError:
                    # If even that fails, just return the raw string.
                    return super().format_field(str(value), '')
            # Not the case we are handling — re-raise.
            raise


def _format_spec_requires_numeric(format_spec: str) -> bool:
    """
    Determine whether a given format specifier implies numeric formatting.

    This function checks if the type code at the end of the format spec
    is one that Python reserves for numeric types.

    Examples that REQUIRE numeric inputs:
        - '.2f', ',.0f', '8.3g', '0.1e', '%', 'd', 'G', 'E'
    Examples that do NOT require numeric inputs:
        - 's' (string, the default)
        - '' (empty)
        - '<10' (alignment)
        - '.10' (precision, but on a string means truncation)

    Args:
        format_spec: The raw format spec string (e.g., '.2f', ',.1%').

    Returns:
        True if the spec implies numeric formatting; otherwise False.
    """
    if not format_spec:
        # An empty format spec is effectively string formatting.
        return False

    # The type code is *always* the last character of the spec,
    # optionally after alignment, sign, width, precision, etc.
    # We just need to check the very last non-whitespace character.
    stripped_spec: str = format_spec.strip()
    if not stripped_spec:
        return False

    return stripped_spec.endswith(_NUMERIC_TYPE_CODES)


def _string_only_format_spec(original_spec: str) -> str:
    """
    Build a safe format spec for strings by preserving only fill/align/width.
    This avoids ValueError from numeric-only flags like ',' or a numeric type code.
    """
    if not original_spec:
        return ''
    match: re.Match[str] | None = _FORMAT_RE.fullmatch(original_spec)
    if not match:
        # If parsing fails, safest is to drop to empty spec (plain string).
        return ''

    # Reconstruct a spec using only string-safe components
    fill: str | Any = match.group('fill') or ''
    align: str | Any = match.group('align') or ''
    width: str | Any = match.group('width') or ''

    # We also preserve precision, as it's valid for strings (truncation)
    precision: str | Any = match.group('prec') or ''

    return f'{fill}{align}{width}{precision}'


def _extract_top_level_field_name(field_expression: str) -> str:
    """
    Resolve a complex field expression to its top-level variable name.

    In a format string like "{records[0].amount:.2f}", the `field_expression`
    is "records[0].amount". This function finds the base variable name
    that is expected to be present in the `kwargs` dict, which is "records".

    Examples:
        - 'alpha' -> 'alpha'
        - 'alpha.value' -> 'alpha'
        - 'records[0].amount' -> 'records'

    Args:
        field_expression: The field expression extracted from the template.

    Returns:
        The top-level variable name to look up in kwargs.
    """
    if not field_expression:
        return field_expression

    # Find the first attribute access ('.') or index access ('[')
    # and take everything before it.
    base_variable_name: str = field_expression.split('.', 1)[0]
    base_variable_name = base_variable_name.split('[', 1)[0]

    return base_variable_name


def _coerce_string_to_number_if_possible(original_value: Any) -> Any:
    """
    Attempt to safely convert a string value to a numeric type (float).

    This function is designed to handle common "human-entered" numeric
    formats gracefully, which standard `float()` does not.

    Handles:
        - '1,234.56' (removes thousands separators)
        - '12%'      (interprets as 0.12)
        - '3e5'      (scientific notation)
        - '  42  '   (leading/trailing whitespace)

    If the value is already numeric (int/float/Decimal), it is returned unchanged.
    If the value is not a string, it is returned unchanged.
    If the value is a string that cannot be parsed as a number (e.g., "N/A"),
    it is returned unchanged, allowing it to be string-formatted.

    Args:
        original_value: The value to coerce if possible.

    Returns:
        A float if coercion succeeds; otherwise the original value.
    """
    # 1. Passthrough: If it's already a known numeric type, do nothing.
    if isinstance(original_value, numeric_types):
        return original_value

    # 2. Passthrough: If it's not a string, don't try to parse it.
    if not isinstance(original_value, str):
        return original_value

    # 3. Pre-process: Clean the string for parsing.
    candidate: str = original_value.strip()
    if candidate == '':
        # Treat empty strings as-is; don't convert to 0.
        return original_value

    # 4. Handle Percentages: Detect and strip a '%' sign for later.
    has_percent_suffix: bool = candidate.endswith('%')
    if has_percent_suffix:
        candidate = candidate[:-1].strip()  # Remove '%' and any new whitespace

    # 5. Handle Thousands Separators: Remove ','
    candidate = candidate.replace(',', '')

    # 6. Parse: Use Decimal for robust parsing.
    # We use Decimal because it avoids the precision pitfalls of float('0.1')
    # and handles scientific notation ('3e5') correctly.
    try:
        numeric_value = Decimal(candidate)

        # 7. Post-process: If it was a percentage, divide by 100.
        if has_percent_suffix:
            numeric_value: Decimal = numeric_value / Decimal(100)

        # 8. Return as float, as this is what format specs like 'f' expect.
        return float(numeric_value)

    except (InvalidOperation, ValueError):
        # The string was not a valid number (e.g., 'Chicago', 'N/A').
        # Return the original string so it can be formatted as such.
        return original_value


def _discover_fields_requiring_numeric(template: str) -> set[str]:
    """
    Inspect the template and identify all top-level variables that are
    used with a *numeric* format specification.

    This function parses the template (e.g., "{alpha:.2f}, {name:s}")
    and checks the format spec for each placeholder. It returns a set
    of the *base variable names* that require numeric values.

    For example, given:
        template = "Val: {alpha.value:.2f}, Rate: {rate:.1%}, Name: {name}"
    This function returns:
        {'alpha', 'rate'}
    ('name' is excluded because it uses the default string format).

    Args:
        template: The format template string.

    Returns:
        A set of top-level field names (as they appear in kwargs) that
        require numeric values to satisfy their format specs.
    """
    # Use our SafeFormatter to parse the template.
    formatter = SafeFormatter()
    fields_requiring_numeric: set[str] = set()

    # .parse() iterates through the template and yields a tuple for
    # each format field: (literal_text, field_name, format_spec, conversion)
    for _, field_name, format_spec, _ in formatter.parse(template):
        # field_name is None for literal text parts (e.g., "Hello ").
        if not field_name:
            continue

        # Check if the format spec (e.g., ".2f") implies a numeric type.
        # We must handle `format_spec` being None (for "{name}").
        if _format_spec_requires_numeric(format_spec or ''):
            # The field_name could be complex (e.g., "data[0].value").
            # We need the top-level key ("data").
            top_level_name: str = _extract_top_level_field_name(field_name)
            if top_level_name:
                fields_requiring_numeric.add(top_level_name)

    return fields_requiring_numeric


def safe_format_template(template: str, **kwargs: Any) -> str:
    """
    Safely format a template string with enhanced error handling.

    This function provides a robust formatting solution that:
      1. Prevents `KeyError` crashes by replacing missing variables with
         a "{MISSING:key}" marker (using `SafeFormatter`).
      2. Prevents `ValueError` crashes by intelligently coercing string
         values (e.g., "1,200", "95%") to numbers *only if* the template
         requests numeric formatting (e.g., "{val:.2f}", "{rate:.1%}").
      3. Returns a "{VALUE_FORMAT_ERROR:...}" marker if a value cannot
         be formatted as requested (e.g., formatting "N/A" as a number).

    Example usage:
        template = "Threshold: {alpha:.2f}, Confidence: {conf:.1%}, ID: {id}"

        # Coerces 'alpha' and 'conf', but leaves 'id' as a string:
        format_template(template, alpha="0.05", conf="95%", id="abc-123")
        # → "Threshold: 0.05, Confidence: 95.0%, ID: abc-123"

        # Handles missing key:
        format_template(template, alpha="0.05", id="abc-123")
        # → "Threshold: 0.05, Confidence: {MISSING:conf}, ID: abc-123"

        # Handles format mismatch:
        format_template(template, alpha="N/A", conf="95%", id="abc-123")
        # → "Threshold: {VALUE_FORMAT_ERROR: ...}, Confidence: 95.0%, ID: abc-123"

    Args:
        template: The format template string with {placeholders}.
        **kwargs: Keyword arguments providing values for placeholders.

    Returns:
        The formatted string, with error markers for any missing keys
        or type mismatches.
    """
    if not template:
        return ''

    # This is our custom formatter class that handles KeyErrors.
    safe_formatter = SafeFormatter()

    # === STEP 1: Discover which kwargs need to be numeric ===
    # Parse the template to find all top-level variable names that
    # are used with a numeric format spec (like ':.2f' or ':.1%').
    numeric_field_names: set[str] = _discover_fields_requiring_numeric(template)

    # === STEP 2: Selectively coerce arguments ===
    # Create a new dictionary, only attempting to convert values
    # for the keys we identified in Step 1.
    coerced_variables: dict[str, Any] = {}
    for variable_name, variable_value in kwargs.items():
        if variable_name in numeric_field_names:
            # This key is used with a numeric format. Attempt coercion.
            coerced_variables[variable_name] = _coerce_string_to_number_if_possible(
                variable_value
            )
        else:
            # This key is not used numerically; keep its original value.
            coerced_variables[variable_name] = variable_value

    # === STEP 3: Format with full error handling ===
    # Use the coerced variables and our SafeFormatter.
    try:
        # SafeFormatter.format handles KeyErrors internally.
        return safe_formatter.format(template, **coerced_variables)

    except ValueError as value_error:
        # This catches ValueErrors that coercion couldn't prevent.
        # Example: template demands {:.2f} but the value was "N/A",
        # which _coerce... returns as "N/A" (still a string).
        # The format() call then fails.
        logger.warning(
            'Template formatting ValueError: %s | template=%r | processed_kwargs=%r',
            value_error,
            template,
            coerced_variables,
        )
        # Return a clear, machine-searchable marker in the output.
        return f'{{VALUE_FORMAT_ERROR: {value_error}}}'
