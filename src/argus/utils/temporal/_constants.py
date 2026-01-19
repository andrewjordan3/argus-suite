# argus/utils/temporal/_constants.py
"""
Centralized configuration constants for temporal analysis modules.

╔══════════════════════════════════════════════════════════════════════════════╗
║  CONFIGURATION MIGRATION NOTICE                                              ║
║                                                                              ║
║  All constants in this module are candidates for YAML configuration.         ║
║  These values were extracted from hardcoded magic numbers to enable:         ║
║    1. Runtime configurability without code changes                           ║
║    2. Environment-specific tuning (dev/staging/prod)                         ║
║    3. A/B testing of threshold values                                        ║
║    4. Domain expert adjustment without developer involvement                 ║
║                                                                              ║
║  TODO: Migrate these to Pydantic models loaded from YAML configuration.      ║
║  Priority: HIGH - These directly affect fraud detection sensitivity.         ║
║  Target: argus/defaults/policy.yaml                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

# =============================================================================
# STATISTICAL SIGNIFICANCE THRESHOLDS
# =============================================================================
# TODO: MIGRATE TO CONFIG - These control false positive/negative tradeoffs

# P-value threshold for declaring statistical significance
# Standard scientific convention; may need adjustment for multiple comparisons
STATISTICAL_SIGNIFICANCE_ALPHA: float = 0.05

# Z-score threshold for 95th percentile (one-tailed)
# Used to identify values in the extreme tail of normal distribution
PERCENTILE_95_Z_SCORE: float = 1.645

# Z-score threshold for outlier detection in rolling window analysis
# Values exceeding ±2 standard deviations flagged as outliers
OUTLIER_Z_SCORE_THRESHOLD: float = 2.0


# =============================================================================
# DATA SUFFICIENCY REQUIREMENTS
# =============================================================================
# TODO: MIGRATE TO CONFIG - Minimum sample sizes for valid statistical inference

# Absolute minimum records for any statistical test
# Below this, results are unreliable and should return insufficient_data
MINIMUM_RECORDS_FOR_STATISTICAL_TEST: int = 3

# Minimum observations for autocorrelation analysis
# ACF requires more data points to estimate lag correlations reliably
MINIMUM_RECORDS_FOR_AUTOCORRELATION: int = 5

# Minimum months of data to include entity in baseline calculations
MINIMUM_MONTHS_FOR_BASELINE_INCLUSION: int = 3


# =============================================================================
# CUSUM CHANGE DETECTION PARAMETERS
# =============================================================================
# TODO: MIGRATE TO CONFIG - Sensitivity vs false alarm tradeoff

# Reference value (slack parameter) - controls sensitivity to small shifts
# Smaller k detects smaller shifts more quickly but increases false alarms
# Typical range: 0.25 to 1.0 standard deviations
CUSUM_REFERENCE_VALUE_K: float = 0.5

# Decision threshold - controls false alarm rate
# Larger h reduces false alarms but delays detection of real changes
# Typical range: 4.0 to 5.0 standard deviations
CUSUM_DECISION_THRESHOLD_H: float = 4.5


# =============================================================================
# MONTH-OVER-MONTH ANALYSIS PARAMETERS
# =============================================================================
# TODO: MIGRATE TO CONFIG - Pattern detection sensitivity

# Maximum z-score for outlier filtering in volatility calculations
# Values beyond this threshold are excluded as likely data errors
VOLATILITY_OUTLIER_MAX_Z_SCORE: float = 5.0

# Minimum consecutive months of increases to flag gradual escalation
# Shorter windows may catch normal fluctuations; longer may miss patterns
GRADUAL_ESCALATION_MINIMUM_CONSECUTIVE_MONTHS: int = 3

# Minimum relative change to flag as significant month-over-month spike
# 0.5 = 50% increase from previous month
SIGNIFICANT_RELATIVE_CHANGE_THRESHOLD: float = 0.5


# =============================================================================
# ROLLING WINDOW ANALYSIS PARAMETERS
# =============================================================================
# TODO: MIGRATE TO CONFIG - Smoothing vs responsiveness tradeoff

# Default rolling window size in months
# Larger windows smooth more noise but respond slower to real changes
DEFAULT_ROLLING_WINDOW_SIZE_MONTHS: int = 3


# =============================================================================
# AUTOCORRELATION ANALYSIS PARAMETERS
# =============================================================================
# TODO: MIGRATE TO CONFIG - Pattern persistence classification

# Maximum lag to calculate in autocorrelation function
# Higher lags detect longer-range patterns but require more data
AUTOCORRELATION_MAXIMUM_LAG: int = 3

# Lag-1 correlation threshold for HIGH risk (persistent pattern)
# Values above this indicate strongly self-correlated behavior
AUTOCORRELATION_HIGH_RISK_THRESHOLD: float = 0.6

# Lag-1 correlation threshold for MEDIUM risk (moderate pattern)
# Values between this and HIGH threshold indicate some persistence
AUTOCORRELATION_MEDIUM_RISK_THRESHOLD: float = 0.4


# =============================================================================
# FRAUD PATTERN DETECTION PARAMETERS
# =============================================================================
# TODO: MIGRATE TO CONFIG - Fraud pattern sensitivity

# After-hours transaction rate threshold for off-hours concentration pattern
# Percentage of transactions outside normal business hours
OFF_HOURS_CONCENTRATION_THRESHOLD_PERCENT: float = 60.0

# Spike detection: minimum relative increase from baseline
# 1.5 = 50% increase over previous value
SPIKE_DETECTION_MINIMUM_INCREASE_MULTIPLIER: float = 1.5

# Retreat detection: maximum relative value after spike
# 0.6 = 40% drop from spike value
RETREAT_DETECTION_MAXIMUM_MULTIPLIER: float = 0.6

# Gradual escalation: minimum increase from first to second half
# 1.3 = 30% increase in second half average vs first half
GRADUAL_ESCALATION_HALF_COMPARISON_THRESHOLD: float = 1.3

# Minimum months required to evaluate gradual escalation pattern
GRADUAL_ESCALATION_MINIMUM_MONTHS: int = 6


# =============================================================================
# EFFECT SIZE INTERPRETATION THRESHOLDS
# =============================================================================
# TODO: MIGRATE TO CONFIG - Effect size classification boundaries

# Cliff's Delta threshold below which effect is considered negligible
# Standard convention: |delta| < 0.147 is negligible
CLIFFS_DELTA_NEGLIGIBLE_THRESHOLD: float = 0.15


# =============================================================================
# PELT CHANGE POINT DETECTION PARAMETERS
# =============================================================================
# TODO: MIGRATE TO CONFIG - Segmentation algorithm tuning

# Minimum segment length between change points
# Prevents detection of spurious changes in short intervals
PELT_MINIMUM_SEGMENT_LENGTH: int = 2

# Minimum total records to attempt change point detection
PELT_MINIMUM_RECORDS: int = 6


# =============================================================================
# METRICS TO ANALYZE
# =============================================================================
# TODO: MIGRATE TO CONFIG - Allow domain experts to add/remove metrics

# Standard metrics for month-over-month and rolling analysis
STANDARD_BEHAVIORAL_METRICS: tuple[str, ...] = (
    'no_eld_rate',
    'non_diesel_rate',
    'after_hours_rate',
    'datetime_count',
)

# Metrics for autocorrelation analysis (exclude count-based metrics)
AUTOCORRELATION_ANALYSIS_METRICS: tuple[str, ...] = (
    'no_eld_rate',
    'non_diesel_rate',
    'after_hours_rate',
)

# Metrics to include in baseline distributions
BASELINE_DISTRIBUTION_METRICS: tuple[str, ...] = (
    'datetime_count',
    'no_eld_rate',
    'non_diesel_rate',
    'after_hours_rate',
    'cost_mean',
    'cost_median',
    'cost_sum',
)
