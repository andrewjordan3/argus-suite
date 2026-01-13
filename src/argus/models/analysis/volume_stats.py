# argus/models/analysis/volume_stats.py
"""
Container for fleet-wide volume statistics used in z-score calculations.
"""

import math
from typing import Self

from pydantic import BaseModel, Field, model_validator

__all__: list[str] = [
    'VolumeStatistics',
]

class VolumeStatistics(BaseModel):
    """
    Container for fleet-wide volume statistics used in z-score calculations.

    When has_volume=False, mean_volume and std_volume will be NaN to indicate
    unavailable data. When has_volume=True, they contain calculated statistics
    (though std_volume may still be NaN if there's insufficient data for calculation).

    Attributes:
        has_volume: Whether volume data is available in the dataset
        mean_volume: Mean fuel volume across all drivers (NaN if unavailable)
        std_volume: Standard deviation of fuel volume across all drivers (NaN if unavailable)
    """

    has_volume: bool = Field(
        description='Whether volume data is available in the dataset',
    )
    mean_volume: float = Field(
        description='Mean fuel volume across all drivers (NaN when has_volume=False)',
    )
    std_volume: float = Field(
        description='Standard deviation of fuel volume across all drivers '
        '(NaN when has_volume=False or insufficient data for calculation)',
    )

    @model_validator(mode='after')
    def validate_volume_consistency(self) -> Self:
        """
        Ensure that when has_volume is False, mean and std are NaN.

        This enforces the semantic constraint that volume statistics should
        not contain real values when volume data is unavailable.

        Returns:
            Self after validation

        Raises:
            ValueError: If has_volume=False but mean_volume or std_volume are not NaN
        """
        if not self.has_volume:
            if not math.isnan(self.mean_volume):
                raise ValueError(
                    'mean_volume must be NaN when has_volume=False, '
                    f'got {self.mean_volume}'
                )
            if not math.isnan(self.std_volume):
                raise ValueError(
                    'std_volume must be NaN when has_volume=False, '
                    f'got {self.std_volume}'
                )

        return self
