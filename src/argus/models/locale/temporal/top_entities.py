# argus/models/locale/temporal/top_entities.py
"""
Top entities models for temporal analysis localization.

Contains models that configure how high-risk entity profiles are displayed,
including their various analysis subsections (month-over-month, change points,
autocorrelation, rolling anomalies, trends, and period comparison).
"""

from pydantic import Field

from argus.models.common import FrozenModel
from argus.models.locale.placeholder_registry import P
from argus.models.locale.placeholder_validators import FormatStr

__all__: list[str] = [
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


class TemporalAnalysisTopEntitiesRecommendations(FrozenModel):
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


class TemporalAnalysisTopEntitiesCurrentRisks(FrozenModel):
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


class TemporalAnalysisTopEntitiesFraudPatternsPatterns(FrozenModel):
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


class TemporalAnalysisTopEntitiesFraudPatterns(FrozenModel):
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


class TemporalAnalysisTopEntitiesMonthOverMonthSuddenSpikes(FrozenModel):
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


class TemporalAnalysisTopEntitiesMonthOverMonthGradualEscalation(FrozenModel):
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


class TemporalAnalysisTopEntitiesMonthOverMonthVolatility(FrozenModel):
    """
    Configuration for one month-over-month volatility subgroup.

    Attributes:
        label: Subsection label
        high_note: Additional note for high volatility
    """

    label: FormatStr[P.TemporalVolatilityScore]
    high_note: str


class TemporalAnalysisTopEntitiesMonthOverMonth(FrozenModel):
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


class TemporalAnalysisTopEntitiesChangePoints(FrozenModel):
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


class TemporalAnalysisTopEntitiesAutocorrelation(FrozenModel):
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


class TemporalAnalysisTopEntitiesRollingAnomalies(FrozenModel):
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


class TemporalAnalysisTopEntitiesTrends(FrozenModel):
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


class TemporalAnalysisTopEntitiesPeriodComparison(FrozenModel):
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


class TemporalAnalysisTopEntitiesEntitySummary(FrozenModel):
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


class TemporalAnalysisTopEntities(FrozenModel):
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
