# argus/models/analysis/statistical_test.py
"""
Statistical Test Result Model for ARGUS Analysis Pipeline.

This module defines the StatisticalTest model, a pure data container that
encapsulates all relevant outputs from a statistical hypothesis test. The
model supports both rate-based tests (comparing proportions between groups)
and continuous variable tests (comparing distributions of costs, volumes, etc.).

Design Philosophy:
    This model follows the ARGUS principle of separating data from policy.
    It contains only raw statistical outputs—no methods that depend on
    configuration thresholds, locale settings, or presentation formatting.
    Interpretation of these values (e.g., categorizing effect size magnitude,
    formatting p-values for reports) belongs in service/processor layers.

Immutability:
    Instances are frozen after creation. Statistical test results represent
    a point-in-time computation and should not be modified. When post-processing
    is required (e.g., applying FDR correction to update q_value and
    is_significant), create a new instance with the updated values:

        >>> corrected = StatisticalTest(
        ...     **original.model_dump(),
        ...     q_value=adjusted_p,
        ...     is_significant=adjusted_p < alpha,
        ...     fdr_corrected=True,
        ... )

Statistical Background:
    The model accommodates results from various non-parametric tests used in
    ARGUS, including:
    - Fisher's Exact Test (rate comparisons)
    - Mann-Whitney U Test (continuous variable comparisons)
    - Barnard's Exact Test (rate comparisons with small samples)

    Effect sizes are stored generically since different tests produce different
    measures (Cliff's Delta, Cohen's d, odds ratios, risk ratios, etc.).

Usage:
    >>> from argus.models.analysis.statistical_test import StatisticalTest
    >>>
    >>> # Rate-based test result
    >>> test = StatisticalTest(
    ...     name='No ELD Rate Comparison',
    ...     p_value=0.0023,
    ...     q_value=0.0089,
    ...     is_significant=True,
    ...     fdr_corrected=True,
    ...     effect_size=0.42,
    ...     effect_size_name='cliffs_delta',
    ...     target_rate=0.35,
    ...     baseline_rate=0.12,
    ...     target_count=28,
    ...     target_n=80,
    ...     baseline_count=60,
    ...     baseline_n=500,
    ...     risk_ratio=2.92,
    ...     risk_ratio_ci=(1.85, 4.61),
    ...     direction='higher',
    ... )
    >>>
    >>> test.is_significant
    True
    >>> test.risk_ratio
    2.92

See Also:
    - argus.models.analysis.driver_risk: Driver-level risk profile aggregations
    - argus.models.analysis.temporal_risk: Time-series risk analysis results
    - argus.services.fdr_correction: Service for applying FDR correction
    - argus.services.effect_interpretation: Service for effect size categorization
"""

import math
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator

from argus.models.common import FrozenModel

# -----------------------------------------------------------------------------
# Type Definitions
# -----------------------------------------------------------------------------
# Defined locally to avoid cross-module dependencies. These types are specific
# to statistical test results and unlikely to be shared with other models.
# -----------------------------------------------------------------------------

Direction = Literal['higher', 'lower']
"""Direction of effect: whether target group metric is higher or lower than baseline."""

__all__: list[str] = [
    'Direction',
    'StatisticalTest',
]


# -----------------------------------------------------------------------------
# Validation Tolerances
# -----------------------------------------------------------------------------
# These module-level constants define the tolerances used in model validators.
# Centralizing them here makes the validation logic clearer and allows easy
# adjustment if upstream statistical libraries have different precision.
# -----------------------------------------------------------------------------

# Absolute tolerance for probability bounds validation.
# Accounts for floating-point representation errors in p-value calculations.
# A p-value of 1.0000000001 due to floating-point arithmetic is acceptable.
_PROBABILITY_BOUND_TOLERANCE: float = 1e-9

# Absolute tolerance for rate bounds validation.
# Accounts for floating-point representation errors in proportion calculations.
_RATE_BOUND_TOLERANCE: float = 1e-9


class StatisticalTest(FrozenModel):
    """
    Container for statistical hypothesis test results.

    This model stores all relevant outputs from a statistical test, including
    p-values, effect sizes, confidence intervals, and descriptive statistics
    for both target and baseline groups. All values represent raw statistical
    outputs with no policy interpretation applied.

    The model supports two primary test types:
        - Rate-based tests: Compare proportions between groups (e.g., comparing
          fraud rates between high-risk and baseline drivers)
        - Continuous tests: Compare distributions of numeric values (e.g.,
          comparing transaction costs between groups)

    Many fields default to math.nan (Not a Number) rather than None to
    facilitate downstream numerical operations. NaN values propagate through
    calculations without raising exceptions, making them suitable for optional
    numeric fields. Use math.isnan() to check for missing values.

    Attributes:
        name: Human-readable identifier for the test. Should describe what
            is being compared (e.g., 'No ELD Rate: Target vs Baseline').

        p_value: Raw p-value from the statistical test, representing the
            probability of observing results at least as extreme as the
            actual results, assuming the null hypothesis is true. Values
            must be in [0.0, 1.0]. Defaults to NaN if not computed.

        q_value: Benjamini-Hochberg adjusted p-value after False Discovery
            Rate (FDR) correction. When running multiple tests, q-values
            control the expected proportion of false positives among
            rejected hypotheses. Values must be in [0.0, 1.0]. Defaults
            to NaN if FDR correction has not been applied.

        is_significant: Boolean flag indicating whether the test result
            is statistically significant after applying the appropriate
            correction (typically FDR). This is the primary field used
            for decision-making; raw p_value should not be used directly
            for significance decisions when multiple tests are performed.

        fdr_corrected: Boolean flag indicating whether FDR correction has
            been applied. When False, q_value should be NaN and is_significant
            reflects raw p-value comparison (if set at all).

        effect_size: Standardized measure of the magnitude of the difference
            between groups, independent of sample size. Common measures include
            Cliff's Delta (ordinal data), Cohen's d (continuous data), and
            phi coefficient (categorical data). Defaults to NaN if not computed.

        effect_size_name: Identifier for the effect size measure used.
            Examples: 'cliffs_delta', 'cohens_d', 'phi_coefficient'.
            Required for downstream interpretation of effect_size magnitude.

        risk_ratio: Ratio of the probability of an event in the target group
            to the probability in the baseline group. A risk ratio of 2.0
            indicates the target group has twice the risk. Also known as
            relative risk. Defaults to NaN if not applicable.

        risk_ratio_ci: 95% confidence interval for the risk ratio as a
            (lower, upper) tuple. Intervals not containing 1.0 indicate
            statistically significant differences in risk.

        odds_ratio: Ratio of odds of an event in the target group to odds
            in the baseline group. Similar to risk ratio but uses odds
            (p / (1-p)) rather than probabilities. Defaults to NaN.

        odds_ratio_ci: 95% confidence interval for the odds ratio as a
            (lower, upper) tuple.

        target_rate: Proportion of events in the target group, expressed
            as a value in [0.0, 1.0]. For rate-based tests only.

        baseline_rate: Proportion of events in the baseline group, expressed
            as a value in [0.0, 1.0]. For rate-based tests only.

        target_count: Number of events (successes) observed in target group.
            Must not exceed target_n.

        baseline_count: Number of events (successes) observed in baseline group.
            Must not exceed baseline_n.

        target_n: Total number of observations in target group.

        baseline_n: Total number of observations in baseline group.

        target_total: Sum of values in target group (continuous tests only).

        baseline_total: Sum of values in baseline group (continuous tests only).

        target_avg: Arithmetic mean of values in target group.

        baseline_avg: Arithmetic mean of values in baseline group.

        target_median: Median value in target group. Often preferred over
            mean for skewed distributions common in cost/volume data.

        baseline_median: Median value in baseline group.

        mean_difference: Difference in means (target_avg - baseline_avg).
            Positive values indicate target group has higher average.

        median_difference: Difference in medians (target_median - baseline_median).

        percent_difference: Percentage difference in means relative to baseline,
            computed as ((target_avg - baseline_avg) / baseline_avg) * 100.

        target_p25: 25th percentile (first quartile) of target group values.

        target_p75: 75th percentile (third quartile) of target group values.

        baseline_p25: 25th percentile of baseline group values.

        baseline_p75: 75th percentile of baseline group values.

        direction: Indicates whether target group metric is 'higher' or
            'lower' than baseline. Provides semantic context for effect_size
            and difference measures.

    Invariants:
        - p_value and q_value, if not NaN, must be in [0.0, 1.0]
        - target_rate and baseline_rate, if not NaN, must be in [0.0, 1.0]
        - target_count <= target_n when both are provided
        - baseline_count <= baseline_n when both are provided
        - If fdr_corrected is False, q_value should typically be NaN

    Example:
        >>> test = StatisticalTest(
        ...     name='After Hours Rate Comparison',
        ...     p_value=0.0156,
        ...     effect_size=0.28,
        ...     effect_size_name='cliffs_delta',
        ...     target_rate=0.22,
        ...     baseline_rate=0.09,
        ...     target_n=45,
        ...     baseline_n=312,
        ...     direction='higher',
        ... )
        >>> print(test)
        StatisticalTest(name='After Hours Rate Comparison', p=0.0156, q=N/A, significant=✗)
    """

    # -------------------------------------------------------------------------
    # Test Identification
    # -------------------------------------------------------------------------

    name: str = Field(
        ...,
        description='Human-readable identifier for the test',
        min_length=1,
    )

    # -------------------------------------------------------------------------
    # Core Statistical Results
    # -------------------------------------------------------------------------
    # These fields capture the primary outputs used for hypothesis testing
    # decisions. The p_value is the raw result; q_value and is_significant
    # reflect post-hoc corrections for multiple comparisons.
    # -------------------------------------------------------------------------

    p_value: float = Field(
        default=math.nan,
        description='Raw p-value from the statistical test (0-1)',
    )

    q_value: float = Field(
        default=math.nan,
        description='Benjamini-Hochberg adjusted p-value after FDR correction (0-1)',
    )

    is_significant: bool = Field(
        default=False,
        description='Whether the test is significant after correction',
    )

    fdr_corrected: bool = Field(
        default=False,
        description='Whether FDR correction has been applied',
    )

    # -------------------------------------------------------------------------
    # Effect Size Measures
    # -------------------------------------------------------------------------
    # Effect sizes quantify the magnitude of differences independent of sample
    # size. The effect_size_name field identifies which measure was used,
    # enabling appropriate interpretation thresholds.
    # -------------------------------------------------------------------------

    effect_size: float = Field(
        default=math.nan,
        description="Standardized effect size (Cliff's Delta, Cohen's d, etc.)",
    )

    effect_size_name: str | None = Field(
        default=None,
        description="Name of effect size measure (e.g., 'cliffs_delta', 'cohens_d')",
    )

    # -------------------------------------------------------------------------
    # Risk and Odds Ratios with Confidence Intervals
    # -------------------------------------------------------------------------
    # These measures quantify relative risk between groups. Confidence intervals
    # that exclude 1.0 indicate statistically significant differences.
    # -------------------------------------------------------------------------

    risk_ratio: float = Field(
        default=math.nan,
        description='Ratio of event probability in target vs baseline group',
    )

    risk_ratio_ci: tuple[float, float] | None = Field(
        default=None,
        description='95% confidence interval for risk ratio (lower, upper)',
    )

    odds_ratio: float = Field(
        default=math.nan,
        description='Ratio of event odds in target vs baseline group',
    )

    odds_ratio_ci: tuple[float, float] | None = Field(
        default=None,
        description='95% confidence interval for odds ratio (lower, upper)',
    )

    # -------------------------------------------------------------------------
    # Rate-Based Test Fields (Categorical Outcomes)
    # -------------------------------------------------------------------------
    # These fields are populated for tests comparing proportions between groups,
    # such as comparing fraud rates or policy violation rates.
    # -------------------------------------------------------------------------

    target_rate: float = Field(
        default=math.nan,
        description='Proportion of events in target group (0-1)',
    )

    baseline_rate: float = Field(
        default=math.nan,
        description='Proportion of events in baseline group (0-1)',
    )

    target_count: int | None = Field(
        default=None,
        description='Number of events observed in target group',
        ge=0,
    )

    baseline_count: int | None = Field(
        default=None,
        description='Number of events observed in baseline group',
        ge=0,
    )

    target_n: int | None = Field(
        default=None,
        description='Total observations in target group',
        ge=0,
    )

    baseline_n: int | None = Field(
        default=None,
        description='Total observations in baseline group',
        ge=0,
    )

    # -------------------------------------------------------------------------
    # Continuous Variable Fields (Cost, Volume, etc.)
    # -------------------------------------------------------------------------
    # These fields are populated for tests comparing distributions of numeric
    # values, such as transaction costs or fuel volumes.
    # -------------------------------------------------------------------------

    target_total: float = Field(
        default=math.nan,
        description='Sum of all values in target group',
    )

    baseline_total: float = Field(
        default=math.nan,
        description='Sum of all values in baseline group',
    )

    target_avg: float = Field(
        default=math.nan,
        description='Arithmetic mean of values in target group',
    )

    baseline_avg: float = Field(
        default=math.nan,
        description='Arithmetic mean of values in baseline group',
    )

    target_median: float = Field(
        default=math.nan,
        description='Median value in target group',
    )

    baseline_median: float = Field(
        default=math.nan,
        description='Median value in baseline group',
    )

    # -------------------------------------------------------------------------
    # Difference Measures
    # -------------------------------------------------------------------------
    # Pre-computed differences for convenience. These can be derived from
    # other fields but are often needed for reporting and visualization.
    # -------------------------------------------------------------------------

    mean_difference: float = Field(
        default=math.nan,
        description='Difference in means (target_avg - baseline_avg)',
    )

    median_difference: float = Field(
        default=math.nan,
        description='Difference in medians (target_median - baseline_median)',
    )

    percent_difference: float = Field(
        default=math.nan,
        description='Percentage difference in means relative to baseline',
    )

    # -------------------------------------------------------------------------
    # Distribution Quartiles
    # -------------------------------------------------------------------------
    # Quartiles provide insight into the spread and skewness of distributions,
    # which is important for understanding non-normal data common in cost
    # and volume analyses.
    # -------------------------------------------------------------------------

    target_p25: float = Field(
        default=math.nan,
        description='25th percentile (Q1) of target group',
    )

    target_p75: float = Field(
        default=math.nan,
        description='75th percentile (Q3) of target group',
    )

    baseline_p25: float = Field(
        default=math.nan,
        description='25th percentile (Q1) of baseline group',
    )

    baseline_p75: float = Field(
        default=math.nan,
        description='75th percentile (Q3) of baseline group',
    )

    # -------------------------------------------------------------------------
    # Direction of Effect
    # -------------------------------------------------------------------------

    # NOTE: This should be used only by the programmer and not meant for presentation
    # to end-users. It provides semantic context for effect_size and difference
    # measures but should not be displayed directly in reports.
    # It will probably be removed in future versions in favor of deriving direction
    # on-the-fly from relevant fields.
    direction: Direction | None = Field(
        default=None,
        description="Direction of difference: 'higher' or 'lower' vs baseline",
    )

    # -------------------------------------------------------------------------
    # Field Validators
    # -------------------------------------------------------------------------
    # These validators enforce mathematical constraints that must hold for
    # any valid statistical test result. They run on individual fields
    # before model validators.
    # -------------------------------------------------------------------------

    @field_validator('target_rate', 'baseline_rate')
    @classmethod
    def validate_rate_bounds(cls, rate_value: float) -> float:
        """
        Validate that rate values are valid proportions.

        Rates (proportions) must be in the closed interval [0.0, 1.0] or
        NaN if not applicable. This is a fundamental mathematical constraint:
        a proportion cannot be negative or exceed 100%.

        A small tolerance is applied to handle floating-point representation
        errors (e.g., 1.0000000001 due to arithmetic).

        Args:
            rate_value: The rate value to validate.

        Returns:
            The validated rate value, unchanged.

        Raises:
            ValueError: If rate is not NaN and not in [0.0, 1.0] (within tolerance).
        """
        if math.isnan(rate_value):
            return rate_value

        # Check lower bound with tolerance
        lower_bound_valid: bool = rate_value >= (0.0 - _RATE_BOUND_TOLERANCE)

        # Check upper bound with tolerance
        upper_bound_valid: bool = rate_value <= (1.0 + _RATE_BOUND_TOLERANCE)

        if not (lower_bound_valid and upper_bound_valid):
            raise ValueError(
                f'Rate must be a proportion in [0.0, 1.0], got {rate_value}. '
                f'Rates represent proportions and cannot be negative or exceed 1.'
            )

        return rate_value

    @field_validator('p_value', 'q_value')
    @classmethod
    def validate_probability_bounds(cls, prob_value: float) -> float:
        """
        Validate that probability values are mathematically valid.

        P-values and q-values are probabilities and must be in the closed
        interval [0.0, 1.0] or NaN if not computed. This is a fundamental
        constraint from probability theory.

        A small tolerance is applied to handle floating-point representation
        errors from statistical library calculations.

        Args:
            prob_value: The probability value to validate.

        Returns:
            The validated probability value, unchanged.

        Raises:
            ValueError: If probability is not NaN and not in [0.0, 1.0].
        """
        if math.isnan(prob_value):
            return prob_value

        # Check lower bound with tolerance
        lower_bound_valid: bool = prob_value >= (0.0 - _PROBABILITY_BOUND_TOLERANCE)

        # Check upper bound with tolerance
        upper_bound_valid: bool = prob_value <= (1.0 + _PROBABILITY_BOUND_TOLERANCE)

        if not (lower_bound_valid and upper_bound_valid):
            raise ValueError(
                f'Probability must be in [0.0, 1.0], got {prob_value}. '
                f'P-values and q-values are probabilities and cannot exceed 1 '
                f'or be negative.'
            )

        return prob_value

    # -------------------------------------------------------------------------
    # Model Validators
    # -------------------------------------------------------------------------
    # These validators enforce cross-field consistency constraints that
    # require access to multiple fields simultaneously.
    # -------------------------------------------------------------------------

    @model_validator(mode='after')
    def validate_count_consistency(self) -> Self:
        """
        Validate that event counts do not exceed sample sizes.

        In a rate-based test, the number of events (count) cannot exceed
        the total number of observations (n). This is a fundamental constraint:
        you cannot observe more successes than trials.

        This validator checks both target and baseline groups when the
        relevant fields are populated.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If target_count > target_n or baseline_count > baseline_n.
        """
        # Validate target group consistency
        if (
            self.target_count is not None
            and self.target_n is not None
            and self.target_count > self.target_n
        ):
            raise ValueError(
                f'Invalid target group data: target_count ({self.target_count}) '
                f'exceeds target_n ({self.target_n}). The number of events cannot '
                f'exceed the total number of observations.'
            )

        # Validate baseline group consistency
        if (
            self.baseline_count is not None
            and self.baseline_n is not None
            and self.baseline_count > self.baseline_n
        ):
            raise ValueError(
                f'Invalid baseline group data: baseline_count ({self.baseline_count}) '
                f'exceeds baseline_n ({self.baseline_n}). The number of events cannot '
                f'exceed the total number of observations.'
            )

        return self

    @model_validator(mode='after')
    def validate_fdr_correction_consistency(self) -> Self:
        """
        Validate consistency between fdr_corrected flag and q_value.

        When fdr_corrected is True, q_value should be a valid probability
        (not NaN), as FDR correction produces adjusted p-values. When
        fdr_corrected is False, q_value is expected to be NaN (correction
        not yet applied).

        This validator warns about inconsistencies but does not raise
        exceptions, as there may be valid edge cases (e.g., q_value could
        be NaN if the test was excluded from FDR correction).

        Returns:
            The validated model instance.

        Note:
            This validator does not raise exceptions to allow flexibility
            in edge cases. The inconsistency is logged for debugging.
        """
        # If FDR corrected, q_value should typically be populated
        if self.fdr_corrected and math.isnan(self.q_value):
            # This is unusual but not necessarily invalid
            # Could occur if test was excluded from correction
            pass  # Consider logging a warning in production

        # If not FDR corrected, q_value should typically be NaN
        if not self.fdr_corrected and not math.isnan(self.q_value):
            # This is unusual - q_value set without fdr_corrected flag
            pass  # Consider logging a warning in production

        return self

    @model_validator(mode='after')
    def validate_rate_count_consistency(self) -> Self:
        """
        Validate that rates are consistent with counts when both are provided.

        When target_rate, target_count, and target_n are all provided, the
        rate should approximately equal count/n. This catches data pipeline
        errors where rates and counts might come from different sources.

        Uses a relative tolerance to handle floating-point arithmetic and
        rounding in upstream systems.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If computed rate differs significantly from provided rate.
        """
        # Relative tolerance for rate consistency (1% = 0.01)
        rate_consistency_tolerance: float = 0.01

        # Validate target rate consistency
        if (
            not math.isnan(self.target_rate)
            and self.target_count is not None
            and self.target_n is not None
            and self.target_n > 0
        ):
            expected_rate: float = self.target_count / self.target_n
            if not math.isclose(
                self.target_rate,
                expected_rate,
                rel_tol=rate_consistency_tolerance,
                abs_tol=_RATE_BOUND_TOLERANCE,
            ):
                raise ValueError(
                    f'Inconsistent target rate data: target_rate ({self.target_rate:.4f}) '
                    f'does not match target_count/target_n '
                    f'({self.target_count}/{self.target_n} = {expected_rate:.4f}).'
                )

        # Validate baseline rate consistency
        if (
            not math.isnan(self.baseline_rate)
            and self.baseline_count is not None
            and self.baseline_n is not None
            and self.baseline_n > 0
        ):
            expected_rate = self.baseline_count / self.baseline_n
            if not math.isclose(
                self.baseline_rate,
                expected_rate,
                rel_tol=rate_consistency_tolerance,
                abs_tol=_RATE_BOUND_TOLERANCE,
            ):
                raise ValueError(
                    f'Inconsistent baseline rate data: baseline_rate ({self.baseline_rate:.4f}) '
                    f'does not match baseline_count/baseline_n '
                    f'({self.baseline_count}/{self.baseline_n} = {expected_rate:.4f}).'
                )

        return self

    @model_validator(mode='after')
    def validate_confidence_interval_ordering(self) -> Self:
        """
        Validate that confidence interval bounds are properly ordered.

        For confidence intervals provided as (lower, upper) tuples, the
        lower bound must not exceed the upper bound. This catches data
        entry errors or bugs in CI calculation code.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If lower bound exceeds upper bound in any CI.
        """
        lower: float
        upper: float
        # Validate risk ratio CI ordering
        if self.risk_ratio_ci is not None:
            lower, upper = self.risk_ratio_ci
            if lower > upper:
                raise ValueError(
                    f'Invalid risk_ratio_ci: lower bound ({lower}) exceeds '
                    f'upper bound ({upper}). Confidence intervals must have '
                    f'lower <= upper.'
                )

        # Validate odds ratio CI ordering
        if self.odds_ratio_ci is not None:
            lower, upper = self.odds_ratio_ci
            if lower > upper:
                raise ValueError(
                    f'Invalid odds_ratio_ci: lower bound ({lower}) exceeds '
                    f'upper bound ({upper}). Confidence intervals must have '
                    f'lower <= upper.'
                )

        return self

    # -------------------------------------------------------------------------
    # String Representation
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        """
        Return a compact string representation for debugging and logging.

        Shows the most important fields for quick assessment of test results:
        name, p-value, q-value, and significance status. The checkmark (✓)
        or cross (✗) provides immediate visual feedback on significance.

        Returns:
            Compact string suitable for logs and REPL inspection.

        Example:
            >>> repr(test)
            "StatisticalTest(name='No ELD Rate', p=0.0023, q=0.0089, significant=✓)"
        """
        # Format significance as visual indicator
        significance_marker: str = '✓' if self.is_significant else '✗'

        # Format q-value, showing N/A if not yet computed
        q_value_display: str = (
            f'{self.q_value:.4f}' if not math.isnan(self.q_value) else 'N/A'
        )

        # Format p-value, showing N/A if not computed (unusual but possible)
        p_value_display: str = (
            f'{self.p_value:.4f}' if not math.isnan(self.p_value) else 'N/A'
        )

        return (
            f"StatisticalTest(name='{self.name}', "
            f'p={p_value_display}, '
            f'q={q_value_display}, '
            f'significant={significance_marker})'
        )
