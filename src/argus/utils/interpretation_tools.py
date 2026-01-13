# argus/utils/interpretation_tools.py

import logging
import math

from argus.config import RiskCategory, RiskScoreThresholds
from argus.formatting.effect_size_mapping import EffectSize
from argus.models import (
    ConfigurationEffectSizesCliffsDelta,
    ConfigurationEffectSizesCohensD,
    ReportConfig,
    TestInterpretationsCliffsDeltaMagnitudeLabels,
    TestInterpretationsCohensDMagnitudeLabels,
)

__all__: list[str] = [
    'categorize_risk_score',
    'check_rate_exceeds_threshold',
    'get_cliffs_delta_magnitude',
    'get_cohens_d_magnitude',
    'get_effect_magnitude',
]

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)


def categorize_risk_score(
    risk_score: float | int,
    thresholds: RiskScoreThresholds,
) -> RiskCategory:
    """
    Convenience function to categorize a risk score into Critical/High/Medium/Low
    based on thresholds.

    This function provides consistent risk categorization across all risk profile
    types (Driver, Vehicle, Temporal) using configurable threshold values.

    Args:
        risk_score: Numeric risk score (0-100 scale).
        thresholds: Risk score threshold configuration defining category boundaries.

    Returns:
        Risk category: 'Critical', 'High', 'Medium', or 'Low'

    Example:
        >>> thresholds = RiskScoreThresholds(critical=75, high=50, medium=25, low=0)
        >>> categorize_risk_score(80, thresholds)
        'Critical'
        >>> categorize_risk_score(45, thresholds)
        'Medium'
    """
    return thresholds.get_risk_category(risk_score)


def check_rate_exceeds_threshold(rate: float, threshold: float) -> bool:
    """
    Check if a rate exceeds a given threshold.

    Simple comparison helper that provides a named, testable function for
    threshold checks rather than inline comparisons.

    Args:
        rate: Rate value to check (0-1 scale).
        threshold: Threshold value to compare against (0-1 scale).

    Returns:
        True if rate >= threshold, False otherwise.

    Example:
        >>> check_rate_exceeds_threshold(0.25, 0.20)
        True
        >>> check_rate_exceeds_threshold(0.15, 0.20)
        False
    """
    return rate >= threshold


def get_effect_magnitude(
    effect_size: float,
    effect_size_type: EffectSize,
    output_config: ReportConfig,
) -> str:
    """
    Get a human-readable description of the effect size magnitude.

    Uses the EffectSize enum's internal key to dynamically access the
    appropriate threshold and label configuration sections.

    Args:
        effect_size: The computed effect size value (can be negative).
        effect_size_type: Which effect size metric this value represents.
        output_config: Report configuration containing thresholds and labels.

    Returns:
        Localized magnitude label ('negligible', 'small', 'medium', 'large'),
        or 'unknown' if the effect size is NaN.

    Example:
        >>> get_effect_magnitude(0.45, EffectSize.CLIFFS_DELTA, config)
        'medium'
    """
    if math.isnan(effect_size):
        logger.debug("Effect size for %r is NaN; returning 'unknown' magnitude.", effect_size_type)
        return 'unknown'

    abs_effect: float = abs(effect_size)

    # Use the enum's internal key to access the correct config sections.
    # e.g., 'cliffs_delta' -> thresholds.cliffs_delta, labels.cliffs_delta
    config_key: str = effect_size_type.internal_key

    thresholds: (
        ConfigurationEffectSizesCliffsDelta | ConfigurationEffectSizesCohensD
    ) = getattr(output_config.configuration.effect_sizes, config_key)
    magnitude_labels: (
        TestInterpretationsCliffsDeltaMagnitudeLabels
        | TestInterpretationsCohensDMagnitudeLabels
    ) = getattr(output_config.test_interpretations, config_key).magnitude_labels

    # Threshold comparisons are identical across effect size types.
    if abs_effect < thresholds.negligible:
        return magnitude_labels.negligible
    elif abs_effect < thresholds.small:
        return magnitude_labels.small
    elif abs_effect < thresholds.medium:
        return magnitude_labels.medium
    else:
        return magnitude_labels.large


def get_cliffs_delta_magnitude(effect_size: float, output_config: ReportConfig) -> str:
    """
    Get a human-readable description of the Cliff's Delta effect size magnitude.

    Args:
        effect_size: The Cliff's Delta effect size value.
        output_config: The report configuration containing the effect size thresholds and labels.
    Returns:
        String describing the magnitude ('negligible', 'small', 'medium', 'large')
    """

    return get_effect_magnitude(effect_size, EffectSize.CLIFFS_DELTA, output_config)


def get_cohens_d_magnitude(effect_size: float, output_config: ReportConfig) -> str:
    """
    Get a human-readable description of the Cohen's d effect size magnitude.

    Args:
        effect_size: The Cohen's d effect size value.
        output_config: The report configuration containing the effect size thresholds and labels.
    Returns:
        String describing the magnitude ('negligible', 'small', 'medium', 'large')
    """

    return get_effect_magnitude(effect_size, EffectSize.COHENS_D, output_config)
