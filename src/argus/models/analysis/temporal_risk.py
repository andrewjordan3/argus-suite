# argus/models/analysis/temporal_risk.py
"""
Temporal Risk Profile Model for ARGUS Analysis Pipeline.

This module defines models for temporal risk analysis results, capturing how
an entity's (driver or vehicle) behavior has changed over time. The analysis
detects change points, behavioral trends, fraud pattern signatures, and
anomalies in time-series data.

Design Philosophy:
    This model follows the ARGUS principle of separating data from policy.
    It contains only raw statistical outputs from temporal analysis—no methods
    that depend on configuration thresholds, locale settings, or presentation
    formatting. Interpretation of these values belongs in service/processor
    layers that receive both this model and the relevant configuration.

    Note: Some nested models contain fields (like `risk_level` in
    AutocorrelationResult) that represent policy interpretations computed
    by the upstream pipeline. These are preserved for compatibility but
    ideally should be computed in the service layer during report generation.

Immutability:
    All model instances are frozen after creation. Temporal analysis results
    represent a point-in-time computation and should not be modified.

Model Hierarchy:
    TemporalRiskProfile (root)
    ├── MonthOverMonthAnalysis      - Volatility and spike detection
    ├── dict[str, RollingAnomalyResult]  - Per-metric outlier detection
    ├── dict[str, AutocorrelationResult] - Per-metric persistence patterns
    ├── FraudPatternFlags           - Named fraud pattern indicators
    └── TemporalRiskSummary         - Aggregate statistics

Usage:
    >>> from argus.models.analysis.temporal_risk import (
    ...     TemporalRiskProfile,
    ...     FraudPatternFlags,
    ...     MonthOverMonthAnalysis,
    ... )
    >>>
    >>> profile = TemporalRiskProfile(
    ...     display_id='John Smith',
    ...     entity_type='Driver',
    ...     risk_score=78,
    ...     months_active=8,
    ...     total_transactions=156,
    ...     change_points={'no_eld_rate': '2024-06'},
    ...     fraud_patterns=FraudPatternFlags(weekend_warrior=True),
    ...     month_over_month=MonthOverMonthAnalysis(
    ...         volatility_score=1.45,
    ...         sudden_spikes=['no_eld_rate'],
    ...     ),
    ... )

See Also:
    - argus.models.analysis.driver_risk: Cross-sectional driver risk profiles
    - argus.models.analysis.statistical_test: Individual statistical test results
    - argus.services.temporal_analysis: Service that produces these results
"""

import math
import re
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from argus.models.common.base import FrozenModel

# -----------------------------------------------------------------------------
# Type Definitions
# -----------------------------------------------------------------------------
# Defined locally to avoid cross-module dependencies. These types are specific
# to temporal risk analysis and unlikely to be shared with other models.
# -----------------------------------------------------------------------------
# NOTE: This should be used only by the programmer and not meant for presentation.
# It will probably be removed in future versions in favor of deriving labels
# on-the-fly from locale configuration.
EntityType = Literal['Driver', 'Vehicle']
"""
Type of entity being analyzed.

Note:
    This type is for internal programming use only and should not appear
    in user-facing output. User-facing labels should be derived from locale
    configuration in the presentation layer.
"""

__all__: list[str] = [
    'AutocorrelationResult',
    'EntityType',
    'FraudPatternFlags',
    'MonthOverMonthAnalysis',
    'RollingAnomalyResult',
    'TemporalRiskProfile',
    'TemporalRiskSummary',
]


# -----------------------------------------------------------------------------
# Validation Tolerances
# -----------------------------------------------------------------------------
# Module-level constants for validation tolerances. Centralizing these makes
# the validation logic clearer and allows adjustment if needed.
# -----------------------------------------------------------------------------

# Absolute tolerance for correlation coefficient bounds.
# Correlations must be in [-1.0, 1.0]; this handles floating-point errors.
_CORRELATION_BOUND_TOLERANCE: float = 1e-9


# Compiled Regex Patterns
# -----------------------------------------------------------------------------
# Pre-compiled patterns for validation. Compiling at module load time avoids
# the overhead of recompilation on every validation call.
# -----------------------------------------------------------------------------

# Pattern for YYYY-MM month identifier format used in change point dates.
# Examples: '2024-01', '2023-12'
_MONTH_DATE_PATTERN: re.Pattern[str] = re.compile(r'^\d{4}-\d{2}$')

# =============================================================================
# Nested Models: Month-Over-Month Analysis
# =============================================================================


class MonthOverMonthAnalysis(FrozenModel):
    """
    Container for month-over-month volatility analysis results.

    This model captures patterns in how metrics change from one month to
    the next, identifying sudden spikes (large single-month jumps) and
    gradual escalation (consistent upward trends over multiple months).

    The volatility score quantifies overall month-to-month variability,
    with higher values indicating more erratic behavior patterns.

    Attributes:
        sudden_spikes: List of metric names that exhibited sudden month-to-month
            spikes exceeding configured thresholds. Example: ['no_eld_rate']
            indicates the no-ELD rate jumped significantly in a single month.

        gradual_escalation: List of metric names showing consistent upward
            trends over multiple consecutive months. This pattern may indicate
            a driver gradually testing boundaries rather than sudden fraud.

        volatility_score: Aggregate measure of month-to-month variability
            across all tracked metrics. Higher values indicate more erratic
            behavior. Scale is implementation-dependent but typically
            normalized where values > 1.0 indicate above-average volatility.

    Example:
        >>> analysis = MonthOverMonthAnalysis(
        ...     sudden_spikes=['no_eld_rate', 'after_hours_rate'],
        ...     gradual_escalation=['non_diesel_rate'],
        ...     volatility_score=1.85,
        ... )
    """

    sudden_spikes: list[str] = Field(
        default_factory=list,
        description='Metric names with sudden month-to-month spikes',
    )

    gradual_escalation: list[str] = Field(
        default_factory=list,
        description='Metric names showing gradual upward trends',
    )

    volatility_score: float = Field(
        default=0.0,
        description='Aggregate month-to-month variability measure',
        ge=0.0,
    )


# =============================================================================
# Nested Models: Rolling Anomaly Detection
# =============================================================================


class RollingAnomalyResult(FrozenModel):
    """
    Container for rolling window anomaly detection results for a single metric.

    This model captures months where a metric's value was a statistical outlier
    compared to the rolling historical window. Outliers are identified using
    z-scores computed against the rolling mean and standard deviation.

    Attributes:
        outlier_months: List of month identifiers (YYYY-MM format) where the
            metric value was flagged as an outlier. An empty list indicates
            no anomalous months were detected for this metric.

        max_z_score: The highest absolute z-score observed across all months
            for this metric. Higher values indicate more extreme deviations
            from the rolling baseline. Typical interpretation:
            - |z| < 2.0: Within normal variation
            - |z| >= 2.0: Unusual
            - |z| >= 3.0: Highly anomalous

        mean_z_score: Average absolute z-score across all months, indicating
            the typical deviation level. Defaults to 0.0 if not computed.

    Example:
        >>> anomaly = RollingAnomalyResult(
        ...     outlier_months=['2024-05', '2024-09'],
        ...     max_z_score=3.42,
        ...     mean_z_score=1.15,
        ... )
    """

    outlier_months: list[str] = Field(
        default_factory=list,
        description='Month identifiers (YYYY-MM) flagged as outliers',
    )

    max_z_score: float = Field(
        default=0.0,
        description='Highest absolute z-score observed',
    )

    mean_z_score: float = Field(
        default=0.0,
        description='Average absolute z-score across all months',
    )


# =============================================================================
# Nested Models: Autocorrelation Analysis
# =============================================================================


class AutocorrelationResult(FrozenModel):
    """
    Container for autocorrelation analysis results for a single metric.

    Autocorrelation measures how strongly a metric's value in one month
    correlates with its value in the previous month. High autocorrelation
    indicates persistent patterns—if a driver has a high no-ELD rate one
    month, they're likely to have a high rate the next month as well.

    This persistence is important for risk assessment because it distinguishes
    between one-time anomalies and sustained problematic behavior.

    Attributes:
        lag1_correlation: Pearson correlation coefficient between each month's
            value and the previous month's value (lag-1 autocorrelation).
            Values range from -1.0 to 1.0:
            - Near 1.0: Strong positive persistence (high follows high)
            - Near 0.0: No persistence (random month-to-month variation)
            - Near -1.0: Alternating pattern (high follows low)

        lag2_correlation: Optional lag-2 autocorrelation (correlation with
            value from two months prior). Useful for detecting bi-monthly
            patterns. Defaults to NaN if not computed.

        persistence_ratio: Ratio of months where the metric remained elevated
            after an initial spike. Values near 1.0 indicate the behavior
            persists; values near 0.0 indicate it was transient.
            Defaults to NaN if not computed.

    Note:
        The upstream pipeline may compute additional interpreted fields
        (like 'risk_level') that are not stored here. Interpretation of
        correlation values into risk categories should be performed in
        the service layer using configuration-defined thresholds.

    Example:
        >>> autocorr = AutocorrelationResult(
        ...     lag1_correlation=0.78,
        ...     lag2_correlation=0.52,
        ...     persistence_ratio=0.85,
        ... )
    """

    lag1_correlation: float = Field(
        default=math.nan,
        description='Lag-1 autocorrelation coefficient (-1 to 1)',
    )

    lag2_correlation: float = Field(
        default=math.nan,
        description='Lag-2 autocorrelation coefficient (-1 to 1)',
    )

    persistence_ratio: float = Field(
        default=math.nan,
        description='Ratio of months behavior persisted after initial spike (0 to 1)',
    )

    @field_validator('lag1_correlation', 'lag2_correlation')
    @classmethod
    def validate_correlation_bounds(cls, correlation_value: float) -> float:
        """
        Validate that correlation coefficients are in valid range.

        Pearson correlation coefficients must be in [-1.0, 1.0] by definition.
        NaN is permitted for optional/uncomputed correlations.

        Args:
            correlation_value: The correlation coefficient to validate.

        Returns:
            The validated correlation value, unchanged.

        Raises:
            ValueError: If correlation is not NaN and not in [-1.0, 1.0].
        """
        if math.isnan(correlation_value):
            return correlation_value

        lower_valid: bool = correlation_value >= (-1.0 - _CORRELATION_BOUND_TOLERANCE)
        upper_valid: bool = correlation_value <= (1.0 + _CORRELATION_BOUND_TOLERANCE)

        if not (lower_valid and upper_valid):
            raise ValueError(
                f'Correlation coefficient must be in [-1.0, 1.0], '
                f'got {correlation_value}.'
            )

        return correlation_value

    @field_validator('persistence_ratio')
    @classmethod
    def validate_persistence_ratio_bounds(cls, ratio_value: float) -> float:
        """
        Validate that persistence ratio is a valid proportion.

        Persistence ratio represents a proportion and must be in [0.0, 1.0].
        NaN is permitted if not computed.

        Args:
            ratio_value: The persistence ratio to validate.

        Returns:
            The validated ratio value, unchanged.

        Raises:
            ValueError: If ratio is not NaN and not in [0.0, 1.0].
        """
        if math.isnan(ratio_value):
            return ratio_value

        if not (0.0 <= ratio_value <= 1.0):
            raise ValueError(
                f'Persistence ratio must be in [0.0, 1.0], got {ratio_value}.'
            )

        return ratio_value


# =============================================================================
# Nested Models: Fraud Pattern Detection
# =============================================================================


class FraudPatternFlags(FrozenModel):
    """
    Container for named fraud pattern detection flags.

    Each flag indicates whether a specific, predefined fraud pattern signature
    was detected in the entity's temporal behavior. These patterns are based
    on domain expertise in fuel card fraud detection.

    Pattern Descriptions:
        weekend_warrior: Disproportionate transaction activity on weekends
            compared to weekdays. May indicate personal use of fleet fuel
            cards when business operations are reduced.

        pump_and_dump: Pattern of high-volume transactions followed by
            extended periods of inactivity. May indicate bulk fuel theft
            or resale operations.

        creeping_charlie: Gradual, incremental increases in suspicious
            metrics over time, suggesting a driver testing boundaries
            while avoiding detection thresholds.

        seasonal_mismatch: Transaction patterns that don't align with
            expected seasonal business cycles. For example, increased
            fuel purchases during periods when fleet activity should
            be reduced.

    Note:
        The detection algorithms and thresholds for these patterns are
        defined in the analysis configuration. This model stores only
        the boolean detection results, not the underlying evidence.

    Attributes:
        weekend_warrior: True if weekend concentration pattern detected.
        pump_and_dump: True if bulk-then-idle pattern detected.
        creeping_charlie: True if gradual escalation pattern detected.
        seasonal_mismatch: True if seasonal anomaly pattern detected.

    Example:
        >>> flags = FraudPatternFlags(
        ...     weekend_warrior=True,
        ...     creeping_charlie=True,
        ... )
        >>> flags.weekend_warrior
        True
    """

    weekend_warrior: bool = Field(
        default=False,
        description='Disproportionate weekend transaction activity detected',
    )

    pump_and_dump: bool = Field(
        default=False,
        description='High-volume followed by inactivity pattern detected',
    )

    creeping_charlie: bool = Field(
        default=False,
        description='Gradual escalation pattern detected',
    )

    seasonal_mismatch: bool = Field(
        default=False,
        description='Seasonal anomaly pattern detected',
    )

    def any_detected(self) -> bool:
        """
        Check if any fraud pattern was detected.

        Returns:
            True if at least one fraud pattern flag is True.
        """
        return (
            self.weekend_warrior
            or self.pump_and_dump
            or self.creeping_charlie
            or self.seasonal_mismatch
        )

    def count_detected(self) -> int:
        """
        Count the number of detected fraud patterns.

        Returns:
            Integer count of True flags (0 to 4).
        """
        return sum(
            [
                self.weekend_warrior,
                self.pump_and_dump,
                self.creeping_charlie,
                self.seasonal_mismatch,
            ]
        )

    def get_detected_names(self) -> list[str]:
        """
        Get list of detected fraud pattern identifiers.

        Returns field names (not user-facing labels) for patterns that
        were detected. User-facing labels should be derived from locale
        configuration in the presentation layer.

        Returns:
            List of field names for detected patterns.

        Example:
            >>> flags = FraudPatternFlags(weekend_warrior=True, pump_and_dump=True)
            >>> flags.get_detected_names()
            ['weekend_warrior', 'pump_and_dump']
        """
        detected: list[str] = []

        if self.weekend_warrior:
            detected.append('weekend_warrior')
        if self.pump_and_dump:
            detected.append('pump_and_dump')
        if self.creeping_charlie:
            detected.append('creeping_charlie')
        if self.seasonal_mismatch:
            detected.append('seasonal_mismatch')

        return detected


# =============================================================================
# Nested Models: Summary Statistics
# =============================================================================


class TemporalRiskSummary(FrozenModel):
    """
    Container for aggregate summary statistics from temporal analysis.

    This model provides a quick overview of the temporal analysis results
    without requiring inspection of all individual components. Useful for
    filtering, sorting, and high-level reporting.

    Attributes:
        total_risk_factors: Count of distinct risk factors identified across
            all temporal analysis components (change points, spikes, patterns,
            current risks). Higher counts indicate more concerning profiles.

        total_change_points: Total number of behavioral change points detected
            across all metrics and detection methods. Change points indicate
            moments when behavior shifted significantly.

        has_fraud_patterns: Boolean indicating whether any named fraud pattern
            was detected. Equivalent to FraudPatternFlags.any_detected().

        volatility_score: Copy of the month-over-month volatility score for
            convenient access without navigating to MonthOverMonthAnalysis.

        recent_behavior_score: Score (0-100 scale) reflecting risk based on
            the most recent observation period only. Distinguishes between
            historical concerns and current/ongoing issues.

    Example:
        >>> summary = TemporalRiskSummary(
        ...     total_risk_factors=7,
        ...     total_change_points=3,
        ...     has_fraud_patterns=True,
        ...     volatility_score=1.45,
        ...     recent_behavior_score=82.5,
        ... )
    """

    total_risk_factors: int = Field(
        default=0,
        description='Count of distinct risk factors identified',
        ge=0,
    )

    total_change_points: int = Field(
        default=0,
        description='Total change points detected across all metrics',
        ge=0,
    )

    has_fraud_patterns: bool = Field(
        default=False,
        description='Whether any named fraud pattern was detected',
    )

    volatility_score: float = Field(
        default=0.0,
        description='Month-over-month volatility score',
        ge=0.0,
    )

    recent_behavior_score: float = Field(
        default=0.0,
        description='Risk score based on most recent period only (0-100)',
        ge=0.0,
        le=100.0,
    )


# =============================================================================
# Main Model: TemporalRiskProfile
# =============================================================================


class TemporalRiskProfile(FrozenModel):
    """
    Container for comprehensive temporal analysis results for a single entity.

    This is the root model for temporal risk analysis, aggregating all
    time-series analysis outputs for a driver or vehicle. It captures
    behavioral changes over time, including change point detection,
    trend analysis, anomaly detection, and fraud pattern recognition.

    The model is organized into several categories:
        - Core identification (display_id, entity_type)
        - Aggregate metrics (risk_score, months_active, total_transactions)
        - Change point detection (change_points, multiple_change_points)
        - Trend analysis (risk_indicators, segment_comparison)
        - Volatility analysis (month_over_month)
        - Anomaly detection (rolling_anomalies)
        - Persistence analysis (autocorrelation)
        - Pattern recognition (fraud_patterns)
        - Current state (current_risk_factors)
        - Summary (summary)

    Attributes:
        display_id: Human-readable identifier for the entity. For drivers,
            this is typically the full name; for vehicles, the VIN or
            fleet ID. Used as the primary identifier in reports.

        entity_type: Type of entity being analyzed ('Driver' or 'Vehicle').
            This is for internal use only; user-facing labels should come
            from locale configuration.

        risk_score: Composite temporal risk score (0-100 scale) aggregating
            all temporal analysis components. Higher values indicate greater
            risk based on behavioral patterns over time.

        months_active: Number of distinct months with transaction activity
            in the analysis period. Provides context for interpreting
            other metrics—more months means more data for pattern detection.

        total_transactions: Total transaction count across the analysis
            period. Combined with months_active, indicates activity level
            and statistical confidence.

        truck_description: Optional vehicle description for vehicle entities
            or the primary vehicle associated with a driver. May include
            make, model, year, or fleet designation.

        change_points: Dictionary mapping metric names to single detected
            change point dates (YYYY-MM format). Each entry represents the
            most significant structural break detected for that metric.
            Example: {'no_eld_rate': '2024-06'} indicates the no-ELD rate
            had a significant shift in June 2024.

        risk_indicators: List of human-readable risk indicator strings
            describing concerning trends detected. These are generated by
            the analysis pipeline and may include directionality.
            Example: ['INCREASING no_eld_rate', 'SUDDEN SPIKE in volume']

        segment_comparison: Dictionary mapping metrics to first-half vs
            second-half comparison results. Useful for detecting whether
            behavior improved or worsened over the analysis period.
            Example: {'no_eld_rate': 'INCREASED (p=0.023, r=0.45)'}

        multiple_change_points: Dictionary mapping metrics to lists of ALL
            detected change points when multiple structural breaks exist.
            Example: {'no_eld_rate': ['2024-03', '2024-07', '2024-10']}

        month_over_month: Structured analysis of month-to-month variability,
            including sudden spikes, gradual escalation, and volatility score.

        rolling_anomalies: Dictionary mapping metric names to their rolling
            window anomaly detection results (outlier months, z-scores).

        autocorrelation: Dictionary mapping metric names to their
            autocorrelation analysis results (persistence patterns).

        fraud_patterns: Structured container for named fraud pattern
            detection flags (weekend_warrior, pump_and_dump, etc.).

        current_risk_factors: List of risk factor descriptions present in
            the most recent month of data. Critical for distinguishing
            between historical issues and ongoing concerns.
            Example: ['High No ELD Rate (45.2%)', 'High After Hours (62.1%)']

        summary: Aggregate summary statistics for quick overview and
            filtering without inspecting all individual components.

    Example:
        >>> profile = TemporalRiskProfile(
        ...     display_id='John Smith',
        ...     entity_type='Driver',
        ...     risk_score=78,
        ...     months_active=8,
        ...     total_transactions=156,
        ...     change_points={'no_eld_rate': '2024-06'},
        ...     fraud_patterns=FraudPatternFlags(weekend_warrior=True),
        ... )
        >>> print(profile)
        TemporalRiskProfile('John Smith', Driver, score=78, months=8, changes=1)
    """

    # -------------------------------------------------------------------------
    # Core Identification
    # -------------------------------------------------------------------------

    display_id: str = Field(
        ...,
        description='Human-readable identifier (driver name or VIN)',
        min_length=1,
    )

    entity_type: EntityType = Field(
        ...,
        description="Entity type ('Driver' or 'Vehicle') - internal use only",
    )

    # -------------------------------------------------------------------------
    # Aggregate Risk Metrics
    # -------------------------------------------------------------------------

    risk_score: int = Field(
        ...,
        description='Composite temporal risk score (0-100 scale)',
        ge=0,
        le=100,
    )

    months_active: int = Field(
        ...,
        description='Number of months with transaction activity',
        ge=0,
    )

    total_transactions: int = Field(
        ...,
        description='Total transaction count in the analysis period',
        ge=0,
    )

    # -------------------------------------------------------------------------
    # Optional Entity Metadata
    # -------------------------------------------------------------------------

    truck_description: str | None = Field(
        default=None,
        description='Vehicle description (make, model, fleet ID)',
    )

    # -------------------------------------------------------------------------
    # Single Change Point Detection Results
    # -------------------------------------------------------------------------
    # Maps metric names to the single most significant change point date.
    # Use multiple_change_points for complete change point histories.
    # -------------------------------------------------------------------------

    change_points: dict[str, str] = Field(
        default_factory=dict,
        description='Metric name -> primary change point date (YYYY-MM)',
    )

    # -------------------------------------------------------------------------
    # Trend Analysis Results
    # -------------------------------------------------------------------------

    risk_indicators: list[str] = Field(
        default_factory=list,
        description='List of detected concerning trend descriptions',
    )

    segment_comparison: dict[str, str] = Field(
        default_factory=dict,
        description='Metric name -> first-half vs second-half comparison result',
    )

    # -------------------------------------------------------------------------
    # Multiple Change Point Detection Results
    # -------------------------------------------------------------------------

    multiple_change_points: dict[str, list[str]] = Field(
        default_factory=dict,
        description='Metric name -> list of all detected change points (YYYY-MM)',
    )

    # -------------------------------------------------------------------------
    # Month-Over-Month Volatility Analysis
    # -------------------------------------------------------------------------

    month_over_month: MonthOverMonthAnalysis = Field(
        default_factory=MonthOverMonthAnalysis,
        description='Month-to-month volatility and spike analysis',
    )

    # -------------------------------------------------------------------------
    # Rolling Window Anomaly Detection
    # -------------------------------------------------------------------------

    rolling_anomalies: dict[str, RollingAnomalyResult] = Field(
        default_factory=dict,
        description='Metric name -> rolling window anomaly detection results',
    )

    # -------------------------------------------------------------------------
    # Autocorrelation (Persistence) Analysis
    # -------------------------------------------------------------------------

    autocorrelation: dict[str, AutocorrelationResult] = Field(
        default_factory=dict,
        description='Metric name -> autocorrelation analysis results',
    )

    # -------------------------------------------------------------------------
    # Named Fraud Pattern Detection
    # -------------------------------------------------------------------------

    fraud_patterns: FraudPatternFlags = Field(
        default_factory=FraudPatternFlags,
        description='Named fraud pattern detection flags',
    )

    # -------------------------------------------------------------------------
    # Current Period Risk Assessment
    # -------------------------------------------------------------------------

    current_risk_factors: list[str] = Field(
        default_factory=list,
        description='Risk factor descriptions from most recent month',
    )

    # -------------------------------------------------------------------------
    # Summary Statistics
    # -------------------------------------------------------------------------

    summary: TemporalRiskSummary = Field(
        default_factory=TemporalRiskSummary,
        description='Aggregate summary statistics for quick overview',
    )

    # -------------------------------------------------------------------------
    # Model Validators
    # -------------------------------------------------------------------------

    @model_validator(mode='after')
    def validate_transaction_month_consistency(self) -> Self:
        """
        Validate that transaction count is consistent with activity period.

        If there are no active months, total transactions should be zero.
        This catches data pipeline errors where counts might be populated
        for entities with no actual activity.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If months_active is 0 but total_transactions > 0.
        """
        if self.months_active == 0 and self.total_transactions > 0:
            raise ValueError(
                f'Inconsistent data: months_active is 0 but total_transactions '
                f'is {self.total_transactions}. Cannot have transactions without '
                f'active months.'
            )

        return self

    @model_validator(mode='after')
    def validate_change_point_date_format(self) -> Self:
        """
        Validate that change point dates follow expected YYYY-MM format.

        Change point dates should be month identifiers in ISO format (YYYY-MM).
        This validator performs a basic format check to catch obvious errors.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If any change point date doesn't match YYYY-MM pattern.
        """

        # Check single change points
        for metric_name, date_value in self.change_points.items():
            if not _MONTH_DATE_PATTERN.match(date_value):
                raise ValueError(
                    f"Invalid change point date format for '{metric_name}': "
                    f"'{date_value}'. Expected YYYY-MM format."
                )

        # Check multiple change points
        for metric_name, date_list in self.multiple_change_points.items():
            for date_value in date_list:
                if not _MONTH_DATE_PATTERN.match(date_value):
                    raise ValueError(
                        f"Invalid change point date format for '{metric_name}': "
                        f"'{date_value}'. Expected YYYY-MM format."
                    )

        return self

    @model_validator(mode='after')
    def validate_summary_fraud_consistency(self) -> Self:
        """
        Validate consistency between fraud_patterns and summary.has_fraud_patterns.

        The summary.has_fraud_patterns field should match the actual state
        of the fraud_patterns flags. This catches synchronization errors
        when summary is computed separately from detailed results.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If summary.has_fraud_patterns doesn't match actual state.
        """
        actual_has_fraud: bool = self.fraud_patterns.any_detected()
        reported_has_fraud: bool = self.summary.has_fraud_patterns

        if actual_has_fraud != reported_has_fraud:
            raise ValueError(
                f'Inconsistent fraud pattern data: fraud_patterns indicates '
                f'{actual_has_fraud} but summary.has_fraud_patterns is '
                f'{reported_has_fraud}.'
            )

        return self

    # -------------------------------------------------------------------------
    # Computed Properties
    # -------------------------------------------------------------------------

    def get_total_change_point_count(self) -> int:
        """
        Get the total number of detected change points across all metrics.

        Counts both single change points and all entries in multiple change
        points lists. This provides a comprehensive measure of behavioral
        instability over time.

        Returns:
            Total count of change points detected.
        """
        single_count: int = len(self.change_points)

        multiple_count: int = sum(
            len(date_list) for date_list in self.multiple_change_points.values()
        )

        return single_count + multiple_count

    def get_earliest_change_point(self) -> str | None:
        """
        Get the earliest change point date across all metrics.

        Searches both single change points and multiple change points to
        find the earliest moment when behavioral change was detected.

        Returns:
            Date string in YYYY-MM format, or None if no change points exist.
        """
        all_dates: list[str] = []

        # Collect single change points
        all_dates.extend(self.change_points.values())

        # Collect multiple change points
        for date_list in self.multiple_change_points.values():
            all_dates.extend(date_list)

        if not all_dates:
            return None

        # YYYY-MM format sorts correctly as strings
        return min(all_dates)

    def get_latest_change_point(self) -> str | None:
        """
        Get the most recent change point date across all metrics.

        Returns:
            Date string in YYYY-MM format, or None if no change points exist.
        """
        all_dates: list[str] = []

        all_dates.extend(self.change_points.values())

        for date_list in self.multiple_change_points.values():
            all_dates.extend(date_list)

        if not all_dates:
            return None

        return max(all_dates)

    # -------------------------------------------------------------------------
    # String Representation
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        """
        Return a compact string representation for debugging and logging.

        Shows the most important fields for quick identification: entity ID,
        type, risk score, months of activity, and change point count.

        Returns:
            Compact string suitable for logs and REPL inspection.

        Example:
            >>> repr(profile)
            "TemporalRiskProfile('John Smith', Driver, score=78, months=8, changes=3)"
        """
        change_count: int = self.get_total_change_point_count()

        return (
            f"TemporalRiskProfile('{self.display_id}', "
            f'{self.entity_type}, '
            f'score={self.risk_score}, '
            f'months={self.months_active}, '
            f'changes={change_count})'
        )
