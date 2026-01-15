# argus/models/analysis/driver_risk.py
"""
Driver Risk Profile Model for ARGUS Analysis Pipeline.

This module defines the DriverRiskProfile model, a pure data container that
encapsulates risk assessment results for an individual driver. The model
stores statistical outputs from the driver risk analysis pipeline, including
composite risk scores, behavioral rate metrics, and transaction statistics.

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
    >>> from argus.models.analysis.driver_risk import DriverRiskProfile
    >>>
    >>> profile = DriverRiskProfile(
    ...     driver_name='John Smith',
    ...     risk_score=72.5,
    ...     transaction_count=156,
    ...     no_eld_rate=0.23,
    ...     non_diesel_rate=0.05,
    ...     after_hours_rate=0.18,
    ...     avg_cost=87.50,
    ...     total_cost=13650.00,
    ...     total_volume=3420.5,
    ...     volume_z_score=1.85,
    ...     rank=3,
    ... )
    >>>
    >>> # Access fields directly
    >>> profile.risk_score
    72.5
    >>> profile.no_eld_rate
    0.23

See Also:
    - argus.models.analysis.temporal_risk: Time-series risk analysis results
    - argus.models.analysis.statistical_test: Individual statistical test results
    - argus.services.risk_categorization: Service for interpreting risk scores
"""

import math
from typing import Self

from pydantic import Field, model_validator

from argus.models.common import FrozenModel

__all__: list[str] = [
    'DriverRiskProfile',
]


# -----------------------------------------------------------------------------
# Validation Tolerances
# -----------------------------------------------------------------------------
# These module-level constants define the tolerances used in model validators.
# Centralizing them here makes the validation logic clearer and allows easy
# adjustment if upstream data sources have different precision characteristics.
# -----------------------------------------------------------------------------

# Absolute tolerance for "close to zero" checks on monetary values.
# Accounts for floating-point representation of values like $0.00.
_COST_ZERO_TOLERANCE: float = 0.01  # $0.01

# Absolute tolerance for "close to zero" checks on volume values.
# Accounts for floating-point representation of values like 0.00 gallons.
_VOLUME_ZERO_TOLERANCE: float = 0.01  # 0.01 gallons

# Relative tolerance for average cost consistency checks.
# Allows 1% deviation to accommodate floating-point arithmetic and
# rounding differences from upstream data processing systems.
_AVG_COST_RELATIVE_TOLERANCE: float = 0.01  # 1%


class DriverRiskProfile(FrozenModel):
    """
    Container for driver risk analysis results.

    This model stores risk assessment information for an individual driver,
    computed by the ARGUS driver analysis pipeline. All values represent
    raw statistical outputs with no policy interpretation applied.

    The risk score is a composite metric (0-100 scale) derived from multiple
    behavioral indicators. Individual rate metrics capture specific patterns
    that may indicate fraud, policy violations, or anomalous behavior.

    Attributes:
        driver_name: Full name of the driver as recorded in the source system.
            Used as the primary human-readable identifier in reports and logs.

        risk_score: Composite risk score on a 0-100 scale, where higher values
            indicate greater risk. This score is computed from weighted
            contributions of individual risk factors (ELD compliance, purchase
            patterns, timing anomalies, volume deviations). The weighting
            methodology is defined in the analysis configuration, not here.

        transaction_count: Total number of fuel transactions analyzed for this
            driver during the analysis period. Higher counts provide more
            statistical confidence in the rate metrics.

        no_eld_rate: Proportion of transactions (0.0 to 1.0) that could not be
            matched to Electronic Logging Device (ELD) telemetry data. High
            values may indicate fuel purchases made without corresponding
            vehicle activity, a common fraud indicator.

        non_diesel_rate: Proportion of transactions (0.0 to 1.0) for products
            other than diesel fuel or Diesel Exhaust Fluid (DEF). For fleet
            vehicles that should only purchase diesel/DEF, elevated non-diesel
            rates may indicate personal use or unauthorized purchases.

        after_hours_rate: Proportion of transactions (0.0 to 1.0) occurring
            outside defined business hours. The definition of "business hours"
            is a policy setting; this field stores only the computed rate.
            High values may indicate unauthorized vehicle use.

        avg_cost: Mean cost per transaction in USD. Useful for identifying
            drivers with unusually high per-transaction spending compared to
            peers operating similar routes or vehicles.

        total_cost: Sum of all transaction costs in USD for the analysis period.
            Combined with transaction_count, provides context for avg_cost and
            enables fleet-wide cost attribution analysis.

        total_volume: Total fuel volume in gallons across all transactions for
            the analysis period. Volume metrics help identify discrepancies
            between fuel purchases and expected consumption based on mileage.

        volume_z_score: Standard score (z-score) of this driver's total volume
            relative to their peer group. Positive values indicate above-average
            volume; negative values indicate below-average. Values beyond ±2.0
            are typically considered statistical outliers. The peer group
            definition is a configuration concern, not stored here.

        rank: Position in the risk-ordered list of all analyzed drivers, where
            1 indicates the highest-risk driver. None if ranking has not been
            performed or if this profile was analyzed in isolation.

    Invariants:
        - All rate fields are proportions in the closed interval [0.0, 1.0]
        - Cost and volume fields are non-negative
        - Risk score is bounded to [0.0, 100.0]
        - Rank, if present, is a positive integer (1-indexed)
        - If transaction_count is 0, cost fields should be 0.0

    Example:
        >>> profile = DriverRiskProfile(
        ...     driver_name='Jane Doe',
        ...     risk_score=45.2,
        ...     transaction_count=89,
        ...     no_eld_rate=0.12,
        ...     non_diesel_rate=0.02,
        ...     after_hours_rate=0.08,
        ...     avg_cost=92.30,
        ...     total_cost=8214.70,
        ...     total_volume=2105.8,
        ...     volume_z_score=-0.34,
        ...     rank=15,
        ... )
        >>> print(profile)
        DriverRiskProfile('Jane Doe', score=45.2, rank=#15, txns=89)
    """

    # -------------------------------------------------------------------------
    # Driver Identification
    # -------------------------------------------------------------------------

    driver_name: str = Field(
        ...,
        description='Full name of the driver as recorded in source system',
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
    # These proportions capture specific behavioral patterns that may indicate
    # fraud, policy violations, or anomalous activity. All are in [0.0, 1.0].
    # -------------------------------------------------------------------------

    no_eld_rate: float = Field(
        ...,
        description='Proportion of transactions without ELD telemetry match (0-1)',
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
    # Volume Metrics
    # -------------------------------------------------------------------------

    total_volume: float = Field(
        default=0.0,
        description='Total fuel volume in gallons across all transactions',
        ge=0.0,
    )

    volume_z_score: float = Field(
        default=0.0,
        description='Z-score of volume relative to peer group (0 = average)',
    )

    # -------------------------------------------------------------------------
    # Ranking
    # -------------------------------------------------------------------------

    rank: int | None = Field(
        default=None,
        description='Risk rank among all drivers (1 = highest risk), None if unranked',
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
        costs might be erroneously populated for drivers with no activity.

        Uses math.isclose() with an absolute tolerance to handle floating-point
        representation of zero values.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If transaction_count is 0 but total_cost is non-zero.
        """
        if self.transaction_count == 0 and not math.isclose(
            self.total_cost, 0.0, abs_tol=_COST_ZERO_TOLERANCE
        ):
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

    @model_validator(mode='after')
    def validate_volume_consistency(self) -> Self:
        """
        Validate that volume totals are consistent with transaction count.

        Enforces the invariant that if there are no transactions, total volume
        should be approximately zero. This catches data pipeline errors where
        volume might be erroneously populated for drivers with no activity.

        Uses math.isclose() with an absolute tolerance to handle floating-point
        representation of zero values.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If transaction_count is 0 but total_volume is non-zero.
        """
        if self.transaction_count == 0 and not math.isclose(
            self.total_volume, 0.0, abs_tol=_VOLUME_ZERO_TOLERANCE
        ):
            raise ValueError(
                f'Inconsistent data: transaction_count is 0 but total_volume '
                f'is {self.total_volume:.2f} gallons. Expected total_volume ≈ 0.0 '
                f'when there are no transactions.'
            )

        return self

    # -------------------------------------------------------------------------
    # String Representation
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        """
        Return a compact string representation for debugging and logging.

        Shows the most important fields for quick identification and risk
        assessment: driver name, risk score, rank, and transaction count.
        The full model can be inspected via model_dump() if needed.

        Returns:
            Compact string suitable for logs and REPL inspection.

        Example:
            >>> repr(profile)
            "DriverRiskProfile('John Smith', score=72.5, rank=#3, txns=156)"
        """
        # Format rank as "#N" or "unranked" for clarity
        rank_display: str = f'#{self.rank}' if self.rank is not None else 'unranked'

        return (
            f"DriverRiskProfile('{self.driver_name}', "
            f'score={self.risk_score:.1f}, '
            f'rank={rank_display}, '
            f'txns={self.transaction_count})'
        )
