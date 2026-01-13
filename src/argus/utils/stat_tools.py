# argus/utils/stat_tools.py

import logging
import math
from collections.abc import Callable

import numpy as np
import pandas as pd
from matplotlib.pylab import Generator
from numpy.typing import NDArray
from scipy import stats
from scipy.stats import chi2_contingency, fisher_exact
from scipy.stats.contingency import Chi2ContingencyResult
from statsmodels.stats.outliers_influence import (
    variance_inflation_factor,  # pyright: ignore[reportUnknownVariableType]
)

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)

__all__: list[str] = [
    'benjamini_hochberg_correction',
    'bootstrap_ci',
    'calculate_vif',
    'chi_square_test',
    'cliffs_delta',
    'cohens_d',
    'fishers_exact_test',
    'hodges_lehmann_diff',
    'newcombe_diff_ci',
    'odds_ratio_ci',
    'risk_ratio_ci',
    'two_prop_z_test',
    'wilson_ci',
]


def wilson_ci(
    successes: int, total_observations: int, alpha: float = 0.05
) -> tuple[float, float]:
    """
    Calculate Wilson score confidence interval for a binomial proportion.

    The Wilson score interval is more accurate than the normal approximation (Wald interval),
    especially for:
    - Small sample sizes (n < 30)
    - Extreme proportions (p near 0 or 1)
    - Situations where the Wald interval would extend beyond [0, 1]

    The method adjusts the center point and uses a more sophisticated variance estimate
    that accounts for the discrete nature of binomial data.

    Args:
        successes: Number of successful outcomes (k)
        total_observations: Total number of trials (n)
        alpha: Significance level (e.g., 0.05 for 95% CI)

    Returns:
        Tuple of (lower_bound, upper_bound). Returns (np.nan, np.nan) if n=0.
    """
    # Handle edge case: cannot compute CI with zero observations
    if total_observations == 0:
        logger.debug('Wilson CI: Cannot compute confidence interval with n=0')
        return (math.nan, math.nan)

    # Get the critical z-value for the desired confidence level
    # For 95% CI, this is ~1.96
    z_critical: float = stats.norm.ppf(1 - alpha / 2)

    # Calculate sample proportion
    sample_proportion: float = successes / total_observations

    # Wilson score denominator: adjusts for the added z²/n term
    # This "shrinks" extreme proportions toward 0.5
    denominator: float = 1 + z_critical**2 / total_observations

    # Wilson center: shifts the center point from p̂ toward 0.5
    # This adjustment is larger for smaller samples
    wilson_center: float = sample_proportion + z_critical**2 / (2 * total_observations)

    # Wilson margin of error: more conservative variance estimate than p̂(1-p̂)/n
    # The z²/(4n) term provides additional stability for extreme proportions
    variance_term: float = (
        sample_proportion * (1 - sample_proportion)
        + z_critical**2 / (4 * total_observations)
    ) / total_observations

    margin_of_error: float = z_critical * math.sqrt(variance_term)

    # Calculate bounds and ensure they stay within [0, 1]
    lower_bound: float = float(
        max(0.0, (wilson_center - margin_of_error) / denominator)
    )
    upper_bound: float = float(
        min(1.0, (wilson_center + margin_of_error) / denominator)
    )

    return (lower_bound, upper_bound)


def newcombe_diff_ci(
    successes_group1: int,
    total_group1: int,
    successes_group2: int,
    total_group2: int,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """
    Calculate Newcombe-Wilson confidence interval for the difference between two proportions.

    This hybrid method combines Wilson score intervals for each proportion to create
    a confidence interval for their difference (p1 - p2). It's recommended for general use
    because it:
    - Maintains proper coverage even with small samples or extreme proportions
    - Avoids the overly conservative nature of simpler methods
    - Uses the mathematically sound Wilson score intervals as building blocks

    The interval for (p1 - p2) is constructed as:
        [lower1 - upper2, upper1 - lower2]

    This ensures proper coverage across the full range of possible differences.

    Args:
        successes_group1: Number of successes in group 1
        total_group1: Total sample size for group 1
        successes_group2: Number of successes in group 2
        total_group2: Total sample size for group 2
        alpha: Significance level (e.g., 0.05 for 95% CI)

    Returns:
        Tuple of (lower_bound, upper_bound) for the difference (p1 - p2).
        Returns (np.nan, np.nan) if either group has n=0.
    """
    # Calculate Wilson score intervals for each group independently
    lower_bound_group1: float
    upper_bound_group1: float
    lower_bound_group2: float
    upper_bound_group2: float

    lower_bound_group1, upper_bound_group1 = wilson_ci(
        successes_group1, total_group1, alpha
    )
    lower_bound_group2, upper_bound_group2 = wilson_ci(
        successes_group2, total_group2, alpha
    )

    # Check if either Wilson interval is invalid (n=0 case)
    if pd.isna(lower_bound_group1) or pd.isna(lower_bound_group2):
        logger.warning(
            'Newcombe CI: Cannot compute difference interval because one or both '
            'groups have zero observations'
        )
        return (np.nan, np.nan)

    # Construct the difference interval using Newcombe's method:
    # Lower bound of difference = lower1 - upper2
    # Upper bound of difference = upper1 - lower2
    difference_lower: float = lower_bound_group1 - upper_bound_group2
    difference_upper: float = upper_bound_group1 - lower_bound_group2

    return (difference_lower, difference_upper)


def risk_ratio_ci(
    successes_group1: int,
    total_group1: int,
    successes_group2: int,
    total_group2: int,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    """
    Calculate Risk Ratio (Relative Risk) with confidence interval using Katz log-transform method.

    Risk Ratio = P(outcome|exposed) / P(outcome|unexposed)

    The Katz method:
    1. Applies continuity correction (add 0.5 to each cell) if any cell would be zero
    2. Computes RR on the log scale where the sampling distribution is more normal
    3. Constructs CI on log scale, then exponentiates back to RR scale

    This is preferred over the normal approximation because:
    - RR is bounded at 0 (cannot be negative)
    - Log transformation makes the distribution more symmetric
    - Continuity correction prevents division by zero and improves small-sample behavior

    Args:
        successes_group1: Number of outcomes in exposed/treatment group
        total_group1: Total sample size in exposed/treatment group
        successes_group2: Number of outcomes in unexposed/control group
        total_group2: Total sample size in unexposed/control group
        alpha: Significance level (e.g., 0.05 for 95% CI)

    Returns:
        Tuple of (risk_ratio, ci_lower, ci_upper). Returns (np.nan, np.nan, np.nan)
        if sample sizes are zero, or (np.inf, np.nan, np.nan) if denominator is zero.
    """
    # Convert to floats for computation (avoiding integer division issues)
    successes_exposed: float = float(successes_group1)
    total_exposed: float = float(total_group1)
    successes_unexposed: float = float(successes_group2)
    total_unexposed: float = float(total_group2)

    # Apply continuity correction if any cell in the 2x2 contingency table would be zero
    # This prevents division by zero and improves accuracy for small counts
    #
    # 2x2 table structure:
    #                 Outcome=Yes    Outcome=No     Total
    # Exposed            k1          (n1-k1)         n1
    # Unexposed          k2          (n2-k2)         n2
    #
    failures_exposed: int = total_group1 - successes_group1
    failures_unexposed: int = total_group2 - successes_group2

    if (
        successes_group1 == 0
        or failures_exposed == 0
        or successes_group2 == 0
        or failures_unexposed == 0
    ):
        logger.debug(
            'Risk Ratio CI: Applying continuity correction (+0.5 to all cells) '
            'due to zero cell(s) in 2x2 table'
        )
        # Add 0.5 to success counts and 1.0 to totals (which adds 0.5 to both success and failure)
        successes_exposed += 0.5
        total_exposed += 1.0
        successes_unexposed += 0.5
        total_unexposed += 1.0

    # Validate sample sizes after adjustment
    if total_exposed == 0 or total_unexposed == 0:
        logger.warning('Risk Ratio CI: Cannot compute with zero sample size')
        return (np.nan, np.nan, np.nan)

    # Calculate sample proportions (risk estimates)
    risk_exposed: float = successes_exposed / total_exposed
    risk_unexposed: float = successes_unexposed / total_unexposed

    # Handle edge case: if unexposed risk is zero, RR is undefined (divide by zero)
    if risk_unexposed == 0:
        logger.warning(
            'Risk Ratio CI: Unexposed group has zero risk after continuity correction. '
            'Returning (inf, nan, nan).'
        )
        return (np.inf, np.nan, np.nan)

    # Calculate risk ratio
    risk_ratio: float = risk_exposed / risk_unexposed

    # Transform to log scale for CI calculation (more symmetric distribution)
    log_risk_ratio: float = np.log(risk_ratio)

    # Calculate standard error of log(RR) using the delta method
    # SE[log(RR)] = sqrt(1/k1 - 1/n1 + 1/k2 - 1/n2)
    standard_error_log_rr: float = np.sqrt(
        1 / successes_exposed
        - 1 / total_exposed
        + 1 / successes_unexposed
        - 1 / total_unexposed
    )

    # Get critical z-value for desired confidence level
    z_critical: float = stats.norm.ppf(1 - alpha / 2)

    # Calculate confidence interval on log scale, then exponentiate back to RR scale
    ci_lower: float = np.exp(log_risk_ratio - z_critical * standard_error_log_rr)
    ci_upper: float = np.exp(log_risk_ratio + z_critical * standard_error_log_rr)

    return (risk_ratio, ci_lower, ci_upper)


def odds_ratio_ci(
    successes_group1: int,
    total_group1: int,
    successes_group2: int,
    total_group2: int,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    """
    Calculate Odds Ratio with confidence interval using Woolf-Haldane method.

    Odds Ratio = [P(outcome|exposed) / (1-P(outcome|exposed))] /
                 [P(outcome|unexposed) / (1-P(outcome|unexposed))]
               = (a*d) / (b*c)  in the 2x2 table notation

    The Woolf-Haldane method:
    1. Applies Haldane-Anscombe correction (add 0.5 to all cells) if any cell is zero
    2. Computes OR on the log scale where the sampling distribution is more normal
    3. Constructs CI on log scale using Woolf's variance formula, then exponentiates

    Unlike Risk Ratio, Odds Ratio is symmetric around 1 (OR and 1/OR have equal distance).
    It's the standard effect measure for case-control studies and logistic regression.

    Args:
        successes_group1: Number of outcomes in exposed/treatment group (cell a)
        total_group1: Total sample size in exposed/treatment group (a+b)
        successes_group2: Number of outcomes in unexposed/control group (cell c)
        total_group2: Total sample size in unexposed/control group (c+d)
        alpha: Significance level (e.g., 0.05 for 95% CI)

    Returns:
        Tuple of (odds_ratio, ci_lower, ci_upper). Returns (inf, nan, nan) or
        (0, nan, nan) if b or c cells are zero after correction.
    """
    # Construct the 2x2 contingency table:
    #
    #                 Outcome=Yes    Outcome=No     Total
    # Exposed            a               b           a+b
    # Unexposed          c               d           c+d
    #
    # OR = (a*d) / (b*c)

    exposed_with_outcome: float = float(successes_group1)
    exposed_without_outcome: float = float(total_group1 - successes_group1)
    unexposed_with_outcome: float = float(successes_group2)
    unexposed_without_outcome: float = float(total_group2 - successes_group2)

    # Apply Haldane-Anscombe continuity correction if any cell is zero
    # This adds 0.5 to all four cells of the 2x2 table
    if 0 in [
        exposed_with_outcome,
        exposed_without_outcome,
        unexposed_with_outcome,
        unexposed_without_outcome,
    ]:
        logger.debug(
            'Odds Ratio CI: Applying Haldane-Anscombe correction (+0.5 to all cells) '
            'due to zero cell(s) in 2x2 table'
        )
        exposed_with_outcome += 0.5
        exposed_without_outcome += 0.5
        unexposed_with_outcome += 0.5
        unexposed_without_outcome += 0.5

    # Handle edge case: if b or c cells are still zero, OR is undefined or infinite
    if exposed_without_outcome == 0 or unexposed_with_outcome == 0:
        if exposed_without_outcome == 0:
            logger.warning(
                'Odds Ratio CI: No exposed subjects without outcome (b=0). '
                'Returning (inf, nan, nan).'
            )
            return (np.inf, np.nan, np.nan)
        else:
            logger.warning(
                'Odds Ratio CI: No unexposed subjects with outcome (c=0). '
                'Returning (0, nan, nan).'
            )
            return (0.0, np.nan, np.nan)

    # Calculate odds ratio: OR = (a*d) / (b*c)
    odds_ratio: float = (exposed_with_outcome * unexposed_without_outcome) / (
        exposed_without_outcome * unexposed_with_outcome
    )

    # Transform to log scale for CI calculation
    log_odds_ratio: float = np.log(odds_ratio)

    # Calculate standard error of log(OR) using Woolf's formula
    # SE[log(OR)] = sqrt(1/a + 1/b + 1/c + 1/d)
    standard_error_log_or: float = np.sqrt(
        1 / exposed_with_outcome
        + 1 / exposed_without_outcome
        + 1 / unexposed_with_outcome
        + 1 / unexposed_without_outcome
    )

    # Get critical z-value for desired confidence level
    z_critical: float = stats.norm.ppf(1 - alpha / 2)

    # Calculate confidence interval on log scale, then exponentiate back to OR scale
    ci_lower: float = np.exp(log_odds_ratio - z_critical * standard_error_log_or)
    ci_upper: float = np.exp(log_odds_ratio + z_critical * standard_error_log_or)

    return (odds_ratio, ci_lower, ci_upper)


def two_prop_z_test(
    successes_group1: int,
    total_group1: int,
    successes_group2: int,
    total_group2: int,
    use_correction: bool = False,
) -> float:
    """
    Two-proportion z-test (pooled) with optional Yates continuity correction.

    Tests whether two population proportions are significantly different using
    a pooled standard error under the null hypothesis that p1 == p2.

    Args:
        successes_group1: Number of successes in group 1
        total_group1: Total sample size for group 1
        successes_group2: Number of successes in group 2
        total_group2: Total sample size for group 2
        use_correction: Whether to apply Yates continuity correction (for small samples)

    Returns:
        Two-tailed p-value. Returns math.nan if inputs are invalid.
    """
    # Validate inputs: ensure sample sizes are positive and success counts are valid
    if (
        total_group1 <= 0
        or total_group2 <= 0
        or successes_group1 < 0
        or successes_group2 < 0
        or successes_group1 > total_group1
        or successes_group2 > total_group2
    ):
        logger.warning(
            'Invalid inputs for two-proportion z-test: k1=%d, n1=%d, k2=%d, n2=%d',
            successes_group1,
            total_group1,
            successes_group2,
            total_group2,
        )
        return math.nan

    # Calculate sample proportions for each group
    proportion_group1: float = successes_group1 / total_group1
    proportion_group2: float = successes_group2 / total_group2

    # Calculate pooled proportion under null hypothesis (H0: p1 == p2)
    # This combines both samples to estimate the common proportion
    pooled_proportion: float = (successes_group1 + successes_group2) / (
        total_group1 + total_group2
    )

    # Handle degenerate case: if all observations are 0s or all 1s across both groups,
    # the variance is zero and there's no meaningful difference to test
    if pooled_proportion in {0.0, 1.0}:
        logger.debug(
            'Two-proportion z-test pooled proportion is %.4f (zero variance case)',
            pooled_proportion,
        )
        # If both proportions are identical, no difference exists (p=1.0)
        # Otherwise this is a degenerate edge case (p=0.0)
        return 1.0 if proportion_group1 == proportion_group2 else 0.0

    # Calculate pooled standard error using the pooled proportion
    # SE = sqrt(p_pooled * (1 - p_pooled) * (1/n1 + 1/n2))
    standard_error: float = math.sqrt(
        pooled_proportion
        * (1 - pooled_proportion)
        * (1 / total_group1 + 1 / total_group2)
    )

    # Safety check: if SE is still zero due to floating-point precision issues
    if standard_error == 0.0:
        logger.warning(
            'Standard error is zero despite non-degenerate pooled proportion '
            '(p_pooled=%.4f). This suggests numerical instability.',
            pooled_proportion,
        )
        return math.nan

    # Calculate absolute difference between proportions
    absolute_difference: float = abs(proportion_group1 - proportion_group2)

    # Apply Yates continuity correction if requested (recommended for small samples)
    # This reduces the test statistic slightly to account for discrete data
    if use_correction:
        correction_factor: float = 0.5 * (1 / total_group1 + 1 / total_group2)
        absolute_difference = max(0.0, absolute_difference - correction_factor)

    # Calculate z-statistic: (observed difference) / (standard error)
    z_statistic: float = absolute_difference / standard_error

    # Convert to two-tailed p-value using standard normal CDF
    # P(|Z| > z) = 2 * P(Z > z) = 2 * (1 - Φ(z))
    p_value: float = 2.0 * (1.0 - stats.norm.cdf(z_statistic))

    if math.isnan(p_value):
        logger.warning(
            'Two-proportion z-test calculation failed (p=%.4f) with values: '
            'k1=%d, n1=%d, '
            'k2=%d, n2=%d',
            p_value,
            successes_group1,
            total_group1,
            successes_group2,
            total_group2,
        )

    return p_value


def chi_square_test(contingency_table: np.ndarray) -> tuple[float, float, float]:
    """
    Perform chi-square test of independence with Cramér's V effect size.

    Tests whether two categorical variables are independent (null hypothesis: no association).
    The chi-square test is appropriate when:
    - All expected cell frequencies are ≥ 5 (rule of thumb)
    - Data represents counts (not proportions or continuous values)
    - Observations are independent

    For 2x2 tables with small expected frequencies (< 5), use Fisher's exact test instead.

    Cramér's V is a measure of association strength:
    - 0.0 = no association
    - 0.1 = weak association
    - 0.3 = moderate association
    - 0.5+ = strong association
    (These thresholds vary by field and table dimensions)

    Args:
        contingency_table: 2D array of observed frequencies where rows and columns
                          represent levels of two categorical variables

    Returns:
        Tuple of (chi_square_statistic, p_value, cramers_v_effect_size)
    """
    # Perform chi-square test of independence
    # Returns: chi2 statistic, p-value, degrees of freedom, expected frequencies
    chi2_tuple: Chi2ContingencyResult = chi2_contingency(contingency_table)

    chi_square_statistic: float = float(chi2_tuple[0])
    p_value: float = float(chi2_tuple[1])

    # Calculate Cramér's V effect size to quantify association strength
    # V = sqrt(χ² / (n * min_dim)) where min_dim = min(rows-1, cols-1)
    total_observations: float = contingency_table.sum()

    # Degrees of freedom factor: smaller dimension minus 1
    # For a 2x2 table, this is 1; for a 3x4 table, this is 2
    min_dimension: int = min(contingency_table.shape) - 1

    # Calculate Cramér's V (normalized chi-square on [0, 1] scale)
    if min_dimension > 0 and total_observations > 0:
        cramers_v_effect_size: float = np.sqrt(
            chi_square_statistic / (total_observations * min_dimension)
        )
    else:
        logger.warning(
            "Chi-square test: Cannot calculate Cramér's V with min_dimension=%d, "
            'n=%.2f. Returning 0.0.',
            min_dimension,
            total_observations,
        )
        cramers_v_effect_size = 0.0

    return (chi_square_statistic, p_value, cramers_v_effect_size)


def fishers_exact_test(contingency_table_2x2: np.ndarray) -> tuple[float, float]:
    """
    Perform Fisher's exact test for 2x2 contingency tables.

    Fisher's exact test calculates the exact probability of observing a table as extreme
    or more extreme than the observed data, given the marginal totals. Unlike chi-square,
    it doesn't rely on asymptotic approximations.

    Use Fisher's exact test when:
    - You have a 2x2 contingency table
    - Any expected cell frequency is < 5 (where chi-square is unreliable)
    - Sample sizes are small
    - You want exact p-values rather than approximations

    The test is computationally intensive for large samples, but modern implementations
    handle this well. For tables larger than 2x2, consider chi-square or Monte Carlo methods.

    Args:
        contingency_table_2x2: 2x2 array of observed frequencies:
                              [[a, b],
                               [c, d]]
                              where rows/columns represent two binary categorical variables

    Returns:
        Tuple of (odds_ratio, p_value) for two-sided test.
        Returns (np.nan, np.nan) if table is not 2x2.
    """
    # Validate that we have a 2x2 table
    if contingency_table_2x2.shape != (2, 2):
        logger.error(
            "Fisher's exact test requires a 2x2 contingency table, "
            'but received shape %r. '
            'Returning (np.nan, np.nan).',
            contingency_table_2x2.shape,
        )
        return (math.nan, math.nan)

    # Perform Fisher's exact test (two-sided alternative)
    # Returns: odds ratio and exact p-value
    odds_ratio: float
    p_value: float
    odds_ratio, p_value = fisher_exact(contingency_table_2x2, alternative='two-sided')

    # Log if we encounter edge cases (e.g., zero cells leading to inf/0 odds ratios)
    if math.isinf(odds_ratio) or odds_ratio == 0:
        logger.debug(
            "Fisher's exact test: Odds ratio is %.4f due to zero cell(s) "
            'in contingency table',
            odds_ratio,
        )

    return (odds_ratio, p_value)


def cliffs_delta(
    x: np.ndarray,
    y: np.ndarray,
    thresholds: tuple[float, float, float] = (0.147, 0.33, 0.474),
) -> tuple[float, str]:
    """
    Cliff's Delta effect size for non-parametric data.

    Cliff's Delta measures the probability that a randomly selected value from
    group X is greater than a randomly selected value from group Y, minus the
    probability of the reverse.

    Formula: δ = P(X > Y) - P(X < Y)

    Interpretation thresholds (Romano et al., 2006):
    - |δ| < 0.147: negligible
    - |δ| < 0.33: small
    - |δ| < 0.474: medium
    - |δ| ≥ 0.474: large

    Args:
        x: First group (numpy array)
        y: Second group (numpy array)
        thresholds: tuple of (negligible, small, medium)

    Returns:
        tuple of (delta, interpretation)
        - delta: Effect size from -1 to +1
        - interpretation: "negligible", "small", "medium", "large", or "undefined"

    Note: Positive delta means x tends to be larger than y
          Negative delta means y tends to be larger than x
    """
    negligible_threshold: float = thresholds[0]
    small_threshold: float = thresholds[1]
    medium_threshold: float = thresholds[2]

    x, y = np.asarray(x), np.asarray(y)
    x = x[~np.isnan(x)]
    y = y[~np.isnan(y)]

    if len(x) == 0 or len(y) == 0:
        return (float(np.nan), 'undefined')

    # Vectorized computation of the dominance matrix
    # Creates matrix where element [i,j] indicates if x[i] > y[j] (+1), = (0), or < (-1)
    dominance_matrix: np.ndarray = np.sign(np.subtract.outer(x, y))
    delta: float = float(np.mean(dominance_matrix))

    # Interpretation using standard thresholds
    abs_delta: float = abs(delta)
    if abs_delta < negligible_threshold:
        interpretation = 'negligible'
    elif abs_delta < small_threshold:
        interpretation = 'small'
    elif abs_delta < medium_threshold:
        interpretation = 'medium'
    else:
        interpretation = 'large'

    return (delta, interpretation)


def cohens_d(
    x: np.ndarray,
    y: np.ndarray,
    min_array: int = 2,
    effect_size_thresholds: tuple[float, float, float] = (0.2, 0.5, 0.8),
) -> tuple[float, str]:
    """
    Cohen's d effect size for comparing means.
    Returns (d, interpretation).
    """
    negligible_upper_bound: float = effect_size_thresholds[0]
    small_upper_bound: float = effect_size_thresholds[1]
    medium_upper_bound: float = effect_size_thresholds[2]

    x = x[~np.isnan(x)]
    y = y[~np.isnan(y)]

    if len(x) < min_array or len(y) < min_array:
        return (math.nan, 'undefined')

    sample_size_x: int = len(x)
    sample_size_y: int = len(y)

    mean_x: float = float(np.mean(x))
    mean_y: float = float(np.mean(y))

    std_dev_x: float = float(np.std(x, ddof=1))
    std_dev_y: float = float(np.std(y, ddof=1))

    # Pooled standard deviation
    s_pooled: float = math.sqrt(
        ((sample_size_x - 1) * std_dev_x**2 + (sample_size_y - 1) * std_dev_y**2)
        / (sample_size_x + sample_size_y - 2)
    )

    if s_pooled == 0:
        return (math.nan, 'undefined')

    d: float = (mean_x - mean_y) / s_pooled

    # Interpretation
    abs_d: float = abs(d)
    if abs_d < negligible_upper_bound:
        interpretation = 'negligible'
    elif abs_d < small_upper_bound:
        interpretation = 'small'
    elif abs_d < medium_upper_bound:
        interpretation = 'medium'
    else:
        interpretation = 'large'

    return (d, interpretation)


def hodges_lehmann_diff(
    x: pd.Series | NDArray[np.float64], y: pd.Series | NDArray[np.float64]
) -> float:
    """
    Hodges-Lehmann estimator of location shift: median of all pairwise differences x_i - y_j.

    Args:
        x: Sample from group X (pandas Series or NumPy array). NaN/NA allowed.
        y: Sample from group Y (pandas Series or NumPy array). NaN/NA allowed.

    Returns:
        Hodges-Lehmann estimator (float). Returns math.nan if either input has no finite values.

    Notes:
        This implementation materializes all pairwise differences, which uses O(n*m) memory.
        Only use when inputs are small enough to fit in memory.
    """
    # Coerce to plain NumPy float64 (pd.NA -> np.nan)
    array_x: NDArray[np.float64] = np.asarray(pd.Series(x), dtype='float64')
    array_y: NDArray[np.float64] = np.asarray(pd.Series(y), dtype='float64')

    # Keep only finite numbers
    finite_x: NDArray[np.float64] = array_x[np.isfinite(array_x)]
    finite_y: NDArray[np.float64] = array_y[np.isfinite(array_y)]

    if finite_x.size == 0 or finite_y.size == 0:
        return math.nan

    # All pairwise differences and median
    diffs: NDArray[np.float64] = np.subtract.outer(finite_x, finite_y).ravel()

    return float(np.median(diffs))


def bootstrap_ci(
    data: np.ndarray,
    func: Callable[[np.ndarray], float],
    alpha: float = 0.05,
    n_boot: int = 5000,
    seed: int = 42,
) -> tuple[float, float, float]:
    """
    Bootstrap percentile confidence interval for an arbitrary statistic.

    Args:
        data: 1D array-like of observations. NaN/inf are discarded.
        func: Statistic function applied to a 1D sample array.
        alpha: Significance level (0.05 -> 95% CI).
        n_boot: Number of bootstrap resamples.
        seed: RNG seed for reproducibility.

    Returns:
        (estimate, ci_lower, ci_upper). If no finite values exist, returns
        (nan, nan, nan).

    Raises:
        ValueError: If alpha is not in (0, 1) or n_boot < 1.
    """
    if not (0.0 < alpha < 1.0):
        raise ValueError('alpha must be in (0, 1).')
    if n_boot < 1:
        raise ValueError('n_boot must be >= 1.')

    rng: Generator = np.random.default_rng(seed)
    array_data: NDArray[np.float64] = np.asarray(data, dtype='float64')
    finite_array: NDArray[np.float64] = array_data[np.isfinite(array_data)]
    cleaned_data: NDArray[np.float64] = finite_array[~np.isnan(finite_array)]

    if cleaned_data.size == 0:
        return (math.nan, math.nan, math.nan)

    # Original estimate
    estimate: float = float(func(cleaned_data))

    # Bootstrap samples
    boot_stats: NDArray[np.float64] = np.array(
        [
            func(rng.choice(cleaned_data, size=cleaned_data.size, replace=True))
            for _ in range(n_boot)
        ]
    )

    # Percentile CI
    ci_lower: float = float(np.percentile(boot_stats, 100 * (alpha / 2)))
    ci_upper: float = float(np.percentile(boot_stats, 100 * (1 - alpha / 2)))

    return (estimate, ci_lower, ci_upper)


def calculate_vif(
    input_dataframe: pd.DataFrame, feature_names: list[str]
) -> pd.DataFrame:
    """
    Calculates the Variance Inflation Factor (VIF) for a set of predictor features
    in a DataFrame to diagnose multicollinearity.

    VIF quantifies how much the variance of an estimated regression coefficient is
    increased due to collinearity with other predictors.

    Args:
        input_dataframe (pd.DataFrame): The DataFrame containing all feature data.
        feature_names (list[str]): A list of column names (predictors) for which VIF
                                    should be calculated.

    Returns:
        pd.DataFrame: A DataFrame with two columns: 'Feature' and its corresponding vif score 'VIF'.
                      - VIF values are interpreted as follows:
                        - VIF = 1: No correlation with other features (ideal).
                        - VIF > 5: Generally considered a moderate indication of multicollinearity.
                        - VIF > 10: Often considered highly problematic, suggesting the feature
                          should be removed or combined.

    Raises:
        ValueError: If any feature in `feature_names` is not found in `input_dataframe`.
    """
    # Defensive check to ensure all requested features exist in the DataFrame.
    missing_features: list[str] = [
        feature_name
        for feature_name in feature_names
        if feature_name not in input_dataframe.columns
    ]
    if missing_features:
        raise ValueError(
            f'The following features were not found in the input DataFrame: {missing_features}'
        )

    # Extract the selected feature columns and convert them into a NumPy array (matrix).
    # The statsmodels' variance_inflation_factor function expects a feature matrix.
    feature_matrix: NDArray[np.float64] = input_dataframe[feature_names].to_numpy(
        dtype='float64', na_value=np.nan
    )

    finite_row_mask: np.bool | NDArray[np.bool[bool]] = np.isfinite(feature_matrix).all(
        axis=1
    )

    feature_matrix = feature_matrix[finite_row_mask]

    # Calculate VIF for each feature using a list comprehension.
    # The VIF function calculates the score for the i-th column in the matrix X
    # regressed against all other columns in X.
    vif_values: list[float] = [
        float(variance_inflation_factor(feature_matrix, feature_index))
        for feature_index in range(len(feature_names))
    ]

    return pd.DataFrame(
        {
            'Feature': feature_names,
            'VIF': vif_values,
        }
    )


def benjamini_hochberg_correction(
    test_p_values: dict[str, float],
    alpha: float = 0.05,
    calculate_q_values: bool = True,
) -> dict[str, tuple[float, bool, float]]:
    """
    Apply Benjamini-Hochberg FDR (False Discovery Rate) correction using step-up procedure.

    This method controls the expected proportion of false discoveries among rejected hypotheses.
    It's more powerful than Bonferroni when conducting multiple comparisons, especially when
    tests are independent or positively dependent.

    The procedure:
    1. Sort p-values in ascending order
    2. Find the largest rank k where p_(k) <= (k/m) * alpha
    3. Reject all hypotheses with rank <= k
    4. Optionally compute q-values (adjusted p-values) for effect size interpretation

    Args:
        test_p_values: Dictionary mapping unique test identifiers to their raw p-values.
        alpha: The Family-wise significance threshold (typically 0.05).
        calculate_q_values: If True, computes the adjusted p-value (q-value) for each test.
                            If False, q-values will be returned as math.nan.

    Returns:
        Dictionary mapping test names to tuples of (original_p, is_significant, q_value)
        where q_value is math.nan if calculate_q_values=False

    Raises:
        ValueError: If alpha is not in the range (0, 1)
    """
    if not test_p_values:
        logger.warning('Benjamini-Hochberg correction received empty input.')
        return {}

    if not (0.0 < alpha < 1.0):
        logger.error('Invalid alpha provided: %s', alpha)
        raise ValueError(f'alpha must be in (0, 1), got {alpha}')

    # Prepare Data
    # We convert dictionary items to a list first to guarantee that test_names
    # and raw_p_values_list remain perfectly synchronized by index.
    test_items: list[tuple[str, float]] = list(test_p_values.items())
    test_names: list[str] = [name for name, _ in test_items]
    raw_p_values_list: list[float] = []

    # Clean inputs: explicitly handle non-finite values as 1.0
    for name, val in test_items:
        try:
            float_val = float(val)

            # Check for NaN or Infinity explicitly
            if not math.isfinite(float_val):
                logger.warning(
                    "Non-finite p-value for test '%s': %s. Treating as 1.0.", name, val
                )
                raw_p_values_list.append(1.0)
            else:
                # Clamp valid finite floats between 0.0 and 1.0
                raw_p_values_list.append(min(max(float_val, 0.0), 1.0))

        except (ValueError, TypeError):
            logger.warning(
                "Invalid p-value type for test '%s': %s. Treating as 1.0.", name, val
            )
            raw_p_values_list.append(1.0)

    p_values_array: NDArray[np.float64] = np.array(raw_p_values_list, dtype=np.float64)
    total_test_count: int = len(p_values_array)

    # Sort Data
    # Get indices that would sort the p-values array (low to high)
    sorted_indices: NDArray[np.intp] = np.argsort(p_values_array)
    sorted_p_values: NDArray[np.float64] = p_values_array[sorted_indices]

    # Rank is 1-based index (1, 2, ..., m)
    ranks: NDArray[np.intp] = np.arange(1, total_test_count + 1)

    # Determine Significance (Vectorized Step-Up)
    # BH Critical Value formula: (rank / m) * alpha
    # A test is significant if its p-value is <= this threshold.
    # The BH procedure rejects all hypotheses with rank <= the largest rank where this condition holds.
    critical_values = (ranks / total_test_count) * alpha
    below_threshold_mask = sorted_p_values <= critical_values

    # Find the largest rank where the condition is met.
    # np.where returns indices where condition is true.
    # If no tests meet the condition, max_significant_index is -1 (meaning index 0 is not significant).
    qualifying_indices = np.where(below_threshold_mask)[0]

    if qualifying_indices.size > 0:
        max_significant_index: int = int(np.max(qualifying_indices))
    else:
        max_significant_index = -1

    # Create boolean array in the sorted order
    # All tests up to max_significant_index are declared significant
    is_significant_sorted: NDArray[np.bool] = np.zeros(total_test_count, dtype=bool)
    is_significant_sorted[: max_significant_index + 1] = True

    # Calculate Q-Values (Optional)
    # Q-value = min( (m/rank) * p_value, q_value_of_next_higher_rank )
    # This enforces monotonicity: a test with a lower p-value cannot have a higher q-value.
    q_values_sorted: NDArray[np.float64] = np.full(
        total_test_count, math.nan, dtype=np.float64
    )

    if calculate_q_values:
        # Calculate raw FDR adjustments: (m / rank) * p
        # We perform the multiplication vector-wise
        fdr_adjusted_p = (total_test_count / ranks) * sorted_p_values

        # Enforce cap at 1.0
        fdr_adjusted_p: NDArray[np.float64] = np.minimum(fdr_adjusted_p, 1.0)

        # Enforce monotonicity from the bottom up (largest p-value to smallest).
        # To do this vectorially, we:
        # 1. Reverse the array (so we go from largest p-value to smallest).
        # 2. Calculate the running minimum (accumulate).
        # 3. Reverse the array back to the original sorted order.
        reversed_fdr_p: NDArray[np.float64] = fdr_adjusted_p[::-1]
        reversed_cumulative_min: NDArray[np.float64] = np.minimum.accumulate(
            reversed_fdr_p
        )
        q_values_sorted = reversed_cumulative_min[::-1]

    # Map Results Back to Original Order
    # We use an empty array for results and fill it using the sorted indices
    final_significance: NDArray[np.bool] = np.zeros(total_test_count, dtype=bool)
    final_q_values: NDArray[np.float64] = np.full(
        total_test_count, math.nan, dtype=np.float64
    )

    # Invert the sorting permutation to put values back in original slots
    # If sorted_indices[i] = k, it means the i-th sorted element came from the k-th original position.
    # We assign result[sorted_indices] = computed_values
    final_significance[sorted_indices] = is_significant_sorted
    final_q_values[sorted_indices] = q_values_sorted

    # Construct the output dictionary
    results: dict[str, tuple[float, bool, float]] = {}
    for i, name in enumerate(test_names):
        results[name] = (
            p_values_array[i],
            bool(final_significance[i]),
            float(final_q_values[i]),
        )

    return results
