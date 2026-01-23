# argus/models/locale/temporal/risk_distribution.py
"""
Risk distribution models for temporal analysis localization.

Contains models that configure how temporal risk score distributions
are displayed across entity types (drivers and vehicles).
"""

from argus.models.common import FrozenModel
from argus.models.locale.placeholder_registry import P
from argus.models.locale.placeholder_validators import FormatStr, FormatStrList

__all__: list[str] = [
    'TemporalAnalysisRiskDistribution',
    'TemporalAnalysisRiskDistributionGroup',
    'TemporalAnalysisRiskDistributionOverall',
]


class TemporalAnalysisRiskDistributionGroup(FrozenModel):
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


class TemporalAnalysisRiskDistributionOverall(FrozenModel):
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


class TemporalAnalysisRiskDistribution(FrozenModel):
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
