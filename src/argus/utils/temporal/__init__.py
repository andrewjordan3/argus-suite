# argus/utils/temporal/__init__.py
"""
Temporal analysis utilities for ARGUS fraud detection.

This package provides statistical methods for analyzing time series data
in the context of fuel card fraud detection. The modules are organized by
analysis type:

Modules:
    trend_detection: Mann-Kendall trends and CUSUM/PELT change points
    segment_comparison: Mann-Whitney U tests for comparing time periods
    monthly_behavior_analyzer: Class for analyzing monthly aggregated patterns
    fraud_pattern_detector: Specific fraud topology detection
    baseline_builder: Population baseline distribution creation

Example:
    from argus.utils.temporal import (
        detect_monotonic_trend,
        detect_single_change_point,
        MonthlyBehaviorAnalyzer,
        FraudPatternDetector,
        build_entity_baselines,
    )
"""

from argus.utils.temporal.baseline_builder import (
    BaselineDistributions,
    EntityTypeBaseline,
    MetricDistributionStatistics,
    build_entity_baselines,
)
from argus.utils.temporal.fraud_pattern_detector import (
    FraudPatternConfiguration,
    FraudPatternDetector,
    FraudPatternResults,
)
from argus.utils.temporal.monthly_behavior_analyzer import (
    AutocorrelationResult,
    GradualEscalationResult,
    MonthlyAnalyzerConfiguration,
    MonthlyBehaviorAnalyzer,
    MonthOverMonthResults,
    RollingWindowOutlierResult,
    SuddenSpikeResult,
)
from argus.utils.temporal.segment_comparison import (
    ChangeDirection,
    EffectMagnitude,
    EffectSizeResult,
    GroupDescriptiveStatistics,
    RiskDistributionComparisonResult,
    SegmentComparisonResult,
    compare_risk_distributions,
    compare_two_segments,
)
from argus.utils.temporal.trend_detection import (
    MannKendallResult,
    detect_all_change_points,
    detect_monotonic_trend,
    detect_single_change_point,
)

__all__: list[str] = [
    'AutocorrelationResult',
    'BaselineDistributions',
    'ChangeDirection',
    'EffectMagnitude',
    'EffectSizeResult',
    'EntityTypeBaseline',
    'FraudPatternConfiguration',
    'FraudPatternDetector',
    'FraudPatternResults',
    'GradualEscalationResult',
    'GroupDescriptiveStatistics',
    'MannKendallResult',
    'MetricDistributionStatistics',
    'MonthOverMonthResults',
    'MonthlyAnalyzerConfiguration',
    'MonthlyBehaviorAnalyzer',
    'RiskDistributionComparisonResult',
    'RollingWindowOutlierResult',
    'SegmentComparisonResult',
    'SuddenSpikeResult',
    'build_entity_baselines',
    'compare_risk_distributions',
    'compare_two_segments',
    'detect_all_change_points',
    'detect_monotonic_trend',
    'detect_single_change_point',
]
