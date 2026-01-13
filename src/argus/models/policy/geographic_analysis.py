# argus/models/policy/geographic_analysis.py
"""
Configuration models for geographic analysis thresholds.

Geographic analysis identifies fuel stations with suspicious transaction patterns.
Stations where fleet drivers consistently exhibit anomalous behavior may indicate
locations being exploited for card misuse (e.g., stations near drivers' homes
where personal vehicles are fueled).
"""

from pydantic import BaseModel, ConfigDict, Field

__all__: list[str] = ['GeographicAnalysisConfig']


class GeographicAnalysisConfig(BaseModel):
    """
    Thresholds for detecting suspicious geographic patterns.

    These thresholds flag fuel stations where transaction patterns deviate
    from expected fleet behavior. High-scoring stations warrant investigation
    as potential misuse hotspots.

    Attributes:
        suspicious_non_diesel_rate: Rate of non-diesel purchases at a station to flag as suspicious.
        suspicious_no_eld_rate: Rate of unverified transactions at a station to flag as suspicious.
        low_avg_cost_percentile: Percentile threshold for flagging stations with low average costs.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    # -------------------------------------------------------------------------
    # Product Type Anomalies
    # -------------------------------------------------------------------------
    suspicious_non_diesel_rate: float = Field(
        default=0.25,
        description=(
            'Rate of non-diesel purchases at a station to flag as suspicious. '
            '0.25 = Stations where 25%+ of fleet transactions are gasoline/other. '
            'High rates suggest personal vehicle fueling.'
        ),
        gt=0.0,
        le=1.0,
    )

    # -------------------------------------------------------------------------
    # Verification Failures
    # -------------------------------------------------------------------------
    suspicious_no_eld_rate: float = Field(
        default=0.40,
        description=(
            'Rate of transactions without ELD verification to flag as suspicious. '
            '0.40 = Stations where 40%+ of transactions lack telematics confirmation. '
            'High rates may indicate off-route or unauthorized stops.'
        ),
        gt=0.0,
        le=1.0,
    )

    # -------------------------------------------------------------------------
    # Cost Anomalies
    # -------------------------------------------------------------------------
    low_avg_cost_percentile: float = Field(
        default=10.0,
        description=(
            'Percentile threshold for flagging stations with suspiciously low average costs. '
            '10 = Stations below the 10th percentile of average transaction cost. '
            'Low averages may indicate partial fills typical of personal vehicle use.'
        ),
        gt=0.0,
        lt=100.0,
    )
