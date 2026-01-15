# argus/models/locale/locale_settings.py
"""
============================================================================
LOCALE SETTINGS
============================================================================
Language-specific formatting preferences for numbers, currency, dates, and
report layout. These settings control how values are displayed in reports
and do not contain business logic or thresholds.
============================================================================
"""

from pydantic import Field

from argus.models.common import FrozenModel

__all__: list[str] = ['LocaleSettings']


class LocaleSettings(FrozenModel):
    """
    Locale-specific formatting preferences for report display.

    This model defines how numbers, currency, dates, and other values are
    formatted in reports. It does not contain business rules or thresholds,
    only display formatting preferences.

    Attributes:
        language_code: ISO language-region code (e.g., "en-US")
        language_name: Human-readable language name
        thousands_separator: Character for thousands grouping (e.g., ",")
        decimal_separator: Character for decimal point (e.g., ".")
        number_decimals: Default decimal places for generic numbers
        currency_symbol: Symbol for monetary values (e.g., "$")
        currency_position: Position of currency symbol ("before" or "after")
        currency_decimals: Decimal places for currency display
        percentage_decimals: Decimal places for percentages
        percentage_symbol: Symbol for percentages (typically "%")
        p_value_decimals: Decimal places for p-values
        effect_size_decimals: Decimal places for effect sizes
        confidence_interval_decimals: Decimal places for confidence intervals
        date_format: strftime format for dates
        datetime_format: strftime format for datetimes
        month_format: strftime format for month grouping
        output_width: Character width for report sections
    """

    language_code: str = Field(
        description='ISO language-region code (e.g., "en-US", "es-MX")'
    )
    language_name: str = Field(
        description='Human-readable language name (e.g., "English (US)")'
    )

    # Number formatting
    thousands_separator: str = Field(
        max_length=1,
        description="Character to separate thousands (typically ',' or ' ')",
    )
    decimal_separator: str = Field(
        max_length=1,
        description="Character for decimal point (typically '.' or ',')",
    )
    number_decimals: int = Field(
        ge=0, le=10, description='Default decimal places for generic numbers'
    )

    # Currency formatting
    currency_symbol: str = Field(
        max_length=3, description="Currency symbol (e.g., '$', '€', '£')"
    )
    currency_position: str = Field(
        pattern=r'^(before|after)$',
        description='Position of currency symbol: "before" ($100) or "after" (100$)',
    )
    currency_decimals: int = Field(
        ge=0, le=4, description='Decimal places for currency display'
    )

    # Percentage formatting
    percentage_decimals: int = Field(
        ge=0, le=4, description='Decimal places for percentage display'
    )
    percentage_symbol: str = Field(
        max_length=2, description='Symbol for percentages (typically "%")'
    )

    # Statistical value formatting
    p_value_decimals: int = Field(
        ge=2, le=5, description='Decimal places for p-values (3 recommended)'
    )
    effect_size_decimals: int = Field(
        ge=2, le=5, description='Decimal places for effect sizes (3 recommended)'
    )
    confidence_interval_decimals: int = Field(
        ge=0, le=4, description='Decimal places for confidence interval bounds'
    )

    # Date/time formatting (Python strftime)
    date_format: str = Field(
        min_length=2, description='strftime format for date display (e.g., "%Y-%m-%d")'
    )
    datetime_format: str = Field(
        min_length=2,
        description='strftime format for datetime display (e.g., "%Y-%m-%d %H:%M:%S")',
    )
    month_format: str = Field(
        min_length=2, description='strftime format for month grouping (e.g., "%Y-%m")'
    )

    # Report layout
    output_width: int = Field(
        ge=60, le=200, description='Character width for section divider lines'
    )
