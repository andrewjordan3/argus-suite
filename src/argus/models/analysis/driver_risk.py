# argus/models/analysis/driver_risk.py
"""
Driver Risk Profile model for the Argus analysis pipeline.
This module defines a Pydantic model to encapsulate driver risk assessment
data, including risk scores and key indicators.
"""
import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from argus.models.config import RiskCategory, RiskScoreThresholds
from argus.utils import categorize_risk_score, check_rate_exceeds_threshold

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)

class DriverRiskProfile(BaseModel):
    """
    Container for driver risk analysis.

    This model stores risk assessment information for an individual driver,
    including their risk score, transaction patterns, and key risk indicators.

    Attributes:
        driver_name: Full name of the driver
        risk_score: Overall risk score (0-100 scale)
        transaction_count: Total number of transactions
        no_eld_rate: Proportion of transactions without ELD match (0-1)
        non_diesel_rate: Proportion of non-diesel/DEF purchases (0-1)
        after_hours_rate: Proportion of transactions outside business hours (0-1)
        avg_cost: Average cost per transaction
        total_cost: Total cost across all transactions
        total_volume: Total volume (gallons) across all transactions
        volume_z_score: Z-score of volume relative to peer group
        rank: Optional rank among all drivers (1 = highest risk)
    """

    model_config = ConfigDict(extra='forbid')

    driver_name: str = Field(..., description='Full name of the driver', min_length=1)
    risk_score: float = Field(
        ...,
        description='Overall risk score (0-100 scale)',
        ge=0.0,
        le=100.0,
    )
    transaction_count: int = Field(
        ...,
        description='Total number of transactions',
        ge=0,
    )
    no_eld_rate: float = Field(
        ...,
        description='Proportion of transactions without ELD match (0-1)',
        ge=0.0,
        le=1.0,
    )
    non_diesel_rate: float = Field(
        ...,
        description='Proportion of non-diesel/DEF purchases (0-1)',
        ge=0.0,
        le=1.0,
    )
    after_hours_rate: float = Field(
        ...,
        description='Proportion of transactions outside business hours (0-1)',
        ge=0.0,
        le=1.0,
    )
    avg_cost: float = Field(
        ...,
        description='Average cost per transaction',
        ge=0.0,
    )
    total_cost: float = Field(
        ...,
        description='Total cost across all transactions',
        ge=0.0,
    )
    total_volume: float = Field(
        default=0.0,
        description='Total volume (gallons) across all transactions',
        ge=0.0,
    )
    volume_z_score: float = Field(
        default=0.0,
        description='Z-score of volume relative to peer group',
    )
    rank: int | None = Field(
        default=None,
        description='Optional rank among all drivers (1 = highest risk)',
        ge=1,
    )

    def to_dict(self, exclude_none: bool = False) -> dict[str, Any]:
        """
        Convert the profile to a dictionary for serialization.

        Args:
            exclude_none: If True, exclude fields with None values.

        Returns:
            Dictionary representation of the model.
        """
        return self.model_dump(exclude_none=exclude_none)

    def get_risk_category(self, thresholds: RiskScoreThresholds) -> RiskCategory:
        """
        Get the risk category based on risk score.

        Args:
            thresholds: Risk score threshold configuration.

        Returns:
            Risk category: 'Critical', 'High', 'Medium', or 'Low'
        """
        return categorize_risk_score(self.risk_score, thresholds)

    def has_high_no_eld(self, threshold: float) -> bool:
        """
        Check if driver has high rate of transactions without ELD match.

        Args:
            threshold: Minimum rate to be considered high (from config).

        Returns:
            True if no_eld_rate exceeds threshold.
        """
        return check_rate_exceeds_threshold(self.no_eld_rate, threshold)

    def has_high_non_diesel(self, threshold: float) -> bool:
        """
        Check if driver has high rate of non-diesel purchases.

        Args:
            threshold: Minimum rate to be considered high (from config).

        Returns:
            True if non_diesel_rate exceeds threshold.
        """
        return check_rate_exceeds_threshold(self.non_diesel_rate, threshold)

    def has_high_after_hours(self, threshold: float) -> bool:
        """
        Check if driver has high rate of after-hours transactions.

        Args:
            threshold: Minimum rate to be considered high (from config).

        Returns:
            True if after_hours_rate exceeds threshold.
        """
        return check_rate_exceeds_threshold(self.after_hours_rate, threshold)

    def __repr__(self) -> str:
        """String representation showing key driver information."""
        return (
            f"DriverRiskProfile(name='{self.driver_name}', "
            f'risk_score={self.risk_score:.1f}, '
            f'transactions={self.transaction_count}, '
            f'volume={self.total_volume:.1f}, '
        )
