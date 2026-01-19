# argus/utils/temporal/monthly_behavior_analyzer.py
"""
Monthly behavioral pattern analysis for entity monitoring.

This module provides a unified analyzer for detecting suspicious patterns in
monthly aggregated data. The MonthlyBehaviorAnalyzer class encapsulates three
complementary analysis methods:

    1. Month-over-Month Analysis: Detects sudden spikes and gradual escalation
    2. Rolling Window Analysis: Identifies outliers vs rolling baseline
    3. Autocorrelation Analysis: Detects persistent (systematic) vs random behavior

These methods share configuration and operate on the same monthly data structure,
making a class-based approach more maintainable than standalone functions.

Typical Usage:
    from argus.utils.temporal.monthly_behavior_analyzer import MonthlyBehaviorAnalyzer

    analyzer = MonthlyBehaviorAnalyzer(
        monthly_data=entity_monthly_df,
        baseline_distributions=fleet_baselines['Driver'],
    )

    # Run all analyses
    mom_results = analyzer.analyze_month_over_month_changes()
    rolling_results = analyzer.analyze_with_rolling_window()
    autocorr_results = analyzer.analyze_autocorrelation_patterns()
"""

import logging
import warnings
from dataclasses import dataclass, field
from typing import Any, cast

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy import stats
from statsmodels.tsa.stattools import acf  # pyright: ignore[reportUnknownVariableType]

from argus.utils.temporal._constants import (
    AUTOCORRELATION_ANALYSIS_METRICS,
    AUTOCORRELATION_HIGH_RISK_THRESHOLD,
    AUTOCORRELATION_MAXIMUM_LAG,
    AUTOCORRELATION_MEDIUM_RISK_THRESHOLD,
    DEFAULT_ROLLING_WINDOW_SIZE_MONTHS,
    GRADUAL_ESCALATION_MINIMUM_CONSECUTIVE_MONTHS,
    MINIMUM_RECORDS_FOR_AUTOCORRELATION,
    MINIMUM_RECORDS_FOR_STATISTICAL_TEST,
    OUTLIER_Z_SCORE_THRESHOLD,
    PERCENTILE_95_Z_SCORE,
    SIGNIFICANT_RELATIVE_CHANGE_THRESHOLD,
    STANDARD_BEHAVIORAL_METRICS,
    VOLATILITY_OUTLIER_MAX_Z_SCORE,
)

__all__: list[str] = [
    'AutocorrelationResult',
    'GradualEscalationResult',
    'MonthOverMonthResults',
    'MonthlyAnalyzerConfiguration',
    'MonthlyBehaviorAnalyzer',
    'RollingWindowOutlierResult',
    'SuddenSpikeResult',
]

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION DATA CLASS
# =============================================================================


@dataclass(frozen=True, slots=True)
class MonthlyAnalyzerConfiguration:
    """
    Configuration parameters for MonthlyBehaviorAnalyzer.

    This frozen dataclass holds all tunable parameters for monthly behavioral
    analysis. Parameters are organized by the analysis method they affect.

    ╔══════════════════════════════════════════════════════════════════════════╗
    ║  CONFIGURATION MIGRATION NOTICE                                          ║
    ║                                                                          ║
    ║  This configuration class should be loaded from YAML in production.      ║
    ║  Current defaults are extracted from hardcoded values for initial        ║
    ║  implementation. Consider migrating to:                                  ║
    ║    argus/defaults/policy.yaml                           ║
    ╚══════════════════════════════════════════════════════════════════════════╝

    Attributes:
        metrics_to_analyze:
            Tuple of column names to analyze for month-over-month and rolling
            window analysis. Must exist in the monthly_data DataFrame.

        autocorrelation_metrics:
            Tuple of column names to analyze for autocorrelation. Typically
            excludes count-based metrics as they have different distributional
            properties.

        volatility_outlier_max_z:
            Maximum absolute z-score to include when calculating volatility.
            Values beyond this are excluded as likely data errors.

        gradual_escalation_min_months:
            Minimum consecutive months of increases required to flag gradual
            escalation pattern.

        significant_change_threshold:
            Minimum relative change (as decimal) to flag as significant
            month-over-month spike. 0.5 = 50% increase.

        percentile_95_z_score:
            Z-score corresponding to 95th percentile (1.645 for normal).
            Used to identify extreme values vs baseline.

        rolling_window_months:
            Number of months to include in rolling calculations.

        outlier_z_threshold:
            Z-score threshold for flagging outliers in rolling analysis.

        autocorr_max_lag:
            Maximum lag to calculate in autocorrelation function.

        autocorr_high_threshold:
            Lag-1 correlation above this indicates HIGH risk persistent pattern.

        autocorr_medium_threshold:
            Lag-1 correlation above this (but below high) indicates MEDIUM risk.

        min_records_statistical:
            Minimum records for most statistical analyses.

        min_records_autocorrelation:
            Minimum records for autocorrelation analysis (needs more data).
    """

    # Metrics configuration
    metrics_to_analyze: tuple[str, ...] = STANDARD_BEHAVIORAL_METRICS
    autocorrelation_metrics: tuple[str, ...] = AUTOCORRELATION_ANALYSIS_METRICS

    # Month-over-month parameters
    volatility_outlier_max_z: float = VOLATILITY_OUTLIER_MAX_Z_SCORE
    gradual_escalation_min_months: int = GRADUAL_ESCALATION_MINIMUM_CONSECUTIVE_MONTHS
    significant_change_threshold: float = SIGNIFICANT_RELATIVE_CHANGE_THRESHOLD
    percentile_95_z_score: float = PERCENTILE_95_Z_SCORE

    # Rolling window parameters
    rolling_window_months: int = DEFAULT_ROLLING_WINDOW_SIZE_MONTHS
    outlier_z_threshold: float = OUTLIER_Z_SCORE_THRESHOLD

    # Autocorrelation parameters
    autocorr_max_lag: int = AUTOCORRELATION_MAXIMUM_LAG
    autocorr_high_threshold: float = AUTOCORRELATION_HIGH_RISK_THRESHOLD
    autocorr_medium_threshold: float = AUTOCORRELATION_MEDIUM_RISK_THRESHOLD

    # Data sufficiency requirements
    min_records_statistical: int = MINIMUM_RECORDS_FOR_STATISTICAL_TEST
    min_records_autocorrelation: int = MINIMUM_RECORDS_FOR_AUTOCORRELATION


# =============================================================================
# RESULT DATA CLASSES
# =============================================================================


@dataclass
class SuddenSpikeResult:
    """Result of sudden spike detection for a single metric."""

    metric_name: str
    spike_months: list[str]
    highest_percentile: float


@dataclass
class GradualEscalationResult:
    """Result of gradual escalation detection for a single metric."""

    metric_name: str
    consecutive_increase_months: int


@dataclass
class MonthOverMonthResults:
    """Aggregated results from month-over-month analysis."""

    sudden_spikes: list[SuddenSpikeResult] = field(
        default_factory=list[SuddenSpikeResult]
    )
    gradual_escalation: list[GradualEscalationResult] = field(
        default_factory=list[GradualEscalationResult]
    )
    volatility_score: float = 0.0


@dataclass
class RollingWindowOutlierResult:
    """Result of rolling window outlier detection for a single metric."""

    outlier_months: list[str]
    maximum_z_score: float


@dataclass
class AutocorrelationResult:
    """Result of autocorrelation analysis for a single metric."""

    lag_1_correlation: float
    pattern_interpretation: str  # 'PERSISTENT_PATTERN' or 'MODERATE_PATTERN'
    risk_level: str  # 'HIGH' or 'MEDIUM'


# =============================================================================
# MONTHLY BEHAVIOR ANALYZER CLASS
# =============================================================================


class MonthlyBehaviorAnalyzer:
    """
    Analyzes monthly aggregated data for suspicious behavioral patterns.

    This class provides three complementary analysis methods that together
    identify different types of concerning patterns:

        1. Month-over-Month: Sudden spikes and gradual escalation
        2. Rolling Window: Deviations from recent baseline
        3. Autocorrelation: Persistent vs random behavior patterns

    The analyzer requires monthly aggregated data with standardized columns
    and baseline distributions for context.

    Attributes:
        monthly_data: DataFrame with monthly aggregated metrics per entity
        baseline_distributions: Dictionary mapping metric names to distribution
            parameters (mean, std, percentiles) from the broader population
        config: MonthlyAnalyzerConfiguration with all tunable parameters

    Example:
        >>> analyzer = MonthlyBehaviorAnalyzer(
        ...     monthly_data=driver_monthly_df,
        ...     baseline_distributions=fleet_baselines['Driver'],
        ... )
        >>> mom_results = analyzer.analyze_month_over_month_changes()
        >>> if mom_results.sudden_spikes:
        ...     print("Warning: Sudden behavioral spikes detected")
    """

    def __init__(
        self,
        monthly_data: pd.DataFrame,
        baseline_distributions: dict[str, dict[str, float]],
        configuration: MonthlyAnalyzerConfiguration | None = None,
    ) -> None:
        """
        Initialize the MonthlyBehaviorAnalyzer.

        Args:
            monthly_data:
                DataFrame indexed by month (typically pd.PeriodIndex) containing
                aggregated metrics. Expected columns include:
                - 'no_eld_rate': Percentage of transactions without ELD activity
                - 'non_diesel_rate': Percentage of non-diesel transactions
                - 'after_hours_rate': Percentage outside business hours
                - 'datetime_count': Number of unique transactions

            baseline_distributions:
                Dictionary mapping metric names to their distribution parameters
                from the broader entity population. Expected structure:
                {
                    'no_eld_rate': {'mean': X, 'std': Y, ...},
                    'non_diesel_rate': {'mean': X, 'std': Y, ...},
                    ...
                }
                Used to contextualize individual entity behavior.

            configuration:
                Optional MonthlyAnalyzerConfiguration instance. If None, uses
                default configuration with constants from _constants.py.

        Raises:
            ValueError: If monthly_data is empty.
        """
        if monthly_data.empty:
            raise ValueError('monthly_data cannot be empty')

        self._monthly_data: pd.DataFrame = monthly_data
        self._baseline_distributions: dict[str, dict[str, float]] = (
            baseline_distributions
        )
        self._config: MonthlyAnalyzerConfiguration = (
            configuration or MonthlyAnalyzerConfiguration()
        )

        logger.debug(
            'MonthlyBehaviorAnalyzer initialized with %d months of data, '
            '%d metrics configured',
            len(monthly_data),
            len(self._config.metrics_to_analyze),
        )

    # =========================================================================
    # MONTH-OVER-MONTH ANALYSIS
    # =========================================================================

    def analyze_month_over_month_changes(self) -> MonthOverMonthResults:
        """
        Analyze month-over-month changes to identify suspicious patterns.

        This method examines how metrics change from one month to the next,
        identifying:
            - Sudden Spikes: Significant increases flagged with baseline percentile
            - Gradual Escalation: 3+ consecutive months of increases
            - Volatility: Overall behavioral instability

        Returns:
            MonthOverMonthResults containing:
                - sudden_spikes: List of SuddenSpikeResult for each metric with spikes
                - gradual_escalation: List of GradualEscalationResult for escalating metrics
                - volatility_score: Cumulative volatility across all metrics

        Note:
            Metrics not present in both monthly_data and baseline_distributions
            are silently skipped.
        """
        results = MonthOverMonthResults()

        for metric_name in self._config.metrics_to_analyze:
            # Skip if metric not available in data or baseline
            if not self._is_metric_available(metric_name):
                continue

            baseline_mean: float
            baseline_std: float
            baseline_mean, baseline_std = self._get_baseline_parameters(metric_name)

            # Cannot calculate z-scores without variance
            if baseline_std == 0:
                logger.debug(
                    'Skipping %s: zero standard deviation in baseline', metric_name
                )
                continue

            metric_series: pd.Series = self._monthly_data[metric_name].dropna()

            if len(metric_series) < self._config.min_records_statistical:
                continue

            # Calculate smart change scores (handles zero-baseline gracefully)
            change_scores: pd.Series = self._calculate_change_scores(metric_series)

            if change_scores.empty:
                continue

            # Detect sudden spikes
            spike_result: SuddenSpikeResult | None = self._detect_sudden_spikes(
                metric_name=metric_name,
                metric_values=metric_series,
                change_scores=change_scores,
                baseline_mean=baseline_mean,
                baseline_std=baseline_std,
            )
            if spike_result:
                results.sudden_spikes.append(spike_result)

            # Detect gradual escalation
            escalation_result: GradualEscalationResult | None = (
                self._detect_gradual_escalation(
                    metric_name=metric_name,
                    change_scores=change_scores,
                )
            )
            if escalation_result:
                results.gradual_escalation.append(escalation_result)

            # Accumulate volatility
            metric_volatility: float = self._calculate_metric_volatility(change_scores)
            results.volatility_score += metric_volatility

        logger.debug(
            'Month-over-month analysis complete: %d spikes, %d escalations, '
            'volatility=%.3f',
            len(results.sudden_spikes),
            len(results.gradual_escalation),
            results.volatility_score,
        )

        return results

    def _is_metric_available(self, metric_name: str) -> bool:
        """Check if metric exists in both data and baseline."""
        return (
            metric_name in self._monthly_data.columns
            and metric_name in self._baseline_distributions
        )

    def _get_baseline_parameters(self, metric_name: str) -> tuple[float, float]:
        """Extract mean and standard deviation from baseline distributions."""
        baseline_stats: dict[str, float] = self._baseline_distributions[metric_name]
        return baseline_stats['mean'], baseline_stats['std']

    def _calculate_change_scores(self, metric_series: pd.Series) -> pd.Series:
        """
        Calculate smart change scores that handle zero-baseline gracefully.

        For each consecutive pair of values, calculates:
            - Both zero: 0.0 (no change)
            - Zero to non-zero: absolute value (emergence)
            - Non-zero to zero: negative absolute (disappearance)
            - Both non-zero: relative change (curr - prev) / prev

        Args:
            metric_series: Time-ordered Series of metric values.

        Returns:
            Series of change scores indexed by the "after" month.
        """
        change_scores_list: list[float] = []
        value_count: int = len(metric_series)

        for index in range(1, value_count):
            previous_value: float = float(metric_series.iloc[index - 1])
            current_value: float = float(metric_series.iloc[index])

            match (previous_value == 0.0, current_value == 0.0):
                case (True, True):
                    change_scores_list.append(0.0)
                case (True, False):
                    # Zero -> something: use absolute change
                    change_scores_list.append(current_value)
                case (False, True):
                    # Something -> zero: negative absolute change
                    change_scores_list.append(-previous_value)
                case (False, False):
                    # Both non-zero: relative change
                    change_scores_list.append(
                        (current_value - previous_value) / previous_value
                    )

        return pd.Series(change_scores_list, index=metric_series.index[1:])

    def _detect_sudden_spikes(
        self,
        metric_name: str,
        metric_values: pd.Series,
        change_scores: pd.Series,
        baseline_mean: float,
        baseline_std: float,
    ) -> SuddenSpikeResult | None:
        """
        Detect sudden spikes based on change scores and baseline percentiles.

        A spike is flagged when:
            - Relative change > significant_change_threshold (e.g., 50%), OR
            - Current value exceeds 95th percentile of baseline
        """
        spike_months: list[str] = []
        spike_percentiles: list[float] = []

        for score_index, change_score in enumerate(change_scores):
            # Get current month and value
            month: pd.Period = change_scores.index[score_index]
            current_value: float = metric_values.iloc[score_index + 1]

            # Calculate how extreme current value is vs baseline
            z_score: float = (current_value - baseline_mean) / baseline_std
            percentile: float = stats.norm.cdf(z_score) * 100

            # Flag as spike if significant change OR extreme percentile
            is_significant_change: bool = (
                change_score > self._config.significant_change_threshold
            )
            is_extreme_percentile: bool = z_score > self._config.percentile_95_z_score

            # Only flag increases, not decreases
            if (is_significant_change or is_extreme_percentile) and change_score > 0:
                spike_months.append(str(month))
                spike_percentiles.append(percentile)

        if spike_months:
            logger.debug(
                'Detected %d sudden spike(s) in %s: months=%s',
                len(spike_months),
                metric_name,
                spike_months,
            )
            return SuddenSpikeResult(
                metric_name=metric_name,
                spike_months=spike_months,
                highest_percentile=max(spike_percentiles),
            )

        return None

    def _detect_gradual_escalation(
        self,
        metric_name: str,
        change_scores: pd.Series,
    ) -> GradualEscalationResult | None:
        """
        Detect gradual escalation (N+ consecutive months of increases).
        """
        consecutive_increases: int = 0
        max_consecutive: int = 0

        for change_score in change_scores:
            if change_score > 0:
                consecutive_increases += 1
                max_consecutive = max(max_consecutive, consecutive_increases)
            else:
                consecutive_increases = 0

        if max_consecutive >= self._config.gradual_escalation_min_months:
            logger.debug(
                'Detected gradual escalation in %s: %d consecutive months',
                metric_name,
                max_consecutive,
            )
            return GradualEscalationResult(
                metric_name=metric_name,
                consecutive_increase_months=max_consecutive,
            )

        return None

    def _calculate_metric_volatility(self, change_scores: pd.Series) -> float:
        """
        Calculate volatility as standard deviation of change scores.

        Filters out extreme outliers to avoid inflating volatility from
        one-off data errors.
        """
        # Exclude extreme outliers
        filtered_scores: pd.Series = change_scores[
            abs(change_scores) < self._config.volatility_outlier_max_z
        ]

        if len(filtered_scores) <= 1:
            return 0.0

        volatility: float = filtered_scores.std()
        return float(volatility) if pd.notna(volatility) else 0.0

    # =========================================================================
    # ROLLING WINDOW ANALYSIS
    # =========================================================================

    def analyze_with_rolling_window(
        self,
    ) -> dict[str, RollingWindowOutlierResult]:
        """
        Identify outlier months using rolling window statistics.

        For each metric, calculates rolling mean and standard deviation,
        then flags months where the value deviates by more than the
        configured z-score threshold (default: 2 standard deviations).

        Returns:
            Dictionary mapping metric names to RollingWindowOutlierResult for
            metrics with detected outliers. Metrics without outliers are not
            included in the result.

        Note:
            Requires at least (window_size + 1) observations to produce
            meaningful results.
        """
        results: dict[str, RollingWindowOutlierResult] = {}
        window_size: int = self._config.rolling_window_months

        for metric_name in self._config.autocorrelation_metrics:
            if metric_name not in self._monthly_data.columns:
                continue

            metric_series: pd.Series = self._monthly_data[metric_name].copy()

            # Need sufficient data for rolling calculation
            if len(metric_series.dropna()) < window_size + 1:
                continue

            # Calculate rolling statistics
            rolling_mean: pd.Series = metric_series.rolling(
                window=window_size, min_periods=2
            ).mean()
            rolling_std: pd.Series = metric_series.rolling(
                window=window_size, min_periods=2
            ).std()

            # Calculate z-scores from rolling baseline
            z_scores: pd.Series = (metric_series - rolling_mean) / rolling_std
            z_scores = z_scores.replace([np.inf, -np.inf], np.nan)

            # Identify outlier months
            valid_z_scores: pd.Series = z_scores.dropna()
            outlier_mask: pd.Series = (
                valid_z_scores.abs() > self._config.outlier_z_threshold
            )
            outlier_indices: list[pd.Period] = valid_z_scores[
                outlier_mask
            ].index.tolist()

            if outlier_indices:
                outlier_months_str: list[str] = [str(m) for m in outlier_indices]
                max_z: float = float(valid_z_scores[outlier_mask].abs().max())

                results[metric_name] = RollingWindowOutlierResult(
                    outlier_months=outlier_months_str,
                    maximum_z_score=max_z,
                )

                logger.debug(
                    'Rolling window outliers in %s: %d months, max_z=%.2f',
                    metric_name,
                    len(outlier_months_str),
                    max_z,
                )

        return results

    # =========================================================================
    # AUTOCORRELATION ANALYSIS
    # =========================================================================

    def analyze_autocorrelation_patterns(self) -> dict[str, AutocorrelationResult]:
        """
        Detect systematic vs random behavioral patterns via autocorrelation.

        High lag-1 autocorrelation indicates that behavior is persistent
        (a high value tends to be followed by another high value), which
        is a stronger indicator of problematic behavior than random spikes.

        Returns:
            Dictionary mapping metric names to AutocorrelationResult for
            metrics exhibiting meaningful autocorrelation. Only includes
            metrics with correlation above the medium threshold.

        Note:
            Metrics with zero variance (all identical values) are skipped
            as autocorrelation is undefined.
        """
        results: dict[str, AutocorrelationResult] = {}

        for metric_name in self._config.autocorrelation_metrics:
            if metric_name not in self._monthly_data.columns:
                continue

            metric_series: pd.Series[Any] = self._monthly_data[metric_name].dropna()

            # Need sufficient data for ACF
            if len(metric_series) < self._config.min_records_autocorrelation:
                continue

            # Skip zero-variance series
            if metric_series.std() == 0 or metric_series.nunique() == 1:
                continue

            # Calculate autocorrelation with warning suppression
            acf_result: float | None = self._calculate_autocorrelation_safely(
                metric_series
            )
            if acf_result is None:
                continue

            lag_1_correlation: float = acf_result

            # Classify based on thresholds
            if lag_1_correlation > self._config.autocorr_high_threshold:
                results[metric_name] = AutocorrelationResult(
                    lag_1_correlation=lag_1_correlation,
                    pattern_interpretation='PERSISTENT_PATTERN',
                    risk_level='HIGH',
                )
                logger.info(
                    'HIGH risk persistent pattern in %s: lag-1 corr=%.3f',
                    metric_name,
                    lag_1_correlation,
                )

            elif lag_1_correlation > self._config.autocorr_medium_threshold:
                results[metric_name] = AutocorrelationResult(
                    lag_1_correlation=lag_1_correlation,
                    pattern_interpretation='MODERATE_PATTERN',
                    risk_level='MEDIUM',
                )
                logger.debug(
                    'MEDIUM risk moderate pattern in %s: lag-1 corr=%.3f',
                    metric_name,
                    lag_1_correlation,
                )

        return results

    def _calculate_autocorrelation_safely(self, series: pd.Series) -> float | None:
        """
        Calculate lag-1 autocorrelation with error handling.

        Args:
            series: Time-ordered numeric Series.

        Returns:
            Lag-1 autocorrelation coefficient, or None if calculation fails.
        """
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=RuntimeWarning)

                max_lag: int = min(self._config.autocorr_max_lag, len(series) - 1)
                acf_values: NDArray[np.float64] = cast(
                    NDArray[np.float64],
                    acf(series, nlags=max_lag, fft=False),
                )

            # Validate result
            if len(acf_values) < self._config.min_records_statistical or np.isnan(
                acf_values[1]
            ):
                return None

            return float(acf_values[1])

        except Exception as calculation_error:
            logger.debug(
                'Autocorrelation calculation failed: %s',
                calculation_error,
            )
            return None
