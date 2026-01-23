# argus/models/locale/temporal/__init__.py
"""
============================================================================
TEMPORAL ANALYSIS LOCALE MODELS
============================================================================
Pydantic models for temporal analysis report localization.

This package splits the temporal analysis locale configuration into focused
modules for maintainability. All models are re-exported here for backwards
compatibility with existing imports.

Modules:
    metric_definitions: Metric names and analysis methodology definitions
    top_entities: High-risk entity profile configuration
    risk_distribution: Risk score distribution reporting
    fraud_timeline: Fraud emergence timeline analysis
    fraud_patterns: Known fraud signature detection
    comparative: Cross-branch comparative analysis
    interpretation: Interpretation guides and caveats
    core: Root model and simple supporting classes
============================================================================
"""

from argus.models.locale.temporal.comparative import (
    TemporalAnalysisComparativeAnalysis,
    TemporalAnalysisComparativeEffectSizeGuide,
    TemporalAnalysisComparativeInterpretationParagraph,
    TemporalAnalysisComparativeInterpretations,
)
from argus.models.locale.temporal.core import (
    TemporalAnalysis,
    TemporalAnalysisInsufficientData,
    TemporalAnalysisIntroduction,
    TemporalAnalysisSummaryStatistics,
)
from argus.models.locale.temporal.fraud_patterns import (
    TemporalAnalysisFraudPatternSummary,
    TemporalAnalysisFraudPatternSummaryGradualEscalation,
    TemporalAnalysisFraudPatternSummaryOffHoursConcentration,
    TemporalAnalysisFraudPatternSummaryOperationalAnomaly,
    TemporalAnalysisFraudPatternSummaryPattern,
    TemporalAnalysisFraudPatternSummarySpikeRetreat,
)
from argus.models.locale.temporal.fraud_timeline import (
    TemporalAnalysisFraudTimeline,
    TemporalAnalysisFraudTimelineFrequencyIntro,
    TemporalAnalysisFraudTimelineNoChanges,
    TemporalAnalysisFraudTimelinePatterns,
    TemporalAnalysisFraudTimelinePeakInsight,
    TemporalAnalysisFraudTimelinePeakInsightMultiple,
    TemporalAnalysisFraudTimelinePeakInsightSingle,
)
from argus.models.locale.temporal.interpretation import (
    TemporalAnalysisCaveats,
    TemporalAnalysisInterpretationGuide,
    TemporalAnalysisInterpretationGuideHighConfidence,
    TemporalAnalysisInterpretationGuideLowerPriority,
    TemporalAnalysisInterpretationGuideMediumConfidence,
)
from argus.models.locale.temporal.metric_definitions import (
    TemporalAnalysisMetricDefinitionAfterHoursRate,
    TemporalAnalysisMetricDefinitionItem,
    TemporalAnalysisMetricDefinitions,
    TemporalAnalysisMetricDefinitionsAnalysisTypes,
    TemporalAnalysisMetricDefinitionsAnalysisTypesAutoCorrelation,
    TemporalAnalysisMetricDefinitionsAnalysisTypesFraudPatternsPatterns,
    TemporalAnalysisMetricDefinitionsAnalysisTypesItem,
    TemporalAnalysisMetricDefinitionsAnalysisTypesMonthOverMonth,
    TemporalAnalysisMetricDefinitionsMetrics,
    TemporalAnalysisMetricDefinitionsPeriodComparison,
    TemporalAnalysisMetricDisplayNames,
)
from argus.models.locale.temporal.risk_distribution import (
    TemporalAnalysisRiskDistribution,
    TemporalAnalysisRiskDistributionGroup,
    TemporalAnalysisRiskDistributionOverall,
)
from argus.models.locale.temporal.top_entities import (
    TemporalAnalysisTopEntities,
    TemporalAnalysisTopEntitiesAutocorrelation,
    TemporalAnalysisTopEntitiesChangePoints,
    TemporalAnalysisTopEntitiesCurrentRisks,
    TemporalAnalysisTopEntitiesEntitySummary,
    TemporalAnalysisTopEntitiesFraudPatterns,
    TemporalAnalysisTopEntitiesFraudPatternsPatterns,
    TemporalAnalysisTopEntitiesMonthOverMonth,
    TemporalAnalysisTopEntitiesMonthOverMonthGradualEscalation,
    TemporalAnalysisTopEntitiesMonthOverMonthSuddenSpikes,
    TemporalAnalysisTopEntitiesMonthOverMonthVolatility,
    TemporalAnalysisTopEntitiesPeriodComparison,
    TemporalAnalysisTopEntitiesRecommendations,
    TemporalAnalysisTopEntitiesRollingAnomalies,
    TemporalAnalysisTopEntitiesTrends,
)

__all__: list[str] = [
    'TemporalAnalysis',
    'TemporalAnalysisCaveats',
    'TemporalAnalysisComparativeAnalysis',
    'TemporalAnalysisComparativeEffectSizeGuide',
    'TemporalAnalysisComparativeInterpretationParagraph',
    'TemporalAnalysisComparativeInterpretations',
    'TemporalAnalysisFraudPatternSummary',
    'TemporalAnalysisFraudPatternSummaryGradualEscalation',
    'TemporalAnalysisFraudPatternSummaryOffHoursConcentration',
    'TemporalAnalysisFraudPatternSummaryOperationalAnomaly',
    'TemporalAnalysisFraudPatternSummaryPattern',
    'TemporalAnalysisFraudPatternSummarySpikeRetreat',
    'TemporalAnalysisFraudTimeline',
    'TemporalAnalysisFraudTimelineFrequencyIntro',
    'TemporalAnalysisFraudTimelineNoChanges',
    'TemporalAnalysisFraudTimelinePatterns',
    'TemporalAnalysisFraudTimelinePeakInsight',
    'TemporalAnalysisFraudTimelinePeakInsightMultiple',
    'TemporalAnalysisFraudTimelinePeakInsightSingle',
    'TemporalAnalysisInsufficientData',
    'TemporalAnalysisInterpretationGuide',
    'TemporalAnalysisInterpretationGuideHighConfidence',
    'TemporalAnalysisInterpretationGuideLowerPriority',
    'TemporalAnalysisInterpretationGuideMediumConfidence',
    'TemporalAnalysisIntroduction',
    'TemporalAnalysisMetricDefinitionAfterHoursRate',
    'TemporalAnalysisMetricDefinitionItem',
    'TemporalAnalysisMetricDefinitions',
    'TemporalAnalysisMetricDefinitionsAnalysisTypes',
    'TemporalAnalysisMetricDefinitionsAnalysisTypesAutoCorrelation',
    'TemporalAnalysisMetricDefinitionsAnalysisTypesFraudPatternsPatterns',
    'TemporalAnalysisMetricDefinitionsAnalysisTypesItem',
    'TemporalAnalysisMetricDefinitionsAnalysisTypesMonthOverMonth',
    'TemporalAnalysisMetricDefinitionsMetrics',
    'TemporalAnalysisMetricDefinitionsPeriodComparison',
    'TemporalAnalysisMetricDisplayNames',
    'TemporalAnalysisRiskDistribution',
    'TemporalAnalysisRiskDistributionGroup',
    'TemporalAnalysisRiskDistributionOverall',
    'TemporalAnalysisSummaryStatistics',
    'TemporalAnalysisTopEntities',
    'TemporalAnalysisTopEntitiesAutocorrelation',
    'TemporalAnalysisTopEntitiesChangePoints',
    'TemporalAnalysisTopEntitiesCurrentRisks',
    'TemporalAnalysisTopEntitiesEntitySummary',
    'TemporalAnalysisTopEntitiesFraudPatterns',
    'TemporalAnalysisTopEntitiesFraudPatternsPatterns',
    'TemporalAnalysisTopEntitiesMonthOverMonth',
    'TemporalAnalysisTopEntitiesMonthOverMonthGradualEscalation',
    'TemporalAnalysisTopEntitiesMonthOverMonthSuddenSpikes',
    'TemporalAnalysisTopEntitiesMonthOverMonthVolatility',
    'TemporalAnalysisTopEntitiesPeriodComparison',
    'TemporalAnalysisTopEntitiesRecommendations',
    'TemporalAnalysisTopEntitiesRollingAnomalies',
    'TemporalAnalysisTopEntitiesTrends',
]
