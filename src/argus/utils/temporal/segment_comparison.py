# argus/utils/temporal/segment_comparison.py
# TODO: Labels and interpretations should be using locale.yaml in future.
"""
Statistical comparison of time segments and distributions.

This module provides non-parametric methods for comparing:
    - Two time segments (before/after periods)
    - Risk score distributions between groups

All methods use the Mann-Whitney U test for robustness to non-normal
distributions, paired with Cliff's Delta for interpretable effect sizes.

Typical Usage:
    from argus.utils.temporal.segment_comparison import (
        compare_two_segments,
        compare_risk_distributions,
    )

    # Compare behavior before and after a change point
    result = compare_two_segments(before_data, after_data)
    if result.is_significant:
        print(f"Behavior {result.direction}: {result.interpretation}")

    # Compare target location to others
    comparison = compare_risk_distributions(target_risks, baseline_risks)
    if comparison and comparison.is_significant:
        print(f"Target group is {comparison.effect_size.direction}")
"""

import logging
from enum import StrEnum
from typing import Protocol, cast

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from pydantic import Field
from scipy.stats import mannwhitneyu

from argus.models.common import FrozenModel
from argus.utils.stat_tools import cliffs_delta
from argus.utils.temporal._constants import (
    CLIFFS_DELTA_NEGLIGIBLE_THRESHOLD,
    MINIMUM_RECORDS_FOR_STATISTICAL_TEST,
    STATISTICAL_SIGNIFICANCE_ALPHA,
)

__all__: list[str] = [
    'ChangeDirection',
    'EffectMagnitude',
    'EffectSizeResult',
    'GroupDescriptiveStatistics',
    'RiskDistributionComparisonResult',
    'SegmentComparisonResult',
    'compare_risk_distributions',
    'compare_two_segments',
]

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)


# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

type FloatOrArray = float | np.ndarray


class MannWhitneyUResultProtocol(Protocol):
    """
    Structural interface for Mann-Whitney U test results.

    This protocol matches scipy.stats.MannwhitneyuResult across versions,
    where return types may be scalar or ndarray depending on input shape.
    """

    @property
    def statistic(self) -> FloatOrArray:
        """The U statistic."""
        ...

    @property
    def pvalue(self) -> FloatOrArray:
        """The two-sided p-value."""
        ...


# =============================================================================
# ENUMS FOR CATEGORICAL RESULTS
# =============================================================================

# NOTE: These strings should come from a localization source in future. (e.g., english.yaml)


class ChangeDirection(StrEnum):
    """
    Direction of change between compared groups or segments.

    Used to indicate whether the target/later group showed higher or lower
    values compared to the comparison/earlier group.
    """

    INCREASED = 'increased'
    DECREASED = 'decreased'
    NO_CHANGE = 'no_change'
    NEGLIGIBLE = 'negligible'
    INSUFFICIENT_DATA = 'insufficient_data'


class EffectMagnitude(StrEnum):
    """
    Magnitude classification for Cliff's Delta effect size.

    Based on standard thresholds:
        - negligible: |δ| < 0.147
        - small: 0.147 ≤ |δ| < 0.33
        - medium: 0.33 ≤ |δ| < 0.474
        - large: |δ| ≥ 0.474
    """

    NEGLIGIBLE = 'negligible'
    SMALL = 'small'
    MEDIUM = 'medium'
    LARGE = 'large'


# =============================================================================
# PYDANTIC MODELS
# =============================================================================


class SegmentComparisonResult(FrozenModel):
    """
    Result of comparing two time segments using Mann-Whitney U test.

    This model captures the outcome of testing whether behavior changed
    significantly between two time periods (e.g., before vs after a change point).

    Attributes:
        p_value: Two-tailed probability under null hypothesis of no difference.
            Range [0, 1]. Lower values indicate stronger evidence of change.
        is_significant: Whether p_value is below the significance threshold.
        effect_size_delta: Cliff's Delta effect size, range [-1, +1].
            Positive indicates later segment has higher values.
        effect_magnitude: Categorical interpretation of effect size magnitude.
        direction: Direction of change (increased, decreased, no_change, insufficient_data).
        interpretation: Human-readable summary string for reporting.
        earlier_segment_count: Number of observations in earlier segment.
        later_segment_count: Number of observations in later segment.

    Example:
        >>> result = compare_two_segments(before_data, after_data)
        >>> if result.is_significant:
        ...     print(f"Significant {result.direction.value} detected")
        ...     print(f"Effect size: {result.effect_size_delta:.2f} ({result.effect_magnitude.value})")
        >>> print(result.interpretation)
        INCREASED (p=0.008, δ=0.85, large)
    """

    p_value: float = Field(
        ge=0.0,
        le=1.0,
        description='Two-tailed p-value from Mann-Whitney U test',
    )
    is_significant: bool = Field(
        description='Whether p_value is below significance threshold',
    )
    effect_size_delta: float = Field(
        ge=-1.0,
        le=1.0,
        description="Cliff's Delta effect size",
    )
    effect_magnitude: EffectMagnitude = Field(
        description='Categorical effect size interpretation',
    )
    direction: ChangeDirection = Field(
        description='Direction of change between segments',
    )
    interpretation: str = Field(
        description='Human-readable summary for reporting',
    )
    earlier_segment_count: int = Field(
        ge=0,
        description='Sample size of earlier segment',
    )
    later_segment_count: int = Field(
        ge=0,
        description='Sample size of later segment',
    )

    def has_sufficient_data(self) -> bool:
        """Check if comparison had sufficient data in both segments."""
        return self.direction != ChangeDirection.INSUFFICIENT_DATA


class EffectSizeResult(FrozenModel):
    """
    Cliff's Delta effect size with interpretation metadata.

    Cliff's Delta measures the probability that a randomly selected value
    from one group is greater than a randomly selected value from another,
    minus the reverse probability. It ranges from -1 to +1.

    Attributes:
        value: The Cliff's Delta statistic, range [-1, +1].
        name: Name of the effect size measure (always "Cliff's Delta").
        magnitude: Categorical magnitude (negligible, small, medium, large).
        direction: Whether target group is higher, lower, or negligible difference.

    Example:
        >>> effect = result.effect_size
        >>> print(f"δ = {effect.value:.3f} ({effect.magnitude.value})")
        >>> if effect.direction == ChangeDirection.INCREASED:
        ...     print("Target group shows higher values")
    """

    value: float = Field(
        ge=-1.0,
        le=1.0,
        description="Cliff's Delta value",
    )
    name: str = Field(
        default="Cliff's Delta",
        description='Name of the effect size measure',
    )
    magnitude: EffectMagnitude = Field(
        description='Categorical magnitude interpretation',
    )
    direction: ChangeDirection = Field(
        description='Direction of effect (higher, lower, negligible)',
    )


class GroupDescriptiveStatistics(FrozenModel):
    """
    Descriptive statistics for a single comparison group.

    Captures central tendency, spread, and sample size for one group
    in a two-group comparison. Used for both target and comparison groups.

    Attributes:
        mean: Arithmetic mean of the group.
        median: 50th percentile (robust central tendency).
        percentile_25: 25th percentile (first quartile).
        percentile_75: 75th percentile (third quartile).
        sample_size: Number of observations in the group.

    Example:
        >>> stats = result.target_group
        >>> iqr = stats.percentile_75 - stats.percentile_25
        >>> print(f"Target: median={stats.median:.1f}, IQR={iqr:.1f}, n={stats.sample_size}")
    """

    mean: float = Field(description='Arithmetic mean')
    median: float = Field(description='50th percentile')
    percentile_25: float = Field(description='25th percentile (Q1)')
    percentile_75: float = Field(description='75th percentile (Q3)')
    sample_size: int = Field(ge=0, description='Number of observations')

    def interquartile_range(self) -> float:
        """Calculate the interquartile range (Q3 - Q1)."""
        return self.percentile_75 - self.percentile_25


class RiskDistributionComparisonResult(FrozenModel):
    """
    Comprehensive result of comparing risk score distributions between groups.

    This model captures the full output of a Mann-Whitney U test comparing
    a target group (e.g., specific location) against a comparison group
    (e.g., all other locations). Includes statistical test results, effect
    size, descriptive statistics for both groups, and raw differences.

    Attributes:
        p_value: Two-tailed p-value from Mann-Whitney U test.
        is_significant: Whether p_value is below significance threshold.
        u_statistic: The Mann-Whitney U test statistic.
        effect_size: Cliff's Delta with magnitude and direction interpretation.
        target_group: Descriptive statistics for the target group.
        comparison_group: Descriptive statistics for the comparison group.
        mean_difference: target_mean - comparison_mean (raw, not standardized).
        median_difference: target_median - comparison_median (raw, not standardized).

    Example:
        >>> result = compare_risk_distributions(target_risks, baseline_risks)
        >>> if result and result.is_significant:
        ...     print(f"Target group is {result.effect_size.direction.value}")
        ...     print(f"Target median: {result.target_group.median:.1f}")
        ...     print(f"Baseline median: {result.comparison_group.median:.1f}")
        ...     print(f"Effect: {result.effect_size.magnitude.value}")
    """

    # Statistical test results
    p_value: float = Field(
        ge=0.0,
        le=1.0,
        description='Two-tailed p-value from Mann-Whitney U test',
    )
    is_significant: bool = Field(
        description='Whether p_value < significance threshold',
    )
    u_statistic: float = Field(
        ge=0.0,
        description='Mann-Whitney U test statistic',
    )

    # Effect size
    effect_size: EffectSizeResult = Field(
        description="Cliff's Delta effect size with interpretation",
    )

    # Group statistics
    target_group: GroupDescriptiveStatistics = Field(
        description='Descriptive statistics for target group',
    )
    comparison_group: GroupDescriptiveStatistics = Field(
        description='Descriptive statistics for comparison group',
    )

    # Raw differences
    mean_difference: float = Field(
        description='target_mean - comparison_mean',
    )
    median_difference: float = Field(
        description='target_median - comparison_median',
    )

    def summary(self) -> str:
        """
        Generate a one-line summary suitable for logging.

        Returns:
            Formatted string summarizing the comparison result.
        """
        sig_marker: str = '✓' if self.is_significant else '✗'
        return (
            f'RiskComparison({sig_marker} p={self.p_value:.4f}, '
            f'δ={self.effect_size.value:.2f} {self.effect_size.magnitude.value}, '
            f'target_n={self.target_group.sample_size}, '
            f'comparison_n={self.comparison_group.sample_size})'
        )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _interpret_effect_magnitude(magnitude_label: str) -> EffectMagnitude:
    """
    Convert string magnitude label to EffectMagnitude enum.

    Args:
        magnitude_label: String from cliffs_delta() function.

    Returns:
        Corresponding EffectMagnitude enum value.
    """
    label_lower: str = magnitude_label.lower()

    if 'negligible' in label_lower:
        return EffectMagnitude.NEGLIGIBLE
    elif 'small' in label_lower:
        return EffectMagnitude.SMALL
    elif 'medium' in label_lower:
        return EffectMagnitude.MEDIUM
    elif 'large' in label_lower:
        return EffectMagnitude.LARGE
    else:
        # Default fallback
        logger.warning(
            "Unknown effect magnitude label '%s', defaulting to NEGLIGIBLE",
            magnitude_label,
        )
        return EffectMagnitude.NEGLIGIBLE


def _determine_direction_from_effect(
    effect_delta: float,
    negligible_threshold: float,
) -> ChangeDirection:
    """
    Determine direction label based on effect size magnitude.

    Args:
        effect_delta: Cliff's Delta value.
        negligible_threshold: Threshold below which effect is negligible.

    Returns:
        ChangeDirection indicating higher, lower, or negligible.
    """
    if abs(effect_delta) < negligible_threshold:
        return ChangeDirection.NEGLIGIBLE
    elif effect_delta > 0:
        return ChangeDirection.INCREASED
    else:
        return ChangeDirection.DECREASED


# =============================================================================
# TWO-SEGMENT COMPARISON
# =============================================================================


def compare_two_segments(
    earlier_segment_data: pd.Series,
    later_segment_data: pd.Series,
    significance_threshold: float = STATISTICAL_SIGNIFICANCE_ALPHA,
) -> SegmentComparisonResult:
    """
    Compare two time segments using Mann-Whitney U test with Cliff's Delta effect size.

    This non-parametric test determines whether the distributions of values in two
    independent time periods are significantly different. It does not assume normality
    and is robust to outliers, making it ideal for fuel transaction data.

    The test answers: "Did behavior change significantly between these two periods?"

    Algorithm:
        1. Combine and rank all observations from both segments
        2. Calculate U statistic based on rank sums
        3. Convert to p-value using normal approximation
        4. Calculate Cliff's Delta for effect size interpretation

    Args:
        earlier_segment_data:
            Pandas Series of numerical values from the first (earlier) time period.
            NaN values are dropped before analysis.

        later_segment_data:
            Pandas Series of numerical values from the second (later) time period.
            NaN values are dropped before analysis.

        significance_threshold:
            P-value threshold for declaring statistical significance.
            Default is 0.05.

    Returns:
        SegmentComparisonResult containing p-value, significance flag, effect size,
        direction, interpretation string, and sample sizes.

    Raises:
        No exceptions are raised; insufficient data returns a result with
        direction=INSUFFICIENT_DATA.

    Example:
        >>> import pandas as pd
        >>> before = pd.Series([10, 12, 11, 13, 10])
        >>> after = pd.Series([25, 28, 24, 26, 27])
        >>> result = compare_two_segments(before, after)
        >>> print(result.interpretation)
        INCREASED (p=0.008, δ=1.00, large)
        >>> if result.is_significant:
        ...     print(f"Change detected: {result.direction.value}")

    See Also:
        - compare_risk_distributions: For comparing risk scores with full statistics
    """
    # Clean data by removing missing values
    clean_earlier: pd.Series = earlier_segment_data.dropna()
    clean_later: pd.Series = later_segment_data.dropna()

    earlier_count: int = len(clean_earlier)
    later_count: int = len(clean_later)

    # Validate minimum data requirements
    if (
        earlier_count < MINIMUM_RECORDS_FOR_STATISTICAL_TEST
        or later_count < MINIMUM_RECORDS_FOR_STATISTICAL_TEST
    ):
        logger.debug(
            'Segment comparison skipped: insufficient data '
            '(earlier=%d, later=%d, minimum=%d each)',
            earlier_count,
            later_count,
            MINIMUM_RECORDS_FOR_STATISTICAL_TEST,
        )
        return SegmentComparisonResult(
            p_value=1.0,
            is_significant=False,
            effect_size_delta=0.0,
            effect_magnitude=EffectMagnitude.NEGLIGIBLE,
            direction=ChangeDirection.INSUFFICIENT_DATA,
            interpretation='insufficient_data',
            earlier_segment_count=earlier_count,
            later_segment_count=later_count,
        )

    # Perform Mann-Whitney U test
    test_result: MannWhitneyUResultProtocol = mannwhitneyu(
        clean_earlier,
        clean_later,
        alternative='two-sided',
    )
    p_value: float = cast(float, test_result.pvalue)

    # Calculate Cliff's Delta effect size
    # Note: later - earlier order so positive delta indicates increase
    effect_size_delta: float
    effect_magnitude_label: str
    effect_size_delta, effect_magnitude_label = cliffs_delta(
        clean_later.to_numpy(),
        clean_earlier.to_numpy(),
    )

    effect_magnitude: EffectMagnitude = _interpret_effect_magnitude(
        effect_magnitude_label
    )
    is_significant: bool = p_value < significance_threshold

    # Determine direction and build interpretation string
    if is_significant:
        # Determine direction based on medians
        earlier_median: float = clean_earlier.median()
        later_median: float = clean_later.median()

        if later_median > earlier_median:
            direction: ChangeDirection = ChangeDirection.INCREASED
            direction_label: str = 'INCREASED'
        else:
            direction = ChangeDirection.DECREASED
            direction_label = 'DECREASED'

        interpretation: str = (
            f'{direction_label} '
            f'(p={p_value:.3f}, δ={effect_size_delta:.2f}, {effect_magnitude.value})'
        )

        logger.info(
            'Significant segment difference: %s (n_early=%d, n_late=%d)',
            interpretation,
            earlier_count,
            later_count,
        )
    else:
        direction = ChangeDirection.NO_CHANGE
        interpretation = f'NO CHANGE (p={p_value:.3f}, δ={effect_size_delta:.2f})'
        logger.debug(
            'No significant segment difference (p=%.3f, n_early=%d, n_late=%d)',
            p_value,
            earlier_count,
            later_count,
        )

    return SegmentComparisonResult(
        p_value=p_value,
        is_significant=is_significant,
        effect_size_delta=effect_size_delta,
        effect_magnitude=effect_magnitude,
        direction=direction,
        interpretation=interpretation,
        earlier_segment_count=earlier_count,
        later_segment_count=later_count,
    )


# =============================================================================
# RISK DISTRIBUTION COMPARISON
# =============================================================================


def compare_risk_distributions(
    target_group_risk_scores: list[float],
    comparison_group_risk_scores: list[float],
    significance_threshold: float = STATISTICAL_SIGNIFICANCE_ALPHA,
    negligible_effect_threshold: float = CLIFFS_DELTA_NEGLIGIBLE_THRESHOLD,
) -> RiskDistributionComparisonResult | None:
    """
    Perform comprehensive statistical comparison of risk score distributions.

    This function compares the distribution of temporal risk scores between a
    target group (e.g., entities at a specific location) and a comparison group
    (e.g., entities at all other locations). It provides both statistical
    significance testing and practical effect size interpretation.

    The analysis uses:
        - Mann-Whitney U test: Non-parametric test for distribution differences
        - Cliff's Delta: Effect size measure for ordinal/non-normal data

    Args:
        target_group_risk_scores:
            List of risk scores for the group being investigated (e.g., a
            specific location's drivers/vehicles).

        comparison_group_risk_scores:
            List of risk scores for the baseline comparison group (e.g., all
            other locations' drivers/vehicles).

        significance_threshold:
            P-value threshold for declaring statistical significance.
            Default is 0.05.

        negligible_effect_threshold:
            Cliff's Delta threshold below which effect is considered negligible.
            Default is 0.15 (following standard conventions).

    Returns:
        RiskDistributionComparisonResult containing statistical test results,
        effect size with interpretation, descriptive statistics for both groups,
        and raw differences.

        Returns None if either group has fewer than MINIMUM_RECORDS_FOR_STATISTICAL_TEST
        observations.

    Raises:
        No exceptions are raised; insufficient data returns None.

    Example:
        >>> target_risks = [75.0, 82.0, 68.0, 91.0, 77.0]
        >>> baseline_risks = [45.0, 52.0, 48.0, 55.0, 42.0, 51.0, 47.0]
        >>> result = compare_risk_distributions(target_risks, baseline_risks)
        >>> if result and result.is_significant:
        ...     print(f"Direction: {result.effect_size.direction.value}")
        ...     print(f"Effect: {result.effect_size.magnitude.value}")
        ...     print(f"P-value: {result.p_value:.4f}")
        Direction: increased
        Effect: large
        P-value: 0.0025

    See Also:
        - compare_two_segments: Simpler comparison for time segments
    """
    # Convert to numpy arrays for efficient computation
    target_array: NDArray[np.float64] = np.array(
        target_group_risk_scores, dtype=np.float64
    )
    comparison_array: NDArray[np.float64] = np.array(
        comparison_group_risk_scores, dtype=np.float64
    )

    target_count: int = len(target_array)
    comparison_count: int = len(comparison_array)

    # Validate minimum data requirements
    if (
        target_count < MINIMUM_RECORDS_FOR_STATISTICAL_TEST
        or comparison_count < MINIMUM_RECORDS_FOR_STATISTICAL_TEST
    ):
        logger.debug(
            'Risk distribution comparison skipped: insufficient data '
            '(target=%d, comparison=%d, minimum=%d each)',
            target_count,
            comparison_count,
            MINIMUM_RECORDS_FOR_STATISTICAL_TEST,
        )
        return None

    # Perform Mann-Whitney U test
    test_result: MannWhitneyUResultProtocol = mannwhitneyu(
        target_array,
        comparison_array,
        alternative='two-sided',
    )

    u_statistic: float = cast(float, test_result.statistic)
    p_value: float = cast(float, test_result.pvalue)

    # Calculate Cliff's Delta effect size
    effect_delta: float
    effect_magnitude_label: str
    effect_delta, effect_magnitude_label = cliffs_delta(target_array, comparison_array)

    effect_magnitude: EffectMagnitude = _interpret_effect_magnitude(
        effect_magnitude_label
    )
    effect_direction: ChangeDirection = _determine_direction_from_effect(
        effect_delta,
        negligible_effect_threshold,
    )

    # Build effect size result
    effect_size_result = EffectSizeResult(
        value=effect_delta,
        name="Cliff's Delta",
        magnitude=effect_magnitude,
        direction=effect_direction,
    )

    # Calculate descriptive statistics for target group
    target_group_stats = GroupDescriptiveStatistics(
        mean=float(np.mean(target_array)),
        median=float(np.median(target_array)),
        percentile_25=float(np.percentile(target_array, 25)),
        percentile_75=float(np.percentile(target_array, 75)),
        sample_size=target_count,
    )

    # Calculate descriptive statistics for comparison group
    comparison_group_stats = GroupDescriptiveStatistics(
        mean=float(np.mean(comparison_array)),
        median=float(np.median(comparison_array)),
        percentile_25=float(np.percentile(comparison_array, 25)),
        percentile_75=float(np.percentile(comparison_array, 75)),
        sample_size=comparison_count,
    )

    # Calculate raw differences for context
    mean_difference: float = target_group_stats.mean - comparison_group_stats.mean
    median_difference: float = target_group_stats.median - comparison_group_stats.median

    is_significant: bool = p_value < significance_threshold

    if is_significant:
        logger.info(
            'Significant risk distribution difference: %s '
            '(δ=%.2f %s, p=%.4f, n_target=%d, n_comparison=%d)',
            effect_direction.value,
            effect_delta,
            effect_magnitude.value,
            p_value,
            target_count,
            comparison_count,
        )
    else:
        logger.debug(
            'No significant risk distribution difference (δ=%.2f, p=%.4f)',
            effect_delta,
            p_value,
        )

    return RiskDistributionComparisonResult(
        p_value=p_value,
        is_significant=is_significant,
        u_statistic=u_statistic,
        effect_size=effect_size_result,
        target_group=target_group_stats,
        comparison_group=comparison_group_stats,
        mean_difference=mean_difference,
        median_difference=median_difference,
    )
