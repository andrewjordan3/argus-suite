# argus/models/locale/temporal/comparative.py
"""
Comparative analysis models for temporal analysis localization.

Contains models that configure cross-branch comparison of temporal risk
patterns, including statistical test results and effect size interpretation.
"""

from argus.models.common import FrozenModel
from argus.models.locale.placeholder_registry import P
from argus.models.locale.placeholder_validators import FormatStr, FormatStrList

__all__: list[str] = [
    'TemporalAnalysisComparativeAnalysis',
    'TemporalAnalysisComparativeEffectSizeGuide',
    'TemporalAnalysisComparativeInterpretationParagraph',
    'TemporalAnalysisComparativeInterpretations',
]


class TemporalAnalysisComparativeInterpretationParagraph(FrozenModel):
    """
    Message for significant comparative temporal analysis interpretation.

    Attributes:
        paragraphs: list of explanation paragraphs
    """

    paragraphs: FormatStrList[P.TemporalComparativeSignificant]


class TemporalAnalysisComparativeInterpretations(FrozenModel):
    """
    Interpretation messages for comparative temporal analysis.

    Different messages based on whether target has significantly higher,
    lower, or similar risk scores compared to other branches.

    Attributes:
        significant_higher: Paragraphs when target is significantly higher
        significant_lower: Paragraphs when target is significantly lower
        not_significant: Paragraphs when no significant difference
    """

    significant_higher: TemporalAnalysisComparativeInterpretationParagraph
    significant_lower: TemporalAnalysisComparativeInterpretationParagraph
    not_significant: TemporalAnalysisComparativeInterpretationParagraph


class TemporalAnalysisComparativeEffectSizeGuide(FrozenModel):
    """
    Guide for interpreting Cliff's Delta in comparative analysis.

    Explains effect size magnitudes and their practical meaning.

    Attributes:
        title: Guide title
        negligible: Negligible effect interpretation
        small: Small effect interpretation
        medium: Medium effect interpretation
        large: Large effect interpretation
        interpretation_note: Note about significance vs effect size
        identical: Message when distributions are identical
        probability_explanation: Simple probability interpretation using calculated variables
    """

    title: str
    negligible: FormatStr[P.TemporalComparativeEffectSizeNegligible]
    small: FormatStr[P.TemporalComparativeEffectSizeSmall]
    medium: FormatStr[P.TemporalComparativeEffectSizeMedium]
    large: FormatStr[P.TemporalComparativeEffectSizeMedium]
    interpretation_note: str
    identical: str
    probability_explanation: FormatStrList[P.TemporalComparativeProbability]


class TemporalAnalysisComparativeAnalysis(FrozenModel):
    """
    Complete comparative temporal analysis configuration.

    Compares target location's temporal risk patterns to other branches.

    Attributes:
        title: Section title
        introduction: Introduction explaining comparison
        comparison_title: Comparison statistics title
        target_line: Format for target statistics
        target_stats: Format for target mean/median
        others_line: Format for others statistics
        others_stats: Format for others mean/median
        test_line: Format for statistical test results
        iqr_format: Format for IQR display
        sample_size_format: Format for sample size display
        effect_size_line: Format for effect size display
        interpretations: Interpretation messages by outcome
        effect_size_guide: Cliff's Delta interpretation guide
    """

    title: str
    introduction: FormatStr[P.TemporalComparativeIntro]
    comparison_title: str
    target_line: FormatStr[P.TemporalComparativeIntro]
    target_stats: FormatStr[P.TemporalComparativeTargetStats]
    others_line: str
    others_stats: FormatStr[P.TemporalComparativeOthersStats]
    test_line: FormatStr[P.TemporalComparativeTestLine]
    iqr_format: FormatStr[P.TemporalComparativeIQR]
    sample_size_format: FormatStr[P.TemporalComparativeSampleSize]
    effect_size_line: FormatStr[P.TemporalComparativeEffectSize]
    interpretations: TemporalAnalysisComparativeInterpretations
    effect_size_guide: TemporalAnalysisComparativeEffectSizeGuide
