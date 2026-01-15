# argus/models/policy/root.py
"""
Root policy configuration for ARGUS.

This module aggregates all policy sub-configurations into a single PolicyConfig
model that can be loaded from a YAML file and validated as a cohesive unit.
"""

from pydantic import Field

from argus.models.common import RootConfigModel
from argus.models.policy.analysis_thresholds import (
    AnomalyThresholds,
    RiskScoreThresholds,
)
from argus.models.policy.business_hours import BusinessHoursConfig
from argus.models.policy.data_requirements import DataRequirementsConfig
from argus.models.policy.effect_size import EffectSizeInterpretationConfig
from argus.models.policy.geographic_analysis import GeographicAnalysisConfig
from argus.models.policy.red_flag_weights import RedFlagWeightsConfig
from argus.models.policy.risk_weights import RiskWeightsConfig
from argus.models.policy.statistical_settings import StatisticsConfig
from argus.models.policy.temporal_analysis import TemporalAnalysisConfig

__all__: list[str] = ['PolicyConfig']


class PolicyConfig(RootConfigModel):
    """
    Root configuration for ARGUS policy settings.

    Aggregates all configurable thresholds, weights, and parameters that control
    ARGUS analysis behavior. Each sub-configuration has sensible defaults, allowing
    partial overrides in the policy YAML file.

    Attributes:
        statistics: Statistical analysis parameters (confidence level, FDR method, p-value thresholds).
        data_requirements: Minimum data quality and quantity requirements for valid analysis.
        business_hours: Business hours definition for after-hours detection.
        risk_weights: Weights for composite driver risk score calculation.
        risk_score_thresholds: Thresholds for categorizing risk scores into severity levels.
        anomaly_thresholds: Thresholds for flagging high rates of suspicious activity.
        red_flag_weights: Weights for multi-fillup red flag scoring.
        effect_size_interpretation: Thresholds for interpreting statistical effect magnitudes.
        temporal_analysis: Thresholds for detecting patterns over time.
        geographic_analysis: Thresholds for detecting suspicious station-level patterns.
    """

    # -------------------------------------------------------------------------
    # Statistical Framework
    # -------------------------------------------------------------------------
    statistics: StatisticsConfig = Field(
        default_factory=StatisticsConfig,
        description='Statistical analysis parameters including confidence level and FDR control.',
    )

    data_requirements: DataRequirementsConfig = Field(
        default_factory=DataRequirementsConfig,
        description='Minimum data quality and quantity requirements for valid analysis.',
    )

    # -------------------------------------------------------------------------
    # Business Context
    # -------------------------------------------------------------------------
    business_hours: BusinessHoursConfig = Field(
        default_factory=BusinessHoursConfig,
        description='Business hours definition for after-hours transaction detection.',
    )

    # -------------------------------------------------------------------------
    # Risk Scoring
    # -------------------------------------------------------------------------
    risk_weights: RiskWeightsConfig = Field(
        default_factory=RiskWeightsConfig,
        description='Weights for composite driver risk score calculation.',
    )

    risk_score_thresholds: RiskScoreThresholds = Field(
        default_factory=RiskScoreThresholds,
        description='Thresholds for categorizing risk scores into severity levels.',
    )

    anomaly_thresholds: AnomalyThresholds = Field(
        default_factory=AnomalyThresholds,
        description='Thresholds for flagging high rates of suspicious activity.',
    )

    red_flag_weights: RedFlagWeightsConfig = Field(
        default_factory=RedFlagWeightsConfig,
        description='Weights for multi-fillup red flag scoring.',
    )

    # -------------------------------------------------------------------------
    # Effect Size Interpretation
    # -------------------------------------------------------------------------
    effect_size_interpretation: EffectSizeInterpretationConfig = Field(
        default_factory=EffectSizeInterpretationConfig,
        description='Thresholds for interpreting statistical effect magnitudes.',
    )

    # -------------------------------------------------------------------------
    # Pattern Detection
    # -------------------------------------------------------------------------
    temporal_analysis: TemporalAnalysisConfig = Field(
        default_factory=TemporalAnalysisConfig,
        description='Thresholds for detecting patterns over time.',
    )

    geographic_analysis: GeographicAnalysisConfig = Field(
        default_factory=GeographicAnalysisConfig,
        description='Thresholds for detecting suspicious station-level patterns.',
    )
