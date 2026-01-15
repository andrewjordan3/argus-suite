# argus/models/policy/risk_weights.py
"""
This module defines the RiskWeightsConfig model for driver risk score
calculation in the Argus fuel card forensics analysis package.
"""

import math
from typing import Self

from pydantic import Field, model_validator

from argus.models.common import FrozenModel

__all__: list[str] = ['RiskWeightsConfig']


# =============================================================================
# RISK WEIGHTS CONFIGURATION
# =============================================================================
class RiskWeightsConfig(FrozenModel):
    """
    Weights contributing to the composite driver risk score.

    These weights determine the relative importance of each risk factor when
    calculating the final 0-100 risk score for a driver. The sum of all
    weights must equal exactly 1.0.

    Attributes:
        no_eld_match: Weight for transactions lacking ELD verification.
        non_diesel: Weight for non-diesel product purchases.
        after_hours: Weight for transactions outside business hours.
        high_cost: Weight for elevated transaction costs.
    """

    no_eld_match: float = Field(
        default=0.30,
        description='Weight for transactions without ELD verification',
        ge=0.0,
        le=1.0,
    )

    non_diesel: float = Field(
        default=0.25,
        description='Weight for non-diesel purchases (unusual for fleet)',
        ge=0.0,
        le=1.0,
    )

    after_hours: float = Field(
        default=0.25,
        description='Weight for transactions outside business hours',
        ge=0.0,
        le=1.0,
    )

    high_cost: float = Field(
        default=0.20,
        description='Weight for elevated transaction costs',
        ge=0.0,
        le=1.0,
    )

    @model_validator(mode='after')
    def validate_weights_sum_to_unity(self) -> Self:
        """
        Validate that the risk weights sum to 1.0.

        Raises:
            ValueError: If the sum of weights is not 1.0.
        """
        total_weight: float = (
            self.no_eld_match + self.non_diesel + self.after_hours + self.high_cost
        )

        # Use epsilon for floating point comparison
        if not math.isclose(total_weight, 1.0, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(
                f'Driver risk score weights must sum to 1.0. '
                f'Current sum: {total_weight:.4f} '
                f'(no_eld_match={self.no_eld_match}, non_diesel={self.non_diesel}, '
                f'after_hours={self.after_hours}, high_cost={self.high_cost})'
            )

        return self
