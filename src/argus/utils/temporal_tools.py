# ARGUS/utils/temporal_tools.py

import logging
import warnings
from typing import Any, cast

import numpy as np
import pandas as pd
import ruptures as rpt  # type: ignore
from numpy.typing import NDArray
from scipy import stats
from scipy.stats import mannwhitneyu  # type: ignore
from statsmodels.tsa.stattools import acf  # type: ignore

from .stat_tools import cliffs_delta

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)


def mann_kendall_trend_test(data: pd.Series) -> tuple[str, float, float]:
    """
    Performs the Mann-Kendall test to detect monotonic trends in time series data.

    This test is non-parametric, meaning it does not assume the data follows a specific
    distribution. It is well-suited for identifying consistent upward or downward
    movements over time.

    IMPORTANT LIMITATION: This test assumes that observations are serially independent.
    Monthly fuel data may exhibit autocorrelation (e.g., a high-volume month
    influencing the next), which can inflate the significance of detected trends.
    Therefore, results should be used as investigative indicators, triangulated with
    other methods like change point detection, rather than conclusive proof.

    Args:
        data (pd.Series): A time-ordered pandas Series of numerical data.

    Returns:
        tuple[str, float, float]: A tuple containing:
            - trend_direction (str): 'increasing', 'decreasing', or 'no trend'.
            - tau (float): Kendall's tau, a measure of the trend's effect size (-1 to 1).
            - p_value (float): The significance level of the trend.
    """
    data = data.dropna()
    n: int = len(data)

    if n < 3:
        return ('insufficient_data', np.nan, 1.0)

    # Calculate the S statistic
    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            s += np.sign(data.iloc[j] - data.iloc[i])

    # Calculate the variance of S, accounting for ties
    unique_vals: pd.Series[int] = data.value_counts()
    g: int = len(unique_vals)

    if n == g:  # No ties
        var_s: float = (n * (n - 1) * (2 * n + 5)) / 18
    else:  # Has ties
        tie_correction: int = sum(t * (t - 1) * (2 * t + 5) for t in unique_vals)
        var_s = (n * (n - 1) * (2 * n + 5) - tie_correction) / 18

    if var_s == 0:
        return ('no_trend', 0.0, 1.0)

    # Calculate the Z statistic with continuity correction
    if s > 0:
        z: float = (s - 1) / np.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / np.sqrt(var_s)
    else:
        z = 0.0

    # Two-tailed p-value from the standard normal distribution
    p_value: float = float(2 * (1 - stats.norm.cdf(abs(z))))  # type: ignore

    # Kendall's tau (effect size)
    tau: float = s / (0.5 * n * (n - 1))

    # Determine trend direction based on p-value and tau
    trend = 'no_trend'
    if p_value < 0.05:
        if tau > 0:
            trend = 'increasing'
        else:
            trend = 'decreasing'

    return (trend, tau, p_value)


def cusum_change_detection(
    data: pd.Series, k: float = 0.5, h: float = 4.5
) -> pd.Period | None:
    """
    Detects a change point in a time series using the tabular CUSUM algorithm.

    CUSUM (Cumulative Sum) charts are effective at detecting small, persistent shifts
    in the mean of a process. This function standardizes the data and tracks two
    cumulative sums: one for upward shifts (cpos) and one for downward shifts (cneg).
    When either sum crosses a decision threshold (h), a change point is flagged.

    Args:
        data (pd.Series): Time-ordered pandas Series.
        k (float): Reference value (slack), typically 0.5σ. Controls sensitivity.
                   A smaller k detects smaller shifts more quickly.
        h (float): Decision threshold, typically 4-5σ. Controls the false alarm rate.
                   A larger h reduces the number of false alarms.

    Returns:
        Optional[pd.Period]: The month where a significant shift occurred, or None.
    """
    series: pd.Series = data.dropna().sort_index()

    if len(series) < 3:
        return None

    # Standardize the data (convert to Z-scores)
    mean: float = series.mean()
    std: float = series.std(ddof=1)

    if std == 0:  # No variation in data
        return None

    z: pd.Series = (series - mean) / std

    # Initialize CUSUM statistics
    cpos: NDArray[np.float64] = np.zeros(len(z))  # Cumulative sum for upward shift
    cneg: NDArray[np.float64] = np.zeros(len(z))  # Cumulative sum for downward shift

    first_cross_pos: int | None = None
    first_cross_neg: int | None = None

    # Tabular CUSUM algorithm
    for i in range(1, len(z)):
        # Accumulate positive deviations from the mean
        cpos[i] = max(0.0, cpos[i - 1] + z.iloc[i] - k)
        # Accumulate negative deviations from the mean
        cneg[i] = min(0.0, cneg[i - 1] + z.iloc[i] + k)

        # Record the first time the thresholds are crossed
        if first_cross_pos is None and cpos[i] > h:
            first_cross_pos = i
        if first_cross_neg is None and cneg[i] < -h:
            first_cross_neg = i

    # Determine the earliest detected change point
    change_indices: list[int] = [
        idx for idx in [first_cross_pos, first_cross_neg] if idx is not None
    ]
    if not change_indices:
        return None

    earliest_change_idx = min(change_indices)
    return series.index[earliest_change_idx]


def segment_comparison_test(
    early_data: pd.Series, late_data: pd.Series
) -> tuple[float, str]:
    """
    Compares two time segments using the Mann-Whitney U test with Cliff's Delta effect size.

    This non-parametric test is ideal for comparing two independent samples when
    normality cannot be assumed. It determines if the distributions of the two
    segments are significantly different.

    Args:
        early_data (pd.Series): Data from the first time period.
        late_data (pd.Series): Data from the second time period.

    Returns:
        tuple[float, str]: A tuple containing:
            - p_value (float): The p-value from the test.
            - interpretation (str): A summary of the finding, including effect size.
    """
    early: pd.Series = early_data.dropna()
    late: pd.Series = late_data.dropna()

    if len(early) < 2 or len(late) < 2:
        return (1.0, 'insufficient_data')

    result: tuple[float, float] = mannwhitneyu(early, late, alternative='two-sided')

    p_value: float = result.pvalue  # type: ignore

    # Calculate effect size using Cliff's Delta (consistent with other analyses)
    effect_size_results: tuple[float, str] = cliffs_delta(
        late.to_numpy(), early.to_numpy()
    )
    # Note: late - early order so positive delta = increase
    delta: float = effect_size_results[0]
    effect_interpretation: str = effect_size_results[1]

    if p_value < 0.05:
        if np.median(late) > np.median(early):
            interpretation = (
                f'INCREASED (p={p_value:.3f}, δ={delta:.2f}, {effect_interpretation})'
            )
        else:
            interpretation = (
                f'DECREASED (p={p_value:.3f}, δ={delta:.2f}, {effect_interpretation})'
            )
    else:
        interpretation = f'NO CHANGE (p={p_value:.3f}, δ={delta:.2f})'

    return (p_value, interpretation)  # type: ignore


def month_over_month_analysis(
    monthly_data: pd.DataFrame, entity_type_distributions: dict[str, dict[str, float]]
) -> dict[str, Any]:
    """
    Compare each month to the previous month to catch sudden changes.
    Uses baseline distributions to report statistical significance.

    Analyzes month-over-month changes to identify:
    - Sudden spikes with percentile ranking vs. baseline
    - Gradual escalation (3+ consecutive months of increases)
    - Overall volatility (instability in behavior patterns)

    Args:
        monthly_data: DataFrame with monthly aggregated metrics
        entity_type_distributions: Baseline distribution for this entity type
                                   (already filtered to 'Driver' or 'VINIndex')

    Returns:
        dictionary with keys:
        - 'sudden_spikes': list of dicts with metric, months, and percentile
        - 'gradual_escalation': list of dicts with metric and consecutive_months
        - 'volatility_score': Float indicating overall behavior volatility
    """
    results: dict[str, Any] = {
        'sudden_spikes': [],
        'gradual_escalation': [],
        'volatility_score': 0.0,
    }

    # Metrics to analyze for month-over-month changes
    metrics_to_analyze: list[str] = [
        'no_eld_rate',
        'non_diesel_rate',
        'after_hours_rate',
        'datetime_count',
    ]

    for metric in metrics_to_analyze:
        # Skip if metric not in data or baseline
        if (
            metric not in monthly_data.columns
            or metric not in entity_type_distributions
        ):
            continue

        # Get baseline distribution parameters
        baseline_mean: float = entity_type_distributions[metric]['mean']
        baseline_std: float = entity_type_distributions[metric]['std']

        # Skip if no variance in baseline (can't calculate z-scores)
        if baseline_std == 0:
            continue

        # Get the metric values and drop any NaN values
        values: pd.Series = monthly_data[metric].dropna()

        # Need at least 2 months to calculate changes
        if len(values) < 2:
            continue

        # =====================================================================
        # CALCULATE SMART CHANGE SCORES (handles zero-baseline gracefully)
        # =====================================================================
        change_scores_list: list[float] = []
        for i in range(1, len(values)):
            prev_val: float = values.iloc[i - 1]
            curr_val: float = values.iloc[i]

            # Smart change calculation
            if prev_val == 0 and curr_val == 0:
                change_scores_list.append(0.0)
            elif prev_val == 0:
                # Zero to something - use absolute change
                change_scores_list.append(curr_val)
            elif curr_val == 0:
                # Something to zero - negative absolute change
                change_scores_list.append(-prev_val)
            else:
                # Both non-zero - use relative change
                change_scores_list.append((curr_val - prev_val) / prev_val)

        change_scores: pd.Series = pd.Series(change_scores_list, index=values.index[1:])

        # =====================================================================
        # DETECT SUDDEN SPIKES
        # =====================================================================
        # Flag significant increases: either >50% relative change OR
        # absolute value in that month is >2 std above baseline
        spike_months: list[str] = []
        spike_percentiles: list[float] = []

        for i, change in enumerate(change_scores):
            month: int = change_scores.index[i]
            curr_val: float = values.iloc[i + 1]

            # Calculate how extreme the current value is vs baseline
            z_score: float = (curr_val - baseline_mean) / baseline_std
            percentile: float = float(stats.norm.cdf(z_score) * 100)  # type: ignore

            # Flag as spike if:
            # 1. Significant relative change (>50% increase), OR
            # 2. Current value is extreme (>95th percentile)
            is_spike: bool = (change > 0.5) or (
                z_score > 1.645
            )  # 1.645 = 95th percentile

            if is_spike and change > 0:  # Only flag increases, not decreases
                spike_months.append(str(month))
                spike_percentiles.append(percentile)

        if len(spike_months) > 0:
            results['sudden_spikes'].append(
                {
                    'metric': metric,
                    'months': spike_months,
                    'percentile': float(
                        max(spike_percentiles)
                    ),  # Report highest percentile
                }
            )

        # =====================================================================
        # DETECT GRADUAL ESCALATION (3+ consecutive months of increases)
        # =====================================================================
        consecutive_increases: int = 0
        max_consecutive: int = 0

        for change in change_scores:
            if change > 0:
                consecutive_increases += 1
                max_consecutive = max(max_consecutive, consecutive_increases)
            else:
                consecutive_increases = 0

        if max_consecutive >= 3:
            results['gradual_escalation'].append(
                {'metric': metric, 'consecutive_months': int(max_consecutive)}
            )

        # =====================================================================
        # CALCULATE VOLATILITY (standard deviation of change scores)
        # =====================================================================
        # Filter out extreme outliers (absolute changes > 5x) to avoid
        # inflating volatility from one-off data errors
        volatility_values: pd.Series = change_scores[abs(change_scores) < 5.0]

        if len(volatility_values) > 1:
            metric_volatility: float = volatility_values.std()
            if pd.notna(metric_volatility):
                results['volatility_score'] += float(metric_volatility)

    return results


def rolling_window_analysis(
    monthly_data: pd.DataFrame, window: int = 3
) -> dict[str, dict[str, list[str] | float]]:
    """
    Calculate rolling statistics to identify when behavior diverges from baseline.
    Window of 3 months smooths out noise while remaining responsive.

    Uses rolling mean and standard deviation to calculate z-scores for each month.
    Months with |z-score| > 2 are flagged as outliers (2 standard deviations from
    the rolling baseline).

    Args:
        monthly_data: DataFrame with monthly aggregated metrics
        window: Rolling window size in months (default: 3)

    Returns:
        dictionary mapping metric names to outlier information:
        {
            'metric_name': {
                'outlier_months': ['2024-06', '2024-09'],
                'max_z_score': 2.87
            }
        }
    """
    results: dict[str, dict[str, list[str] | float]] = {}

    # Metrics to analyze with rolling windows
    metrics_to_analyze: list[str] = [
        'no_eld_rate',
        'non_diesel_rate',
        'after_hours_rate',
    ]

    for metric in metrics_to_analyze:
        # Skip if metric not in data
        if metric not in monthly_data.columns:
            continue

        # Get the metric series
        series: pd.Series = monthly_data[metric].copy()

        # Need at least window size + 1 for meaningful rolling analysis
        if len(series.dropna()) < window + 1:
            continue

        # Calculate rolling mean and std
        rolling_mean: pd.Series[np.float64] = series.rolling(
            window=window, min_periods=2
        ).mean()
        rolling_std: pd.Series[np.float64] = series.rolling(
            window=window, min_periods=2
        ).std()

        # Calculate z-score from rolling baseline
        # Z-score = (actual - rolling_mean) / rolling_std
        z_scores: pd.Series = (series - rolling_mean) / rolling_std

        # Replace infinite values with NaN (can happen when rolling_std = 0)
        z_scores = z_scores.replace([np.inf, -np.inf], np.nan)  # type: ignore

        # Get the months that are outliers (filter out NaN z-scores first)
        valid_z_scores: pd.Series = z_scores.dropna()
        # Find outlier months (|z| > 2)
        outlier_mask: pd.Series = valid_z_scores.abs() > 2
        outlier_months: list[int] = valid_z_scores[outlier_mask].index.tolist()

        if len(outlier_months) > 0:
            # Convert Period index to strings for serialization
            outlier_months_str: list[str] = [str(month) for month in outlier_months]

            # Get the maximum absolute z-score among outliers
            max_z_score: float = valid_z_scores[outlier_mask].abs().max()

            results[metric] = {
                'outlier_months': outlier_months_str,
                'max_z_score': float(max_z_score),
            }

    return results


def autocorrelation_analysis(
    monthly_data: pd.DataFrame, max_lag: int = 3
) -> dict[str, dict[str, float | str]]:
    """
    Detect if suspicious behavior is becoming systematic rather than random.
    High autocorrelation = behavior is persistent (very bad sign).

    Autocorrelation measures whether values in a time series are related to their
    own past values. High positive autocorrelation at lag-1 indicates that high
    values tend to be followed by high values (persistent bad behavior).

    Args:
        monthly_data: DataFrame with monthly aggregated metrics
        max_lag: Maximum lag to calculate (default: 3)

    Returns:
        dictionary mapping metric names to autocorrelation analysis:
        {
            'metric_name': {
                'lag1_correlation': 0.78,
                'interpretation': 'PERSISTENT_PATTERN',
                'risk_level': 'HIGH'
            }
        }
    """
    results: dict[str, dict[str, float | str]] = {}

    # Metrics to analyze for autocorrelation
    metrics_to_analyze: list[str] = [
        'no_eld_rate',
        'non_diesel_rate',
        'after_hours_rate',
    ]

    for metric in metrics_to_analyze:
        # Skip if metric not in data
        if metric not in monthly_data.columns:
            continue

        # Get the metric series and drop NaN values
        series: pd.Series[Any] = monthly_data[metric].dropna()

        # Need at least 5 observations for meaningful autocorrelation
        if len(series) < 5:
            continue

        # Check for zero variance (all values are the same)
        if series.std() == 0 or series.nunique() == 1:
            # All values are identical - no autocorrelation to calculate
            # This isn't necessarily suspicious, could just be consistently low/high
            continue

        try:
            # Suppress warnings about division by zero in ACF calculation
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=RuntimeWarning)

                # Calculate autocorrelation function
                acf_values: NDArray[np.float64] = acf(  # type: ignore[assignment]
                    series, nlags=min(max_lag, len(series) - 1), fft=False
                )

            # Check if ACF calculation produced valid results
            if len(acf_values) < 2 or np.isnan(acf_values[1]):
                continue

            # Get lag-1 autocorrelation (correlation with previous month)
            lag1_correlation: float = float(acf_values[1])

            # High lag-1 autocorrelation indicates persistent behavior
            if lag1_correlation > 0.6:
                results[metric] = {
                    'lag1_correlation': lag1_correlation,
                    'interpretation': 'PERSISTENT_PATTERN',
                    'risk_level': 'HIGH',
                }
            elif lag1_correlation > 0.4:
                results[metric] = {
                    'lag1_correlation': lag1_correlation,
                    'interpretation': 'MODERATE_PATTERN',
                    'risk_level': 'MEDIUM',
                }
            # Only include in results if there's meaningful autocorrelation
            # Don't clutter output with low correlations

        except Exception:
            # If ACF calculation fails for any reason, skip this metric
            # Don't let one metric failure break the entire analysis
            continue

    return results


def detect_multiple_changepoints(
    series: pd.Series, min_segment_length: int = 2
) -> list[pd.Period]:
    """
    Detect ALL significant change points, not just the first one.
    Uses Pruned Exact Linear Time (PELT) algorithm.
    """
    values = series.dropna().values

    if len(values) < 6:
        return []

    # PELT algorithm with BIC penalty
    model: Any = cast(
        Any, rpt.Pelt(model='rbf', min_size=min_segment_length).fit(values)
    )  # type: ignore
    change_points: list[float] = model.predict(pen=np.log(len(values)) * 2)

    # Convert float indices to integers
    change_indices: list[int] = [int(cp - 1) for cp in change_points[:-1]]
    # Convert indices to months
    change_months: list[pd.Period] = [
        series.index[idx] for idx in change_indices
    ]  # Last point is always end

    return change_months


def detect_fraud_patterns(monthly_data: pd.DataFrame) -> dict[str, bool]:
    """
    Look for specific patterns commonly associated with fuel card fraud.

    Pattern Definitions:
    - Off-Hours Concentration: >60% of transactions outside normal business hours
    - Spike-and-Retreat: Sudden 50%+ increase followed by 40%+ drop within 2 months
    - Gradual Escalation: Second half average >30% higher than first half
    - Operational Anomaly: Behavior inconsistent with expected business patterns
    """
    patterns: dict[str, bool] = {
        'off_hours_concentration': False,
        'spike_retreat': False,
        'gradual_escalation': False,
        'operational_anomaly': False,
    }

    # Off-Hours Concentration Pattern
    if 'after_hours_rate' in monthly_data.columns:
        recent_avg: float = monthly_data['after_hours_rate'].tail(3).mean()
        if recent_avg > 60:  # More than 60% after hours
            patterns['off_hours_concentration'] = True

    # Spike-and-Retreat Pattern (spike followed by drop >40%)
    for metric in ['datetime_count', 'no_eld_rate']:
        if metric in monthly_data.columns:
            values: pd.Series = monthly_data[metric]
            for i in range(len(values) - 2):
                if values.iloc[i + 1] > values.iloc[i] * 1.5:  # 50% spike
                    if values.iloc[i + 2] < values.iloc[i + 1] * 0.6:  # 40% drop
                        patterns['spike_retreat'] = True

    # Gradual Escalation Pattern (6+ months of steady increase)
    if 'no_eld_rate' in monthly_data.columns:
        values = monthly_data['no_eld_rate']
        if len(values) >= 6:
            first_half: float = values.iloc[: len(values) // 2].mean()
            second_half: float = values.iloc[len(values) // 2 :].mean()
            if second_half > first_half * 1.3:  # 30% increase
                patterns['gradual_escalation'] = True

    return patterns


def compare_temporal_risk_distributions(
    target_risks: list[float], other_risks: list[float]
) -> dict[str, float | bool | str] | None:
    """
    Perform statistical comparison of temporal risk score distributions.
    Uses Mann-Whitney U test and Cliff's Delta effect size, consistent with
    the cost distribution analysis methodology.

    Args:
        target_risks: list of risk scores for target location entities
        other_risks: list of risk scores for other location entities

    Returns:
        dictionary containing:
        - p_value: Statistical significance (Mann-Whitney U test)
        - is_significant: Boolean (p < 0.05)
        - effect_size: Cliff's Delta
        - effect_size_name: "Cliff's Delta"
        - direction: 'higher', 'lower', or 'negligible'
        - target_mean, target_median, target_p25, target_p75
        - others_mean, others_median, others_p25, others_p75
        - mean_difference, median_difference
        - target_n, others_n

        Returns None if insufficient data
    """
    # Convert to numpy arrays and ensure we have data
    target_array: NDArray[np.float64] = np.array(target_risks)
    others_array: NDArray[np.float64] = np.array(other_risks)

    # Need at least 2 observations per group for Mann-Whitney U test
    if len(target_array) < 2 or len(others_array) < 2:
        return None

    # Mann-Whitney U test (non-parametric comparison of distributions)
    mannwhitney_result: tuple[float, float] = mannwhitneyu(
        target_array, others_array, alternative='two-sided'
    )

    u_stat: float = float(mannwhitney_result.statistic)  # type: ignore
    p_value: float = float(mannwhitney_result.pvalue)  # type: ignore

    # Cliff's Delta: effect size for ordinal/non-normal data
    # Measures probability that random value from target > random value from others
    delta, delta_interpretation = cliffs_delta(target_array, others_array)

    # Calculate summary statistics for target location
    target_mean = float(np.mean(target_array))
    target_median = float(np.median(target_array))
    target_p25 = float(np.percentile(target_array, 25))
    target_p75 = float(np.percentile(target_array, 75))

    # Calculate summary statistics for other locations
    others_mean = float(np.mean(others_array))
    others_median = float(np.median(others_array))
    others_p25 = float(np.percentile(others_array, 25))
    others_p75 = float(np.percentile(others_array, 75))

    # Calculate differences
    mean_diff: float = target_mean - others_mean
    median_diff: float = target_median - others_median

    # Determine direction for interpretation
    # Using same thresholds as cost analysis for consistency
    if abs(delta) < 0.15:
        direction = 'negligible'
    elif delta > 0:
        direction = 'higher'
    else:
        direction = 'lower'

    return {
        'p_value': float(p_value),
        'is_significant': p_value < 0.05,
        'u_statistic': float(u_stat),
        # Effect size (standardized, interpretable)
        'effect_size': float(delta),
        'effect_size_name': "Cliff's Delta",
        'effect_interpretation': delta_interpretation,
        'direction': direction,
        # Target location statistics
        'target_mean': target_mean,
        'target_median': target_median,
        'target_p25': target_p25,
        'target_p75': target_p75,
        'target_n': len(target_array),
        # Other locations statistics
        'others_mean': others_mean,
        'others_median': others_median,
        'others_p25': others_p25,
        'others_p75': others_p75,
        'others_n': len(others_array),
        # Differences (for context, not effect size)
        'mean_difference': mean_diff,
        'median_difference': median_diff,
    }


def create_baseline_from_others(
    others_df: pd.DataFrame, min_months: int = 3
) -> dict[str, dict[str, dict[str, float]]]:
    """
    Create separate baseline distributions for drivers and vehicles.

    Returns:
        dictionary with two baselines:
        {
            'Driver': {
                'no_eld_rate': {'mean': X, 'std': Y, ...},
                'non_diesel_rate': {...},
                ...
            },
            'VINIndex': {
                'no_eld_rate': {'mean': X, 'std': Y, ...},
                ...
            }
        }
    """
    # Validate required columns
    required_columns: list[str] = [
        'month',
        'Driver',
        'VINIndex',
        'has_eld_activity',
        'is_diesel_def',
        'is_business_hours',
        'cost',
        'datetime_parsed',
    ]
    missing: list[str] = [
        col for col in required_columns if col not in others_df.columns
    ]
    if missing:
        raise ValueError(f'Missing required columns: {missing}')

    # Storage for monthly metrics by entity type
    baselines: dict[str, list[dict[str, Any]]] = {'Driver': [], 'VINIndex': []}

    # Process each entity type separately
    for entity_type in ['Driver', 'VINIndex']:
        logger.debug(f'\nBuilding baseline for {entity_type}s...')

        # Get unique entities of this type
        unique_entities_array: np.ndarray = others_df[entity_type].dropna().unique()
        unique_entities: list[str | int] = [
            e for e in unique_entities_array if e and e != 'Unknown'
        ]

        logger.debug(f'  Found {len(unique_entities)} unique {entity_type}s')

        # Process each entity
        for entity_id in unique_entities:
            # Filter to this entity
            entity_df: pd.DataFrame = others_df[
                others_df[entity_type] == entity_id
            ].copy()

            # Skip if insufficient data
            if len(entity_df) < min_months or entity_df['month'].nunique() < min_months:
                continue

            # Aggregate by month
            for month, group in entity_df.groupby('month'):  # type: ignore
                # Count unique transactions
                unique_transactions: int = (
                    group['datetime_parsed'].nunique()
                    if 'datetime_parsed' in group.columns
                    else len(group)
                )

                # Calculate monthly metrics
                monthly_record: dict[str, str | int | float | pd.Period] = {
                    'entity_id': entity_id,
                    'month': month,  # type: ignore
                    'datetime_count': unique_transactions,
                    'no_eld_rate': 100 * (~group['has_eld_activity']).mean(),
                    'non_diesel_rate': 100 * (~group['is_diesel_def']).mean(),
                    'after_hours_rate': 100 * (~group['is_business_hours']).mean(),
                    'cost_mean': group['cost'].mean(),
                    'cost_median': group['cost'].median(),
                    'cost_sum': group['cost'].sum(),
                }

                baselines[entity_type].append(monthly_record)

        logger.debug(f'  Collected {len(baselines[entity_type])} entity-months')

    # Calculate distribution parameters for each entity type
    metrics_to_baseline: list[str] = [
        'datetime_count',
        'no_eld_rate',
        'non_diesel_rate',
        'after_hours_rate',
        'cost_mean',
        'cost_median',
        'cost_sum',
    ]

    baseline_stats: dict[str, dict[str, dict[str, float | int]]] = {}

    for entity_type in ['Driver', 'VINIndex']:
        baseline_df = pd.DataFrame(baselines[entity_type])

        if len(baseline_df) == 0:
            logger.warning(f'WARNING: No valid {entity_type} data for baseline')
            continue

        baseline_stats[entity_type] = {}

        for metric in metrics_to_baseline:
            values: pd.Series[Any] = baseline_df[metric].dropna()

            if len(values) > 0:
                baseline_stats[entity_type][metric] = {
                    'mean': float(np.mean(values)),
                    'std': float(np.std(values)),
                    'median': float(np.median(values)),
                    'q25': float(np.percentile(values, 25)),
                    'q75': float(np.percentile(values, 75)),
                    'q90': float(np.percentile(values, 90)),
                    'q95': float(np.percentile(values, 95)),
                    'q99': float(np.percentile(values, 99)),
                    'min': float(np.min(values)),
                    'max': float(np.max(values)),
                    'count': len(values),
                }

    return baseline_stats
