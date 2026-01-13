# ARGUS/categoricals.py

import logging
import math
from typing import Any, NamedTuple

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

from argus.models import StatisticalTest
from argus.utils import (
    benjamini_hochberg_correction,
    bootstrap_ci,
    chi_square_test,
    cliffs_delta,
    odds_ratio_ci,
    risk_ratio_ci,
    two_prop_z_test,
)
from argus.models.context.context_model import AnalysisContext

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)

# ========================================================================
# Helper Functions
# ========================================================================


def add_inverted_column(
    df: pd.DataFrame, source_col: str, target_col: str
) -> pd.DataFrame:
    """Add a column that is the inverse of an existing boolean column."""
    return df.assign(**{target_col: ~df[source_col]})


def add_comparison_column(
    df: pd.DataFrame, source_col: str, target_col: str, threshold: float
) -> pd.DataFrame:
    """Add a boolean column based on comparing a column to a threshold."""
    return df.assign(**{target_col: df[source_col] > threshold})


def _calculate_categorical_test(
    target_df: pd.DataFrame, other_df: pd.DataFrame, condition_col: str, alpha: float
) -> tuple[float, dict[str, Any]]:
    """
    Run a full suite of statistical tests for a binary categorical metric.

    Args:
        target_df: DataFrame for the target group
        other_df: DataFrame for the baseline group
        condition_col: Boolean column defining the event of interest
        alpha: Significance level for confidence intervals

    Returns:
        tuple of (raw_p_value, metrics_dict)
        Returns (np.nan, {}) if insufficient data for testing
    """
    target_n: int = len(target_df)
    other_n: int = len(other_df)

    # Check for sufficient data
    if target_n == 0 or other_n == 0:
        logger.warning(
            'Statistical testing failed: target_df size=%d, others_df size=%d', target_n, other_n
        )
        return math.nan, {}

    if condition_col not in target_df.columns or condition_col not in other_df.columns:
        logger.warning(
            'Statistical testing failed: column named %r not in one or both dataframes', condition_col
        )
        return math.nan, {}

    target_count = int(target_df[condition_col].sum())
    other_count = int(other_df[condition_col].sum())

    # Two-proportion z-test for significance
    p_value: float = two_prop_z_test(target_count, target_n, other_count, other_n)

    # Calculate effect sizes
    rr: float
    rr_l: float
    rr_u: float
    rr, rr_l, rr_u = risk_ratio_ci(target_count, target_n, other_count, other_n, alpha)
    or_val: float
    or_l: float
    or_u: float
    or_val, or_l, or_u = odds_ratio_ci(
        target_count, target_n, other_count, other_n, alpha
    )

    # Chi-square test for association strength
    contingency: np.ndarray = np.array(
        [[target_count, target_n - target_count], [other_count, other_n - other_count]]
    )
    cramers_v: float
    _, _, cramers_v = chi_square_test(contingency)

    metrics: dict[str, int | float | str | tuple[float, float]] = {
        'target_count': target_count,
        'target_n': target_n,
        'target_rate': target_count / target_n if target_n > 0 else 0.0,
        'baseline_count': other_count,
        'baseline_n': other_n,
        'baseline_rate': other_count / other_n if other_n > 0 else 0.0,
        'risk_ratio': rr,
        'risk_ratio_ci': (rr_l, rr_u),
        'odds_ratio': or_val,
        'odds_ratio_ci': (or_l, or_u),
        'effect_size': cramers_v,
        'effect_size_name': "Cramér's V",
    }

    return p_value, metrics


def _analyze_cost_distribution(
    context: AnalysisContext,
) -> tuple[float, dict[str, int | float | str]]:
    """
    Perform statistical analysis on transaction cost distributions.
    Uses non-parametric tests as cost data is often non-normal.

    Args:
        target_df: DataFrame for the target group
        other_df: DataFrame for the baseline group
        alpha: Significance level (unused here but kept for consistency)
        n_boot: Number of bootstrap iterations (unused here but kept for consistency)

    Returns:
        tuple of (raw_p_value, metrics_dict)
        Returns (1.0, {}) if insufficient data
    """
    target_df: pd.DataFrame = context.target_period_transactions.copy()
    peers_df: pd.DataFrame = context.peer_period_transactions.copy()
    target_cost: pd.Series[float] = target_df['cost'].dropna()
    other_cost: pd.Series[float] = peers_df['cost'].dropna()

    # Need at least 2 observations per group for Mann-Whitney U test
    if len(target_cost) < 2 or len(other_cost) < 2:  # noqa: PLR2004
        return 1.0, {}

    # Mann-Whitney U test (non-parametric alternative to t-test)
    res: NamedTuple = mannwhitneyu(target_cost, other_cost, alternative='two-sided')
    p_value = float(res.pvalue)

    # Cliff's Delta: effect size for ordinal/non-normal data
    delta: float
    delta, _ = cliffs_delta(target_cost.to_numpy(), other_cost.to_numpy())

    # Calculate summary statistics
    target_mean = float(target_cost.mean())
    target_median = float(target_cost.median())
    baseline_mean = float(other_cost.mean())
    baseline_median = float(other_cost.median())

    # Calculate differences
    mean_diff: float = target_mean - baseline_mean
    median_diff: float = target_median - baseline_median
    pct_diff: float = (mean_diff / baseline_mean * 100) if baseline_mean > 0 else 0.0

    # Determine direction for interpretation
    direction: str = ''
    if abs(delta) < context.config.thresholds.effect_sizes.cliffs_delta.negligible:
        direction = 'negligible'
    elif delta > 0:
        direction = 'higher'
    elif delta < 0:
        direction = 'lower'

    # Calculate percentiles for additional context
    target_p25 = float(target_cost.quantile(0.25))
    target_p75 = float(target_cost.quantile(0.75))
    baseline_p25 = float(other_cost.quantile(0.25))
    baseline_p75 = float(other_cost.quantile(0.75))

    metrics: dict[str, int | float | str] = {
        'target_total': float(target_cost.sum()),
        'baseline_total': float(other_cost.sum()),
        'target_avg': target_mean,
        'baseline_avg': baseline_mean,
        'target_median': target_median,
        'baseline_median': baseline_median,
        'mean_difference': mean_diff,
        'median_difference': median_diff,
        'percent_difference': pct_diff,
        'target_n': len(target_cost),
        'baseline_n': len(other_cost),
        'target_p25': target_p25,
        'target_p75': target_p75,
        'baseline_p25': baseline_p25,
        'baseline_p75': baseline_p75,
        'effect_size': delta,
        'effect_size_name': "Cliff's Delta",
        'direction': direction,
    }

    return p_value, metrics


def _calculate_exposure_estimate(
    target_df: pd.DataFrame, other_df: pd.DataFrame, alpha: float, n_boot: int
) -> dict[str, Any] | None:
    """
    Estimate potential financial exposure from excess unverified transactions.

    This calculates how much money is at risk due to transactions that exceed
    the baseline rate of unverified transactions.

    Args:
        target_df: DataFrame for the target group
        other_df: DataFrame for the baseline group
        alpha: Significance level for confidence intervals
        n_boot: Number of bootstrap iterations for CI calculation

    Returns:
        dictionary with exposure details, or None if no excess exposure detected
    """
    # Calculate unverified transaction rates
    target_unverified: int = (~target_df['has_eld_activity']).sum()
    other_unverified: int = (~other_df['has_eld_activity']).sum()

    target_rate: float = (
        target_unverified / len(target_df) if len(target_df) > 0 else 0.0
    )
    baseline_rate: float = (
        other_unverified / len(other_df) if len(other_df) > 0 else 0.0
    )

    # Only calculate exposure if target rate exceeds baseline
    if target_rate <= baseline_rate:
        return None

    # Calculate excess transactions
    excess_count = int((target_rate - baseline_rate) * len(target_df))

    # Get costs of unverified transactions in target group
    unverified_costs: pd.Series = target_df.loc[
        ~target_df['has_eld_activity'], 'cost'
    ].dropna()

    if excess_count <= 0 or unverified_costs.empty:
        return None

    # Calculate exposure estimate
    avg_cost = float(unverified_costs.mean())
    total_exposure: float = excess_count * avg_cost

    # Bootstrap confidence interval for more robust mean estimate
    try:
        cost_ci: tuple[float, float, float] = bootstrap_ci(
            unverified_costs.to_numpy(), np.mean, alpha, n_boot
        )
        exposure_ci_low: float = excess_count * cost_ci[1]
        exposure_ci_high: float = excess_count * cost_ci[2]

        return {
            'excess_count': excess_count,
            'avg_cost': avg_cost,
            'total_exposure': total_exposure,
            'confidence_interval': (exposure_ci_low, exposure_ci_high),
        }
    except Exception:
        # If bootstrap fails, return without CI
        return {
            'excess_count': excess_count,
            'avg_cost': avg_cost,
            'total_exposure': total_exposure,
        }


# ========================================================================
# Main Public Function
# ========================================================================


def run_key_metric_analysis(context: AnalysisContext) -> dict[str, StatisticalTest]:
    """
    Orchestrate calculation and reporting of all key statistical tests.

    This function:
    1. Defines and runs categorical tests for risk indicators
    2. Analyzes cost distribution differences
    3. Applies multiple testing correction (Benjamini-Hochberg FDR)
    4. Calculates financial exposure if warranted
    5. Delegates all output to the report writer

    Args:
        context: An AnalysisContext object containing:
            target_location: Main analysis data for the target branch
            others: Main analysis data for all other branches
            report_writer: Instance of ForensicReportWriter for output
            alpha: Significance level for statistical tests
            n_boot: Number of bootstrap iterations for confidence intervals
            config: Master configuration object for the current run

    Returns:
        dictionary mapping test names to StatisticalTest objects
    """
    target_df: pd.DataFrame = context.target_period_transactions.copy()
    peers_df: pd.DataFrame = context.peer_period_transactions.copy()
    alpha: float = context.config.analysis.get_alpha()
    all_p_values: dict[str, float] = {}
    all_tests: dict[str, StatisticalTest] = {}

    # Define all categorical tests with their data preparation logic
    test_definitions: dict[str, dict[str, Any]] = {
        'No ELD Match': {
            'col': 'has_eld_activity_inv',
            'source_col': 'has_eld_activity',
            'operation': 'invert',
        },
        'Non-Diesel/DEF Purchases': {
            'col': 'is_diesel_def_inv',
            'source_col': 'is_diesel_def',
            'operation': 'invert',
        },
        'After-Hours Transactions': {
            'col': 'is_business_hours_inv',
            'source_col': 'is_business_hours',
            'operation': 'invert',
        },
        'Multiple Same-Day Fillups': {
            'col': 'fillups_per_day_gt1',
            'source_col': 'fillups_per_day',
            'operation': 'compare',
            'threshold': 1,
        },
    }

    # Step 1: Calculate all categorical tests
    for test_name, params in test_definitions.items():
        try:
            # Prepare dataframes based on operation type
            if params['operation'] == 'invert':
                target_prep: pd.DataFrame = add_inverted_column(
                    target_df, params['source_col'], params['col']
                )
                others_prep: pd.DataFrame = add_inverted_column(
                    peers_df, params['source_col'], params['col']
                )
            elif params['operation'] == 'compare':
                target_prep = add_comparison_column(
                    target_df,
                    params['source_col'],
                    params['col'],
                    params['threshold'],
                )
                others_prep = add_comparison_column(
                    peers_df, params['source_col'], params['col'], params['threshold']
                )
            else:
                raise ValueError(f'Unknown operation: {params["operation"]}')

            p_val: float
            metrics: dict[str, Any]
            p_val, metrics = _calculate_categorical_test(
                target_prep, others_prep, params['col'], alpha
            )
            if math.isnan(p_val):
                logger.warning('Statistical tests for %r failed.', test_name)

            # Only store valid test results
            if metrics:
                all_p_values[test_name] = p_val
                all_tests[test_name] = StatisticalTest(
                    name=test_name, p_value=p_val, **metrics
                )
        except Exception as e:
            # Log the error but continue with other tests
            logger.warning('Warning: Failed to calculate test %r: %r', test_name, e)
            continue

    # Step 2: Calculate financial distribution test
    try:
        p_financial: float
        financial_metrics: dict[str, int | float | str]
        p_financial, financial_metrics = _analyze_cost_distribution(
            context
        )

        if financial_metrics:
            test_name = 'Cost Distribution'
            all_p_values[test_name] = p_financial
            all_tests[test_name] = StatisticalTest(
                name='Cost Distribution',
                p_value=p_financial,
                **financial_metrics,  # pyright: ignore[reportArgumentType]
            )
    except Exception as e:
        logger.warning('Warning: Failed to calculate cost distribution test: %r', e)

    # Step 3: Handle case with no valid tests
    if not all_p_values:
        logger.warning(
            'Warning: No valid statistical tests could be performed (no valid p values)'
        )
        logger.debug(
            'Target df length: %d\tOthers df length: %d',
            len(target_df),
            len(peers_df),
        )
        return all_tests

    # Step 4: Apply multiple testing correction (Benjamini-Hochberg FDR)
    corrected_p_values: dict[str, tuple[float, bool, float]] = (
        benjamini_hochberg_correction(all_p_values, alpha)
    )
    context.report_writer.write_multiple_testing_correction(corrected_p_values)

    # Step 5: Update tests with corrected significance and report
    for test_name, test_obj in all_tests.items():
        if test_name in corrected_p_values:
            is_sig: bool
            q_val: float
            _, is_sig, q_val = corrected_p_values[test_name]
            test_obj.is_significant = is_sig
            test_obj.q_value = q_val
            test_obj.fdr_corrected = True

        # Write each test result to the report
        context.report_writer.write_statistical_test(test_obj)

    # Step 6: Calculate and report financial impact
    exposure_estimate = None

    # Only calculate exposure if "No ELD Match" test is significant
    if 'No ELD Match' in all_tests and all_tests['No ELD Match'].is_significant:
        try:
            exposure_estimate: dict[str, Any] | None = _calculate_exposure_estimate(
                target_df, peers_df, alpha, context.config.analysis.n_bootstrap
            )
        except Exception as e:
            logger.warning('Warning: Failed to calculate exposure estimate: %r', e)

    # Write financial impact section if we have cost data
    if 'Cost Distribution' in all_tests:
        financials: StatisticalTest = all_tests['Cost Distribution']
        context.report_writer.write_financial_impact(
            target_total=financials.target_total,
            baseline_total=financials.baseline_total,
            target_avg=financials.target_avg,
            baseline_avg=financials.baseline_avg,
            exposure_estimate=exposure_estimate,
        )

    return all_tests
