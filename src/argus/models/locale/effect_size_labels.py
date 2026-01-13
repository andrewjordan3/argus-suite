# argus/models/locale/effect_size_labels.py
"""
============================================================================
EFFECT SIZE LABELS
============================================================================
Localized text labels for interpreting effect size magnitudes and
directions. These labels are used in report narratives to translate
numeric effect sizes into human-readable descriptions.
============================================================================
"""

from pydantic import Field

from argus.models.common import BaseConfigModel

__all__: list[str] = [
    'EffectSizeCliffsDeltaLabels',
    'EffectSizeCohensDLabels',
    'EffectSizeDirectionLabels',
    'EffectSizeLabels',
]


class EffectSizeCliffsDeltaLabels(BaseConfigModel):
    """
    Text labels for interpreting Cliff's Delta effect size magnitudes.

    Cliff's Delta is a non-parametric effect size ranging from -1 to +1.
    These labels translate numeric thresholds into descriptive text.

    Attributes:
        negligible: Label for negligible effects
        small: Label for small effects
        medium: Label for medium effects
        large: Label for large effects
    """

    negligible: str = Field(description="Label for negligible Cliff's Delta")
    small: str = Field(description="Label for small Cliff's Delta")
    medium: str = Field(description="Label for medium Cliff's Delta")
    large: str = Field(description="Label for large Cliff's Delta")


class EffectSizeCohensDLabels(BaseConfigModel):
    """
    Text labels for interpreting Cohen's d effect size magnitudes.

    Cohen's d is a parametric effect size measuring standardized mean
    difference. These labels translate numeric thresholds into text.

    Attributes:
        negligible: Label for negligible effects
        small: Label for small effects
        medium: Label for medium effects
        large: Label for large effects
    """

    negligible: str = Field(description="Label for negligible Cohen's d")
    small: str = Field(description="Label for small Cohen's d")
    medium: str = Field(description="Label for medium Cohen's d")
    large: str = Field(description="Label for large Cohen's d")


class EffectSizeDirectionLabels(BaseConfigModel):
    """
    Text labels for describing direction of effects.

    Used in comparative statements to indicate whether the target
    location has higher or lower values than the baseline.

    Attributes:
        higher: Label for higher/increased values
        lower: Label for lower/decreased values
    """

    higher: str = Field(description='Label for higher/increased direction')
    lower: str = Field(description='Label for lower/decreased direction')


class EffectSizeLabels(BaseConfigModel):
    """
    Complete set of effect size interpretation labels.

    Provides localized text for all effect size measures used in
    statistical analysis, including magnitude descriptors and
    directional indicators.

    Attributes:
        cliffs_delta: Labels for Cliff's Delta magnitudes
        cohens_d: Labels for Cohen's d magnitudes
        direction: Labels for effect directions
    """

    cliffs_delta: EffectSizeCliffsDeltaLabels = Field(
        description="Magnitude labels for Cliff's Delta effect sizes"
    )
    cohens_d: EffectSizeCohensDLabels = Field(
        description="Magnitude labels for Cohen's d effect sizes"
    )
    direction: EffectSizeDirectionLabels = Field(
        description='Directional labels for comparative statements'
    )
