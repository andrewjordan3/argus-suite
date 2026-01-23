# argus/models/locale/temporal/interpretation.py
"""
Interpretation guide and caveats models for temporal analysis localization.

Contains models that configure how findings should be prioritized and
interpreted, plus important limitations and disclaimers.
"""

from pydantic import Field

from argus.models.common import FrozenModel
from argus.models.locale.placeholder_registry import P
from argus.models.locale.placeholder_validators import FormatStrList

__all__: list[str] = [
    'TemporalAnalysisCaveats',
    'TemporalAnalysisInterpretationGuide',
    'TemporalAnalysisInterpretationGuideHighConfidence',
    'TemporalAnalysisInterpretationGuideLowerPriority',
    'TemporalAnalysisInterpretationGuideMediumConfidence',
]


class TemporalAnalysisInterpretationGuideHighConfidence(FrozenModel):
    """
    High-confidence interpretation guidelines group.

    Attributes:
        title: Group title
        items: list of guideline items
    """

    title: str
    items: FormatStrList[P.TemporalInterpCriticalThreshold] = Field(
        description='List of high-confidence guideline items'
    )


class TemporalAnalysisInterpretationGuideMediumConfidence(FrozenModel):
    """
    Medium-confidence interpretation guidelines group.

    Groups findings by confidence/priority level.

    Attributes:
        title: Group title
        items: list of guideline items
    """

    title: str
    items: FormatStrList[P.TemporalInterpHighRange] = Field(
        description='List of medium-confidence guideline items'
    )


class TemporalAnalysisInterpretationGuideLowerPriority(FrozenModel):
    """
    Lower-priority interpretation guidelines group.

    Groups findings by confidence/priority level.

    Attributes:
        title: Group title
        items: list of guideline items
    """

    title: str
    items: FormatStrList[P.TemporalInterpLowPriority] = Field(
        description='List of lower-priority guideline items'
    )


class TemporalAnalysisInterpretationGuide(FrozenModel):
    """
    Complete interpretation guide for temporal findings.

    Helps investigators prioritize which findings to focus on first.

    Attributes:
        title: Guide title
        high_confidence: High-confidence indicators to investigate first
        medium_confidence: Medium-confidence indicators needing context
        lower_priority: Lower-priority items for monitoring
    """

    title: str
    high_confidence: TemporalAnalysisInterpretationGuideHighConfidence
    medium_confidence: TemporalAnalysisInterpretationGuideMediumConfidence
    lower_priority: TemporalAnalysisInterpretationGuideLowerPriority


class TemporalAnalysisCaveats(FrozenModel):
    """
    Limitations and caveats for temporal analysis.

    Important disclaimer about what temporal analysis can and cannot show.

    Attributes:
        title: Caveats section title
        items: list of limitation items
        recommendation: Recommendation for holistic analysis
        continuation: Continuation of recommendation
    """

    title: str
    items: list[str]
    recommendation: str
    continuation: str
