# argus/models/locale/temporal/core.py
"""
Core models for temporal analysis localization.

Contains the root TemporalAnalysis model and simple supporting classes
that don't fit into other specialized modules.
"""

from pydantic import Field

from argus.models.common import FrozenModel
from argus.models.locale.placeholder_registry import P
from argus.models.locale.placeholder_validators import FormatStr, FormatStrList
from argus.models.locale.temporal.comparative import TemporalAnalysisComparativeAnalysis
from argus.models.locale.temporal.fraud_patterns import (
    TemporalAnalysisFraudPatternSummary,
)
from argus.models.locale.temporal.fraud_timeline import TemporalAnalysisFraudTimeline
from argus.models.locale.temporal.interpretation import (
    TemporalAnalysisCaveats,
    TemporalAnalysisInterpretationGuide,
)
from argus.models.locale.temporal.metric_definitions import (
    TemporalAnalysisMetricDefinitions,
    TemporalAnalysisMetricDisplayNames,
)
from argus.models.locale.temporal.risk_distribution import (
    TemporalAnalysisRiskDistribution,
)
from argus.models.locale.temporal.top_entities import TemporalAnalysisTopEntities

__all__: list[str] = [
    'TemporalAnalysis',
    'TemporalAnalysisInsufficientData',
    'TemporalAnalysisIntroduction',
    'TemporalAnalysisSummaryStatistics',
]


class TemporalAnalysisInsufficientData(FrozenModel):
    """
    Warning messages when insufficient data for temporal analysis.

    Displayed when entities don't meet minimum transaction or month requirements.

    Attributes:
        warning: Warning header
        details: Explanation of minimum requirements
        recommendation: Suggested actions
    """

    warning: str
    details: FormatStr[P.TemporalInsufficientDataThresholds] = Field(
        description='Explanation of minimum requirements'
    )
    recommendation: str


class TemporalAnalysisSummaryStatistics(FrozenModel):
    """
    Configuration for summary statistics subsection.

    Attributes:
        title: Title for summary statistics subsection
        stats_items: list of summary statistic line items
    """

    title: str
    stats_items: FormatStrList[P.TemporalSummaryItems] = Field(
        description='list of summary statistic line items (with placeholders)'
    )


class TemporalAnalysisIntroduction(FrozenModel):
    """
    Introduction to temporal analysis section.

    Explains purpose and methodology at high level.

    Attributes:
        paragraphs: list of introductory paragraphs
    """

    paragraphs: FormatStrList[P.TemporalIntroAll]


class TemporalAnalysis(FrozenModel):
    """
    Complete advanced temporal analysis section configuration.

    This is the most complex section, tracking behavior changes over time
    for individual drivers and vehicles. Uses multiple statistical techniques
    to detect fraud emergence, pattern changes, and temporal anomalies.

    Attributes:
        section_title: Main section title
        introduction: Introduction explaining temporal analysis
        metric_display_names: Human-readable metric names
        metric_definitions: Complete metric and methodology definitions
        insufficient_data: Warning for insufficient data scenarios
        summary_statistics: Summary statistics configuration
        top_entities: Top high-risk entities configuration
        risk_distribution: Risk distribution configuration
        fraud_timeline: Fraud emergence timeline configuration
        fraud_pattern_summary: Fraud pattern summary configuration
        comparative_analysis: Comparative analysis configuration
        interpretation_guide: Interpretation guide configuration
        caveats: Limitations and caveats configuration
    """

    section_title: str
    introduction: TemporalAnalysisIntroduction
    metric_display_names: TemporalAnalysisMetricDisplayNames
    metric_definitions: TemporalAnalysisMetricDefinitions
    insufficient_data: TemporalAnalysisInsufficientData
    summary_statistics: TemporalAnalysisSummaryStatistics
    top_entities: TemporalAnalysisTopEntities
    risk_distribution: TemporalAnalysisRiskDistribution
    fraud_timeline: TemporalAnalysisFraudTimeline
    fraud_pattern_summary: TemporalAnalysisFraudPatternSummary
    comparative_analysis: TemporalAnalysisComparativeAnalysis
    interpretation_guide: TemporalAnalysisInterpretationGuide
    caveats: TemporalAnalysisCaveats
