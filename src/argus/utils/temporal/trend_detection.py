# argus/utils/temporal/trend_detection.py
"""
Time series trend and change point detection algorithms.

This module provides statistical methods for identifying:
    - Monotonic trends (Mann-Kendall test)
    - Single change points (CUSUM algorithm)
    - Multiple change points (PELT algorithm)

These methods are non-parametric where possible, making them robust to
non-normal distributions commonly found in fuel transaction data.

Typical Usage:
    from argus.utils.temporal.trend_detection import (
        detect_monotonic_trend,
        detect_single_change_point,
        detect_all_change_points,
    )

    # Check for upward/downward trend
    trend_direction, effect_size, p_value = detect_monotonic_trend(monthly_amounts)

    # Find the first significant shift in behavior
    change_month = detect_single_change_point(monthly_rates)

    # Find all regime changes
    all_change_months = detect_all_change_points(monthly_rates)
"""

import logging
from typing import Any

import numpy as np
import pandas as pd
import ruptures as rpt
from numpy.typing import NDArray
from scipy import stats

from argus.utils.temporal._constants import (
    CUSUM_DECISION_THRESHOLD_H,
    CUSUM_REFERENCE_VALUE_K,
    MINIMUM_RECORDS_FOR_STATISTICAL_TEST,
    PELT_MINIMUM_RECORDS,
    PELT_MINIMUM_SEGMENT_LENGTH,
    STATISTICAL_SIGNIFICANCE_ALPHA,
)

__all__: list[str] = [
    'MannKendallResult',
    'detect_all_change_points',
    'detect_monotonic_trend',
    'detect_single_change_point',
]

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)


# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

# Result type for Mann-Kendall trend test
type MannKendallResult = tuple[str, float, float]


# =============================================================================
# MANN-KENDALL TREND DETECTION
# =============================================================================


def detect_monotonic_trend(
    time_series_data: pd.Series,
    significance_threshold: float = STATISTICAL_SIGNIFICANCE_ALPHA,
) -> MannKendallResult:
    """
    Detect monotonic (consistently increasing or decreasing) trends using Mann-Kendall test.

    The Mann-Kendall test is a non-parametric method that does not assume any specific
    distribution of the data. It tests whether there is a statistically significant
    tendency for values to increase or decrease over time.

    IMPORTANT LIMITATION:
        This test assumes that observations are serially independent. Monthly fuel data
        may exhibit autocorrelation (e.g., a high-volume month influencing the next),
        which can inflate the significance of detected trends. Results should be used
        as investigative indicators, triangulated with change point detection and other
        methods, rather than treated as conclusive proof of fraud.

    Algorithm:
        1. For each pair of observations (i, j) where i < j, count:
           - Concordant pairs (later value > earlier value): +1
           - Discordant pairs (later value < earlier value): -1
           - Tied pairs: 0
        2. Sum these to get the S statistic
        3. Calculate variance with tie correction
        4. Convert to Z-score and p-value
        5. Calculate Kendall's tau as effect size

    Args:
        time_series_data:
            A time-ordered pandas Series of numerical values. The index should
            represent time (e.g., dates, months) and values should be the metric
            being tested for trend. NaN values are dropped before analysis.

        significance_threshold:
            P-value threshold for declaring a trend significant. Default is 0.05
            (standard 95% confidence level). Lower values are more conservative.

    Returns:
        A tuple containing three elements:
            - trend_direction (str): One of:
                - 'increasing': Statistically significant upward trend
                - 'decreasing': Statistically significant downward trend
                - 'no_trend': No significant monotonic trend detected
                - 'insufficient_data': Fewer than 3 valid observations
            - kendalls_tau (float): Effect size measure ranging from -1 to +1.
                - +1 indicates perfect positive concordance (always increasing)
                - -1 indicates perfect negative concordance (always decreasing)
                - 0 indicates no association between time and values
                - NaN if insufficient data
            - p_value (float): Two-tailed probability of observing this trend
                (or more extreme) under the null hypothesis of no trend.
                - 1.0 if insufficient data or no variance

    Raises:
        No exceptions are raised; edge cases return appropriate sentinel values.

    Example:
        >>> import pandas as pd
        >>> monthly_rates = pd.Series([10, 12, 15, 18, 22, 25])
        >>> direction, tau, p_val = detect_monotonic_trend(monthly_rates)
        >>> print(f"Trend: {direction}, Effect Size: {tau:.3f}, p={p_val:.4f}")
        Trend: increasing, Effect Size: 1.000, p=0.0028

    See Also:
        - detect_single_change_point: For detecting abrupt shifts rather than gradual trends
        - detect_all_change_points: For finding multiple regime changes
    """
    # Remove missing values while preserving order
    clean_series: pd.Series = time_series_data.dropna()
    observation_count: int = len(clean_series)

    # Validate minimum data requirement
    if observation_count < MINIMUM_RECORDS_FOR_STATISTICAL_TEST:
        logger.debug(
            'Mann-Kendall test skipped: only %d observations (minimum %d required)',
            observation_count,
            MINIMUM_RECORDS_FOR_STATISTICAL_TEST,
        )
        return ('insufficient_data', np.nan, 1.0)

    # Calculate the S statistic by comparing all pairs
    s_statistic: int = _calculate_kendall_s_statistic(clean_series)

    # Calculate variance with tie correction
    variance_of_s: float = _calculate_s_variance_with_tie_correction(clean_series)

    if variance_of_s == 0:
        logger.debug('Mann-Kendall test: zero variance in data, no trend detectable')
        return ('no_trend', 0.0, 1.0)

    # Calculate Z-score with continuity correction
    z_score: float = _calculate_z_score_with_continuity_correction(
        s_statistic, variance_of_s
    )

    # Two-tailed p-value from standard normal distribution
    p_value: float = 2 * (1 - stats.norm.cdf(abs(z_score)))

    # Kendall's tau: effect size normalized to [-1, 1]
    total_pairs: float = 0.5 * observation_count * (observation_count - 1)
    kendalls_tau: float = s_statistic / total_pairs

    # Determine trend direction based on significance and direction
    if p_value < significance_threshold:
        trend_direction: str = 'increasing' if kendalls_tau > 0 else 'decreasing'
        logger.info(
            'Significant %s trend detected (tau=%.3f, p=%.4f)',
            trend_direction,
            kendalls_tau,
            p_value,
        )
    else:
        trend_direction = 'no_trend'
        logger.debug(
            'No significant trend detected (tau=%.3f, p=%.4f)',
            kendalls_tau,
            p_value,
        )

    return (trend_direction, kendalls_tau, p_value)


def _calculate_kendall_s_statistic(series: pd.Series) -> int:
    """
    Calculate the Kendall S statistic for Mann-Kendall trend test.

    The S statistic counts the difference between concordant and discordant pairs.
    A concordant pair has a later value greater than an earlier value.

    Args:
        series: Time-ordered pandas Series of numerical values.

    Returns:
        The S statistic (integer). Positive indicates upward trend tendency,
        negative indicates downward trend tendency.
    """
    observation_count: int = len(series)
    s_statistic: int = 0

    for earlier_index in range(observation_count - 1):
        for later_index in range(earlier_index + 1, observation_count):
            difference: float = series.iloc[later_index] - series.iloc[earlier_index]
            s_statistic += int(np.sign(difference))

    return s_statistic


def _calculate_s_variance_with_tie_correction(series: pd.Series) -> float:
    """
    Calculate the variance of the S statistic, accounting for tied values.

    When there are no ties, variance = n(n-1)(2n+5)/18.
    When ties exist, a correction term is subtracted for each tie group.

    Args:
        series: Time-ordered pandas Series of numerical values.

    Returns:
        The variance of S (float). Returns 0 if all values are identical.
    """
    observation_count: int = len(series)

    # Count occurrences of each unique value
    value_counts: pd.Series[int] = series.value_counts()
    unique_value_count: int = len(value_counts)

    # Base variance formula (no ties)
    base_variance: float = (
        observation_count * (observation_count - 1) * (2 * observation_count + 5)
    ) / 18

    if observation_count == unique_value_count:
        # No ties present
        return base_variance

    # Calculate tie correction: sum of t(t-1)(2t+5) for each tie group of size t
    tie_correction: int = sum(
        tie_count * (tie_count - 1) * (2 * tie_count + 5)
        for tie_count in value_counts
        if tie_count > 1
    )

    return base_variance - (tie_correction / 18)


def _calculate_z_score_with_continuity_correction(
    s_statistic: int, variance: float
) -> float:
    """
    Calculate Z-score from S statistic with continuity correction.

    The continuity correction (subtracting or adding 1 to S before dividing by
    standard deviation) improves the normal approximation for discrete S.

    Args:
        s_statistic: The Kendall S statistic.
        variance: The variance of S.

    Returns:
        The Z-score (float). Zero if S is zero.
    """
    standard_deviation: float = np.sqrt(variance)

    if s_statistic > 0:
        return (s_statistic - 1) / standard_deviation
    elif s_statistic < 0:
        return (s_statistic + 1) / standard_deviation
    else:
        return 0.0


# =============================================================================
# CUSUM CHANGE POINT DETECTION
# =============================================================================


def detect_single_change_point(
    time_series_data: pd.Series,
    reference_value_k: float = CUSUM_REFERENCE_VALUE_K,
    decision_threshold_h: float = CUSUM_DECISION_THRESHOLD_H,
) -> pd.Period | None:
    """
    Detect the first significant change point using the tabular CUSUM algorithm.

    CUSUM (Cumulative Sum) charts are highly effective at detecting small, persistent
    shifts in the mean of a process. The algorithm standardizes data to Z-scores and
    tracks two cumulative sums: one for upward shifts (positive) and one for downward
    shifts (negative). When either sum crosses the decision threshold, a change point
    is flagged.

    Algorithm:
        1. Standardize data to Z-scores using overall mean and standard deviation
        2. Initialize positive and negative cumulative sums to zero
        3. For each observation t:
           - C_pos[t] = max(0, C_pos[t-1] + Z[t] - k)  # Accumulates upward drift
           - C_neg[t] = min(0, C_neg[t-1] + Z[t] + k)  # Accumulates downward drift
        4. First time either |C| > h is the detected change point

    The reference value k acts as "slack" - small deviations below k are ignored,
    while the decision threshold h controls the false alarm rate.

    Args:
        time_series_data:
            A time-ordered pandas Series with a PeriodIndex (typically monthly).
            Values should be the metric being monitored for shifts. NaN values
            are dropped before analysis.

        reference_value_k:
            Reference value (slack parameter) in standard deviation units.
            Controls sensitivity to shift magnitude:
            - Smaller k: Detects smaller shifts more quickly, but more false alarms
            - Larger k: Only detects larger shifts, fewer false alarms
            - Typical range: 0.25 to 1.0 (default: 0.5)

        decision_threshold_h:
            Decision threshold in standard deviation units.
            Controls the tradeoff between detection speed and false alarm rate:
            - Smaller h: Faster detection but more false alarms
            - Larger h: Slower detection but fewer false alarms
            - Typical range: 4.0 to 5.0 (default: 4.5)

    Returns:
        The Period (typically month) where the first significant shift was detected,
        or None if no change point was found or if there was insufficient data.

    Raises:
        No exceptions are raised; edge cases return None.

    Example:
        >>> import pandas as pd
        >>> # Data with a shift at index 5
        >>> values = [10, 11, 10, 12, 11, 25, 26, 24, 27, 25]
        >>> months = pd.period_range('2024-01', periods=10, freq='M')
        >>> series = pd.Series(values, index=months)
        >>> change_month = detect_single_change_point(series)
        >>> print(f"Change detected at: {change_month}")
        Change detected at: 2024-06

    See Also:
        - detect_all_change_points: When you expect multiple regime changes
        - detect_monotonic_trend: When looking for gradual trends rather than shifts
    """
    # Clean and sort data
    clean_series: pd.Series = time_series_data.dropna().sort_index()
    observation_count: int = len(clean_series)

    if observation_count < MINIMUM_RECORDS_FOR_STATISTICAL_TEST:
        logger.debug(
            'CUSUM detection skipped: only %d observations (minimum %d required)',
            observation_count,
            MINIMUM_RECORDS_FOR_STATISTICAL_TEST,
        )
        return None

    # Standardize to Z-scores
    series_mean: float = clean_series.mean()
    series_std: float = clean_series.std(ddof=1)

    if series_std == 0:
        logger.debug('CUSUM detection skipped: zero variance in data')
        return None

    z_scores: pd.Series = (clean_series - series_mean) / series_std

    # Run CUSUM algorithm
    positive_cusum: NDArray[np.float64] = np.zeros(observation_count)
    negative_cusum: NDArray[np.float64] = np.zeros(observation_count)

    first_positive_crossing_index: int | None = None
    first_negative_crossing_index: int | None = None

    for observation_index in range(1, observation_count):
        current_z: float = z_scores.iloc[observation_index]

        # Accumulate positive deviations (detecting upward shifts)
        positive_cusum[observation_index] = max(
            0.0,
            positive_cusum[observation_index - 1] + current_z - reference_value_k,
        )

        # Accumulate negative deviations (detecting downward shifts)
        negative_cusum[observation_index] = min(
            0.0,
            negative_cusum[observation_index - 1] + current_z + reference_value_k,
        )

        # Check for threshold crossings
        if (
            first_positive_crossing_index is None
            and positive_cusum[observation_index] > decision_threshold_h
        ):
            first_positive_crossing_index = observation_index
            logger.debug(
                'CUSUM positive threshold crossed at index %d (C+=%.2f)',
                observation_index,
                positive_cusum[observation_index],
            )

        if (
            first_negative_crossing_index is None
            and negative_cusum[observation_index] < -decision_threshold_h
        ):
            first_negative_crossing_index = observation_index
            logger.debug(
                'CUSUM negative threshold crossed at index %d (C-=%.2f)',
                observation_index,
                negative_cusum[observation_index],
            )

    # Return the earliest detected change point
    crossing_indices: list[int] = [
        idx
        for idx in [first_positive_crossing_index, first_negative_crossing_index]
        if idx is not None
    ]

    if not crossing_indices:
        logger.debug('CUSUM: No change point detected')
        return None

    earliest_change_index: int = min(crossing_indices)
    change_period: pd.Period = clean_series.index[earliest_change_index]

    logger.info(
        'CUSUM change point detected at %s (index %d)',
        change_period,
        earliest_change_index,
    )

    return change_period


# =============================================================================
# PELT MULTIPLE CHANGE POINT DETECTION
# =============================================================================


def detect_all_change_points(
    time_series_data: pd.Series,
    minimum_segment_length: int = PELT_MINIMUM_SEGMENT_LENGTH,
    minimum_observations: int = PELT_MINIMUM_RECORDS,
) -> list[pd.Period]:
    """
    Detect ALL significant change points using the PELT algorithm.

    PELT (Pruned Exact Linear Time) is an optimal segmentation algorithm that
    efficiently finds multiple change points by minimizing a cost function plus
    a penalty term. Unlike CUSUM which finds only the first change, PELT identifies
    all regime changes in the data.

    Algorithm:
        The algorithm uses dynamic programming with pruning to achieve O(n) complexity
        in many practical cases. It uses:
        - RBF (Radial Basis Function) kernel for cost calculation
        - BIC (Bayesian Information Criterion) penalty to prevent overfitting

    Args:
        time_series_data:
            A time-ordered pandas Series with a PeriodIndex (typically monthly).
            Values should be the metric being analyzed. NaN values are dropped
            before analysis.

        minimum_segment_length:
            Minimum number of observations between change points. Prevents
            detection of spurious changes in very short intervals.
            Default is 2.

        minimum_observations:
            Minimum total observations required to attempt change point detection.
            Fewer observations result in empty list return. Default is 6.

    Returns:
        A list of Period objects representing detected change points, ordered
        chronologically. Returns empty list if insufficient data or no change
        points detected.

    Raises:
        No exceptions are raised; edge cases return empty list.

    Example:
        >>> import pandas as pd
        >>> # Data with two regime changes
        >>> values = [10, 11, 10, 25, 26, 24, 50, 51, 49, 52]
        >>> months = pd.period_range('2024-01', periods=10, freq='M')
        >>> series = pd.Series(values, index=months)
        >>> changes = detect_all_change_points(series)
        >>> print(f"Change points: {changes}")
        Change points: [Period('2024-04', 'M'), Period('2024-07', 'M')]

    See Also:
        - detect_single_change_point: When only the first change matters
        - detect_monotonic_trend: When looking for gradual trends
    """
    clean_values: NDArray[np.float64] = time_series_data.dropna().to_numpy()
    observation_count: int = len(clean_values)

    if observation_count < minimum_observations:
        logger.debug(
            'PELT detection skipped: only %d observations (minimum %d required)',
            observation_count,
            minimum_observations,
        )
        return []

    # Configure and run PELT algorithm with RBF kernel
    pelt_model: Any = rpt.Pelt(model='rbf', min_size=minimum_segment_length)
    pelt_model.fit(clean_values)

    # BIC penalty: 2 * log(n) balances model fit vs complexity
    bic_penalty: float = np.log(observation_count) * 2
    raw_change_points: list[int] = pelt_model.predict(pen=bic_penalty)

    # PELT returns indices 1-indexed and includes the endpoint; convert to 0-indexed
    # and exclude the final point (which is just the series end, not a change)
    change_indices: list[int] = [int(cp - 1) for cp in raw_change_points[:-1]]

    # Convert indices back to Period objects
    original_index: pd.Index[pd.Period] = time_series_data.dropna().index
    change_periods: list[pd.Period] = [original_index[idx] for idx in change_indices]

    if change_periods:
        logger.info(
            'PELT detected %d change point(s): %s',
            len(change_periods),
            [str(p) for p in change_periods],
        )
    else:
        logger.debug('PELT: No change points detected')

    return change_periods
