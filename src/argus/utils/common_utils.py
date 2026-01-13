# argus/utils/common_utils.py

import logging
import math
from typing import Any

import pandas as pd

__all__: list[str] = [
    'is_missing_like',
]

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)

_MISSING_STRING_PLACEHOLDERS: frozenset[str] = frozenset(
    {
        '',
        'N/A',
        'NA',
        'NULL',
        'NONE',
        'NAN',
        'INF',
        'INFINITY',
        '-INF',
        '-INFINITY',
        '+INF',
        '+INFINITY',
    }
)


def is_missing_like(value: Any) -> bool:
    """
    Determines if a value represents a 'missing' or 'null' state across multiple types.

    Checks handled:
    - NoneType
    - Strings: Empty, whitespace, or common placeholders ('N/A', 'NULL')
    - Floats: NaN and Infinity
    - Pandas/NumPy: NaT or other library-specific nulls

    Args:
        value (Any): The data point to evaluate.

    Returns:
        bool: True if the value is considered 'missing', False otherwise.
    """
    # Identify explicit None types immediately
    if value is None:
        return True

    # Booleans are never missing.
    # This prevents True/False from being treated as 1/0 or evaluated by pandas.
    if isinstance(value, bool):
        return False

    # Identify string-based placeholders common in CSV and API returns
    if isinstance(value, str):
        return value.strip().upper() in _MISSING_STRING_PLACEHOLDERS

    # Identify numeric edge cases for floating point numbers
    if isinstance(value, float):
        return math.isnan(value) or math.isinf(value)

    # Pandas handles pd.NA, pd.NaT, numpy scalars, etc.
    if pd.api.types.is_scalar(value):
        try:
            return bool(pd.isna(value))
        except (ValueError, TypeError) as exc:
            logger.debug('Non-scalar or incompatible type passed to pd.isna: %s', exc)

    return False
