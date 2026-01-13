# argus/utils/tail_test.py

"""
Tail Distribution Analysis Module for ARGUS.

This module provides statistical tools to analyze the tail behavior of distributions
and determine whether log transformations would be beneficial for downstream analysis.
The primary use case is detecting heavy-tailed (right-skewed) data common in financial
and operational metrics like transaction amounts, fuel costs, and time durations.

The main entry point is `decide_log1p()`, which orchestrates several focused helper
functions to produce a recommendation and diagnostic metrics.
"""

import logging
import math
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy.stats import kurtosis, skew

__all__: list[str] = ['decide_log1p']

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)


# =============================================================================
# Constants & Thresholds
# =============================================================================
# These thresholds are based on standard statistical heuristics for detecting
# heavy-tailed distributions. They can be tuned based on domain-specific needs.

# Minimum number of data points required to make a statistically valid decision.
MINIMUM_SAMPLE_SIZE: int = 30

# Percentiles to compute in a single pass for efficiency.
# Corresponds to [Q1, Median, Q3, P90, P99]
PERCENTILES_TO_COMPUTE: list[float] = [25, 50, 75, 90, 99]

# Thresholds for detecting heavy tails (Right-Skewed Data)
SKEWNESS_THRESHOLD: float = 1.0
EXCESS_KURTOSIS_THRESHOLD: float = 3.0
P99_TO_P50_RATIO_THRESHOLD: float = 3.0

# Outlier Detection: Fraction of data allowed beyond (Median + 3*IQR)
TAIL_FRACTION_THRESHOLD: float = 0.02

# The minimum percentage reduction in dispersion (MAD/Median) required to justify
# applying the log transformation. If the reduction is less than this, the added
# complexity of the log transform is deemed unnecessary.
MINIMUM_DISPERSION_REDUCTION_PERCENT: float = 20.0


# =============================================================================
# Data Preparation Functions
# =============================================================================


def _clean_series_for_analysis(raw_input_series: pd.Series) -> pd.Series:
    """
    Clean and prepare a pandas Series for statistical analysis.

    This function coerces non-numeric values to NaN and removes all null values,
    producing a clean numeric Series suitable for statistical computations.

    Args:
        raw_input_series: The pandas Series to clean. May contain mixed types,
                          strings, nulls, or other non-numeric values.

    Returns:
        A pandas Series containing only valid numeric (float64) values.
        The returned Series may be empty if no valid numeric values exist.

    Side Effects:
        Logs DEBUG message with original and cleaned row counts.
    """
    original_count: int = len(raw_input_series)

    clean_numeric_series: pd.Series = pd.to_numeric(
        raw_input_series, errors='coerce'
    ).dropna()

    cleaned_count: int = len(clean_numeric_series)
    dropped_count: int = original_count - cleaned_count

    logger.debug(
        'Data cleaning complete: %d original rows, %d valid numeric rows, %d dropped',
        original_count,
        cleaned_count,
        dropped_count,
    )

    return clean_numeric_series


def _initialize_diagnostics_dict(
    sample_size: int, has_negative_values: bool
) -> dict[str, Any]:
    """
    Initialize the diagnostics dictionary with default NaN values.

    This function creates the standard diagnostics structure used throughout
    the tail analysis process. All numeric fields are initialized to NaN to
    indicate "not yet computed" state.

    CRITICAL: The keys in this dictionary are part of the public API contract.
    Downstream logic depends on these exact key names. DO NOT MODIFY KEYS.

    Args:
        sample_size: The count of valid observations in the cleaned series.
        has_negative_values: Boolean flag indicating presence of negative values.

    Returns:
        A dictionary with all diagnostic fields initialized.
        Numeric fields are set to math.nan, rules_triggered is an empty list.
    """
    diagnostics: dict[str, Any] = {
        'n': sample_size,
        # Check for negative values immediately. Log1p is undefined/invalid for x < -1,
        # and generally we expect strictly non-negative data (like cost, volume) for this test.
        'has_negative': has_negative_values,
        'skew': math.nan,
        'excess_kurtosis': math.nan,
        'p50': math.nan,
        'p90_over_p50': math.nan,
        'p99_over_p50': math.nan,
        'iqr': math.nan,
        'tail_frac_over_p50_plus_3iqr': math.nan,
        'mad_over_median': math.nan,
        'mad_over_median_log1p': math.nan,
        'dispersion_reduction_pct': math.nan,
        'rules_triggered': [],
    }

    logger.debug(
        'Initialized diagnostics dict: n=%d, has_negative=%s',
        sample_size,
        has_negative_values,
    )

    return diagnostics


# =============================================================================
# Statistical Calculation Functions
# =============================================================================


def _calculate_shape_statistics(clean_numeric_series: pd.Series) -> tuple[float, float]:
    """
    Calculate skewness and excess kurtosis for a numeric series.

    Skewness measures the asymmetry of the distribution:
    - Positive skew indicates a right tail (common in financial data)
    - Negative skew indicates a left tail

    Excess kurtosis (Fisher's definition) measures tail heaviness relative to normal:
    - Values > 0 indicate heavier tails than normal distribution
    - Values < 0 indicate lighter tails than normal distribution

    Args:
        clean_numeric_series: A pandas Series of clean numeric values.
                              Must contain at least 3 observations for valid results.

    Returns:
        A tuple of (skewness, excess_kurtosis) as floats.
        Both use bias=False for sample-corrected estimates.

    Side Effects:
        Logs DEBUG message with computed shape statistics.
    """
    # bias=False corrects for statistical bias in sample skew/kurtosis estimates
    skewness_value: float = float(skew(clean_numeric_series, bias=False))
    excess_kurtosis_value: float = float(
        kurtosis(clean_numeric_series, fisher=True, bias=False)
    )

    logger.debug(
        'Shape statistics calculated: skewness=%.4f, excess_kurtosis=%.4f',
        skewness_value,
        excess_kurtosis_value,
    )

    return (skewness_value, excess_kurtosis_value)


def _calculate_percentiles_and_iqr(
    clean_numeric_series: pd.Series,
) -> tuple[float, float, float, float]:
    """
    Calculate key percentiles and interquartile range in a single pass.

    This function computes Q1, Median (P50), Q3, P90, P99, and IQR efficiently
    by calculating all percentiles in one numpy operation to minimize sorting overhead.

    Args:
        clean_numeric_series: A pandas Series of clean numeric values.

    Returns:
        A tuple of four floats in order:
        (median_value, p90_value, p99_value, interquartile_range)

    Side Effects:
        Logs DEBUG message with computed percentile values.
    """
    # Compute all required percentiles in a single pass to minimize sorting overhead.
    # Order: [25 (Q1), 50 (Median), 75 (Q3), 90, 99]
    percentile_values_array: NDArray[np.floating] = np.percentile(
        clean_numeric_series, PERCENTILES_TO_COMPUTE
    )

    # Unpack and cast explicitly for type safety and clarity
    q1_value: float = float(percentile_values_array[0])
    median_value: float = float(percentile_values_array[1])
    q3_value: float = float(percentile_values_array[2])
    p90_value: float = float(percentile_values_array[3])
    p99_value: float = float(percentile_values_array[4])

    interquartile_range: float = q3_value - q1_value

    logger.debug(
        'Percentiles calculated: Q1=%.4f, P50=%.4f, Q3=%.4f, P90=%.4f, P99=%.4f, IQR=%.4f',
        q1_value,
        median_value,
        q3_value,
        p90_value,
        p99_value,
        interquartile_range,
    )

    return (median_value, p90_value, p99_value, interquartile_range)


def _calculate_median_absolute_deviation(
    clean_numeric_series: pd.Series, median_value: float
) -> float:
    """
    Calculate the Median Absolute Deviation (MAD) from the median.

    MAD is a robust measure of statistical dispersion that is less sensitive
    to outliers than standard deviation. It's calculated as the median of the
    absolute deviations from the data's median.

    Formula: MAD = median(|X_i - median(X)|)

    Args:
        clean_numeric_series: A pandas Series of clean numeric values.
        median_value: The pre-computed median of the series.

    Returns:
        The Median Absolute Deviation as a float.

    Side Effects:
        Logs DEBUG message with the computed MAD value.
    """
    absolute_deviation_from_median: pd.Series = (
        clean_numeric_series - median_value
    ).abs()
    median_absolute_deviation: float = float(absolute_deviation_from_median.median())

    logger.debug(
        'Median Absolute Deviation calculated: MAD=%.4f', median_absolute_deviation
    )

    return median_absolute_deviation


def _calculate_percentile_ratios(
    median_value: float,
    p90_value: float,
    p99_value: float,
    median_absolute_deviation: float,
) -> tuple[float, float, float]:
    """
    Calculate ratios that indicate tail heaviness relative to the center.

    These ratios help identify heavy-tailed distributions:
    - P90/P50 > 2 suggests moderate right skew
    - P99/P50 >= 3 suggests heavy right tail
    - MAD/Median indicates overall dispersion relative to center

    Args:
        median_value: The median (P50) of the distribution.
        p90_value: The 90th percentile value.
        p99_value: The 99th percentile value.
        median_absolute_deviation: The MAD of the distribution.

    Returns:
        A tuple of three floats: (p90_over_p50, p99_over_p50, mad_over_median).
        Returns np.inf for any ratio where division by zero would occur.

    Side Effects:
        Logs DEBUG message with computed ratios.
        Logs WARNING if median is zero (ratios become infinite).
    """
    if median_value > 0:
        p90_over_p50: float = p90_value / median_value
        p99_over_p50: float = p99_value / median_value
        mad_over_median: float = median_absolute_deviation / median_value
    else:
        # If median is 0, ratios are undefined (Infinity).
        logger.warning(
            'Median value is zero or negative (%.4f); percentile ratios set to infinity',
            median_value,
        )
        p90_over_p50 = np.inf
        p99_over_p50 = np.inf
        mad_over_median = np.inf

    logger.debug(
        'Percentile ratios calculated: P90/P50=%.4f, P99/P50=%.4f, MAD/Median=%.4f',
        p90_over_p50,
        p99_over_p50,
        mad_over_median,
    )

    return (p90_over_p50, p99_over_p50, mad_over_median)


def _calculate_tail_fraction(
    clean_numeric_series: pd.Series,
    median_value: float,
    interquartile_range: float,
) -> float:
    """
    Calculate the fraction of data points in the extreme right tail.

    The "extreme tail" is defined as values beyond (Median + 3*IQR). This threshold
    is based on the empirical rule: for normal distributions, virtually no data
    should exceed this boundary. A high fraction indicates fat-tailed behavior
    characteristic of log-normal or power-law distributions.

    Args:
        clean_numeric_series: A pandas Series of clean numeric values.
        median_value: The median (P50) of the distribution.
        interquartile_range: The IQR (Q3 - Q1) of the distribution.

    Returns:
        The fraction (0.0 to 1.0) of data points exceeding the tail threshold.
        Returns 0.0 if IQR is zero or non-positive (no meaningful tail boundary).

    Side Effects:
        Logs DEBUG message with tail threshold and fraction.
    """
    if interquartile_range > 0:
        tail_cutoff_threshold: float = median_value + (3 * interquartile_range)
    else:
        # If IQR is zero (constant data), there's no meaningful tail boundary
        tail_cutoff_threshold = np.inf

    if np.isfinite(tail_cutoff_threshold):
        tail_fraction: float = float(
            (clean_numeric_series > tail_cutoff_threshold).mean()
        )
    else:
        tail_fraction = 0.0

    logger.debug(
        'Tail fraction calculated: threshold=%.4f, fraction=%.4f (%.2f%%)',
        tail_cutoff_threshold if np.isfinite(tail_cutoff_threshold) else float('inf'),
        tail_fraction,
        tail_fraction * 100,
    )

    return tail_fraction


# =============================================================================
# Transformation Evaluation Functions
# =============================================================================


def _evaluate_log1p_transformation(
    clean_numeric_series: pd.Series,
) -> float:
    """
    Evaluate the effect of log1p transformation on data dispersion.

    This function applies log1p(x) = ln(1 + x) to the data and calculates
    the MAD/Median dispersion metric on the transformed values. Log1p is
    preferred over log because it handles zero values gracefully.

    The dispersion metric (MAD/Median) measures relative spread:
    - Lower values indicate tighter, more symmetric distributions
    - Comparing before/after transformation shows if log helps

    Args:
        clean_numeric_series: A pandas Series of clean, non-negative numeric values.
                              Values must be >= 0 for log1p to be valid.

    Returns:
        - mad_over_median_log1p: Dispersion metric after transformation

    Side Effects:
        Logs DEBUG message with transformation results.
        Logs WARNING if transformed median is non-positive.
    """
    # Convert to numpy array with explicit float64 type for numerical precision
    log_transformed_values: NDArray[np.float64] = np.log1p(
        clean_numeric_series.to_numpy(dtype=np.float64, copy=False)
    )

    # Calculate median of transformed data
    median_log_transformed: float = float(np.percentile(log_transformed_values, 50))

    # Calculate MAD manually using NumPy (working with NDArray, not Series)
    abs_deviation_log: NDArray[np.float64] = np.abs(
        log_transformed_values - median_log_transformed
    )
    mad_log_transformed: float = float(np.median(abs_deviation_log))

    # Calculate dispersion metric for transformed data
    if median_log_transformed > 0:
        mad_over_median_log1p: float = mad_log_transformed / median_log_transformed
    else:
        logger.warning(
            'Log-transformed median is non-positive (%.4f); dispersion set to infinity',
            median_log_transformed,
        )
        mad_over_median_log1p = np.inf

    logger.debug(
        'Log1p transformation evaluated: median_log=%.4f, MAD_log=%.4f, dispersion_log=%.4f',
        median_log_transformed,
        mad_log_transformed,
        mad_over_median_log1p,
    )

    return mad_over_median_log1p


def _calculate_dispersion_reduction(
    original_dispersion: float, transformed_dispersion: float
) -> float:
    """
    Calculate the percentage reduction in dispersion from log transformation.

    This metric quantifies how much the log1p transformation "tightens" the
    distribution. A positive percentage means the transformation reduced spread,
    making the data more symmetric and easier to model.

    Formula: reduction_pct = 100 * (original - transformed) / original

    Args:
        original_dispersion: MAD/Median ratio of the original data.
        transformed_dispersion: MAD/Median ratio after log1p transformation.

    Returns:
        The percentage reduction in dispersion (can be negative if transformation
        increased dispersion). Returns math.nan if inputs are non-finite or
        original dispersion is zero/negative.

    Side Effects:
        Logs DEBUG message with dispersion comparison.
        Logs INFO message if transformation increased dispersion (negative reduction).
    """
    if not (np.isfinite(original_dispersion) and np.isfinite(transformed_dispersion)):
        logger.debug(
            'Cannot calculate dispersion reduction: non-finite inputs '
            '(original=%.4f, transformed=%.4f)',
            original_dispersion,
            transformed_dispersion,
        )
        return math.nan

    if original_dispersion <= 0:
        logger.debug(
            'Cannot calculate dispersion reduction: original dispersion is %.4f',
            original_dispersion,
        )
        return 0.0

    reduction_amount: float = original_dispersion - transformed_dispersion
    dispersion_reduction_pct: float = 100.0 * reduction_amount / original_dispersion

    logger.debug(
        'Dispersion reduction: original=%.4f, transformed=%.4f, reduction=%.2f%%',
        original_dispersion,
        transformed_dispersion,
        dispersion_reduction_pct,
    )

    if dispersion_reduction_pct < 0:
        logger.info(
            'Log1p transformation INCREASED dispersion by %.2f%%; transformation not beneficial',
            abs(dispersion_reduction_pct),
        )

    return dispersion_reduction_pct


# =============================================================================
# Rule Evaluation Functions
# =============================================================================


def _evaluate_heavy_tail_rules(
    skewness: float,
    excess_kurtosis: float,
    p99_over_p50: float,
    tail_fraction: float,
) -> list[str]:
    """
    Evaluate heuristic rules for detecting heavy-tailed distributions.

    This function checks multiple statistical indicators against established
    thresholds to identify heavy right tails. Multiple triggered rules provide
    stronger evidence of heavy-tailed behavior.

    Rules evaluated:
    1. Skewness > 1.0 (moderate to high positive skew)
    2. Excess Kurtosis > 3.0 (heavier tails than normal)
    3. P99/P50 >= 3.0 (extreme values are 3x+ the median)
    4. Tail fraction >= 2% beyond (P50 + 3*IQR)

    Args:
        skewness: Sample skewness of the distribution.
        excess_kurtosis: Fisher's excess kurtosis of the distribution.
        p99_over_p50: Ratio of 99th percentile to median.
        tail_fraction: Fraction of data beyond (median + 3*IQR).

    Returns:
        A list of string identifiers for each triggered rule.
        CRITICAL: These exact strings are part of the API contract. DO NOT MODIFY.

    Side Effects:
        Logs DEBUG message for each rule evaluated.
        Logs INFO message summarizing triggered rules.
    """
    rules_triggered: list[str] = []

    # Rule 1: High positive skewness indicates right tail
    logger.debug(
        'Evaluating skewness rule: %.4f vs threshold %.4f', skewness, SKEWNESS_THRESHOLD
    )
    if skewness > SKEWNESS_THRESHOLD:
        rules_triggered.append('skew>1')

    # Rule 2: High excess kurtosis indicates heavy tails
    logger.debug(
        'Evaluating kurtosis rule: %.4f vs threshold %.4f',
        excess_kurtosis,
        EXCESS_KURTOSIS_THRESHOLD,
    )
    if excess_kurtosis > EXCESS_KURTOSIS_THRESHOLD:
        rules_triggered.append('excess_kurtosis>3')

    # Rule 3: Extreme percentile ratio indicates long right tail
    logger.debug(
        'Evaluating P99/P50 rule: %.4f vs threshold %.4f',
        p99_over_p50,
        P99_TO_P50_RATIO_THRESHOLD,
    )
    if p99_over_p50 >= P99_TO_P50_RATIO_THRESHOLD:
        rules_triggered.append('p99/p50>=3')

    # Rule 4: Significant mass in extreme tail
    logger.debug(
        'Evaluating tail fraction rule: %.4f vs threshold %.4f',
        tail_fraction,
        TAIL_FRACTION_THRESHOLD,
    )
    if tail_fraction >= TAIL_FRACTION_THRESHOLD:
        rules_triggered.append('tail>2% beyond p50+3*IQR')

    if rules_triggered:
        logger.info(
            'Heavy tail rules triggered (%d of 4): %s',
            len(rules_triggered),
            ', '.join(rules_triggered),
        )
    else:
        logger.debug('No heavy tail rules triggered; distribution appears well-behaved')

    return rules_triggered


def _make_final_decision(
    rules_triggered: list[str], dispersion_reduction_pct: float
) -> bool:
    """
    Make the final decision on whether to recommend log1p transformation.

    The recommendation requires BOTH conditions to be true:
    1. At least one heavy-tail indicator rule was triggered
    2. The log1p transformation meaningfully reduces dispersion

    This dual requirement prevents unnecessary transformations:
    - Heavy tail without dispersion improvement: transform won't help
    - Dispersion improvement without heavy tail: data is already well-behaved

    Args:
        rules_triggered: List of triggered heavy-tail rule identifiers.
        dispersion_reduction_pct: Percentage reduction in MAD/Median dispersion.

    Returns:
        True if log1p transformation is recommended, False otherwise.

    Side Effects:
        Logs INFO message with final decision and reasoning.
    """
    has_heavy_tail_signal: bool = len(rules_triggered) > 0
    is_dispersion_improved: bool = (
        dispersion_reduction_pct >= MINIMUM_DISPERSION_REDUCTION_PERCENT
    )

    should_use_log: bool = has_heavy_tail_signal and is_dispersion_improved

    # Log decision with clear reasoning
    if should_use_log:
        logger.info(
            'DECISION: Recommend log1p transformation '
            '(heavy_tail=%s, dispersion_reduction=%.2f%% >= %.2f%%)',
            has_heavy_tail_signal,
            dispersion_reduction_pct,
            MINIMUM_DISPERSION_REDUCTION_PERCENT,
        )
    else:
        reason_parts: list[str] = []
        if not has_heavy_tail_signal:
            reason_parts.append('no heavy tail detected')
        if not is_dispersion_improved:
            reason_parts.append(
                f'insufficient dispersion reduction ({dispersion_reduction_pct:.2f}% < '
                f'{MINIMUM_DISPERSION_REDUCTION_PERCENT:.2f}%)'
            )
        logger.info(
            'DECISION: Do NOT recommend log1p transformation (%s)',
            '; '.join(reason_parts),
        )

    return should_use_log


# =============================================================================
# Main Entry Point
# =============================================================================


def decide_log1p(
    raw_input_series: pd.Series, minimum_sample_size: int = MINIMUM_SAMPLE_SIZE
) -> tuple[bool, dict[str, Any]]:
    """
    Decide whether to apply a log1p transformation based on statistical properties.

    This function analyzes the distribution of the input series to detect heavy right tails
    (positive skew) and determines if a log1p transformation significantly reduces
    the dispersion of the data.

    It returns a boolean decision and a dictionary of diagnostic metrics.

    The analysis proceeds through several stages:
    1. Data cleaning and validation
    2. Shape statistics (skew, kurtosis)
    3. Percentile analysis and dispersion metrics
    4. Log1p transformation evaluation
    5. Heuristic rule application
    6. Final decision synthesis

    Args:
        raw_input_series: The pandas Series to evaluate. Can contain non-numeric or null values.
        minimum_sample_size: The minimum number of valid, non-null observations required
                             to perform the test. Defaults to 30.

    Returns:
        A tuple containing:
        1. use_log1p (bool): True if the series is heavy-tailed AND log1p reduces dispersion
                             significantly. False otherwise.
        2. diagnostics (dict): A dictionary containing calculated statistics and flags.
                               KEYS ARE IMMUTABLE FOR DOWNSTREAM COMPATIBILITY.

    Side Effects:
        Logs INFO message at start and end of analysis.
        Logs DEBUG messages throughout for detailed tracing.
        Logs WARNING for edge cases (zero median, non-positive values after transform).
    """
    logger.info(
        'Starting log1p decision analysis for series with %d raw elements',
        len(raw_input_series),
    )

    # ==========================================================================
    # Stage 1: Data Cleaning
    # ==========================================================================
    clean_numeric_series: pd.Series = _clean_series_for_analysis(raw_input_series)

    # Determine if negative values are present (disqualifies log1p)
    has_negative_values: bool = bool((clean_numeric_series < 0).any())

    # Initialize diagnostics with sample metadata
    diagnostics: dict[str, Any] = _initialize_diagnostics_dict(
        sample_size=len(clean_numeric_series),
        has_negative_values=has_negative_values,
    )

    # ==========================================================================
    # Stage 2: Pre-flight Checks
    # ==========================================================================
    # If we have insufficient data or negative values, we cannot recommend log1p safely.
    if diagnostics['n'] < minimum_sample_size:
        logger.info(
            'Insufficient sample size (%d < %d); returning early with no recommendation',
            diagnostics['n'],
            minimum_sample_size,
        )
        return (False, diagnostics)

    if diagnostics['has_negative']:
        logger.info(
            'Negative values detected in series; log1p is invalid. Returning early with no recommendation'
        )
        return (False, diagnostics)

    # ==========================================================================
    # Stage 3: Calculate Shape Statistics
    # ==========================================================================
    shape_stats: tuple[float, float] = _calculate_shape_statistics(clean_numeric_series)
    skewness_value: float = shape_stats[0]
    excess_kurtosis_value: float = shape_stats[1]
    diagnostics['skew'] = skewness_value
    diagnostics['excess_kurtosis'] = excess_kurtosis_value

    # ==========================================================================
    # Stage 4: Calculate Percentiles and Dispersion Metrics
    # ==========================================================================
    percentiles_and_iqr: tuple[float, float, float, float] = (
        _calculate_percentiles_and_iqr(clean_numeric_series)
    )

    median_value: float = percentiles_and_iqr[0]
    p90_value: float = percentiles_and_iqr[1]
    p99_value: float = percentiles_and_iqr[2]
    interquartile_range: float = percentiles_and_iqr[3]

    diagnostics['p50'] = median_value
    diagnostics['iqr'] = interquartile_range

    # Calculate MAD for original data
    median_absolute_deviation: float = _calculate_median_absolute_deviation(
        clean_numeric_series, median_value
    )

    # Calculate percentile ratios (indicators of tail heaviness)
    percentile_ratios: tuple[float, float, float] = _calculate_percentile_ratios(
        median_value=median_value,
        p90_value=p90_value,
        p99_value=p99_value,
        median_absolute_deviation=median_absolute_deviation,
    )
    p90_over_p50: float = percentile_ratios[0]
    p99_over_p50: float = percentile_ratios[1]
    mad_over_median: float = percentile_ratios[2]

    diagnostics['p90_over_p50'] = p90_over_p50
    diagnostics['p99_over_p50'] = p99_over_p50
    diagnostics['mad_over_median'] = mad_over_median

    # Calculate tail mass beyond (Median + 3*IQR)
    tail_fraction: float = _calculate_tail_fraction(
        clean_numeric_series=clean_numeric_series,
        median_value=median_value,
        interquartile_range=interquartile_range,
    )
    diagnostics['tail_frac_over_p50_plus_3iqr'] = tail_fraction

    # ==========================================================================
    # Stage 5: Evaluate Log1p Transformation Effect
    # ==========================================================================
    mad_over_median_log1p: float = _evaluate_log1p_transformation(clean_numeric_series)
    diagnostics['mad_over_median_log1p'] = mad_over_median_log1p

    # Calculate improvement in dispersion
    dispersion_reduction_pct: float = _calculate_dispersion_reduction(
        original_dispersion=mad_over_median,
        transformed_dispersion=mad_over_median_log1p,
    )
    diagnostics['dispersion_reduction_pct'] = dispersion_reduction_pct

    # ==========================================================================
    # Stage 6: Apply Heuristic Rules
    # ==========================================================================
    rules_triggered: list[str] = _evaluate_heavy_tail_rules(
        skewness=skewness_value,
        excess_kurtosis=excess_kurtosis_value,
        p99_over_p50=p99_over_p50,
        tail_fraction=tail_fraction,
    )
    diagnostics['rules_triggered'] = rules_triggered

    # ==========================================================================
    # Stage 7: Final Decision
    # ==========================================================================
    should_use_log: bool = _make_final_decision(
        rules_triggered=rules_triggered,
        dispersion_reduction_pct=dispersion_reduction_pct,
    )

    logger.info(
        'Log1p decision analysis complete: recommend_log1p=%s, rules_triggered=%d, dispersion_reduction=%.2f%%',
        should_use_log,
        len(rules_triggered),
        dispersion_reduction_pct
        if np.isfinite(dispersion_reduction_pct)
        else float('nan'),
    )

    return (should_use_log, diagnostics)
