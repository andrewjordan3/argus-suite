# argus/models/policy/data_requirements.py
"""
This module defines configuration models for data requirements used in ARGUS policies. It includes
settings for minimum data quality and quantity needed for analyses.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__: list[str] = ['DataRequirementsConfig']


class DataRequirementsConfig(BaseModel):
    """
    Configuration for data requirements in ARGUS policies.

    This configuration defines the minimum data quality and quantity
    requirements that must be met for analyses to be considered valid.

    Attributes:
        monthend_threshold: Days from month-end to consider a month's data complete.
        min_transactions_risk: Minimum transactions required to calculate a risk score for an entity.
        min_transactions_temporal: Minimum transactions required for temporal/trend analysis.
        min_months_temporal: Minimum months of activity required for temporal analysis.
        min_months_current_year: Minimum current-year months before splitting analysis periods.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    monthend_threshold: int = Field(
        default=5,
        description="Days from month-end to consider a month's data complete.",
        ge=0,
        le=31,
    )
    min_transactions_risk: int = Field(
        default=10,
        description='Minimum transactions required to calculate a risk score for an entity.',
        ge=1,
    )

    min_transactions_temporal: int = Field(
        default=20,
        description='Minimum transactions required for temporal/trend analysis.',
        ge=1,
    )
    min_months_temporal: int = Field(
        default=3,
        description='Minimum months of activity required for temporal analysis.',
        ge=1,
        le=12,
    )
    min_months_current_year: int = Field(
        default=3,
        description='Minimum current-year months before splitting analysis periods.',
        ge=0,
        le=12,
    )

    @model_validator(mode='after')
    def validate_transaction_thresholds(self) -> Self:
        """
        Ensure temporal analysis requires at least as many transactions as risk scoring.

        Temporal/trend analysis is inherently more demanding than point-in-time risk
        scoring—detecting patterns over time requires sufficient data density per period.
        Allowing fewer transactions for temporal analysis than for basic risk scoring
        would produce unreliable trend conclusions.

        Returns:
            Self, if validation passes.

        Raises:
            ValueError: If min_transactions_temporal < min_transactions_risk.
        """
        if self.min_transactions_temporal < self.min_transactions_risk:
            raise ValueError(
                'Temporal analysis requires at least as many transactions as risk scoring: '
                f'{self.min_transactions_temporal=} must be >= {self.min_transactions_risk=}.'
            )
        return self
