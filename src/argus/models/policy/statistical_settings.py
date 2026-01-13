# argus/models/policy/statistical_settings.py
"""
This module defines configuration models for statistical settings used in ARGUS. It includes
settings for p-value thresholds and overall statistical analysis parameters.
"""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__: list[str] = [
    'FdrMethodType',
    'PValueThresholdsConfig',
    'StatisticsConfig',
]

# Define the allowed FDR methods. Will eventually add "benjamini_yekutieli" and "bonferroni".
FdrMethodType = Literal['benjamini-hochberg']


# =============================================================================
# STATISTICS CONFIGURATION
# =============================================================================
class PValueThresholdsConfig(BaseModel):
    """
    Configuration for p-value interpretation thresholds.

    This configuration defines the cutoffs ARGUS uses to bucket p-values into
    human-readable categories.

    Interpretation rule (inclusive):
        - p <= highly_significant  -> "highly significant"
        - p <= very_significant    -> "very significant"
        - p <= significant         -> "significant"
        - p  > significant         -> "not significant"

    Validation rules:
        - Each threshold must be strictly between 0 and 1.
        - Ordering must be: highly_significant < very_significant < significant

    Attributes:
        significant: Largest (least stringent) threshold. Common default is 0.05.
        very_significant: More stringent threshold. Common default is 0.01.
        highly_significant: Most stringent threshold. Common default is 0.001.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    significant: float = Field(
        default=0.05,
        description='Largest (least stringent) p-value threshold; p <= this is significant.',
        gt=0.0,
        lt=1.0,
    )
    very_significant: float = Field(
        default=0.01,
        description='Intermediate p-value threshold; p <= this is very significant.',
        gt=0.0,
        lt=1.0,
    )
    highly_significant: float = Field(
        default=0.001,
        description='Smallest (most stringent) p-value threshold; p <= this is highly significant.',
        gt=0.0,
        lt=1.0,
    )

    @model_validator(mode='after')
    def validate_monotonic_thresholds(self) -> Self:
        """
        Ensure thresholds are strictly ordered: highly < very < significant.

        Returns:
            Self, if validation passes.

        Raises:
            ValueError: If thresholds are not strictly ordered.
        """
        if not (self.highly_significant < self.very_significant < self.significant):
            raise ValueError(
                'Invalid p_value thresholds: expected '
                'highly_significant < very_significant < significant, but got '
                f'{self.highly_significant=}, {self.very_significant=}, {self.significant=}.'
            )
        return self


class StatisticsConfig(BaseModel):
    """
    Configuration for statistical analysis parameters.

    Controls the rigor of statistical tests, bootstrap parameters, and
    minimum data requirements for various analyses.

    Attributes:
        confidence_level: Statistical confidence level for interval estimation (0-1).
        fdr_method: Method for controlling false discovery rate in multiple testing.
            NOTE: benjamini-hochberg is the only currently supported method.
        p_value: Thresholds used to bucket p-values into significance categories.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    confidence_level: float = Field(
        default=0.95,
        description='Statistical confidence level for intervals (0-1)',
        gt=0.0,
        lt=1.0,
    )

    fdr_method: FdrMethodType = Field(
        default='benjamini-hochberg',
        description='Method for controlling false discovery rate in multiple testing.',
    )

    p_value: PValueThresholdsConfig = Field(
        default_factory=PValueThresholdsConfig,
        description='P-value thresholds used for significance bucketing in reports.',
    )

    def get_alpha(self) -> float:
        """
        Calculate alpha (significance level) from confidence level.

        Alpha represents the probability of rejecting the null hypothesis when it
        is actually true (Type I error rate). It is the complement of the
        confidence level.

        Returns:
            Alpha value (significance threshold).

        Example:
            >>> config = StatisticsConfig(confidence_level=0.95)
            >>> config.get_alpha()
            0.05
        """
        return 1.0 - self.confidence_level
