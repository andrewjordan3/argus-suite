# argus/models/analysis/statistical_test.py
"""
Container for statistical test results.
"""
import logging
import math
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from argus.formatting import EffectSize, EffectSizeLabelRegistry
from argus.models.analysis.type_definitions import (
    Direction,
)
from argus.models.locale.root_config import ReportConfig
from argus.utils import get_effect_magnitude

__all__: list[str] = [
    'StatisticalTest',
]

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)


class StatisticalTest(BaseModel):
    """
    Container for statistical test results.

    This model stores all relevant information from a statistical test,
    including p-values, effect sizes, confidence intervals, and descriptive
    statistics for both target and baseline groups.

    Attributes:
        name: Human-readable name of the test
        p_value: Raw p-value from the statistical test
        q_value: Benjamini-Hochberg adjusted p-value (FDR correction)
        risk_ratio: Ratio of risk in target vs baseline
        risk_ratio_ci: 95% confidence interval for risk ratio
        odds_ratio: Odds ratio comparing groups
        odds_ratio_ci: 95% confidence interval for odds ratio
        effect_size: Standardized effect size (Cliff's Delta, Cohen's d, etc.)
        effect_size_name: Name of the effect size measure used
        is_significant: Whether the test is significant after FDR correction
        fdr_corrected: Whether FDR correction has been applied

        # Rate-based tests (categorical outcomes)
        target_rate: Proportion in target group (0-1)
        baseline_rate: Proportion in baseline group (0-1)
        target_count: Number of events in target group
        baseline_count: Number of events in baseline group
        target_n: Total observations in target group
        baseline_n: Total observations in baseline group

        # Cost/continuous variable tests
        target_total: Sum of values in target group
        baseline_total: Sum of values in baseline group
        target_avg: Mean value in target group
        baseline_avg: Mean value in baseline group
        target_median: Median value in target group
        baseline_median: Median value in baseline group
        mean_difference: Difference in means (target - baseline)
        median_difference: Difference in medians (target - baseline)
        percent_difference: Percentage difference in means
        target_p25: 25th percentile in target group
        target_p75: 75th percentile in target group
        baseline_p25: 25th percentile in baseline group
        baseline_p75: 75th percentile in baseline group
        direction: Direction of difference ('higher' or 'lower')
    """

    model_config = ConfigDict(extra='forbid')

    name: str = Field(..., description='Human-readable name of the test')
    p_value: float = Field(
        default=math.nan,
        description='Raw p-value from the statistical test',
    )
    q_value: float = Field(
        default=math.nan,
        description='Benjamini-Hochberg adjusted p-value (FDR correction)',
    )
    risk_ratio: float = Field(
        default=math.nan,
        description='Ratio of risk in target vs baseline',
    )
    risk_ratio_ci: tuple[float, float] | None = Field(
        default=None,
        description='95% confidence interval for risk ratio',
    )
    odds_ratio: float = Field(
        default=math.nan,
        description='Odds ratio comparing groups',
    )
    odds_ratio_ci: tuple[float, float] | None = Field(
        default=None,
        description='95% confidence interval for odds ratio',
    )
    effect_size: float = Field(
        default=math.nan,
        description="Standardized effect size (Cliff's Delta, Cohen's d, etc.)",
    )
    effect_size_name: EffectSize | None = Field(
        default=None,
        description='Name of the effect size measure used',
    )
    is_significant: bool = Field(
        default=False,
        description='Whether the test is significant after FDR correction',
    )
    fdr_corrected: bool = Field(
        default=False,
        description='Whether FDR correction has been applied',
    )

    # Rate-based test fields
    target_rate: float = Field(
        default=math.nan,
        description='Proportion in target group (0-1)',
    )
    baseline_rate: float = Field(
        default=math.nan,
        description='Proportion in baseline group (0-1)',
    )
    target_count: int | None = Field(
        default=None,
        description='Number of events in target group',
        ge=0,
    )
    baseline_count: int | None = Field(
        default=None,
        description='Number of events in baseline group',
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

    # Cost/continuous variable fields
    target_total: float = Field(
        default=math.nan,
        description='Sum of values in target group',
    )
    baseline_total: float = Field(
        default=math.nan,
        description='Sum of values in baseline group',
    )
    target_avg: float = Field(
        default=math.nan,
        description='Mean value in target group',
    )
    baseline_avg: float = Field(
        default=math.nan,
        description='Mean value in baseline group',
    )
    target_median: float = Field(
        default=math.nan,
        description='Median value in target group',
    )
    baseline_median: float = Field(
        default=math.nan,
        description='Median value in baseline group',
    )
    mean_difference: float = Field(
        default=math.nan,
        description='Difference in means (target - baseline)',
    )
    median_difference: float = Field(
        default=math.nan,
        description='Difference in medians (target - baseline)',
    )
    percent_difference: float = Field(
        default=math.nan,
        description='Percentage difference in means',
    )
    target_p25: float = Field(
        default=math.nan,
        description='25th percentile in target group',
    )
    target_p75: float = Field(
        default=math.nan,
        description='75th percentile in target group',
    )
    baseline_p25: float = Field(
        default=math.nan,
        description='25th percentile in baseline group',
    )
    baseline_p75: float = Field(
        default=math.nan,
        description='75th percentile in baseline group',
    )
    direction: Direction | None = Field(
        default=None,
        description="Direction of difference ('higher' or 'lower')",
    )

    @field_validator('target_rate', 'baseline_rate')
    @classmethod
    def validate_rate_bounds(cls, rate_value: float) -> float:
        """
        Validate that rate values are between 0 and 1 (or NaN).

        Args:
            rate_value: The rate value to validate.

        Returns:
            The validated rate value.

        Raises:
            ValueError: If rate is not NaN and not between 0 and 1.
        """
        if not math.isnan(rate_value) and not (0.0 <= rate_value <= 1.0):
            raise ValueError(f'Rate must be between 0 and 1, got {rate_value}')
        return rate_value

    @field_validator('p_value', 'q_value')
    @classmethod
    def validate_probability_bounds(cls, prob_value: float) -> float:
        """
        Validate that probability values are between 0 and 1 (or NaN).

        Args:
            prob_value: The probability value to validate.

        Returns:
            The validated probability value.

        Raises:
            ValueError: If probability is not NaN and not between 0 and 1.
        """
        if not math.isnan(prob_value) and not (0.0 <= prob_value <= 1.0):
            raise ValueError(f'Probability must be between 0 and 1, got {prob_value}')
        return prob_value

    @model_validator(mode='after')
    def validate_count_consistency(self) -> Self:
        """
        Validate that counts are consistent with sample sizes.

        Ensures that target_count <= target_n and baseline_count <= baseline_n
        when these fields are populated.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If counts exceed sample sizes.
        """
        if (
            self.target_count is not None
            and self.target_n is not None
            and self.target_count > self.target_n
        ):
            raise ValueError(
                f'target_count ({self.target_count}) cannot exceed '
                f'target_n ({self.target_n})'
            )

        if (
            self.baseline_count is not None
            and self.baseline_n is not None
            and self.baseline_count > self.baseline_n
        ):
            raise ValueError(
                f'baseline_count ({self.baseline_count}) cannot exceed '
                f'baseline_n ({self.baseline_n})'
            )

        return self

    def to_dict(self, exclude_none: bool = False) -> dict[str, Any]:
        """
        Convert the test results to a dictionary for serialization.

        Args:
            exclude_none: If True, exclude fields with None values.

        Returns:
            Dictionary representation of the model.
        """
        return self.model_dump(exclude_none=exclude_none)

    def is_rate_test(self) -> bool:
        """Check if this is a rate-based (categorical) test."""
        return not math.isnan(self.target_rate) and not math.isnan(self.baseline_rate)

    def is_cost_test(self) -> bool:
        """Check if this is a cost/continuous variable test."""
        return not math.isnan(self.target_median) and not math.isnan(
            self.baseline_median
        )

    def get_effect_magnitude(self, output_config: ReportConfig) -> str:
        """
        Get a human-readable description of the effect size magnitude. This is a convenience method
        that leverages the `get_effect_magnitude` function from `interpretation_tools`.

        Returns:
            String describing the magnitude ('negligible', 'small', 'medium', 'large')
        """
        if self.effect_size_name is None:
            return 'unknown'
        label_registry: EffectSizeLabelRegistry = EffectSizeLabelRegistry.from_config(
            output_config.statistical_methodology.non_parametric_tests
        )
        effect_key: EffectSize = label_registry.from_label(self.effect_size_name)
        return get_effect_magnitude(
            effect_size=self.effect_size,
            effect_size_type=effect_key,
            output_config=output_config,
        )

    def __repr__(self) -> str:
        """String representation showing key test information."""
        sig_marker: Literal['✓'] | Literal['✗'] = '✓' if self.is_significant else '✗'
        return (
            f"StatisticalTest(name='{self.name}', "
            f'p={self.p_value:.4f}, '
            f"q={self.q_value:.4f if not math.isnan(self.q_value) else 'N/A'}, "
            f'significant={sig_marker})'
        )
