# argus/utils/temporal/fraud_pattern_detector.py
"""
Fuel card fraud pattern detection module.

This module identifies specific behavioral patterns commonly associated with
fuel card fraud schemes. Each pattern represents a distinct fraud topology:

    - Off-Hours Concentration: Transactions clustered outside business hours
    - Spike-and-Retreat: Sudden surge followed by quick reduction (test fraud)
    - Gradual Escalation: Slowly increasing suspicious behavior over time
    - Operational Anomaly: Behavior inconsistent with expected patterns

Typical Usage:
    from argus.utils.temporal.fraud_pattern_detector import FraudPatternDetector

    detector = FraudPatternDetector(monthly_data=entity_monthly_df)
    detected_patterns = detector.detect_all_patterns()

    if detected_patterns['spike_retreat']:
        print("WARNING: Spike-and-retreat pattern detected - possible test fraud")
"""

import logging
from dataclasses import dataclass
from typing import Any

import pandas as pd

from argus.utils.temporal._constants import (
    GRADUAL_ESCALATION_HALF_COMPARISON_THRESHOLD,
    GRADUAL_ESCALATION_MINIMUM_MONTHS,
    OFF_HOURS_CONCENTRATION_THRESHOLD_PERCENT,
    RETREAT_DETECTION_MAXIMUM_MULTIPLIER,
    SPIKE_DETECTION_MINIMUM_INCREASE_MULTIPLIER,
)

__all__: list[str] = [
    'FraudPatternConfiguration',
    'FraudPatternDetector',
    'FraudPatternResults',
]

# Set up module logger
logger: logging.Logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION DATA CLASS
# =============================================================================


@dataclass(frozen=True, slots=True)
class FraudPatternConfiguration:
    """
    Configuration parameters for fraud pattern detection.

    ╔══════════════════════════════════════════════════════════════════════════╗
    ║  CONFIGURATION MIGRATION NOTICE                                          ║
    ║                                                                          ║
    ║  These thresholds directly affect fraud detection sensitivity and        ║
    ║  false positive rates. Domain experts should be able to tune these       ║
    ║  without code changes. Migrate to YAML configuration.                    ║
    ║  Target: argus/defaults/policy.yaml                                ║
    ╚══════════════════════════════════════════════════════════════════════════╝

    Attributes:
        off_hours_threshold_percent:
            Percentage of transactions outside business hours required to
            trigger off-hours concentration pattern. Default 60%.

        spike_increase_multiplier:
            Minimum multiplier from baseline to flag as spike.
            1.5 = 50% increase from previous value.

        retreat_max_multiplier:
            Maximum multiplier from spike to flag retreat.
            0.6 = 40% drop from spike value.

        escalation_half_threshold:
            Minimum multiplier for second-half vs first-half averages
            to flag gradual escalation. 1.3 = 30% increase.

        escalation_min_months:
            Minimum months of data required to evaluate gradual escalation.

        spike_retreat_metrics:
            Metrics to examine for spike-and-retreat pattern.

        after_hours_column:
            Column name for after-hours rate metric.

        no_eld_column:
            Column name for no-ELD-activity rate metric.
    """

    # Off-hours concentration
    off_hours_threshold_percent: float = OFF_HOURS_CONCENTRATION_THRESHOLD_PERCENT
    after_hours_column: str = 'after_hours_rate'

    # Spike-and-retreat
    spike_increase_multiplier: float = SPIKE_DETECTION_MINIMUM_INCREASE_MULTIPLIER
    retreat_max_multiplier: float = RETREAT_DETECTION_MAXIMUM_MULTIPLIER
    spike_retreat_metrics: tuple[str, ...] = ('datetime_count', 'no_eld_rate')

    # Gradual escalation
    escalation_half_threshold: float = GRADUAL_ESCALATION_HALF_COMPARISON_THRESHOLD
    escalation_min_months: int = GRADUAL_ESCALATION_MINIMUM_MONTHS
    no_eld_column: str = 'no_eld_rate'


# =============================================================================
# RESULT DATA CLASS
# =============================================================================


@dataclass
class FraudPatternResults:
    """
    Results from fraud pattern detection.

    Attributes:
        off_hours_concentration:
            True if >60% of recent transactions occur outside business hours.
            Indicates possible unauthorized personal use or theft.

        spike_retreat:
            True if a sudden spike (>50% increase) is followed by a drop
            (>40% decrease) within 2 months. Indicates possible test fraud
            where fraudster tests with large amount then retreats.

        gradual_escalation:
            True if the second half of the observation period shows >30%
            higher average than the first half. Indicates possible slow
            escalation of fraud to avoid detection.

        operational_anomaly:
            Reserved for future implementation. Will flag behavior that
            is inconsistent with expected operational patterns.
    """

    off_hours_concentration: bool = False
    spike_retreat: bool = False
    gradual_escalation: bool = False
    operational_anomaly: bool = False

    def any_pattern_detected(self) -> bool:
        """Return True if any fraud pattern was detected."""
        return (
            self.off_hours_concentration
            or self.spike_retreat
            or self.gradual_escalation
            or self.operational_anomaly
        )

    def to_dict(self) -> dict[str, bool]:
        """Convert to dictionary for serialization."""
        return {
            'off_hours_concentration': self.off_hours_concentration,
            'spike_retreat': self.spike_retreat,
            'gradual_escalation': self.gradual_escalation,
            'operational_anomaly': self.operational_anomaly,
        }


# =============================================================================
# FRAUD PATTERN DETECTOR CLASS
# =============================================================================


class FraudPatternDetector:
    """
    Detects specific behavioral patterns commonly associated with fuel card fraud.

    This class examines monthly aggregated transaction data to identify
    established fraud topologies. Each pattern detection method is independent
    and can be run selectively or all together.

    Pattern Definitions:

        Off-Hours Concentration:
            More than threshold% of transactions occur outside normal business
            hours (typically 6am-6pm). This pattern may indicate:
            - Personal use of company fuel cards
            - Card sharing with unauthorized users
            - Systematic theft during off-hours

        Spike-and-Retreat:
            A sudden increase of >50% followed by a >40% drop within 2 months.
            This pattern may indicate:
            - Testing fraud scheme viability
            - One-time large theft followed by cooling off
            - Opportunistic fraud during low-oversight period

        Gradual Escalation:
            The second half of observation period shows >30% higher suspicious
            activity than the first half. This pattern may indicate:
            - Systematic escalation to avoid detection thresholds
            - Growing confidence in fraud going undetected
            - Increasing financial pressure driving more fraud

    Attributes:
        monthly_data: DataFrame with monthly aggregated metrics
        config: FraudPatternConfiguration with all thresholds

    Example:
        >>> detector = FraudPatternDetector(monthly_data=driver_df)
        >>> results = detector.detect_all_patterns()
        >>> if results.spike_retreat:
        ...     print("ALERT: Spike-and-retreat pattern detected")
        >>> print(f"Patterns detected: {results.any_pattern_detected()}")
    """

    def __init__(
        self,
        monthly_data: pd.DataFrame,
        configuration: FraudPatternConfiguration | None = None,
    ) -> None:
        """
        Initialize the FraudPatternDetector.

        Args:
            monthly_data:
                DataFrame indexed by month containing aggregated metrics.
                Expected columns depend on configured pattern detections:
                - 'after_hours_rate': For off-hours concentration
                - 'datetime_count': For spike-retreat
                - 'no_eld_rate': For spike-retreat and gradual escalation

            configuration:
                Optional FraudPatternConfiguration. If None, uses defaults
                from module constants.

        Raises:
            ValueError: If monthly_data is empty.
        """
        if monthly_data.empty:
            raise ValueError('monthly_data cannot be empty')

        self._monthly_data: pd.DataFrame = monthly_data
        self._config: FraudPatternConfiguration = (
            configuration or FraudPatternConfiguration()
        )

        logger.debug(
            'FraudPatternDetector initialized with %d months of data',
            len(monthly_data),
        )

    def detect_all_patterns(self) -> FraudPatternResults:
        """
        Run all fraud pattern detections and return aggregated results.

        Returns:
            FraudPatternResults with boolean flags for each pattern type.
        """
        results = FraudPatternResults(
            off_hours_concentration=self.detect_off_hours_concentration(),
            spike_retreat=self.detect_spike_and_retreat(),
            gradual_escalation=self.detect_gradual_escalation(),
            operational_anomaly=False,  # Reserved for future implementation
        )

        if results.any_pattern_detected():
            logger.warning(
                'Fraud patterns detected: off_hours=%s, spike_retreat=%s, '
                'gradual_escalation=%s',
                results.off_hours_concentration,
                results.spike_retreat,
                results.gradual_escalation,
            )

        return results

    def detect_off_hours_concentration(self) -> bool:
        """
        Detect if recent transactions are concentrated outside business hours.

        Examines the most recent 3 months of after_hours_rate to determine
        if the average exceeds the configured threshold.

        Returns:
            True if average recent after-hours rate exceeds threshold.
        """
        column_name: str = self._config.after_hours_column

        if column_name not in self._monthly_data.columns:
            logger.debug(
                'Off-hours detection skipped: column %s not found', column_name
            )
            return False

        recent_after_hours_rates: pd.Series[float] = self._monthly_data[
            column_name
        ].tail(3)
        average_recent_rate: float = recent_after_hours_rates.mean()

        is_concentrated: bool = (
            average_recent_rate > self._config.off_hours_threshold_percent
        )

        if is_concentrated:
            logger.info(
                'Off-hours concentration detected: %.1f%% average (threshold: %.1f%%)',
                average_recent_rate,
                self._config.off_hours_threshold_percent,
            )

        return is_concentrated

    def detect_spike_and_retreat(self) -> bool:
        """
        Detect spike-and-retreat pattern (test fraud topology).

        Searches for any occurrence where:
            - Month M+1 value is >50% higher than month M, AND
            - Month M+2 value is >40% lower than month M+1

        Checks multiple metrics as configured.

        Returns:
            True if spike-and-retreat pattern found in any metric.
        """
        for metric_name in self._config.spike_retreat_metrics:
            if metric_name not in self._monthly_data.columns:
                continue

            metric_values: pd.Series[Any] = self._monthly_data[metric_name]
            value_count: int = len(metric_values)

            # Need at least 3 consecutive months to detect pattern
            if value_count < 3:  # noqa: PLR2004
                continue

            # Search for spike-retreat pattern
            for month_index in range(value_count - 2):
                baseline_value: float = metric_values.iloc[month_index]
                potential_spike_value: float = metric_values.iloc[month_index + 1]
                retreat_value: float = metric_values.iloc[month_index + 2]

                # Check for spike (>50% increase)
                spike_threshold: float = (
                    baseline_value * self._config.spike_increase_multiplier
                )
                is_spike: bool = potential_spike_value > spike_threshold

                # Check for retreat (>40% drop from spike)
                retreat_threshold: float = (
                    potential_spike_value * self._config.retreat_max_multiplier
                )
                is_retreat: bool = retreat_value < retreat_threshold

                if is_spike and is_retreat:
                    logger.info(
                        'Spike-and-retreat detected in %s at month index %d: '
                        '%.1f -> %.1f -> %.1f',
                        metric_name,
                        month_index,
                        baseline_value,
                        potential_spike_value,
                        retreat_value,
                    )
                    return True

        return False

    def detect_gradual_escalation(self) -> bool:
        """
        Detect gradual escalation pattern (slow fraud ramp-up).

        Compares the average of the first half of observations to the
        second half. If second half is >30% higher, flags escalation.

        Requires minimum configured months of data.

        Returns:
            True if second half shows significant escalation over first half.
        """
        column_name: str = self._config.no_eld_column

        if column_name not in self._monthly_data.columns:
            logger.debug(
                'Gradual escalation detection skipped: column %s not found',
                column_name,
            )
            return False

        metric_values: pd.Series[Any] = self._monthly_data[column_name]
        value_count: int = len(metric_values)

        if value_count < self._config.escalation_min_months:
            logger.debug(
                'Gradual escalation detection skipped: only %d months '
                '(minimum %d required)',
                value_count,
                self._config.escalation_min_months,
            )
            return False

        # Split into halves and compare averages
        midpoint: int = value_count // 2
        first_half_average: float = metric_values.iloc[:midpoint].mean()
        second_half_average: float = metric_values.iloc[midpoint:].mean()

        # Check if second half exceeds threshold vs first half
        escalation_threshold: float = (
            first_half_average * self._config.escalation_half_threshold
        )
        is_escalating: bool = second_half_average > escalation_threshold

        if is_escalating:
            percent_increase: float = (
                ((second_half_average - first_half_average) / first_half_average) * 100
                if first_half_average > 0
                else 0
            )
            logger.info(
                'Gradual escalation detected in %s: first half avg=%.1f, '
                'second half avg=%.1f (%.1f%% increase)',
                column_name,
                first_half_average,
                second_half_average,
                percent_increase,
            )

        return is_escalating
