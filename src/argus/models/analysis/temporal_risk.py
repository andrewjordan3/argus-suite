# argus/models/analysis/temporal_risk.py
"""
Temporal Risk Profile Data Model
This module defines the data model for temporal risk profiles used in ARGUS.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from argus.models.analysis.type_definitions import EntityType
from argus.models.config import RiskCategory, RiskScoreThresholds
from argus.utils import categorize_risk_score

__all__: list[str] = [
    'TemporalRiskProfile',
]

class TemporalRiskProfile(BaseModel):
    """
    Container for comprehensive temporal analysis results for a single entity (driver or vehicle).

    This model stores detailed information about how an entity's behavior has changed
    over time, including:
    - Detected change points (single and multiple)
    - Concerning trends and risk indicators
    - Month-over-month volatility and spikes
    - Rolling window anomalies
    - Autocorrelation patterns (persistent behavior)
    - Specific fraud pattern signatures
    - Current state risk factors
    - Period-to-period comparisons

    Attributes:
        display_id: Human-readable identifier (driver name or VIN)
        entity_type: Type of entity ('Driver' or 'Vehicle')
        risk_score: Comprehensive temporal risk score (0-100 scale)
        months_active: Number of months with transactions
        total_transactions: Total number of transactions in the period
        truck_description: Optional vehicle description

        # Original temporal analysis fields
        change_points: dictionary mapping metric names to single change point dates
                      Example: {'no_eld_rate': '2024-06', 'transaction_volume': '2024-08'}
        risk_indicators: list of all concerning trends and patterns detected
                        Example: ['INCREASING no_eld_rate', 'SUDDEN SPIKE in transaction_volume']
        segment_comparison: dictionary mapping metrics to first-half vs second-half comparison results
                          Example: {'no_eld_rate': 'INCREASED (p=0.023, r=0.45)'}

        # Enhanced temporal analysis fields
        multiple_change_points: dictionary mapping metrics to lists of ALL detected change points
                               Example: {'no_eld_rate': ['2024-03', '2024-07', '2024-10']}
        month_over_month: dictionary containing month-to-month volatility analysis
                         Keys: 'sudden_spikes', 'gradual_escalation', 'volatility_score'
        rolling_anomalies: dictionary mapping metrics to rolling window outlier detection results
                          Example: {'no_eld_rate': {'outlier_months': ['2024-05'], 'max_z_score': 2.3}}
        autocorrelation: dictionary mapping metrics to autocorrelation analysis
                        Example: {'after_hours_rate': {'lag1_correlation': 0.78, 'risk_level': 'HIGH'}}
        fraud_patterns: dictionary of specific fraud pattern flags
                       Keys: 'weekend_warrior', 'pump_and_dump', 'creeping_charlie', 'seasonal_mismatch'
        current_risk_factors: list of risk factors present in the most recent month
                             Example: ['High No ELD Rate (45.2%)', 'High After Hours Rate (62.1%)']
        summary: dictionary containing summary statistics for quick overview
                Keys: 'total_risk_factors', 'total_change_points', 'has_fraud_patterns',
                      'volatility_score', 'recent_behavior_score'
    """

    model_config = ConfigDict(extra='forbid')

    # Core identification fields
    display_id: str = Field(
        ...,
        description='Human-readable identifier (driver name or VIN)',
        min_length=1,
    )
    entity_type: EntityType = Field(
        ...,
        description="Type of entity ('Driver' or 'Vehicle')",
    )
    risk_score: int = Field(
        ...,
        description='Comprehensive temporal risk score (0-100 scale)',
        ge=0,
        le=100,
    )
    months_active: int = Field(
        ...,
        description='Number of months with transactions',
        ge=0,
    )
    total_transactions: int = Field(
        ...,
        description='Total number of transactions in the period',
        ge=0,
    )
    truck_description: str | None = Field(
        default=None,
        description='Optional vehicle description',
    )

    # Original temporal analysis fields (maintained for backward compatibility)
    change_points: dict[str, str] = Field(
        default_factory=dict,
        description='Mapping of metric names to single change point dates',
    )
    risk_indicators: list[str] = Field(
        default_factory=list,
        description='List of all concerning trends and patterns detected',
    )
    segment_comparison: dict[str, str] = Field(
        default_factory=dict,
        description='Mapping of metrics to first-half vs second-half comparison results',
    )

    # Enhanced temporal analysis fields
    multiple_change_points: dict[str, list[str]] = Field(
        default_factory=dict,
        description='Mapping of metrics to lists of ALL detected change points',
    )
    month_over_month: dict[str, Any] = Field(
        default_factory=dict,
        description='Month-to-month volatility analysis',
    )
    rolling_anomalies: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description='Mapping of metrics to rolling window outlier detection results',
    )
    autocorrelation: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description='Mapping of metrics to autocorrelation analysis',
    )
    fraud_patterns: dict[str, bool] = Field(
        default_factory=dict,
        description='Dictionary of specific fraud pattern flags',
    )
    current_risk_factors: list[str] = Field(
        default_factory=list,
        description='List of risk factors present in the most recent month',
    )
    summary: dict[str, Any] = Field(
        default_factory=dict,
        description='Dictionary containing summary statistics for quick overview',
    )

    def to_dict(self, exclude_none: bool = False) -> dict[str, Any]:
        """
        Convert the profile to a dictionary for serialization.

        Args:
            exclude_none: If True, exclude fields with None values.

        Returns:
            Dictionary representation of the profile with all fields.
        """
        return self.model_dump(exclude_none=exclude_none)

    def get_risk_category(self, thresholds: RiskScoreThresholds) -> RiskCategory:
        """
        Get the risk category based on temporal risk score.

        Risk Score Thresholds:
        - Critical: 75-100 (immediate investigation required)
        - High: 50-74 (priority review needed)
        - Medium: 25-49 (monitoring recommended)
        - Low: 0-24 (normal behavior)

        Args:
            thresholds: Risk score threshold configuration.

        Returns:
            Risk category: 'Critical', 'High', 'Medium', or 'Low'
        """
        return categorize_risk_score(self.risk_score, thresholds)

    def has_change_points(self) -> bool:
        """
        Check if any change points were detected (single or multiple).

        Returns:
            True if change points exist in either change_points or multiple_change_points
        """
        result: bool = False
        if self.change_points and len(self.change_points) > 0:
            result = True
        if self.multiple_change_points and len(self.multiple_change_points) > 0:
            result = True
        return result

    def has_risk_indicators(self) -> bool:
        """
        Check if any concerning trends were detected.

        Returns:
            True if risk_indicators list contains any items
        """
        return len(self.risk_indicators) > 0

    def get_change_point_count(self) -> int:
        """
        Get the total number of detected change points across all metrics.

        This includes both single change points and all multiple change points.

        Returns:
            Total count of change points detected
        """
        single_count: int = 0
        multiple_count: int = 0
        if self.change_points:
            single_count = len(self.change_points)
        if self.multiple_change_points:
            multiple_count = sum(
                len(cp_list) for cp_list in self.multiple_change_points.values()
            )
        return single_count + multiple_count

    def get_earliest_change_point(self) -> str | None:
        """
        Get the earliest change point date across all metrics.

        Searches both single change points and multiple change points to find
        the earliest date when behavioral change was detected.

        Returns:
            Date string of earliest change point (YYYY-MM format), or None if no change points
        """
        all_dates: list[str] = []

        # Add single change points
        if self.change_points:
            all_dates.extend(self.change_points.values())

        # Add all multiple change points
        if self.multiple_change_points:
            for cp_list in self.multiple_change_points.values():
                all_dates.extend(cp_list)

        if not all_dates:
            return None

        return min(all_dates)

    def has_fraud_patterns(self) -> bool:
        """
        Check if any specific fraud patterns were detected.

        Returns:
            True if any fraud pattern flag is True
        """
        return any(self.fraud_patterns.values())

    def get_detected_fraud_patterns(self) -> list[str]:
        """
        Get list of detected fraud pattern names.

        Returns:
            list of fraud pattern names that were detected (flagged as True)
            Example: ['weekend_warrior', 'pump_and_dump']
        """
        return [
            pattern for pattern, detected in self.fraud_patterns.items() if detected
        ]

    def has_sudden_spikes(self) -> bool:
        """
        Check if any sudden month-over-month spikes were detected.

        Returns:
            True if sudden_spikes list in month_over_month is non-empty
        """
        return bool(self.month_over_month.get('sudden_spikes', []))

    def has_gradual_escalation(self) -> bool:
        """
        Check if any gradual escalation patterns were detected.

        Returns:
            True if gradual_escalation list in month_over_month is non-empty
        """
        return bool(self.month_over_month.get('gradual_escalation', []))

    def has_persistent_patterns(self) -> bool:
        """
        Check if any metrics show high autocorrelation (persistent bad behavior).

        Returns:
            True if any metric has risk_level of 'HIGH' in autocorrelation analysis
        """
        return any(
            data.get('risk_level') == 'HIGH' for data in self.autocorrelation.values()
        )

    def get_volatility_score(self) -> float:
        """
        Get the month-over-month volatility score.

        Higher values indicate more erratic behavior changes.

        Returns:
            Volatility score, or 0.0 if not available
        """
        return self.month_over_month.get('volatility_score', 0.0)

    def get_current_risk_factor_count(self) -> int:
        """
        Get the count of risk factors present in the most recent month.

        Returns:
            Number of current risk factors
        """
        return len(self.current_risk_factors)

    def has_current_risks(self) -> bool:
        """
        Check if there are any risk factors in the most recent month.

        This is particularly important because it shows whether risky
        behavior is ongoing rather than historical.

        Returns:
            True if current_risk_factors list is non-empty
        """
        return len(self.current_risk_factors) > 0

    def get_risk_summary(self, thresholds: RiskScoreThresholds) -> dict[str, Any]:
        """
        Get a comprehensive summary of all risk factors.

        Args:
            thresholds: Risk score threshold configuration.

        Returns:
            dictionary with categorized risk information including:
            - risk_category: Overall risk level
            - risk_score: Numeric score
            - has_change_points: Boolean
            - change_point_count: Integer
            - fraud_patterns_detected: list of pattern names
            - has_sudden_spikes: Boolean
            - has_persistent_patterns: Boolean
            - current_risks: Boolean
            - volatility: Float
        """
        return {
            'risk_category': self.get_risk_category(thresholds),
            'risk_score': self.risk_score,
            'has_change_points': self.has_change_points(),
            'change_point_count': self.get_change_point_count(),
            'fraud_patterns_detected': self.get_detected_fraud_patterns(),
            'has_sudden_spikes': self.has_sudden_spikes(),
            'has_persistent_patterns': self.has_persistent_patterns(),
            'current_risks': self.has_current_risks(),
            'volatility': self.get_volatility_score(),
        }

    def get_analysis_flags(self) -> list[str]:
        """
        Get a list of all active analysis flags for quick scanning.

        This provides a high-level overview of what types of suspicious
        behavior were detected, useful for reporting and prioritization.

        Returns:
            list of flag descriptions
            Example: ['FRAUD_PATTERNS', 'SUDDEN_SPIKES', 'PERSISTENT_BEHAVIOR', 'CURRENT_RISKS']
        """
        flags: list[str] = []

        if self.has_fraud_patterns():
            flags.append('FRAUD_PATTERNS')

        if self.has_change_points():
            flags.append('BEHAVIORAL_CHANGES')

        if self.has_sudden_spikes():
            flags.append('SUDDEN_SPIKES')

        if self.has_gradual_escalation():
            flags.append('GRADUAL_ESCALATION')

        if self.has_persistent_patterns():
            flags.append('PERSISTENT_BEHAVIOR')

        if self.has_current_risks():
            flags.append('CURRENT_RISKS')

        if self.get_volatility_score() > 1.0:
            flags.append('HIGH_VOLATILITY')

        return flags

    def format_brief_summary(self, thresholds: RiskScoreThresholds) -> str:
        """
        Generate a brief one-line summary of the temporal analysis.

        Useful for reports, logs, and quick scanning of multiple entities.

        Returns:
            Formatted string with key information
            Example: "Driver-12345 | Critical Risk (Score: 87) | 3 fraud patterns | 5 change points | ACTIVE"
        """
        active_status: Literal['ACTIVE RISKS'] | Literal['Historical'] = (
            'ACTIVE RISKS' if self.has_current_risks() else 'Historical'
        )
        fraud_count: int = len(self.get_detected_fraud_patterns())

        summary_parts: list[str] = [
            f'{self.entity_type}-{self.display_id}',
            f'{self.get_risk_category(thresholds)} Risk (Score: {self.risk_score})',
        ]

        if fraud_count > 0:
            summary_parts.append(f'{fraud_count} fraud patterns')

        change_count: int = self.get_change_point_count()
        if change_count > 0:
            summary_parts.append(f'{change_count} change points')

        summary_parts.append(active_status)

        return ' | '.join(summary_parts)

    def __repr__(self) -> str:
        """
        String representation showing key temporal analysis information.

        Returns:
            Formatted string for debugging and logging
        """
        flags: str = (
            ', '.join(self.get_analysis_flags())
            if self.get_analysis_flags()
            else 'None'
        )

        return (
            f"TemporalRiskProfile(id='{self.display_id}', "
            f"type='{self.entity_type}', "
            f'risk_score={self.risk_score}, '
            f'months_active={self.months_active}, '
            f'change_points={self.get_change_point_count()}, '
            f'flags=[{flags}])'
        )
