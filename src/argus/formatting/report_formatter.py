# argus/formatting/report_formatter.py
"""
Report Formatting Utilities for ARGUS Fuel Card Forensics.

This module provides the ReportFormatter class, which centralizes all
data formatting, interpretation, and presentation logic for forensic
analysis reports.

Capabilities:
    - Numeric formatting (currency, percentages, integers, decimals)
    - Date and time formatting with locale awareness
    - Statistical value formatting (p-values, confidence intervals)
    - Statistical interpretation (significance levels, effect sizes)
    - Risk score categorization
    - Template variable substitution
    - Text layout utilities (separators, centering)

Architecture:
    ReportFormatter depends on ArgusConfig, which bundles:
        - PolicyConfig: Numeric thresholds (significance levels, risk cutoffs)
        - LocaleConfig: User-facing text templates and format settings

Example:
    >>> from argus.models.context import ArgusConfig
    >>> from argus.formatting import ReportFormatter
    >>>
    >>> context = ArgusConfig(user=user_cfg, policy=policy_cfg, locale=locale_cfg)
    >>> formatter = ReportFormatter(context)
    >>>
    >>> formatter.format_currency(1234.56)
    '$1,234.56'
    >>> formatter.interpret_p_value(0.003)
    'very significant (p = 0.003)'
"""

import logging
import math
from datetime import UTC, datetime
from typing import Any

import pandas as pd

from argus.formatting.safe_template import safe_format_template
from argus.models.context import ArgusConfig
from argus.models.locale.interpretations import TestInterpretationsPValues
from argus.models.locale.temporal import TemporalAnalysisMetricDisplayNames
from argus.models.policy import PValueThresholdsConfig
from argus.utils import (
    categorize_risk_score,
    get_cliffs_delta_magnitude,
    get_cohens_d_magnitude,
    is_missing_like,
)

__all__: list[str] = ['ReportFormatter']

logger: logging.Logger = logging.getLogger(__name__)


class ReportFormatter:
    """
    Centralized formatting and interpretation for forensic report generation.

    This class provides consistent data presentation across all ARGUS reports
    by combining policy-defined thresholds with locale-defined display text.

    Attributes:
        context: The ArgusConfig containing all configuration.
        thousands_separator: Character used for numeric grouping (from locale).
        output_width: Default width for text layout operations (from locale).
    """

    def __init__(self, context: ArgusConfig) -> None:
        """
        Initialize the report formatter.

        Args:
            context: ArgusConfig containing policy and locale settings.
        """
        self.context: ArgusConfig = context
        self.thousands_separator: str = self.context.locale.locale.thousands_separator
        self.output_width: int = self.context.locale.locale.output_width
        self.missing_value: str = self.context.locale.locale.missing_value

        logger.debug(
            'ReportFormatter initialized with locale=%r',
            self.context.locale.locale.language_code,
        )

    # =========================================================================
    # Private Helpers
    # =========================================================================

    @staticmethod
    def _str_to_num(
        value: str | int | float | None,
        target_type: type[int] | type[float],
        caller: str,
    ) -> int | float:
        """
        Convert a scalar to a numeric type, returning NaN on failure.

        This method provides a consistent contract for numeric conversion
        across all formatting methods, handling edge cases gracefully.

        Conversion Rules:
            - Missing-like values (None, NaN, empty strings) -> math.nan
            - For float: attempts float(value)
            - For int: attempts float(value) then truncates toward zero
            - Non-finite results (NaN, Inf) -> math.nan
            - Conversion failures -> math.nan with warning logged

        Args:
            value: Scalar to convert (string, int, float, or None).
            target_type: Desired numeric type (int or float).
            caller: Method name for log context.

        Returns:
            Converted numeric value, or math.nan on failure.

        Note:
            Return type is always float when conversion fails, since
            math.nan is a float. Callers should check with math.isnan().
        """
        if value is None or isinstance(value, bool) or is_missing_like(value):
            return math.nan

        try:
            float_value = float(value)
        except (TypeError, ValueError) as exc:
            logger.warning(
                '%s: Failed to convert %r to %s (%s). Returning NaN.',
                caller,
                value,
                target_type.__name__,
                exc,
            )
            return math.nan

        if not math.isfinite(float_value):
            return math.nan

        if target_type is float:
            return float_value

        if target_type is int:
            return int(float_value)

        logger.warning(
            '%s: Unsupported target_type=%r. Expected int or float. Returning NaN.',
            caller,
            target_type,
        )
        return math.nan

    # =========================================================================
    # Template Substitution
    # =========================================================================

    def format_template(self, template: str, **kwargs: Any) -> str:
        """
        Substitute variables into a template string.

        Wraps safe_format_template to provide graceful handling of missing
        keys and type mismatches.

        Args:
            template: Template string with {placeholder} syntax.
            **kwargs: Variable names and values for substitution.

        Returns:
            Formatted string with placeholders replaced.

        Examples:
            >>> formatter.format_template(
            ...     "Analyzing {location} for {period}",
            ...     location='Chicago',
            ...     period='2025 YTD'
            ... )
            'Analyzing Chicago for 2025 YTD'
        """
        if not template:
            logger.debug('Empty template provided with kwargs: %r', kwargs)
            return ''

        return safe_format_template(template, **kwargs)

    def format_template_list(self, templates: list[str], **kwargs: Any) -> list[str]:
        """
        Apply variable substitution to a list of template strings.

        Args:
            templates: List of template strings.
            **kwargs: Variables for substitution.

        Returns:
            List of formatted strings.
        """
        return [self.format_template(item, **kwargs) for item in templates]

    # =========================================================================
    # Numeric Formatting
    # =========================================================================

    def format_currency(
        self, value: float | str | None, decimals: int | None = None
    ) -> str:
        """
        Format a value as currency.

        Args:
            value: Numeric value to format.
            decimals: Decimal places (uses locale default if None).

        Returns:
            Formatted currency string (e.g., "$1,234.56").

        Examples:
            >>> formatter.format_currency(1234.56)
            '$1,234.56'
            >>> formatter.format_currency(1234.56, decimals=0)
            '$1,235'
        """
        clean_value: float = self._str_to_num(value, float, 'format_currency')

        if math.isnan(clean_value):
            return self.missing_value

        precision: int = (
            decimals
            if decimals is not None
            else self.context.locale.locale.currency_decimals
        )

        formatted: str = f'{clean_value:,.{precision}f}'

        if self.thousands_separator != ',':
            formatted = formatted.replace(',', self.thousands_separator)

        return f'{self.context.locale.locale.currency_symbol}{formatted}'

    def format_percent(
        self, value: float | str | None, decimals: int | None = None
    ) -> str:
        """
        Format a proportion (0-1) as a percentage.

        Args:
            value: Proportion value between 0 and 1.
            decimals: Decimal places (uses locale default if None).

        Returns:
            Formatted percentage string (e.g., "15.2%").

        Examples:
            >>> formatter.format_percent(0.1523)
            '15.2%'
            >>> formatter.format_percent(0.1523, decimals=2)
            '15.23%'
        """
        clean_value: float = self._str_to_num(value, float, 'format_percent')

        if math.isnan(clean_value):
            return self.missing_value

        precision: int = (
            decimals
            if decimals is not None
            else self.context.locale.locale.percentage_decimals
        )

        percentage: float = 100.0 * clean_value
        return f'{percentage:.{precision}f}%'

    def format_number(
        self, value: float | str | None, decimals: int | None = None
    ) -> str:
        """
        Format a decimal number with thousands separator.

        Args:
            value: Numeric value to format.
            decimals: Decimal places (uses locale default if None).

        Returns:
            Formatted number string (e.g., "1,234.56").

        Examples:
            >>> formatter.format_number(1234.56)
            '1,234.56'
            >>> formatter.format_number(1234567.89, decimals=0)
            '1,234,568'
        """
        clean_value: float = self._str_to_num(value, float, 'format_number')

        if math.isnan(clean_value):
            return self.missing_value

        precision: int = (
            decimals
            if decimals is not None
            else self.context.locale.locale.number_decimals
        )

        formatted: str = f'{clean_value:,.{precision}f}'

        if self.thousands_separator != ',':
            formatted = formatted.replace(',', self.thousands_separator)

        return formatted

    def format_integer(self, value: int | float | str | None) -> str:
        """
        Format an integer with thousands separator.

        Args:
            value: Integer value to format (floats are truncated).

        Returns:
            Formatted integer string (e.g., "1,234").

        Examples:
            >>> formatter.format_integer(1234)
            '1,234'
            >>> formatter.format_integer(1234.7)
            '1,234'
        """
        clean_value: int | float = self._str_to_num(value, int, 'format_integer')

        if math.isnan(clean_value):
            return self.missing_value

        formatted: str = f'{clean_value:,}'

        if self.thousands_separator != ',':
            formatted = formatted.replace(',', self.thousands_separator)

        return formatted

    def format_count_with_label(self, count: int, singular: str, plural: str) -> str:
        """
        Format a count with grammatically correct singular/plural label.

        Args:
            count: Number to format.
            singular: Singular form of the label.
            plural: Plural form of the label.

        Returns:
            Formatted count with label (e.g., "1 transaction", "5 transactions").

        Examples:
            >>> formatter.format_count_with_label(1, "transaction", "transactions")
            '1 transaction'
            >>> formatter.format_count_with_label(5, "transaction", "transactions")
            '5 transactions'
        """
        label: str = singular if count == 1 else plural
        return f'{self.format_integer(count)} {label}'

    # =========================================================================
    # Date and Time Formatting
    # =========================================================================

    def format_date(self, value: datetime, format_string: str | None = None) -> str:
        """
        Format a date using locale-configured or custom format.

        Args:
            value: Datetime object to format.
            format_string: Custom strftime format (uses locale default if None).

        Returns:
            Formatted date string.

        Examples:
            >>> formatter.format_date(datetime(2025, 3, 15))
            '2025-03-15'
        """
        if pd.isna(value):
            return self.missing_value

        fmt: str = (
            format_string
            if format_string is not None
            else self.context.locale.locale.date_format
        )

        return value.strftime(fmt)

    def format_datetime(self, value: datetime, format_string: str | None = None) -> str:
        """
        Format a datetime using locale-configured or custom format.

        Args:
            value: Datetime object to format.
            format_string: Custom strftime format (uses locale default if None).

        Returns:
            Formatted datetime string.
        """
        if pd.isna(value):
            return self.missing_value

        fmt: str = (
            format_string
            if format_string is not None
            else self.context.locale.locale.datetime_format
        )

        return value.strftime(fmt)

    def format_month(self, month_str: str) -> str:
        """
        Convert a YYYY-MM string to locale-configured month format.

        Args:
            month_str: Month in YYYY-MM format.

        Returns:
            Formatted month string (e.g., "2024-06" or locale equivalent).

        Note:
            Returns input unchanged on parse failure rather than missing_value,
            since a malformed date string may still be human-readable.
        """
        try:
            dt: datetime = datetime.strptime(month_str, '%Y-%m').replace(tzinfo=UTC)
            return dt.strftime(self.context.locale.locale.month_format)
        except (ValueError, AttributeError):
            logger.debug('Failed to parse month string: %r', month_str)
            return month_str

    def format_analysis_period(
        self, date_min: pd.Timestamp, date_max: pd.Timestamp
    ) -> str:
        """
        Format a date range as a human-readable analysis period label.

        Formatting Rules:
            - Same year: "YYYY YTD (MMM-MMM)" (e.g., "2025 YTD (Jan-Jun)")
            - Different years: "(MMM YYYY-MMM YYYY)" (e.g., "(Nov 2024-Feb 2025)")
            - Invalid dates: Returns locale missing value label

        Note:
            Month abbreviations use strftime %b, which depends on system locale
            (e.g., "Jan" in en_US, "Ene" in es_ES). For consistent output,
            ensure system locale is set or extend this method to use
            locale-config driven month names.

        Args:
            date_min: Start date of the analysis period.
            date_max: End date of the analysis period.

        Returns:
            Formatted analysis period string.

        Examples:
            >>> formatter.format_analysis_period(
            ...     pd.Timestamp('2025-01-01'),
            ...     pd.Timestamp('2025-06-30')
            ... )
            '2025 YTD (Jan-Jun)'
        """
        if pd.isna(date_min) or pd.isna(date_max):
            logger.debug(
                'Invalid date range for analysis period: min=%r, max=%r',
                date_min,
                date_max,
            )
            return self.missing_value

        if date_min > date_max:
            logger.warning(
                'Invalid date range: min=%s > max=%s, swapping values.',
                date_min,
                date_max,
            )
            date_min, date_max = date_max, date_min

        if date_min.year == date_max.year:
            month_range: str = f'({date_min.strftime("%b")}-{date_max.strftime("%b")})'
            return f'{date_max.year} YTD {month_range}'

        month_range = f'({date_min.strftime("%b %Y")}-{date_max.strftime("%b %Y")})'
        return month_range

    # =========================================================================
    # Statistical Value Formatting
    # =========================================================================

    def format_p_value(self, value: float | str | None) -> str:
        """
        Format a p-value to locale-configured decimal precision.

        This method only formats the numeric value. For significance
        interpretation with labels, use interpret_p_value().

        Args:
            value: P-value to format.

        Returns:
            Formatted p-value string (e.g., "0.023").

        Examples:
            >>> formatter.format_p_value(0.023456)
            '0.023'
        """
        clean_value: float = self._str_to_num(value, float, 'format_p_value')

        if math.isnan(clean_value):
            return self.missing_value

        decimals: int = self.context.locale.locale.p_value_decimals
        return f'{clean_value:.{decimals}f}'

    def format_confidence_interval(
        self,
        lower: float | str | None,
        upper: float | str | None,
        decimals: int | None = None,
    ) -> str:
        """
        Format a confidence interval as "[lower, upper]".

        Args:
            lower: Lower bound of interval.
            upper: Upper bound of interval.
            decimals: Decimal places (uses locale default if None).

        Returns:
            Formatted confidence interval string (e.g., "[1.23, 4.56]").
        """
        clean_lower: float = self._str_to_num(
            lower, float, 'format_confidence_interval'
        )
        clean_upper: float = self._str_to_num(
            upper, float, 'format_confidence_interval'
        )

        if math.isnan(clean_lower) or math.isnan(clean_upper):
            return self.missing_value

        precision: int = (
            decimals
            if decimals is not None
            else self.context.locale.locale.confidence_interval_decimals
        )

        return f'[{clean_lower:.{precision}f}, {clean_upper:.{precision}f}]'

    # =========================================================================
    # Statistical Interpretation
    # =========================================================================

    def interpret_p_value(self, value: float | str | None) -> str:
        """
        Interpret a p-value into a significance category with locale text.

        Uses policy-defined thresholds to categorize significance and
        locale-defined templates for user-facing output.

        Significance Levels (per policy thresholds):
            - p <= highly_significant: "highly significant (p < {threshold})"
            - p <= very_significant: "very significant (p = {value})"
            - p <= significant: "significant (p = {value})"
            - p > significant: "not significant (p = {value})"

        Args:
            value: P-value from statistical test.

        Returns:
            Interpreted significance string from locale templates.

        Examples:
            >>> formatter.interpret_p_value(0.0001)
            'highly significant (p < 0.001)'
            >>> formatter.interpret_p_value(0.023)
            'significant (p = 0.023)'
        """
        clean_value: float = self._str_to_num(value, float, 'interpret_p_value')

        if math.isnan(clean_value):
            return self.missing_value

        thresholds: PValueThresholdsConfig = self.context.policy.statistics.p_value
        templates: TestInterpretationsPValues = (
            self.context.locale.test_interpretations.p_value
        )

        decimals: int = self.context.locale.locale.p_value_decimals
        formatted_value: str = f'{clean_value:.{decimals}f}'

        # templates* is type FormatStr, which is a validated template
        # from locale config; extract as str for formatting.
        if clean_value <= thresholds.highly_significant:
            return self.format_template(
                template=str(templates.highly_significant),
                p_highly_significant=thresholds.highly_significant,
            )

        if clean_value <= thresholds.very_significant:
            return self.format_template(
                template=str(templates.very_significant),
                clean_p_value=formatted_value,
            )

        if clean_value <= thresholds.significant:
            return self.format_template(
                template=str(templates.significant),
                clean_p_value=formatted_value,
            )

        return self.format_template(
            template=str(templates.not_significant),
            clean_p_value=formatted_value,
        )

    def interpret_cliffs_delta(self, value: float | str | None) -> str:
        """
        Interpret Cliff's Delta effect size into a magnitude category.

        Uses policy-defined thresholds and locale-defined labels.

        Args:
            value: Cliff's Delta value (-1 to +1).

        Returns:
            Magnitude label (e.g., "negligible", "small", "medium", "large") or
            self.missing_value if input is invalid.
        """
        clean_value: float = self._str_to_num(value, float, 'interpret_cliffs_delta')

        if math.isnan(clean_value):
            return self.missing_value

        return get_cliffs_delta_magnitude(clean_value, self.context)

    def interpret_cohens_d(self, value: float | str | None) -> str:
        """
        Interpret Cohen's d effect size into a magnitude category.

        Uses policy-defined thresholds and locale-defined labels.

        Args:
            value: Cohen's d value.

        Returns:
            Magnitude label (e.g., "negligible", "small", "medium", "large") or
            self.missing_value if input is invalid.
        """
        clean_value: float = self._str_to_num(value, float, 'interpret_cohens_d')

        if math.isnan(clean_value):
            return self.missing_value

        return get_cohens_d_magnitude(clean_value, self.context)

    def interpret_risk_score(self, score: float | str | None) -> str:
        """
        Interpret a risk score into a categorical risk level label.

        Uses policy-defined thresholds to categorize and locale-defined
        labels for display.

        Args:
            score: Risk score (0-100).

        Returns:
            Risk level label (e.g., "Critical", "High", "Medium", "Low") or
            self.missing_value if input is invalid.
        """
        clean_score: float = self._str_to_num(score, float, 'interpret_risk_score')

        if math.isnan(clean_score):
            return self.missing_value

        category_label: str | None = categorize_risk_score(clean_score, self.context)

        if category_label is None:
            return self.missing_value

        return category_label

    # =========================================================================
    # Display Name Formatting
    # =========================================================================

    def format_temporal_metric_name(self, metric_key: str) -> str:
        """
        Convert an internal temporal metric key to a user-friendly display name.

        Looks up the metric in locale configuration. Falls back to
        title-casing the key with underscores replaced by spaces.

        Args:
            metric_key: Internal metric name (e.g., "avg_cost_per_transaction").

        Returns:
            Display name (e.g., "Average Cost Per Transaction").

        Examples:
            >>> formatter.format_metric_display_name('avg_cost_per_transaction')
            'Average Cost Per Transaction'
        """
        metric_names: TemporalAnalysisMetricDisplayNames = (
            self.context.locale.temporal_analysis.metric_display_names
        )
        display_name: str | None = getattr(metric_names, metric_key, None)

        if display_name is None:
            logger.debug(
                'No locale display name for metric %r; using fallback.', metric_key
            )
            return metric_key.replace('_', ' ').title()

        return display_name

    def format_snake_case_label(self, raw_name: str) -> str:
        """
        Convert a snake_case string to a Title Case display label.

        This is a generic fallback for keys not in locale configuration.

        Args:
            raw_name: Snake_case string (e.g., "total_cost").

        Returns:
            Title case string (e.g., "Total Cost").

        Examples:
            >>> formatter.format_snake_case_label('total_cost')
            'Total Cost'
        """
        return raw_name.replace('_', ' ').title()

    # =========================================================================
    # Text Layout
    # =========================================================================

    def separator(self, char: str = '=', width: int | None = None) -> str:
        """
        Create a horizontal separator line.

        Args:
            char: Character to repeat (default "=").
            width: Line width (uses locale default if None).

        Returns:
            Separator string.

        Examples:
            >>> formatter.separator()
            '========================================'
            >>> formatter.separator('-', width=20)
            '--------------------'
        """
        effective_width: int = width if width is not None else self.output_width
        return char * effective_width

    def center_text(self, text: str, width: int | None = None) -> str:
        """
        Center text within a specified width.

        Args:
            text: Text to center.
            width: Total width (uses locale default if None).

        Returns:
            Centered text padded with spaces.

        Examples:
            >>> formatter.center_text("TITLE", width=20)
            '       TITLE        '
        """
        effective_width: int = width if width is not None else self.output_width
        return text.center(effective_width)

    # =========================================================================
    # Dunder Methods
    # =========================================================================

    def __repr__(self) -> str:
        """Return a developer-friendly representation."""
        return f'ReportFormatter(locale={self.context.locale.locale.language_code!r})'

    def __str__(self) -> str:
        """Return a human-readable description."""
        return (
            f'ReportFormatter using {self.context.locale.locale.language_code} locale'
        )
