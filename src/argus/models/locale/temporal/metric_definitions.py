# argus/models/locale/temporal/metric_definitions.py
"""
Metric definition models for temporal analysis localization.

Contains models that define metric names, calculation methodologies,
and analysis type documentation for the temporal analysis section.
"""

from pydantic import Field

from argus.models.common import FrozenModel
from argus.models.locale.placeholder_registry import P
from argus.models.locale.placeholder_validators import FormatStr, FormatStrList

__all__: list[str] = [
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
]


class TemporalAnalysisMetricDisplayNames(FrozenModel):
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


class TemporalAnalysisMetricDefinitionItem(FrozenModel):
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


class TemporalAnalysisMetricDefinitionAfterHoursRate(FrozenModel):
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


class TemporalAnalysisMetricDefinitionsMetrics(FrozenModel):
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


class TemporalAnalysisMetricDefinitionsAnalysisTypesMonthOverMonth(FrozenModel):
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


class TemporalAnalysisMetricDefinitionsAnalysisTypesAutoCorrelation(FrozenModel):
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


class TemporalAnalysisMetricDefinitionsAnalysisTypesFraudPatternsPatterns(FrozenModel):
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


class TemporalAnalysisMetricDefinitionsAnalysisTypesItem(FrozenModel):
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


class TemporalAnalysisMetricDefinitionsAnalysisTypes(FrozenModel):
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


class TemporalAnalysisMetricDefinitionsPeriodComparison(FrozenModel):
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


class TemporalAnalysisMetricDefinitions(FrozenModel):
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
