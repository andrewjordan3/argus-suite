# argus/formatting/format_tools.py

import logging
import re
import unicodedata
from collections.abc import Iterable
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
from numpy.typing import NDArray

__all__: list[str] = [
    'format_duration_between_times',
    'format_entities_by_metric_for_month',
    'slugify',
]

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)

# --- Define Time Constants ---
SECONDS_IN_DAY: int = 86400  # 60 seconds * 60 minutes * 24 hours
SECONDS_IN_HOUR: int = 3600  # 60 seconds * 60 minutes
SECONDS_IN_MINUTE: int = 60

# ================================================================
# --- Precompiled regex patterns (module level for performance) ---
# ================================================================

# Treat common separators and Windows-invalid filename characters as separators.
#   - Whitespace (\s), underscore, forward/back slashes, colon, pipe, asterisk,
#     question mark, double quote, angle brackets
_SEPARATORS_PATTERN: re.Pattern[str] = re.compile(r'[\s_\/\\:|*?\"<>]+')

# Whitelist: keep only lowercase ASCII letters, digits, and dashes.
# (We will have already lowercased; this enforces a minimal, portable set.)
_ASCII_WHITElist_PATTERN: re.Pattern[str] = re.compile(r'[^a-z0-9-]+')

# Collapse any runs of multiple dashes into a single dash.
_MULTIDASH_PATTERN: re.Pattern[str] = re.compile(r'-{2,}')

# Windows reserved device names (case-insensitive). If the final slug equals
# one of these basenames, we suffix with "-file" to avoid issues on Windows.
_WINDOWS_RESERVED_BASENAMES: set[str] = {
    'con',
    'prn',
    'aux',
    'nul',
    'com1',
    'com2',
    'com3',
    'com4',
    'com5',
    'com6',
    'com7',
    'com8',
    'com9',
    'lpt1',
    'lpt2',
    'lpt3',
    'lpt4',
    'lpt5',
    'lpt6',
    'lpt7',
    'lpt8',
    'lpt9',
}


def format_entities_by_metric_for_month(
    unique_entities_by_group: pd.Series,
    target_month: Any,
    empty_token: str = '',
    surround_with_brackets: bool = True,
    sort_entities: bool = True,
) -> str:
    """
    Format a string: "{metric}: {list of entities}; {other_metric}: {list of entities}" for one month.

    Parameters
    ----------
    unique_entities_by_group : pd.Series
        MultiIndex Series with index levels ['month','metric'] and values = list of entity_ids.
        (Built with groupby(...).apply(list(...)).rename('entity_list'))
    target_month : Any
        Month key exactly matching the 'month' level (e.g., Period('2024-02','M') or a
        string if that's the index).
    empty_token : str
        What to display when a metric has no entities.
    surround_with_brackets : bool
        If True, wrap the entity list in square brackets for readability.
    sort_entities : bool
        If True, sort the deduplicated entities before joining.

    Returns
    -------
    str
        A single string like: "Metric A: [e1, e2]; Metric B: [—]"
    """

    # Ensure the month exists by extracting the level values
    months: pd.Index = unique_entities_by_group.index.get_level_values('month')

    # We check if 'equals' exists; if not, we default to None.
    equals_method: Any | None = getattr(months, 'equals', None)

    # If the method exists, we use it to check against an empty index.
    # If it doesn't exist, we fall through to the manual membership check.
    if equals_method is not None and equals_method(pd.Index([])):
        # Defensive: if months is an empty index, handle it
        if target_month not in list(months):
            return ''
    elif target_month not in months:
        # Standard check for membership in the Index
        return ''

    # Slice down to the month -> now a Series indexed by 'metric' with list values
    month_slice: pd.Series = unique_entities_by_group.xs(
        key=target_month, level='month'
    )

    def normalize_and_join(entity_iterable: Iterable[Any] | None) -> str:
        """Deduplicate, optionally sort, and join entity identifiers."""
        if entity_iterable is None:
            return empty_token

        # Convert to list (handles numpy arrays, sets, etc.)
        entity_list: list[Any] = list(entity_iterable)

        if len(entity_list) == 0:
            return empty_token

        # Deduplicate while preserving first-seen order
        # (pd.unique preserves order for 1D sequences)
        deduped_series: NDArray[Any] = pd.Series(entity_list).unique()

        # Optional sorting (convert to string so mixed types won't error)
        if sort_entities:
            deduped: list[str] = sorted(map(str, deduped_series))
        else:
            deduped = list(map(str, deduped_series))

        joined: str = ', '.join(deduped)
        return f'[{joined}]' if surround_with_brackets else joined

    parts: list[str] = [
        f'{metric}: {normalize_and_join(entity_list)}'
        for metric, entity_list in month_slice.items()
    ]

    # Join metric sections with semicolons for readability
    return '; '.join(parts)


# ================================================================
# Portable, and Safe `slugify` Implementation
# ----------------------------------------------------
# Goals:
#   1) Produce **filesystem-safe** slugs that are consistent across
#      Windows/macOS/Linux (avoid illegal characters and reserved names).
#   2) Ensure **predictability** by restricting output to ASCII
#      lowercase letters, digits, and single dashes (`-`).
#   3) Handle **edge cases** gracefully: None/empty input, emojis,
#      diacritics (e.g., “Québec”), sequences of separators, and very
#      long inputs.
#   4) Keep performance in mind by **precompiling** regex patterns.
#
# Design Notes:
#   • We normalize Unicode (NFKD), then encode to ASCII and drop
#     non-ASCII codepoints. This preserves human intent while avoiding
#     filesystem surprises.
#   • We treat a wide set of separators (whitespace, underscores,
#     slashes, Windows-invalid characters like : * ? " < > |) as
#     **equivalent separators** and collapse them to a single dash.
#   • We **whitelist** allowed characters (a-z, 0-9, -) instead of
#     blacklisting disallowed ones; whitelisting is safer and more
#     predictable.
#   • We avoid Windows **reserved device names** (e.g., `con`, `nul`,
#     `com1`, `lpt9`) by appending a suffix if the final slug equals
#     one of these names.
#   • We provide an `empty_token` fallback so the function never
#     returns an empty string.
# ================================================================


def slugify(
    input_value: Any,
    maximum_length: int = 40,
    empty_token: str = 'report-data-unknown',
    reserved_suffix: str = '-file',
) -> str:
    """
    Convert arbitrary input into a filesystem-safe, portable *slug*.

    The output is strictly ASCII lowercase with only the characters
    `[a-z0-9-]`, and with separators normalized to single dashes. This
    function aims to be robust across platforms and edge cases.

    Parameters
    ----------
    input_value : Any
        The value to slugify (e.g., a string like "Québec / Montréal" or even
        a number). Non-strings are converted via `str()`.
    maximum_length : int, optional (default=40)
        Maximum number of characters for the final slug. The function trims
        to this length *after* normalization. Trailing dashes are removed
        post-trim to avoid ending with a separator.
    empty_token : str, optional (default="report-data-unknown")
        Fallback value returned if the slug would otherwise be empty
        after cleaning (e.g., input is only emojis/punctuation).
    reserved_suffix : str, optional (default="-file")
        Suffix appended when the final slug is a Windows-reserved basename
        (e.g., "con" -> "con-file"). Use a leading dash so the slug stays
        within the `[a-z0-9-]` character set.

    Returns
    -------
    str
        A portable, ASCII-only slug safe for use in filenames and URLs.

    Rationale & Guarantees
    ----------------------
    • Unicode is normalized (NFKD) and non-ASCII is removed to avoid
      cross-platform surprises.
    • Separator runs collapse to a single dash for readability.
    • Only `[a-z0-9-]` remain for predictability and safety.
    • No leading/trailing dashes in the final result.
    • No empty string—`empty_token` is returned instead.
    • Windows-reserved names are avoided by suffixing with `reserved_suffix`.
    """
    # Convert to string and strip outer whitespace early to handle None,
    #    numbers, and other types gracefully.
    raw_text: str = '' if input_value is None else str(input_value)
    raw_text = raw_text.strip()
    if not raw_text:
        return empty_token

    # Normalize to NFKD and drop non-ASCII symbols. This removes diacritics
    #    (e.g., "Québec" -> "Quebec") and emojis, producing a plain ASCII base.
    #    We lower-case *after* ASCII conversion for consistency.
    normalized_text: str = (
        unicodedata.normalize('NFKD', raw_text)
        .encode('ascii', 'ignore')
        .decode('ascii')
    )

    # Lowercase for uniformity.
    normalized_text = normalized_text.lower()

    # Convert all recognized separators to a dash. This includes whitespace,
    #    underscores, slashes, and Windows-invalid characters like `:` `*` `?` etc.
    separator_normalized_text: str = _SEPARATORS_PATTERN.sub('-', normalized_text)

    # Remove any characters outside our strict ASCII whitelist.
    ascii_only_text: str = _ASCII_WHITElist_PATTERN.sub('', separator_normalized_text)

    # Collapse multiple dashes to a single dash and trim leading/trailing dashes.
    single_dash_text: str = _MULTIDASH_PATTERN.sub('-', ascii_only_text).strip('-')

    # If cleaning steps removed everything, return the safety token.
    if not single_dash_text:
        single_dash_text = empty_token

    # Enforce maximum length. After trimming, ensure we do not end with a dash.
    trimmed_text: str = single_dash_text[:maximum_length].strip('-')
    if not trimmed_text:
        trimmed_text = empty_token

    # Avoid Windows-reserved device names by suffixing a safe token.
    if trimmed_text in _WINDOWS_RESERVED_BASENAMES:
        trimmed_text = f'{trimmed_text}{reserved_suffix}'

    return trimmed_text.title()


def format_duration_between_times(start_time: datetime, end_time: datetime) -> str:
    """
    Calculates the duration between two datetime objects and formats it
    into a human-readable string, omitting zero-value components
    unless the total duration is zero.

    Examples:
    - start="2025-01-01 10:00:00", end="2025-01-02 12:03:04" -> "1 day 2 hrs 3 mins 4 secs"
    - start="2025-01-01 10:00:00", end="2025-01-03 10:05:00" -> "2 days 5 mins"
    - start="2025-01-01 10:00:00", end="2025-01-01 10:00:30" -> "30 secs"
    - start="2025-01-01 10:00:00", end="2025-01-01 10:00:00" -> "0 secs"
    - start="2025-01-01 10:00:30", end="2025-01-01 10:00:00" -> "0 secs" (handles negative)

    Args:
        start_time: The starting datetime object.
        end_time: The ending datetime object.

    Returns:
        A string representing the duration in a human-readable format.
    """

    # --- Calculate Timedelta ---
    # The first step is to get the timedelta object by subtracting
    # the start time from the end time.
    duration_delta: timedelta = end_time - start_time

    # --- Get Total Seconds ---
    # Get the total duration in seconds as an integer.
    # This truncates any fractional seconds (microseconds), which is
    # appropriate for this function's level of precision.
    total_seconds_int = int(duration_delta.total_seconds())

    # Handle edge cases for zero or negative durations immediately.
    if total_seconds_int < 1:
        return '0 secs'

    # --- Calculate Each Time Component ---
    # divmod() takes two numbers and returns a tuple of (quotient, remainder).
    # It's more efficient than doing division and modulo separately.

    # Calculate days and the remaining seconds
    days: int
    remainder_after_days: int
    days, remainder_after_days = divmod(total_seconds_int, SECONDS_IN_DAY)

    # From the remaining seconds, calculate hours and the new remainder
    hours: int
    remainder_after_hours: int
    hours, remainder_after_hours = divmod(remainder_after_days, SECONDS_IN_HOUR)

    # From that remainder, calculate minutes and the final seconds
    minutes: int
    seconds: int
    minutes, seconds = divmod(remainder_after_hours, SECONDS_IN_MINUTE)

    # --- Build the Output String ---
    # We define our values and labels in a structured way to allow for a
    # vectorized (Pythonic) approach using zip.
    time_values: list[int] = [days, hours, minutes, seconds]
    time_labels: list[str] = ['day', 'hr', 'min', 'sec']

    # Refined list comprehension:
    # 1. zip(time_labels, time_values) pairs units with their quantities.
    # 2. Filtering (if time_value > 0) removes units with zero duration.
    # 3. Pluralization logic: append 's' only if the value is not 1.
    duration_parts: list[str] = [
        f'{time_value} {time_label}{"s" if time_value != 1 else ""}'
        for time_label, time_value in zip(time_labels, time_values, strict=False)
        if time_value > 0
    ]

    # --- Return the Final String ---
    # Join all the collected parts with a single space.
    # e.g., ["1 day", "5 hrs"] -> "1 day 5 hrs"
    return ' '.join(duration_parts)
