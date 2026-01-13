# argus/formatting/report_formatter.py

"""
Report Formatting Utilities for ARGUS Fuel Card Forensics
==========================================================

This module provides formatting utilities for creating standardized,
professional output in forensic analysis reports.

The ReportFormatter class provides:
- Currency formatting with configurable symbols and decimals
- Percentage formatting
- Number formatting with thousands separators
- Date and time formatting
- Delta interpretation (increase/decrease language)
- Statistical interpretation helpers
- Effect size categorization
- Template variable substitution
- Text layout and formatting (separators, centering)

Usage:
    from argus.utils.config_loader import ConfigLoader
    from argus.utils.report_formatter import ReportFormatter

    config = ConfigLoader()
    formatter = ReportFormatter(config)

    # Format currency
    formatted_cost = formatter.format_currency(1234.56)  # "$1,234.56"

    # Format percentage
    formatted_pct = formatter.format_percent(0.1523, decimals=1)  # "15.2%"

    # Apply template variables
    template = config.get('section.template')
    output = formatter.format_template(template, target='Chicago', year=2025)
"""

import logging
import math
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from argus.config import FuelCardForensicsConfig
from argus.models.config.user_config_models import PValueThresholdsConfig
from argus.formatting.safe_template import safe_format_template
from argus.models import (
    ConfigurationFormatting,
    ReportConfig,
    TemporalAnalysisMetricDisplayNames,
)
from argus.utils import get_cliffs_delta_magnitude, is_missing_like

__all__: list[str] = ['ReportFormatter']

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)


class ReportFormatter:
    """
    Provides formatting utilities for forensic report generation.

    This class handles all data formatting, interpretation, and presentation logic,
    using configuration settings from a ConfigLoader instance.

    Responsibilities:
    - Format numerical values (currency, percentages, numbers)
    - Format dates and times
    - Interpret statistical results
    - Categorize effect sizes
    - Generate human-readable delta descriptions
    - Apply template variable substitution
    - Format text layout (separators, centering)
    - Apply consistent formatting standards across reports
    """

    def __init__(
        self, locale_template: ReportConfig, user_config: FuelCardForensicsConfig
    ) -> None:
        """
        Initialize the report formatter.

        Args:
            config_loader: ConfigLoader instance containing formatting preferences
                          and thresholds
        """
        self.template: ReportConfig = locale_template
        self.user_config: FuelCardForensicsConfig = user_config

        # Cache formatting configuration for performance
        self._formatting: ConfigurationFormatting = (
            self.template.configuration.formatting
        )

        # Extract commonly used values
        self.thousands_separator: str = self._formatting.thousands_separator
        self.output_width: int = self._formatting.output_width

    # ========================================================================
    # Internal Helper Functions
    # ========================================================================
    @staticmethod
    def _str_to_num(
        value: str | int | float | None,
        desired_type: type[int] | type[float],
        caller: str,
    ) -> int | float:
        """
        Convert a scalar to a numeric type with a NaN-on-failure contract.

        Contract:
            - If `value` is missing-like, return `math.nan`.
            - If `desired_type` is `float`, attempt `float(value)`.
            - If `desired_type` is `int`, attempt `float(value)` first and then truncate
            toward zero via `int(float_value)` (e.g., "3.2" -> 3, "-3.2" -> -3).
            - If conversion fails or the parsed number is NaN/Inf, return `math.nan`
            and log a warning.

        Type note:
            - `math.nan` is always a `float`.
            - Therefore, even when `desired_type` is `int`, failures return a float NaN.

        Args:
            value: Scalar to convert (string, int, float, or None).
            desired_type: Conversion target type; pass the built-in `int` or `float`.
            caller: Calling context used in logs.

        Returns:
            - An `int` when `desired_type` is `int` and conversion succeeds.
            - A `float` when `desired_type` is `float` and conversion succeeds.
            - `math.nan` (float) when missing-like, NaN/Inf, or conversion fails.

        Side effects:
            Emits a WARNING log entry on conversion failure.

        Raises:
            Never raises; errors are handled internally.
        """
        # Immediate Guard: Reject explicitly invalid types or missing values.
        # We group None, bool, and missing checks here to clear the noise.
        # Note: We check isinstance(bool) because Python treats True as 1.0, which we do not want.
        if value is None or isinstance(value, bool) or is_missing_like(value):
            return math.nan

        try:
            float_value = float(value)
        except (TypeError, ValueError) as exc:
            logger.warning(
                'Failed to convert %r to %s in %s (%s). Returning NaN.',
                value,
                desired_type.__name__,
                caller,
                exc,
            )
            return math.nan

        # Ensure the number is usable (finite).
        # math.isfinite() returns False for both NaN and Infinity.
        if not math.isfinite(float_value):
            return math.nan

        if desired_type is float:
            return float_value

        if desired_type is int:
            # Truncate toward zero (Python's int() behavior).
            return int(float_value)

        # Defensive: if someone passes an unexpected callable/type.
        logger.warning(
            'Unsupported desired_type=%r in %s. Expected int or float. Returning NaN.',
            desired_type,
            caller,
        )
        return math.nan

    # ========================================================================
    # Template Variable Substitution
    # ========================================================================

    def format_template(self, template: str, **kwargs: Any) -> str:
        """
        Format a template string with variable substitution. This is a wrapper
        for the from safe_format_template function.

        Args:
            template: Template string with {variable} placeholders
            **kwargs: Variable names and values for substitution

        Returns:
            Formatted string with variables replaced

        Examples:
            >>> template = "Analyzing {target_location} for {analysis_period}"
            >>> formatter.format_template(template,
            ...     target_location='Chicago North',
            ...     analysis_period='2025 YTD')
            'Analyzing Chicago North for 2025 YTD'
        """
        if not template:
            logger.debug(
                'Empty template provided to format_template with keywords: %r', kwargs
            )
            return ''

        return safe_format_template(template, **kwargs)

    def format_list(self, items: list[str], **kwargs: Any) -> list[str]:
        """
        Format a list of template strings.

        Args:
            items: list of template strings
            **kwargs: Variables for substitution

        Returns:
            list of formatted strings
        """
        return [self.format_template(item, **kwargs) for item in items]

    # ========================================================================
    # Number Formatting Methods
    # ========================================================================

    def format_currency(
        self, value: float | str | None, decimals: int | None = None
    ) -> str:
        """
        Format a value as currency using configured settings.

        Args:
            value: Numerical value to format
            decimals: Optional number of decimal places (uses config default if None)

        Returns:
            Formatted currency string (e.g., "$1,234.56")

        Examples:
            >>> formatter.format_currency(1234.56)
            '$1,234.56'
            >>> formatter.format_currency(1234.56, decimals=0)
            '$1,235'
        """
        clean_value: float = self._str_to_num(value, float, 'format_currency')

        if math.isnan(clean_value):
            return 'N/A'

        precision: int = (
            decimals if decimals is not None else self._formatting.currency_decimals
        )

        # Format with thousands separator
        formatted: str = f'{clean_value:,.{precision}f}'

        # Only pay the cost of replacement if we aren't using the default ','
        if self.thousands_separator != ',':
            formatted = formatted.replace(',', self.thousands_separator)
        return f'{self._formatting.currency_symbol}{formatted}'

    def format_percent(
        self, value: float | str | None, decimals: int | None = None
    ) -> str:
        """
        Format a proportion (0-1) as a percentage.

        Args:
            value: Proportion value (0-1)
            decimals: Optional number of decimal places (uses config default if None)

        Returns:
            Formatted percentage string (e.g., "15.2%")

        Examples:
            >>> formatter.format_percent(0.1523)
            '15.2%'
            >>> formatter.format_percent(0.1523, decimals=2)
            '15.23%'
        """
        clean_value: float = self._str_to_num(value, float, 'format_percent')

        if math.isnan(clean_value):
            return 'N/A'

        decimals = (
            decimals if decimals is not None else self._formatting.percentage_decimals
        )

        percentage: float = 100.0 * clean_value
        return f'{percentage:.{decimals}f}%'

    def format_number(
        self, value: float | str | None, decimals: int | None = None
    ) -> str:
        """
        Format a number with thousands separator.

        Args:
            value: Numerical value to format
            decimals: Number of decimal places (default from config)

        Returns:
            Formatted number string (e.g., "1,234.56")

        Examples:
            >>> formatter.format_number(1234.56)
            '1,234.56'
            >>> formatter.format_number(1234567, decimals=0)
            '1,234,567'
        """
        clean_value: float = self._str_to_num(value, float, 'format_number')

        if math.isnan(clean_value):
            return 'N/A'

        decimals = (
            decimals if decimals is not None else self._formatting.number_decimals
        )

        formatted: str = f'{clean_value:,.{decimals}f}'
        if self.thousands_separator != ',':
            formatted = formatted.replace(',', self.thousands_separator)

        return formatted

    def format_integer(self, value: int | float | str | None) -> str:
        """
        Format an integer with thousands separator.

        Args:
            value: Integer value to format

        Returns:
            Formatted integer string (e.g., "1,234")

        Examples:
            >>> formatter.format_integer(1234)
            '1,234'
        """
        clean_value: int | float = self._str_to_num(value, int, 'format_integer')

        if math.isnan(clean_value):
            return 'N/A'

        formatted: str = f'{clean_value:,}'
        if self.thousands_separator != ',':
            formatted = formatted.replace(',', self.thousands_separator)

        return formatted

    # ========================================================================
    # Date and Time Formatting Methods
    # ========================================================================

    def format_date(self, date: datetime, format_string: str | None = None) -> str:
        """
        Format a date according to configured preferences.

        Args:
            date: datetime object to format
            format_string: Optional custom format string (uses config default if None)

        Returns:
            Formatted date string

        Examples:
            >>> formatter.format_date(datetime(2025, 3, 15))
            '2025-03-15'  # or configured format
        """
        if pd.isna(date):
            return 'N/A'

        format_string = (
            format_string
            if format_string is not None
            else self._formatting.datetime_formats.date_format
        )

        return date.strftime(format_string)

    def format_datetime(self, dt: datetime, format_string: str | None = None) -> str:
        """
        Format a datetime according to configured preferences.

        Args:
            dt: datetime object to format
            format_string: Optional custom format string (uses config default if None)

        Returns:
            Formatted datetime string
        """
        if pd.isna(dt):
            return 'N/A'

        format_string = (
            format_string
            if format_string is not None
            else self._formatting.datetime_formats.datetime_format
        )

        return dt.strftime(format_string)

    def format_month(self, month_str: str) -> str:
        """
        Format a YYYY-MM string to a more readable format.

        Args:
            month_str: Month in YYYY-MM format

        Returns:
            Formatted month string like "Jun 2024"
        """
        try:
            dt: datetime = datetime.strptime(month_str, '%Y-%m').replace(tzinfo=UTC)
            return dt.strftime('%b %Y')  # e.g., "Jun 2024"
        except (ValueError, AttributeError):
            return month_str  # Return as-is if parsing fails

    # ========================================================================
    # Statistical Formatting Methods
    # ========================================================================

    def format_p_value(self, p: float | str | None) -> str:
        """
        Format p-value with precision and conventional markers.

        Args:
            p: P-value from statistical test

        Returns:
            Formatted p-value string with significance markers
            (*, **, *** for p < 0.05, 0.01, 0.001)
        """
        clean_value: float = self._str_to_num(p, float, 'format_p_value')

        if math.isnan(clean_value):
            return 'N/A'

        # We use the user configured thresholds for significance levels
        p_value_thresholds: PValueThresholdsConfig = self.user_config.statistics.p_value
        highly_significant: float = p_value_thresholds.highly_significant
        decimals: int = self._formatting.p_value_decimals

        if clean_value < highly_significant:
            return f'p < {highly_significant}***'
        elif clean_value < p_value_thresholds.very_significant:
            return f'p = {clean_value:.{decimals}f}**'
        elif clean_value < p_value_thresholds.significant:
            return f'p = {clean_value:.{decimals}f}*'
        else:
            return f'p = {clean_value:.2f}'

    def format_confidence_interval(
        self,
        lower: float | str | None,
        upper: float | str | None,
        decimals: int | None = None,
    ) -> str:
        """
        Format a confidence interval.

        Args:
            lower: Lower bound of interval
            upper: Upper bound of interval
            decimals: Number of decimal places (uses config default if None)

        Returns:
            Formatted confidence interval string (e.g., "[1.23, 4.56]")
        """
        clean_lower: float = self._str_to_num(
            lower, float, 'format_confidence_interval'
        )
        clean_upper: float = self._str_to_num(
            upper, float, 'format_confidence_interval'
        )

        if math.isnan(clean_lower) or math.isnan(clean_upper):
            return 'N/A'

        if decimals is None:
            decimals = self._formatting.confidence_interval_decimals

        return f'[{clean_lower:.{decimals}f}, {clean_upper:.{decimals}f}]'

    # ========================================================================
    # Text Layout and Formatting Methods
    # ========================================================================

    def separator(self, char: str = '=', width: int | None = None) -> str:
        """
        Create a separator line using configured width.

        Args:
            char: Character to use for separator
            width: Optional width (uses config default if None)

        Returns:
            Separator line string

        Examples:
            >>> formatter.separator()
            '===================================================================='
            >>> formatter.separator('-')
            '--------------------------------------------------------------------'
        """
        if width is None:
            width = self.output_width
        return char * width

    def center_text(self, text: str, width: int | None = None) -> str:
        """
        Center text within configured width.

        Args:
            text: Text to center
            width: Optional width (uses config default if None)

        Returns:
            Centered text string

        Examples:
            >>> formatter.center_text("REPORT TITLE")
            '                           REPORT TITLE                            '
        """
        return text.center(self.output_width if width is None else width)

    # ========================================================================
    # Statistical Interpretation Methods
    # ========================================================================

    def interpret_p_value(
        self, p_value: float | str | None, alpha: float | None = None
    ) -> str:
        """
        Interpret a p-value in human-readable terms.

        Args:
            p_value: P-value from statistical test
            alpha: Optional significance threshold (uses config default if None)

        Returns:
            Interpretation string

        Examples:
            >>> formatter.interpret_p_value(0.001)
            'highly significant (p < 0.001)'
            >>> formatter.interpret_p_value(0.15)
            'not significant (p = 0.15)'
        """
        if alpha is None:
            alpha = self.get_alpha()

        clean_p_value: float = self._str_to_num(p_value, float, 'interpret_p_value')

        if clean_p_value < 0.001:  # noqa: PLR2004
            return self.template.test_interpretations.p_value.highly_significant
        elif clean_p_value < 0.01:  # noqa: PLR2004
            return self.format_template(
                self.template.test_interpretations.p_value.very_significant,
                clean_p_value=clean_p_value,
            )
        elif clean_p_value < alpha:
            return self.format_template(
                self.template.test_interpretations.p_value.significant,
                clean_p_value=clean_p_value,
            )
        else:
            return self.format_template(
                self.template.test_interpretations.p_value.not_significant,
                clean_p_value=clean_p_value,
            )

    def get_alpha(self, confidence_level: float | None = None) -> float:
        """
        Calculate alpha (significance threshold) from confidence level.

        Args:
            confidence_level: Optional confidence level (0-1). If None, uses default.

        Returns:
            Alpha value (1 - confidence_level)
        """
        return (
            self.user_config.statistics.get_alpha()
            if confidence_level is None
            else 1.0 - confidence_level
        )

    # ========================================================================
    # Effect Size Categorization
    # ========================================================================
    def interpret_cliffs_delta(self, delta: float | str | None) -> str:
        """
        Interpret Cliff's Delta effect size.

        Args:
            delta: Cliff's Delta value (-1 to +1)

        Returns:
            Interpretation label ('negligible', 'small', 'medium', 'large')
        """
        clean_delta: float = self._str_to_num(delta, float, 'interpret_cliffs_delta')
        abs_delta: float = abs(clean_delta)
        return get_cliffs_delta_magnitude(abs_delta, self.template)

    # ========================================================================
    # Report-Specific Formatting
    # ========================================================================

    def format_risk_level(self, risk_score: float) -> str:
        """
        Format a risk score into a categorical risk level.

        Args:
            risk_score: Numerical risk score (float 0-100)

        Returns:
            Risk level string: 'Critical', 'High', 'Medium', or 'Low'
        """
        return self.user_config.risk_thresholds.get_risk_category(risk_score)

    def format_count_with_label(self, count: int, singular: str, plural: str) -> str:
        """
        Format a count with appropriate singular/plural label.

        Args:
            count: Number to format
            singular: Singular form of the label
            plural: Plural form of the label

        Returns:
            Formatted string (e.g., "1 transaction", "5 transactions")

        Examples:
            >>> formatter.format_count_with_label(1, "transaction", "transactions")
            '1 transaction'
            >>> formatter.format_count_with_label(5, "transaction", "transactions")
            '5 transactions'
        """
        label: str = singular if count == 1 else plural
        return f'{self.format_integer(count)} {label}'

    # ========================================================================
    # String Transformation Methods
    # ========================================================================

    def format_temporal_metric_name(self, metric: str) -> str:
        """
        Convert internal temporal metric name to user-friendly display name.

        Args:
            metric: Internal metric name (e.g., 'avg_cost_per_transaction')

        Returns:
            User-friendly display name (e.g., 'Average Cost Per Transaction')

        Examples:
            >>> formatter.format_temporal_metric_name('avg_cost_per_transaction')
            'Average Cost Per Transaction'
        """
        get_metric_names: TemporalAnalysisMetricDisplayNames = (
            self.template.temporal_analysis.metric_display_names
        )
        display_name: str = getattr(
            get_metric_names, metric, metric.replace('_', ' ').title()
        )

        return display_name

    def format_display_name(self, raw_name: str) -> str:
        """
        Convert a dictionary key value into a string suitable for reporting.

        Args:
            raw_name: Raw name with underscores (e.g., 'total_cost')

        Returns:
            Formatted display name (e.g., 'Total Cost')

        Examples:
            >>> formatter.format_display_name('total_cost')
            'Total Cost'
            >>> formatter.format_display_name('avg_transactions_per_month')
            'Avg Transactions Per Month'
        """
        return raw_name.replace('_', ' ').title()

    def calculate_analysis_period_label(
        self, date_min: pd.Timestamp, date_max: pd.Timestamp
    ) -> str:
        """
        Calculate and format an analysis period label from date range.

        This method intelligently formats date ranges:
        - Same year: Shows "YYYY YTD (MMM-MMM)" format
        - Different years: Shows "(MMM YYYY-MMM YYYY)" format

        Args:
            date_min: Start date of the analysis period
            date_max: End date of the analysis period

        Returns:
            Formatted analysis period string

        Examples:
            >>> formatter.calculate_analysis_period_label(
            ...     pd.Timestamp('2025-01-01'),
            ...     pd.Timestamp('2025-06-30')
            ... )
            '2025 YTD (Jan-Jun)'

            >>> formatter.calculate_analysis_period_label(
            ...     pd.Timestamp('2024-11-01'),
            ...     pd.Timestamp('2025-02-28')
            ... )
            '(Nov 2024-Feb 2025)'
        """
        # Validate that both dates are valid
        if pd.notna(date_min) and pd.notna(date_max):
            # Check if dates are in the same year
            if date_min.year == date_max.year:
                # Format: "YYYY YTD (MMM-MMM)"
                month_range: str = (
                    f'({date_min.strftime("%b")}-{date_max.strftime("%b")})'
                )
                return f'{date_max.year} YTD {month_range}'
            else:
                # Format: "(MMM YYYY-MMM YYYY)"
                month_range = (
                    f'({date_min.strftime("%b %Y")}-{date_max.strftime("%b %Y")})'
                )
                return month_range

    def is_missing_like(self, value: str | None) -> bool:
        """Small helper to check strings for none like text"""
        if value is None:
            return True
        return value.strip().lower() in {'none', 'na', 'n/a', 'null', 'nan', ''}

    def __repr__(self) -> str:
        """String representation of ReportFormatter."""
        return 'ReportFormatter'

    def __str__(self) -> str:
        """Human-readable string representation."""
        return 'ReportFormatter with settings'
