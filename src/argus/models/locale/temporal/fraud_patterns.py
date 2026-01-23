# argus/models/locale/temporal/fraud_patterns.py
"""
Fraud pattern summary models for temporal analysis localization.

Contains models that configure how known fraud signatures are documented
and displayed in reports (off-hours concentration, spike-and-retreat,
gradual escalation, operational anomaly).
"""

from argus.models.common import FrozenModel
from argus.models.locale.placeholder_registry import P
from argus.models.locale.placeholder_validators import FormatStr

__all__: list[str] = [
    'TemporalAnalysisFraudPatternSummary',
    'TemporalAnalysisFraudPatternSummaryGradualEscalation',
    'TemporalAnalysisFraudPatternSummaryOffHoursConcentration',
    'TemporalAnalysisFraudPatternSummaryOperationalAnomaly',
    'TemporalAnalysisFraudPatternSummaryPattern',
    'TemporalAnalysisFraudPatternSummarySpikeRetreat',
]


class TemporalAnalysisFraudPatternSummaryPattern[DescriptionType](FrozenModel):
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


class TemporalAnalysisFraudPatternSummary(FrozenModel):
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
