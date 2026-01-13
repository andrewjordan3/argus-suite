# argus/models/policy/effect_size.py

"""
Configuration models for effect size interpretation thresholds.

Effect sizes measure the MAGNITUDE of statistical effects, complementing p-values
which only indicate statistical significance. A statistically significant result
may not be practically significant—effect sizes tell us whether differences are
large enough to matter.
"""

from enum import IntEnum, unique
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__: list[str] = [
    'CliffsDeltaThresholds',
    'CohensDThresholds',
    'EffectMagnitude',
    'EffectSizeInterpretationConfig',
    'OddsRatioThresholds',
    'RiskDifferenceThresholds',
    'RiskRatioThresholds',
]


# =============================================================================
# EFFECT MAGNITUDE ENUM
# =============================================================================
@unique
class EffectMagnitude(IntEnum):
    """
    Effect size magnitude categories with ordinal ranking.

    Integer values represent magnitude (higher = larger effect), enabling
    direct comparisons: EffectMagnitude.LARGE > EffectMagnitude.SMALL evaluates True.

    Display names should be sourced from locale configuration.
    """

    NEGLIGIBLE = 1
    SMALL = 2
    MEDIUM = 3
    LARGE = 4


# =============================================================================
# CLIFF'S DELTA
# =============================================================================
class CliffsDeltaThresholds(BaseModel):
    """
    Thresholds for interpreting Cliff's Delta effect size.

    Cliff's Delta is a non-parametric effect size measure ranging from -1 to +1.
    It represents the probability that a randomly selected value from one group
    exceeds a randomly selected value from another group, minus the reverse
    probability.

    Interpretation uses absolute value:
        - |δ| < negligible -> "negligible" (groups essentially indistinguishable)
        - |δ| < small      -> "small" (detectable but modest)
        - |δ| < medium     -> "medium" (meaningful practical difference)
        - |δ| >= medium    -> "large" (substantial practical difference)

    Attributes:
        negligible: Upper bound for negligible effect.
        small: Upper bound for small effect.
        medium: Upper bound for medium effect; values >= this are large.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    negligible: float = Field(
        default=0.147,
        description='Upper bound for negligible effect.',
        gt=0.0,
        lt=1.0,
    )
    small: float = Field(
        default=0.33,
        description='Upper bound for small effect.',
        gt=0.0,
        lt=1.0,
    )
    medium: float = Field(
        default=0.474,
        description='Upper bound for medium effect; >= this is large.',
        gt=0.0,
        lt=1.0,
    )

    @model_validator(mode='after')
    def validate_threshold_ordering(self) -> Self:
        """
        Ensure thresholds are strictly ordered: negligible < small < medium.

        Returns:
            Self, if validation passes.

        Raises:
            ValueError: If thresholds are not strictly ordered.
        """
        if not (self.negligible < self.small < self.medium):
            raise ValueError(
                "Cliff's Delta thresholds must be strictly ordered: "
                f'negligible < small < medium, but got '
                f'{self.negligible=}, {self.small=}, {self.medium=}.'
            )
        return self

    def get_effect_magnitude(self, delta: float) -> EffectMagnitude:
        """
        Determine effect magnitude for a Cliff's Delta value.

        Args:
            delta: Cliff's Delta value (-1 to +1).

        Returns:
            Effect magnitude category.
        """
        abs_delta: float = abs(delta)
        if abs_delta < self.negligible:
            return EffectMagnitude.NEGLIGIBLE
        if abs_delta < self.small:
            return EffectMagnitude.SMALL
        if abs_delta < self.medium:
            return EffectMagnitude.MEDIUM
        return EffectMagnitude.LARGE


# =============================================================================
# COHEN'S D
# =============================================================================
class CohensDThresholds(BaseModel):
    """
    Thresholds for interpreting Cohen's d effect size.

    Cohen's d measures the standardized difference between two means
    (difference in standard deviation units). Unlike Cliff's Delta,
    Cohen's d is unbounded.

    Interpretation uses absolute value:
        - |d| < negligible -> "negligible"
        - |d| < small      -> "small"
        - |d| < medium     -> "medium"
        - |d| >= medium    -> "large"

    Attributes:
        negligible: Upper bound for negligible effect.
        small: Upper bound for small effect.
        medium: Upper bound for medium effect; values >= this are large.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    negligible: float = Field(
        default=0.2,
        description='Upper bound for negligible effect.',
        gt=0.0,
    )
    small: float = Field(
        default=0.5,
        description='Upper bound for small effect.',
        gt=0.0,
    )
    medium: float = Field(
        default=0.8,
        description='Upper bound for medium effect; >= this is large.',
        gt=0.0,
    )

    @model_validator(mode='after')
    def validate_threshold_ordering(self) -> Self:
        """
        Ensure thresholds are strictly ordered: negligible < small < medium.

        Returns:
            Self, if validation passes.

        Raises:
            ValueError: If thresholds are not strictly ordered.
        """
        if not (self.negligible < self.small < self.medium):
            raise ValueError(
                "Cohen's d thresholds must be strictly ordered: "
                f'negligible < small < medium, but got '
                f'{self.negligible=}, {self.small=}, {self.medium=}.'
            )
        return self

    def get_effect_magnitude(self, d: float) -> EffectMagnitude:
        """
        Determine effect magnitude for a Cohen's d value.

        Args:
            d: Cohen's d value (unbounded).

        Returns:
            Effect magnitude category.
        """
        abs_d: float = abs(d)
        if abs_d < self.negligible:
            return EffectMagnitude.NEGLIGIBLE
        if abs_d < self.small:
            return EffectMagnitude.SMALL
        if abs_d < self.medium:
            return EffectMagnitude.MEDIUM
        return EffectMagnitude.LARGE


# =============================================================================
# RISK RATIO
# =============================================================================
class RiskRatioThresholds(BaseModel):
    """
    Thresholds for interpreting Risk Ratio (Relative Risk).

    Risk Ratio measures how many times more likely an event is in the target
    group versus the baseline. RR = 1.0 means no difference.

    Interpretation (for RR >= 1.0):
        - RR < substantial    -> "minimal difference"
        - RR < major_concern  -> "substantial difference"
        - RR >= major_concern -> "major concern"

    Note:
        For protective effects (RR < 1.0), interpretation uses 1/RR.

    Attributes:
        substantial: Threshold for substantial difference (e.g., 2x as likely).
        major_concern: Threshold for major concern warranting investigation.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    substantial: float = Field(
        default=2.0,
        description='Threshold for substantial difference.',
        gt=1.0,
    )
    major_concern: float = Field(
        default=3.0,
        description='Threshold for major concern warranting investigation.',
        gt=1.0,
    )

    @model_validator(mode='after')
    def validate_threshold_ordering(self) -> Self:
        """
        Ensure thresholds are strictly ordered: substantial < major_concern.

        Returns:
            Self, if validation passes.

        Raises:
            ValueError: If thresholds are not strictly ordered.
        """
        if not (self.substantial < self.major_concern):
            raise ValueError(
                'Risk Ratio thresholds must be strictly ordered: '
                f'substantial < major_concern, but got '
                f'{self.substantial=}, {self.major_concern=}.'
            )
        return self


# =============================================================================
# ODDS RATIO
# =============================================================================
class OddsRatioThresholds(BaseModel):
    """
    Thresholds for interpreting Odds Ratio.

    Odds Ratio measures the strength of association between group membership
    and event occurrence. OR = 1.0 means no association.

    Interpretation (for OR >= 1.0):
        - OR < strong      -> "weak/moderate association"
        - OR < very_strong -> "strong association"
        - OR >= very_strong -> "very strong association"

    Note:
        For protective associations (OR < 1.0), interpretation uses 1/OR.

    Attributes:
        strong: Threshold for strong association.
        very_strong: Threshold for very strong association.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    strong: float = Field(
        default=3.0,
        description='Threshold for strong association.',
        gt=1.0,
    )
    very_strong: float = Field(
        default=10.0,
        description='Threshold for very strong association.',
        gt=1.0,
    )

    @model_validator(mode='after')
    def validate_threshold_ordering(self) -> Self:
        """
        Ensure thresholds are strictly ordered: strong < very_strong.

        Returns:
            Self, if validation passes.

        Raises:
            ValueError: If thresholds are not strictly ordered.
        """
        if not (self.strong < self.very_strong):
            raise ValueError(
                'Odds Ratio thresholds must be strictly ordered: '
                f'strong < very_strong, but got '
                f'{self.strong=}, {self.very_strong=}.'
            )
        return self


# =============================================================================
# RISK DIFFERENCE
# =============================================================================
class RiskDifferenceThresholds(BaseModel):
    """
    Thresholds for interpreting Risk Difference (Absolute Risk Reduction).

    Risk Difference is the absolute difference in event rates between groups,
    expressed as a proportion (0.10 = 10 percentage points).

    Interpretation (using absolute value):
        - |RD| < practically_significant -> "minimal difference"
        - |RD| < major_difference        -> "practically significant"
        - |RD| >= major_difference       -> "major difference"

    Attributes:
        practically_significant: Threshold for practical significance (e.g., 10pp).
        major_difference: Threshold for major difference (e.g., 20pp).
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    practically_significant: float = Field(
        default=0.10,
        description='Threshold for practical significance.',
        gt=0.0,
        le=1.0,
    )
    major_difference: float = Field(
        default=0.20,
        description='Threshold for major difference.',
        gt=0.0,
        le=1.0,
    )

    @model_validator(mode='after')
    def validate_threshold_ordering(self) -> Self:
        """
        Ensure thresholds are strictly ordered: practically_significant < major_difference.

        Returns:
            Self, if validation passes.

        Raises:
            ValueError: If thresholds are not strictly ordered.
        """
        if not (self.practically_significant < self.major_difference):
            raise ValueError(
                'Risk Difference thresholds must be strictly ordered: '
                f'practically_significant < major_difference, but got '
                f'{self.practically_significant=}, {self.major_difference=}.'
            )
        return self


# =============================================================================
# ROOT CONFIGURATION
# =============================================================================
class EffectSizeInterpretationConfig(BaseModel):
    """
    Configuration for effect size interpretation thresholds.

    Aggregates thresholds for all supported effect size measures.

    Attributes:
        cliffs_delta: Thresholds for Cliff's Delta (non-parametric, bounded).
        cohens_d: Thresholds for Cohen's d (parametric, unbounded).
        risk_ratio: Thresholds for Risk Ratio interpretation.
        odds_ratio: Thresholds for Odds Ratio interpretation.
        risk_difference: Thresholds for Risk Difference interpretation.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    cliffs_delta: CliffsDeltaThresholds = Field(
        default_factory=CliffsDeltaThresholds,
        description="Thresholds for Cliff's Delta effect size.",
    )
    cohens_d: CohensDThresholds = Field(
        default_factory=CohensDThresholds,
        description="Thresholds for Cohen's d effect size.",
    )
    risk_ratio: RiskRatioThresholds = Field(
        default_factory=RiskRatioThresholds,
        description='Thresholds for Risk Ratio interpretation.',
    )
    odds_ratio: OddsRatioThresholds = Field(
        default_factory=OddsRatioThresholds,
        description='Thresholds for Odds Ratio interpretation.',
    )
    risk_difference: RiskDifferenceThresholds = Field(
        default_factory=RiskDifferenceThresholds,
        description='Thresholds for Risk Difference interpretation.',
    )
