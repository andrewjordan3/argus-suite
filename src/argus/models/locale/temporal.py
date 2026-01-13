# argus/schemas/temporal.py
"""
============================================================================
TEMPORAL ANALYSIS
============================================================================
Content for advanced temporal analysis tracking behavior changes over time.
This is the most complex section with many nested structures. It uses multiple
statistical techniques to detect fraud emergence, pattern changes, and temporal anomalies.
============================================================================
"""

from pydantic import Field

from argus.models.common import BaseConfigModel, FormatStr, FormatStrList, P

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


class TemporalAnalysisMetricDisplayNames(BaseConfigModel):
    """
    Human-readable names for temporal metrics.

    Maps internal metric names to display names for reports.

    Attributes:
        datetime_count: Display name for transaction count metric
        transaction_volume: Display name for transaction volume metric
        no_eld_rate: Display name for no-ELD-match rate
        non_diesel_rate: Display name for non-diesel purchase rate
        after_hours_rate: Display name for after-hours transaction rate
        avg_transaction_cost: Display name for average cost metric
    """

    datetime_count: str = Field(description='Display name for transaction count metric')
    transaction_volume: str = Field(
        description='Display name for transaction volume metric'
    )
    no_eld_rate: str = Field(description='Display name for no-ELD-match rate')
    non_diesel_rate: str = Field(
        description='Display name for non-diesel purchase rate'
    )
    after_hours_rate: str = Field(
        description='Display name for after-hours transaction rate'
    )
    avg_transaction_cost: str = Field(
        description='Display name for average cost metric'
    )


class TemporalAnalysisMetricDefinitionItem(BaseConfigModel):
    """
    Definition of a single temporal metric.

    Each metric tracks a different aspect of behavior over time.

    Attributes:
        label: Display label for this metric
        definition: Technical definition of how metric is calculated
        note: Optional additional note about calculation
        risk: Optional risk interpretation guidance
    """

    label: str
    definition: str
    note: str | None = None
    risk: str | None = None


class TemporalAnalysisMetricDefinitionAfterHoursRate(BaseConfigModel):
    """
    Definition of after-hours transaction rate metric.

    Attributes:
        label: Display label for this metric
        definition: Percentage of transactions outside business hours
        risk: Risk interpretation guidance
    """

    label: str
    definition: FormatStr[P.TemporalBusinessHoursRange] = Field(
        description='Percentage of transactions outside business hours'
    )
    risk: str


class TemporalAnalysisMetricDefinitionsMetrics(BaseConfigModel):
    """
    Definitions of all temporal metrics tracked.

    Attributes:
        transaction_volume: Definition of transaction volume metric
        no_eld_rate: Definition of no-ELD-match rate metric
        non_diesel_rate: Definition of non-diesel purchase rate metric
        after_hours_rate: Definition of after-hours transaction rate metric
        avg_transaction_cost: Definition of average cost metric
    """

    transaction_volume: TemporalAnalysisMetricDefinitionItem
    no_eld_rate: TemporalAnalysisMetricDefinitionItem
    non_diesel_rate: TemporalAnalysisMetricDefinitionItem
    after_hours_rate: TemporalAnalysisMetricDefinitionAfterHoursRate
    avg_transaction_cost: TemporalAnalysisMetricDefinitionItem


class TemporalAnalysisMetricDefinitionsAnalysisTypesMonthOverMonth(BaseConfigModel):
    """
    Definition of month-over-month analysis methodology.

    This analysis type has specific thresholds that need to be documented.

    Attributes:
        label: Display label for this analysis type
        description: What this analysis detects
        thresholds: list of threshold descriptions
    """

    label: str
    description: str
    thresholds: FormatStrList[P.TemporalSpikeThresholds] = Field(
        description='List of threshold descriptions for month-over-month analysis'
    )


class TemporalAnalysisMetricDefinitionsAnalysisTypesAutoCorrelation(BaseConfigModel):
    """
    Definition of autocorrelation analysis methodology.

    Attributes:
        label: Display label for this analysis type
        description: What this analysis detects
        interpretation: Interpretation guidance for autocorrelation analysis
    """

    label: str
    description: str
    interpretation: FormatStr[P.TemporalAutocorrelationThreshold] = Field(
        description='Interpretation guidance for autocorrelation analysis'
    )


class TemporalAnalysisMetricDefinitionsAnalysisTypesFraudPatternsPatterns(
    BaseConfigModel
):
    """
    Definitions of known fraud patterns for temporal analysis.
    Each fraud signature has its own description.
    Attributes:
        off_hours_concentration: Description of off-hours concentration pattern
        spike_retreat: Description of spike-and-retreat pattern
        gradual_escalation: Description of gradual escalation pattern
        operational_anomaly: Description of operational anomaly pattern
    """

    off_hours_concentration: FormatStr[P.TemporalFraudPatternThresholdsOffHours] = (
        Field(description='Description of off-hours concentration pattern')
    )
    spike_retreat: FormatStr[P.TemporalFraudPatternThresholdsSpikeRetreat] = Field(
        description='Description of spike-and-retreat pattern'
    )
    gradual_escalation: FormatStr[P.TemporalFraudPatternThresholdsGradualEscalation] = (
        Field(description='Description of gradual escalation pattern')
    )
    operational_anomaly: str


class TemporalAnalysisMetricDefinitionsAnalysisTypesItem(BaseConfigModel):
    """
    Definition of a temporal analysis methodology.

    Different statistical approaches are used to detect patterns over time.

    Attributes:
        label: Display label for this analysis type
        description: What this analysis detects
        note: Optional additional context
        methods: Optional description of methods used
        interpretation: Optional interpretation guidance
        patterns: Used only for fraud patterns
    """

    label: str
    description: str
    note: str | None = None
    methods: str | None = None
    patterns: (
        TemporalAnalysisMetricDefinitionsAnalysisTypesFraudPatternsPatterns | None
    ) = Field(
        default=None,
        description='Used for fraud patterns analysis type',
    )


class TemporalAnalysisMetricDefinitionsAnalysisTypes(BaseConfigModel):
    """
    Definitions of all temporal analysis methodologies.

    Multiple statistical techniques are used to detect different patterns.

    Attributes:
        title: Section title
        trend_detection: Mann-Kendall trend test definition
        change_points: Change point detection definition
        month_over_month: Month-over-month analysis definition
        rolling_windows: Rolling window anomaly detection definition
        autocorrelation: Autocorrelation analysis definition
        fraud_patterns: Fraud pattern recognition definition
    """

    title: str
    trend_detection: TemporalAnalysisMetricDefinitionsAnalysisTypesItem
    change_points: TemporalAnalysisMetricDefinitionsAnalysisTypesItem
    month_over_month: TemporalAnalysisMetricDefinitionsAnalysisTypesMonthOverMonth
    rolling_windows: TemporalAnalysisMetricDefinitionsAnalysisTypesItem
    autocorrelation: TemporalAnalysisMetricDefinitionsAnalysisTypesAutoCorrelation
    fraud_patterns: TemporalAnalysisMetricDefinitionsAnalysisTypesItem


class TemporalAnalysisMetricDefinitionsPeriodComparison(BaseConfigModel):
    """
    Definition of period comparison methodology.

    Compares first half of time period to second half.

    Attributes:
        title: Subsection title
        items: list of interpretation items
    """

    title: str
    items: FormatStrList[P.TemporalPSignificant] = Field(
        description='List of interpretation items for period comparison'
    )


class TemporalAnalysisMetricDefinitions(BaseConfigModel):
    """
    Complete metric definitions section configuration.

    Explains all metrics tracked and methodologies used for temporal analysis.

    Attributes:
        section_title: Title for metric definitions section
        metrics: Definitions of all metrics tracked
        analysis_types: Definitions of all analysis methodologies
        period_comparison: Definition of period comparison approach
    """

    section_title: str
    metrics: TemporalAnalysisMetricDefinitionsMetrics
    analysis_types: TemporalAnalysisMetricDefinitionsAnalysisTypes
    period_comparison: TemporalAnalysisMetricDefinitionsPeriodComparison


class TemporalAnalysisInsufficientData(BaseConfigModel):
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


class TemporalAnalysisSummaryStatistics(BaseConfigModel):
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


class TemporalAnalysisTopEntitiesRecommendations(BaseConfigModel):
    """
    Investigation priority recommendations by risk category.

    Different actions recommended based on risk level.

    Attributes:
        critical: Recommendation for critical risk entities
        high: Recommendation for high risk entities
        moderate: Recommendation for moderate risk entities
        low: Recommendation for low risk entities
    """

    critical: str
    high: str
    moderate: str
    low: str


class TemporalAnalysisTopEntitiesCurrentRisks(BaseConfigModel):
    """
    Configuration for current risks subsection.

    Highlights risk factors present in the most recent month.

    Attributes:
        title: Subsection title
        format: Format string for risk factor items
        none: Message when no current risks detected
    """

    title: str
    format: FormatStr[P.TemporalCurrentRiskFactor]
    none: str


class TemporalAnalysisTopEntitiesFraudPatternsPatterns(BaseConfigModel):
    """
    Configuration for fraud patterns patterns subsection.

    Attributes:
        off_hours_concentration: Description of off-hours concentration pattern
        spike_retreat: Description of spike-and-retreat pattern
        gradual_escalation: Description of gradual escalation pattern
        operational_anomaly: Description of operational anomaly pattern
    """

    off_hours_concentration: str
    spike_retreat: str
    gradual_escalation: str
    operational_anomaly: str


class TemporalAnalysisTopEntitiesFraudPatterns(BaseConfigModel):
    """
    Configuration for fraud patterns subsection.

    lists specific fraud signatures detected in entity's behavior.

    Attributes:
        title: Subsection title
        patterns: dictionary mapping pattern names to descriptions
        none: Message when no patterns detected
    """

    title: str
    patterns: TemporalAnalysisTopEntitiesFraudPatternsPatterns
    none: str


class TemporalAnalysisTopEntitiesMonthOverMonthSuddenSpikes(BaseConfigModel):
    """
    Configuration for one month-over-month sudden spikes subgroup.

    Attributes:
        label: Subsection label
        format: Format string for items
        none: Message when none detected
    """

    label: str
    format: FormatStr[P.TemporalSuddenSpike]
    none: str


class TemporalAnalysisTopEntitiesMonthOverMonthGradualEscalation(BaseConfigModel):
    """
    Configuration for one month-over-month gradual escalation subgroup.

    Attributes:
        label: Subsection label
        format: Format string for items
        none: Message when none detected
    """

    label: str
    format: FormatStr[P.TemporalGradualEscalation]
    none: str


class TemporalAnalysisTopEntitiesMonthOverMonthVolatility(BaseConfigModel):
    """
    Configuration for one month-over-month volatility subgroup.

    Attributes:
        label: Subsection label
        format: Format string for items
        none: Message when none detected
    """

    label: FormatStr[P.TemporalVolatilityScore]
    high_note: str


class TemporalAnalysisTopEntitiesMonthOverMonth(BaseConfigModel):
    """
    Configuration for month-over-month analysis subsection.

    Reports sudden spikes, gradual escalation, and volatility.

    Attributes:
        title: Subsection title
        sudden_spikes: Configuration for sudden spikes reporting
        gradual_escalation: Configuration for escalation reporting
        volatility: Configuration for volatility score reporting
    """

    title: str
    sudden_spikes: TemporalAnalysisTopEntitiesMonthOverMonthSuddenSpikes
    gradual_escalation: TemporalAnalysisTopEntitiesMonthOverMonthGradualEscalation
    volatility: TemporalAnalysisTopEntitiesMonthOverMonthVolatility


class TemporalAnalysisTopEntitiesChangePoints(BaseConfigModel):
    """
    Configuration for change points subsection.

    Reports months when behavior significantly changed.

    Attributes:
        title: Subsection title
        single_format: Format for single change point
        multiple_intro: Introduction for multiple changes
        format: Format for change point items
        multiple_format: Format for multiple changes on same metric
        none: Message when no change points detected
    """

    title: str
    single_format: FormatStr[P.TemporalChangePointSingle]
    multiple_intro: FormatStr[P.TemporalChangePointMultipleIntro]
    format: FormatStr[P.TemporalChangePointDate]
    multiple_format: FormatStr[P.TemporalChangePointMultipleDates]
    none: str


class TemporalAnalysisTopEntitiesAutocorrelation(BaseConfigModel):
    """
    Configuration for autocorrelation subsection.

    Reports persistent patterns indicating systematic behavior.

    Attributes:
        title: Subsection title
        explanation: Explanation of what autocorrelation means
        format: Format string for autocorrelation items
        high_note: Additional note for high autocorrelation
        none: Message when no high persistence detected
    """

    title: str
    explanation: str
    format: FormatStr[P.TemporalAutocorrelation]
    high_note: str
    none: str


class TemporalAnalysisTopEntitiesRollingAnomalies(BaseConfigModel):
    """
    Configuration for rolling window anomalies subsection.

    Reports months that deviate significantly from rolling baseline.

    Attributes:
        title: Subsection title
        format: Format string for anomaly items
        z_score: Format for z-score display
        none: Message when no anomalies detected
    """

    title: str
    format: FormatStr[P.TemporalRollingAnomaly]
    z_score: FormatStr[P.TemporalMaxZScore]
    none: str


class TemporalAnalysisTopEntitiesTrends(BaseConfigModel):
    """
    Configuration for trends subsection.

    Reports long-term monotonic trends in behavior.

    Attributes:
        title: Subsection title
        format: Format string for trend items
        none: Message when no trends detected
    """

    title: str
    format: FormatStr[P.TemporalTrendIndicator]
    none: str


class TemporalAnalysisTopEntitiesPeriodComparison(BaseConfigModel):
    """
    Configuration for period comparison subsection.

    Compares first half to second half of analysis period.

    Attributes:
        title: Subsection title
        format: Format string for comparison items
        explanation: Explanation of comparison methodology
    """

    title: str
    format: FormatStr[P.TemporalPeriodComparison]
    explanation: str


class TemporalAnalysisTopEntitiesEntitySummary(BaseConfigModel):
    """
    Configuration for final entity summary and recommendation.

    Appears at end of each entity profile.

    Attributes:
        title: Summary section title
        risk_format: Format for risk level statement
        flags_format: Format for active flags statement
        recommendations: Recommendations by risk category
    """

    title: str
    risk_format: FormatStr[P.TemporalEntitySummaryRisk]
    flags_format: FormatStr[P.TemporalEntityFlagsLine]
    recommendations: TemporalAnalysisTopEntitiesRecommendations


class TemporalAnalysisTopEntities(BaseConfigModel):
    """
    Complete configuration for top high-risk entities section.

    This complex subsection presents detailed profiles of entities with
    the highest temporal risk scores.

    Attributes:
        title: Section title
        introduction: Introductory text
        priority_note: Note about prioritizing current risks
        entity_header: Separator line for entity sections
        entity_title: Title format for entity profiles
        truck_entity_title: Alternative title format for truck entities
        risk_line: Format for risk score line
        activity_line: Format for activity summary line
        flags_line: Format for analysis flags line
        current_risks: Current risks subsection configuration
        fraud_patterns: Fraud patterns subsection configuration
        month_over_month: Month-over-month subsection configuration
        change_points: Change points subsection configuration
        autocorrelation: Autocorrelation subsection configuration
        rolling_anomalies: Rolling anomalies subsection configuration
        trends: Trends subsection configuration
        period_comparison: Period comparison subsection configuration
        summary_stats: Summary statistics configuration
        entity_summary: Final summary and recommendation configuration
    """

    title: FormatStr[P.TemporalTopN] = Field(
        description='Section title with top N placeholder'
    )
    introduction: str
    priority_note: str
    entity_header: str
    entity_title: FormatStr[P.TemporalEntityTitle] = Field(
        description='Entity title with placeholders for entity name and risk score'
    )
    truck_entity_title: FormatStr[P.TemporalEntityTitleWithTruck] = Field(
        description='Truck entity title with placeholders for entity_type, display_id, and truck_description'
    )
    risk_line: FormatStr[P.TemporalEntityRiskLine] = Field(
        description='Format for risk score line with placeholders for risk score and risk category'
    )
    activity_line: FormatStr[P.TemporalEntityActivityLine] = Field(
        description='Format for activity summary line with placeholders for activity details'
    )
    flags_line: FormatStr[P.TemporalEntityFlagsLine] = Field(
        description='Format for analysis flags line with placeholders for flags'
    )
    current_risks: TemporalAnalysisTopEntitiesCurrentRisks
    fraud_patterns: TemporalAnalysisTopEntitiesFraudPatterns
    month_over_month: TemporalAnalysisTopEntitiesMonthOverMonth
    change_points: TemporalAnalysisTopEntitiesChangePoints
    autocorrelation: TemporalAnalysisTopEntitiesAutocorrelation
    rolling_anomalies: TemporalAnalysisTopEntitiesRollingAnomalies
    trends: TemporalAnalysisTopEntitiesTrends
    period_comparison: TemporalAnalysisTopEntitiesPeriodComparison
    entity_summary: TemporalAnalysisTopEntitiesEntitySummary


class TemporalAnalysisRiskDistributionGroup(BaseConfigModel):
    """
    Configuration for one entity type's risk distribution.

    Shows distribution of risk scores for drivers or vehicles.

    Attributes:
        title: Group title
        items: list of statistic line items (optional)
        none: Message when no entities meet threshold (optional)
    """

    title: FormatStr[P.TemporalRiskDistEntityType]
    items: FormatStrList[P.TemporalRiskDistEntityStats]
    none: str


class TemporalAnalysisRiskDistributionOverall(BaseConfigModel):
    """
    Configuration for overall risk distribution summary.

    Shows count of entities in each risk category.

    Attributes:
        title: Overall distribution title
        critical: Format for critical risk count
        high: Format for high risk count
        medium: Format for medium risk count
        low: Format for low risk count
    """

    title: str
    critical: FormatStr[P.TemporalRiskDistCritical]
    high: FormatStr[P.TemporalRiskDistHigh]
    medium: FormatStr[P.TemporalRiskDistMedium]
    low: FormatStr[P.TemporalRiskDistLow]


class TemporalAnalysisRiskDistribution(BaseConfigModel):
    """
    Complete risk distribution section configuration.

    Shows how temporal risk scores are distributed across entity types.

    Attributes:
        title: Section title
        overall: Overall distribution configuration
        drivers: Driver-specific distribution configuration
        vehicles: Vehicle-specific distribution configuration
    """

    title: str
    overall: TemporalAnalysisRiskDistributionOverall
    drivers: TemporalAnalysisRiskDistributionGroup
    vehicles: TemporalAnalysisRiskDistributionGroup


class TemporalAnalysisFraudTimelinePeakInsightSingle(BaseConfigModel):
    """
    Insight text for one peak scenario.

    Different messages for single peak vs multiple peaks.

    Attributes:
        paragraphs: list of insight paragraphs
    """

    paragraphs: FormatStrList[P.TemporalTimelinePeakSingle]


class TemporalAnalysisFraudTimelinePeakInsightMultiple(BaseConfigModel):
    """
    Insight text for one peak scenario.

    Different messages for single peak vs multiple peaks.

    Attributes:
        paragraphs: list of insight paragraphs
    """

    paragraphs: FormatStrList[P.TemporalTimelinePeakMultiple]


class TemporalAnalysisFraudTimelinePeakInsight(BaseConfigModel):
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


class TemporalAnalysisFraudTimelineFrequencyIntro(BaseConfigModel):
    """
    Introduction to change point frequency analysis.

    Attributes:
        title: Subsection title
        subtitle: Explanatory subtitle
    """

    title: str
    subtitle: str


class TemporalAnalysisFraudTimelinePatterns(BaseConfigModel):
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


class TemporalAnalysisFraudTimelineNoChanges(BaseConfigModel):
    """
    Message when no change points detected.

    Attributes:
        paragraphs: list of explanation paragraphs
    """

    paragraphs: list[str]


class TemporalAnalysisFraudTimeline(BaseConfigModel):
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
        entity_details: Entity-level details configuration
        no_changes: No changes detected message
    """

    title: str
    subtitle: str
    frequency_intro: TemporalAnalysisFraudTimelineFrequencyIntro
    month_format: FormatStr[P.TemporalTimelineMonthFormat]
    peak_insight: TemporalAnalysisFraudTimelinePeakInsight
    patterns: TemporalAnalysisFraudTimelinePatterns
    no_changes: TemporalAnalysisFraudTimelineNoChanges


class TemporalAnalysisFraudPatternSummaryPattern[DescriptionType](BaseConfigModel):
    """
    Configuration for one fraud pattern type.

    Each known fraud signature has its own documentation.

    Attributes:
        title: Pattern name
        description: Pattern description
        count: Format for entity count display
        concern: Explanation of why this pattern is concerning
    """

    title: str
    description: DescriptionType
    count: FormatStr[P.TemporalFraudPatternCount]
    concern: str


class TemporalAnalysisFraudPatternSummaryOffHoursConcentration(
    TemporalAnalysisFraudPatternSummaryPattern[
        FormatStr[P.TemporalFraudPatternOffHours]
    ]
):
    """Pattern configuration for off-hours concentration."""


class TemporalAnalysisFraudPatternSummarySpikeRetreat(
    TemporalAnalysisFraudPatternSummaryPattern[
        FormatStr[P.TemporalFraudPatternSpikeRetreat]
    ]
):
    """Pattern configuration for spike-and-retreat."""


class TemporalAnalysisFraudPatternSummaryGradualEscalation(
    TemporalAnalysisFraudPatternSummaryPattern[
        FormatStr[P.TemporalFraudPatternGradualEscalation]
    ]
):
    """Pattern configuration for gradual escalation."""


class TemporalAnalysisFraudPatternSummaryOperationalAnomaly(
    TemporalAnalysisFraudPatternSummaryPattern[str]
):
    """Pattern configuration for operational anomaly."""


class TemporalAnalysisFraudPatternSummary(BaseConfigModel):
    """
    Complete fraud pattern detection summary configuration.

    Summarizes which entities match known fraud signatures.

    Attributes:
        title: Section title
        intro: Introduction text
        off_hours_concentration: Off-hours pattern configuration
        spike_retreat: Spike-and-retreat pattern configuration
        gradual_escalation: Gradual escalation pattern configuration
        operational_anomaly: Operational anomaly pattern configuration
        none_detected: Message when no patterns detected
    """

    title: str
    intro: str
    off_hours_concentration: TemporalAnalysisFraudPatternSummaryOffHoursConcentration
    spike_retreat: TemporalAnalysisFraudPatternSummarySpikeRetreat
    gradual_escalation: TemporalAnalysisFraudPatternSummaryGradualEscalation
    operational_anomaly: TemporalAnalysisFraudPatternSummaryOperationalAnomaly
    none_detected: str


class TemporalAnalysisComparativeInterpretationParagraph(BaseConfigModel):
    """
    Message for significant comparative temporal analysis interpretation.

    Attributes:
        paragraphs: list of explanation paragraphs
    """

    paragraphs: FormatStrList[P.TemporalComparativeSignificant]


class TemporalAnalysisComparativeInterpretations(BaseConfigModel):
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


class TemporalAnalysisComparativeEffectSizeGuide(BaseConfigModel):
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


class TemporalAnalysisComparativeAnalysis(BaseConfigModel):
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


class TemporalAnalysisInterpretationGuideHighConfidence(BaseConfigModel):
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


class TemporalAnalysisInterpretationGuideMediumConfidence(BaseConfigModel):
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


class TemporalAnalysisInterpretationGuideLowerPriority(BaseConfigModel):
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


class TemporalAnalysisInterpretationGuide(BaseConfigModel):
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


class TemporalAnalysisCaveats(BaseConfigModel):
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


class TemporalAnalysisIntroduction(BaseConfigModel):
    """
    Introduction to temporal analysis section.

    Explains purpose and methodology at high level.

    Attributes:
        paragraphs: list of introductory paragraphs
    """

    paragraphs: FormatStrList[P.TemporalIntroAll]


class TemporalAnalysis(BaseConfigModel):
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
