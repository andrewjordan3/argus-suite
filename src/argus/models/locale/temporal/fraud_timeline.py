# argus/models/locale/temporal/fraud_timeline.py
"""
Fraud timeline models for temporal analysis localization.

Contains models that configure how fraud emergence timelines are displayed,
including change point frequency analysis and temporal pattern insights.
"""

from argus.models.common import FrozenModel
from argus.models.locale.placeholder_registry import P
from argus.models.locale.placeholder_validators import FormatStr, FormatStrList

__all__: list[str] = [
    'TemporalAnalysisFraudTimeline',
    'TemporalAnalysisFraudTimelineFrequencyIntro',
    'TemporalAnalysisFraudTimelineNoChanges',
    'TemporalAnalysisFraudTimelinePatterns',
    'TemporalAnalysisFraudTimelinePeakInsight',
    'TemporalAnalysisFraudTimelinePeakInsightMultiple',
    'TemporalAnalysisFraudTimelinePeakInsightSingle',
]


class TemporalAnalysisFraudTimelinePeakInsightSingle(FrozenModel):
    """
    Insight text for single peak scenario.

    Attributes:
        paragraphs: list of insight paragraphs
    """

    paragraphs: FormatStrList[P.TemporalTimelinePeakSingle]


class TemporalAnalysisFraudTimelinePeakInsightMultiple(FrozenModel):
    """
    Insight text for multiple peaks scenario.

    Attributes:
        paragraphs: list of insight paragraphs
    """

    paragraphs: FormatStrList[P.TemporalTimelinePeakMultiple]


class TemporalAnalysisFraudTimelinePeakInsight(FrozenModel):
    """
    Configuration for peak change activity insights.

    Highlights months with unusual change point clustering.

    Attributes:
        marker: Insight marker (e.g., "⚠ EXECUTIVE INSIGHT:")
        peak_single: Insight for single peak scenario
        peak_multiple: Insight for multiple peaks scenario
    """

    marker: str
    peak_single: TemporalAnalysisFraudTimelinePeakInsightSingle
    peak_multiple: TemporalAnalysisFraudTimelinePeakInsightMultiple


class TemporalAnalysisFraudTimelineFrequencyIntro(FrozenModel):
    """
    Introduction to change point frequency analysis.

    Attributes:
        title: Subsection title
        subtitle: Explanatory subtitle
    """

    title: str
    subtitle: str


class TemporalAnalysisFraudTimelinePatterns(FrozenModel):
    """
    Configuration for temporal pattern insights.

    Analyzes when changes occurred (early vs late, clustered vs distributed).

    Attributes:
        title: Patterns subsection title
        early_changes: Insight for early-period changes
        late_changes: Insight for late-period changes
        clustered: Insight for clustered changes
        distributed: Insight for distributed changes
    """

    title: str
    early_changes: FormatStr[P.TemporalTimelinePatternsEarlyPct]
    late_changes: FormatStr[P.TemporalTimelinePatternsLatePct]
    clustered: str
    distributed: str


class TemporalAnalysisFraudTimelineNoChanges(FrozenModel):
    """
    Message when no change points detected.

    Attributes:
        paragraphs: list of explanation paragraphs
    """

    paragraphs: list[str]


class TemporalAnalysisFraudTimeline(FrozenModel):
    """
    Complete fraud emergence timeline section configuration.

    Analyzes when suspicious patterns first appeared and evolved.

    Attributes:
        title: Section title
        subtitle: Section subtitle
        frequency_intro: Frequency analysis introduction
        month_format: Format for month frequency items
        peak_insight: Peak activity insights configuration
        patterns: Temporal patterns configuration
        no_changes: No changes detected message
    """

    title: str
    subtitle: str
    frequency_intro: TemporalAnalysisFraudTimelineFrequencyIntro
    month_format: FormatStr[P.TemporalTimelineMonthFormat]
    peak_insight: TemporalAnalysisFraudTimelinePeakInsight
    patterns: TemporalAnalysisFraudTimelinePatterns
    no_changes: TemporalAnalysisFraudTimelineNoChanges
