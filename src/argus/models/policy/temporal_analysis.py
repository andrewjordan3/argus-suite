# argus/models/policy/temporal_analysis.py
"""
Configuration models for temporal analysis thresholds.

These thresholds control detection of patterns over time including sudden spikes,
gradual escalations, period comparisons, and persistent behavioral patterns.
"""

from pydantic import BaseModel, ConfigDict, Field

__all__: list[str] = ['TemporalAnalysisConfig']


class TemporalAnalysisConfig(BaseModel):
    """
    Thresholds for detecting temporal patterns in transaction behavior.

    Controls sensitivity of various time-series analyses including spike detection,
    trend identification, and pattern recognition.

    Attributes:
        spike_threshold_pct: Percentage increase from prior month to flag as sudden spike.
        spike_percentile: Percentile threshold vs. historical baseline for spike detection.
        consecutive_increase_months: Consecutive months of increases to flag gradual escalation.
        period_change_threshold: Minimum change ratio for concerning period comparison.
        autocorrelation_threshold: Lag-1 autocorrelation threshold for persistent pattern flag.
        off_hours_concentration_threshold: Proportion of off-hours transactions to flag pattern.
        retreat_drop_threshold: Percentage drop after spike to flag spike-and-retreat pattern.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    # -------------------------------------------------------------------------
    # Sudden Spike Detection
    # -------------------------------------------------------------------------
    spike_threshold_pct: float = Field(
        default=50.0,
        description=(
            'Percentage increase from prior month to flag as sudden spike. '
            '50 = 50% month-over-month increase triggers flag.'
        ),
        gt=0.0,
    )

    spike_percentile: float = Field(
        default=95.0,
        description=(
            'Percentile threshold vs. historical baseline for spike detection. '
            "95 = Month's value exceeds 95th percentile of baseline."
        ),
        gt=0.0,
        lt=100.0,
    )

    # -------------------------------------------------------------------------
    # Gradual Escalation Detection
    # -------------------------------------------------------------------------
    consecutive_increase_months: int = Field(
        default=3,
        description=(
            'Consecutive months of increases required to flag gradual escalation. '
            'Minimum of 2 required to establish a trend.'
        ),
        ge=2,
    )

    # -------------------------------------------------------------------------
    # Period Comparison (First Half vs Second Half)
    # -------------------------------------------------------------------------
    period_change_threshold: float = Field(
        default=0.30,
        description=(
            'Minimum change ratio to flag period comparison as concerning. '
            '0.30 = Second half is 30%+ higher than first half.'
        ),
        gt=0.0,
    )

    # -------------------------------------------------------------------------
    # Autocorrelation (Persistent Behavior)
    # -------------------------------------------------------------------------
    autocorrelation_threshold: float = Field(
        default=0.6,
        description=(
            'Lag-1 autocorrelation threshold to flag persistent pattern. '
            'High autocorrelation indicates systematic rather than random behavior.'
        ),
        gt=0.0,
        le=1.0,
    )

    # -------------------------------------------------------------------------
    # Off-Hours Concentration Pattern
    # -------------------------------------------------------------------------
    off_hours_concentration_threshold: float = Field(
        default=0.60,
        description=(
            'Proportion of transactions outside business hours to flag pattern. '
            '0.60 = 60%+ of transactions are after hours or weekends.'
        ),
        gt=0.0,
        le=1.0,
    )

    # -------------------------------------------------------------------------
    # Spike-and-Retreat Pattern
    # -------------------------------------------------------------------------
    retreat_drop_threshold: float = Field(
        default=0.40,
        description=(
            'Percentage drop after spike to flag spike-and-retreat pattern. '
            '0.40 = 40%+ drop following a spike suggests threshold testing.'
        ),
        gt=0.0,
        le=1.0,
    )
