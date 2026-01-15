# argus/models/analysis/vehicle_risk.py
"""
Vehicle Risk Profile Model for ARGUS Analysis Pipeline.

This module defines the VehicleRiskProfile model, a pure data container that
encapsulates risk assessment results for an individual vehicle. The model
stores statistical outputs from the vehicle risk analysis pipeline, including
composite risk scores, behavioral metrics, and transaction statistics.

Design Philosophy:
    This model follows the ARGUS principle of separating data from policy.
    It contains only raw statistical outputs—no methods that depend on
    configuration thresholds, locale settings, or presentation formatting.
    Interpretation of these values (e.g., categorizing risk levels, generating
    reports) belongs in service/processor layers that receive both this model
    and the relevant configuration.

Immutability:
    Instances are frozen after creation. Risk assessment results represent
    a point-in-time computation and should not be modified. If values need
    updating (e.g., after re-ranking), create a new instance.

Usage:
    >>> from argus.models.analysis.vehicle_risk import VehicleRiskProfile
    >>>
    >>> profile = VehicleRiskProfile(
    ...     vin='1HGCM82633A004352',
    ...     primary_driver='John Smith',
    ...     risk_score=65.2,
    ...     transaction_count=89,
    ...     no_eld_rate=0.18,
    ...     avg_cost=94.50,
    ...     total_cost=8410.50,
    ...     rank=7,
    ... )
    >>>
    >>> profile.risk_score
    65.2

See Also:
    - argus.models.analysis.driver_risk: Driver-level risk profiles
    - argus.models.analysis.temporal_risk: Time-series risk analysis results
    - argus.services.risk_categorization: Service for interpreting risk scores
"""

import math
from typing import Self

from pydantic import Field, model_validator

from argus.models.common.base import FrozenModel

__all__: list[str] = [
    'VehicleRiskProfile',
]


# -----------------------------------------------------------------------------
# Validation Tolerances
# -----------------------------------------------------------------------------
# Module-level constants for validation tolerances. Centralizing these makes
# the validation logic clearer and allows adjustment if needed.
# -----------------------------------------------------------------------------

# Absolute tolerance for "close to zero" checks on monetary values.
# Accounts for floating-point representation of values like $0.00.
_COST_ZERO_TOLERANCE: float = 0.01  # $0.01

# Relative tolerance for average cost consistency checks.
# Allows 1% deviation to accommodate floating-point arithmetic and
# rounding differences from upstream data processing systems.
_AVG_COST_RELATIVE_TOLERANCE: float = 0.01  # 1%


class VehicleRiskProfile(FrozenModel):
    """
    Container for vehicle risk analysis results.

    This model stores risk assessment information for an individual vehicle,
    computed by the ARGUS vehicle analysis pipeline. All values represent
    raw statistical outputs with no policy interpretation applied.

    The risk score is a composite metric (0-100 scale) derived from multiple
    factors including ELD compliance rates, transaction patterns, and
    cost anomalies associated with the vehicle.

    Attributes:
        vin: Vehicle Identification Number. The unique identifier for the
            vehicle as recorded in fleet management systems. Used as the
            primary key for vehicle-level analysis.

        primary_driver: Full name of the driver most frequently associated
            with this vehicle during the analysis period. Determined by
            transaction attribution in the source data. Useful for
            cross-referencing with driver-level risk profiles.

        risk_score: Composite risk score on a 0-100 scale, where higher values
            indicate greater risk. This score is computed from weighted
            contributions of vehicle-specific risk factors. The weighting
            methodology is defined in the analysis configuration, not here.

        transaction_count: Total number of fuel transactions associated with
            this vehicle during the analysis period. Higher counts provide
            more statistical confidence in the rate and average metrics.

        no_eld_rate: Proportion of transactions (0.0 to 1.0) that could not be
            matched to Electronic Logging Device (ELD) telemetry data for this
            vehicle. High values may indicate fuel purchases made without
            corresponding vehicle activity, a common fraud indicator.

        avg_cost: Mean cost per transaction in USD for this vehicle. Useful
            for identifying vehicles with unusually high per-transaction
            spending compared to similar vehicles in the fleet.

        total_cost: Sum of all transaction costs in USD for the analysis period.
            Combined with transaction_count, provides context for avg_cost and
            enables fleet-wide cost attribution analysis.

        rank: Position in the risk-ordered list of all analyzed vehicles, where
            1 indicates the highest-risk vehicle. None if ranking has not been
            performed or if this profile was analyzed in isolation.

    Invariants:
        - no_eld_rate is a proportion in the closed interval [0.0, 1.0]
        - Cost fields are non-negative
        - Risk score is bounded to [0.0, 100.0]
        - Rank, if present, is a positive integer (1-indexed)
        - If transaction_count is 0, total_cost should be ≈ 0.0
        - avg_cost should equal total_cost / transaction_count (within tolerance)

    Example:
        >>> profile = VehicleRiskProfile(
        ...     vin='1HGCM82633A004352',
        ...     primary_driver='Jane Doe',
        ...     risk_score=45.2,
        ...     transaction_count=67,
        ...     no_eld_rate=0.09,
        ...     avg_cost=88.75,
        ...     total_cost=5946.25,
        ...     rank=12,
        ... )
        >>> print(profile)
        VehicleRiskProfile('1HGCM82633A004352', score=45.2, rank=#12, txns=67)
    """

    # -------------------------------------------------------------------------
    # Vehicle Identification
    # -------------------------------------------------------------------------

    vin: str = Field(
        ...,
        description='Vehicle Identification Number',
        min_length=1,
    )

    primary_driver: str = Field(
        ...,
        description='Name of the driver most frequently associated with this vehicle',
        min_length=1,
    )

    # -------------------------------------------------------------------------
    # Composite Risk Assessment
    # -------------------------------------------------------------------------

    risk_score: float = Field(
        ...,
        description='Composite risk score (0-100 scale, higher = greater risk)',
        ge=0.0,
        le=100.0,
    )

    # -------------------------------------------------------------------------
    # Transaction Volume Metrics
    # -------------------------------------------------------------------------

    transaction_count: int = Field(
        ...,
        description='Total number of transactions analyzed',
        ge=0,
    )

    # -------------------------------------------------------------------------
    # Behavioral Rate Indicators
    # -------------------------------------------------------------------------

    no_eld_rate: float = Field(
        ...,
        description='Proportion of transactions without ELD telemetry match (0-1)',
        ge=0.0,
        le=1.0,
    )

    # -------------------------------------------------------------------------
    # Cost Metrics
    # -------------------------------------------------------------------------

    avg_cost: float = Field(
        ...,
        description='Mean cost per transaction in USD',
        ge=0.0,
    )

    total_cost: float = Field(
        ...,
        description='Sum of all transaction costs in USD',
        ge=0.0,
    )

    # -------------------------------------------------------------------------
    # Ranking
    # -------------------------------------------------------------------------

    rank: int | None = Field(
        default=None,
        description='Risk rank among all vehicles (1 = highest risk), None if unranked',
        ge=1,
    )

    # -------------------------------------------------------------------------
    # Model Validators
    # -------------------------------------------------------------------------

    @model_validator(mode='after')
    def validate_cost_consistency(self) -> Self:
        """
        Validate that cost totals are consistent with transaction count.

        Enforces the invariant that if there are no transactions, total cost
        should be approximately zero. This catches data pipeline errors where
        costs might be erroneously populated for vehicles with no activity.

        Uses math.isclose() with an absolute tolerance to handle floating-point
        representation of zero values.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If transaction_count is 0 but total_cost is non-zero.
        """
        if self.transaction_count == 0 and not math.isclose(self.total_cost, 0.0, abs_tol=_COST_ZERO_TOLERANCE):
                raise ValueError(
                    f'Inconsistent data: transaction_count is 0 but total_cost '
                    f'is ${self.total_cost:.2f}. Expected total_cost ≈ $0.00 when '
                    f'there are no transactions.'
                )

        return self

    @model_validator(mode='after')
    def validate_average_cost_consistency(self) -> Self:
        """
        Validate that average cost is consistent with total cost and count.

        When transaction_count > 0, verifies that avg_cost approximately equals
        total_cost / transaction_count. This catches data pipeline errors where
        averages might be computed incorrectly or from mismatched data sources.

        Uses math.isclose() with a relative tolerance to handle the comparison
        of potentially large monetary values where absolute differences may be
        acceptable if proportionally small.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If avg_cost deviates significantly from expected value.
        """
        # Skip validation when there are no transactions (division by zero)
        if self.transaction_count == 0:
            return self

        # Skip validation if both values are zero (valid edge case)
        if math.isclose(
            self.avg_cost, 0.0, abs_tol=_COST_ZERO_TOLERANCE
        ) and math.isclose(self.total_cost, 0.0, abs_tol=_COST_ZERO_TOLERANCE):
            return self

        expected_avg: float = self.total_cost / self.transaction_count

        if not math.isclose(
            self.avg_cost,
            expected_avg,
            rel_tol=_AVG_COST_RELATIVE_TOLERANCE,
        ):
            raise ValueError(
                f'Inconsistent cost data: avg_cost (${self.avg_cost:.2f}) does not '
                f'match total_cost / transaction_count '
                f'(${self.total_cost:.2f} / {self.transaction_count} = ${expected_avg:.2f}). '
                f'Values must be within {_AVG_COST_RELATIVE_TOLERANCE:.0%} relative tolerance.'
            )

        return self

    # -------------------------------------------------------------------------
    # String Representation
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        """
        Return a compact string representation for debugging and logging.

        Shows the most important fields for quick identification: VIN,
        risk score, rank, and transaction count. The full model can be
        inspected via model_dump() if needed.

        Returns:
            Compact string suitable for logs and REPL inspection.

        Example:
            >>> repr(profile)
            "VehicleRiskProfile('1HGCM82633A004352', score=65.2, rank=#7, txns=89)"
        """
        rank_display: str = f'#{self.rank}' if self.rank is not None else 'unranked'

        return (
            f"VehicleRiskProfile('{self.vin}', "
            f'score={self.risk_score:.1f}, '
            f'rank={rank_display}, '
            f'txns={self.transaction_count})'
        )
