# argus/models/analysis/vehicle_risk.py
"""
Vehicle Risk Profile model definition.
This module defines the data model used to encapsulate risk assessment
information for individual vehicles within the Argus analytics framework.
"""


import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from argus.models.config import RiskCategory, RiskScoreThresholds
from argus.utils import (
    categorize_risk_score,
    check_rate_exceeds_threshold,
)

__all__: list[str] = ['VehicleRiskProfile']

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)

class VehicleRiskProfile(BaseModel):
    """
    Container for vehicle risk analysis.

    This model stores risk assessment information for an individual vehicle,
    including its risk score, transaction patterns, and primary driver.

    Attributes:
        vin: Vehicle Identification Number
        primary_driver: Name of the primary driver for this vehicle
        risk_score: Overall risk score (0-100 scale)
        transaction_count: Total number of transactions
        no_eld_rate: Proportion of transactions without ELD match (0-1)
        avg_cost: Average cost per transaction
        total_cost: Total cost across all transactions
        rank: Optional rank among all vehicles (1 = highest risk)
    """

    model_config = ConfigDict(extra='forbid')

    vin: str = Field(..., description='Vehicle Identification Number', min_length=1)
    primary_driver: str = Field(
        ...,
        description='Name of the primary driver for this vehicle',
        min_length=1,
    )
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
    rank: int | None = Field(
        default=None,
        description='Optional rank among all vehicles (1 = highest risk)',
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

    def __repr__(self) -> str:
        """String representation showing key vehicle information."""
        return (
            f"VehicleRiskProfile(vin='{self.vin}', "
            f"driver='{self.primary_driver}', "
            f'risk_score={self.risk_score:.1f}, '
            f'transactions={self.transaction_count}, '
        )
