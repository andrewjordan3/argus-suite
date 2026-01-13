# argus/models/policy/red_flag_weights.py
"""
This module defines the RedFlagWeightsConfig model for red flag score
calculation in the Argus fuel card forensics analysis package. It includes
individual weights for various red flag indicators as well as multipliers for
passenger vehicle and card misuse indicators.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__: list[str] = ['IndividualFlagWeightConfig', 'RedFlagWeightsConfig']


class IndividualFlagWeightConfig(BaseModel):
    """
    Weights contributing to individual red flag indicators.

    These can be customized if certain flags are more/less concerning
    for your organization. Default: all flags equal weight of 1.0.

    Attributes:
        low_cost: Weight for transaction amounts below fleet norms.
        low_volume: Weight for low volume fuel purchases.
        non_diesel: Weight for frequent non-diesel product purchases.
        multiple_fillups: Weight for multiple fill-ups in the same day.
        multiple_stations: Weight for purchases at multiple stations on the same day.
        no_eld_match: Weight for transactions without ELD verification.
        rapid_succession: Weight for transactions in rapid succession.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    # Passenger Vehicle Indicators
    low_cost: float = Field(
        default=1.0,
        description='Weight for transaction amounts below fleet norms.',
        ge=0.0,
    )

    low_volume: float = Field(
        default=1.0,
        description='Weight for low volume fuel purchases',
        ge=0.0,
    )

    non_diesel: float = Field(
        default=1.0,
        description='Weight for frequent non-diesel product purchases',
        ge=0.0,
    )

    # Card Misuse Indicators
    multiple_fillups: float = Field(
        default=1.0,
        description='Weight for multiple fill-ups in the same day.',
        ge=0.0,
    )

    multiple_stations: float = Field(
        default=1.0,
        description='Weight for purchases at multiple stations on the same day.',
        ge=0.0,
    )

    no_eld_match: float = Field(
        default=1.0,
        description='Weight for transactions without ELD verification',
        ge=0.0,
    )

    rapid_succession: float = Field(
        default=1.0,
        description='Weight for transactions in rapid succession',
        ge=0.0,
    )


# =============================================================================
# RED FLAG WEIGHTS CONFIGURATION
# =============================================================================
class RedFlagWeightsConfig(BaseModel):
    """
    Weights contributing to the composite red flag score.

    These weights determine the relative importance of each red flag factor
    when calculating the final 0-100 red flag score for a driver. The sum of
    all weights must equal exactly 1.0.

    The suspicion score formula:
        Score = (Passenger vehicle indicators * passenger_vehicle_multiplier) +
                (Card misuse indicators * card_misuse_multiplier)

    Attributes:
        passenger_vehicle_multiplier: Passenger vehicle indicators are typically weighted more heavily.
        card_misuse_multiplier: Weight for card misuse indicators.
        individual_weights: Weights for individual red flag indicators.
    """

    model_config = ConfigDict(extra='forbid', frozen=True)

    passenger_vehicle_multiplier: float = Field(
        default=2.0,
        description='Passenger vehicle indicators are typically weighted more heavily.',
        ge=0.0,
    )

    card_misuse_multiplier: float = Field(
        default=1.0,
        description='Weight for card misuse indicators.',
        ge=0.0,
    )

    individual_weights: IndividualFlagWeightConfig = Field(
        default_factory=IndividualFlagWeightConfig,
        description='Weights for individual red flag indicators.',
    )

    @model_validator(mode='after')
    def validate_nondegenerate_weights(self) -> Self:
        """
        Ensure configuration produces meaningful scores.

        Raises:
            ValueError: If all multipliers are zero (no scoring possible).
        """
        if (
            self.passenger_vehicle_multiplier == 0.0
            and self.card_misuse_multiplier == 0.0
        ):
            raise ValueError(
                'At least one category multiplier must be non-zero; '
                'both passenger_vehicle_multiplier and card_misuse_multiplier are 0.'
            )
        return self
