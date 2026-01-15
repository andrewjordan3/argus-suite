# argus/models/analysis/volume_stats.py
"""
Volume Statistics Model for ARGUS Analysis Pipeline.

This module defines the VolumeStatistics model, a pure data container that
encapsulates fleet-wide fuel volume statistics used for z-score calculations
in driver and vehicle risk analysis.

Design Philosophy:
    This model follows the ARGUS principle of separating data from policy.
    It contains only raw statistical outputs—the population parameters needed
    to compute standardized scores. No methods depend on configuration
    thresholds, locale settings, or presentation formatting.

Usage Context:
    Volume statistics are computed once per analysis run from the full
    population of transactions, then used to calculate individual z-scores:

        z_score = (driver_volume - mean_volume) / std_volume

    The has_volume flag handles datasets where volume data may be unavailable
    (e.g., some fuel card vendors don't report gallons). When has_volume=False,
    downstream analysis should skip volume-based risk factors.

Immutability:
    Instances are frozen after creation. Population statistics represent
    a point-in-time computation from a specific dataset and should not
    be modified.

Usage:
    >>> from argus.models.analysis.volume_stats import VolumeStatistics
    >>> import math
    >>>
    >>> # When volume data is available
    >>> stats = VolumeStatistics(
    ...     has_volume=True,
    ...     mean_volume=2450.5,
    ...     std_volume=890.2,
    ... )
    >>>
    >>> # Calculate z-score for a driver
    >>> driver_volume = 3500.0
    >>> z_score = (driver_volume - stats.mean_volume) / stats.std_volume
    >>> z_score
    1.178...
    >>>
    >>> # When volume data is unavailable
    >>> no_volume = VolumeStatistics(
    ...     has_volume=False,
    ...     mean_volume=math.nan,
    ...     std_volume=math.nan,
    ... )

See Also:
    - argus.models.analysis.driver_risk: Uses volume_z_score computed from these stats
    - argus.models.analysis.vehicle_risk: Vehicle-level risk profiles
"""

import math
from typing import Self

from pydantic import Field, field_validator, model_validator

from argus.models.common.base import FrozenModel

__all__: list[str] = [
    'VolumeStatistics',
]


class VolumeStatistics(FrozenModel):
    """
    Container for fleet-wide volume statistics used in z-score calculations.

    This model stores population-level statistics (mean and standard deviation)
    for fuel volume across all entities in the analysis. These parameters are
    used to compute standardized z-scores that indicate how unusual an
    individual entity's volume is relative to the fleet.

    The model explicitly handles the case where volume data is unavailable
    through the has_volume flag. When has_volume=False, both mean_volume and
    std_volume must be NaN. This allows downstream code to check the flag
    rather than testing for NaN values throughout.

    Note on std_volume:
        Even when has_volume=True, std_volume may be NaN if there is
        insufficient data to compute a meaningful standard deviation
        (e.g., fewer than 2 observations, or all observations identical).
        Z-score calculations should handle this case gracefully.

    Attributes:
        has_volume: Boolean flag indicating whether volume data is available
            in the source dataset. When False, volume-based risk factors
            should be skipped in downstream analysis.

        mean_volume: Arithmetic mean of fuel volume (in gallons) across all
            entities in the analysis population. Must be NaN when has_volume
            is False. When has_volume is True, must be a non-negative value.

        std_volume: Population standard deviation of fuel volume (in gallons)
            across all entities. Must be NaN when has_volume is False. May
            also be NaN when has_volume is True if there is insufficient data
            for calculation. When present, must be non-negative.

    Invariants:
        - When has_volume=False: both mean_volume and std_volume must be NaN
        - When has_volume=True: mean_volume must not be NaN and must be >= 0
        - std_volume, when not NaN, must be >= 0 (std dev is non-negative)

    Example:
        >>> # Fleet with volume data
        >>> stats = VolumeStatistics(
        ...     has_volume=True,
        ...     mean_volume=2450.5,
        ...     std_volume=890.2,
        ... )
        >>> print(stats)
        VolumeStatistics(has_volume=True, mean=2450.50, std=890.20)
        >>>
        >>> # Fleet without volume data
        >>> no_vol = VolumeStatistics(
        ...     has_volume=False,
        ...     mean_volume=math.nan,
        ...     std_volume=math.nan,
        ... )
        >>> print(no_vol)
        VolumeStatistics(has_volume=False, mean=N/A, std=N/A)
    """

    # -------------------------------------------------------------------------
    # Data Availability Flag
    # -------------------------------------------------------------------------

    has_volume: bool = Field(
        ...,
        description='Whether volume data is available in the source dataset',
    )

    # -------------------------------------------------------------------------
    # Population Statistics
    # -------------------------------------------------------------------------

    mean_volume: float = Field(
        ...,
        description='Mean fuel volume in gallons across all entities (NaN if unavailable)',
    )

    std_volume: float = Field(
        ...,
        description='Standard deviation of fuel volume in gallons (NaN if unavailable)',
    )

    # -------------------------------------------------------------------------
    # Field Validators
    # -------------------------------------------------------------------------

    @field_validator('mean_volume')
    @classmethod
    def validate_mean_volume_non_negative(cls, value: float) -> float:
        """
        Validate that mean volume is non-negative when present.

        Fuel volume cannot be negative, so the mean of fuel volumes must
        also be non-negative. NaN is permitted to indicate unavailable data.

        Args:
            value: The mean volume value to validate.

        Returns:
            The validated value, unchanged.

        Raises:
            ValueError: If mean_volume is not NaN and is negative.
        """
        if not math.isnan(value) and value < 0.0:
            raise ValueError(
                f'mean_volume must be non-negative when present, got {value}'
            )
        return value

    @field_validator('std_volume')
    @classmethod
    def validate_std_volume_non_negative(cls, value: float) -> float:
        """
        Validate that standard deviation is non-negative when present.

        Standard deviation is mathematically non-negative by definition.
        NaN is permitted to indicate unavailable or uncomputable data.

        Args:
            value: The standard deviation value to validate.

        Returns:
            The validated value, unchanged.

        Raises:
            ValueError: If std_volume is not NaN and is negative.
        """
        if not math.isnan(value) and value < 0.0:
            raise ValueError(
                f'std_volume must be non-negative when present, got {value}'
            )
        return value

    # -------------------------------------------------------------------------
    # Model Validators
    # -------------------------------------------------------------------------

    @model_validator(mode='after')
    def validate_unavailable_volume_is_nan(self) -> Self:
        """
        Validate that statistics are NaN when volume data is unavailable.

        Enforces the semantic constraint that when has_volume=False, both
        mean_volume and std_volume must be NaN. This ensures consistent
        representation of missing data throughout the pipeline.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If has_volume=False but statistics are not NaN.
        """
        if not self.has_volume:
            if not math.isnan(self.mean_volume):
                raise ValueError(
                    f'mean_volume must be NaN when has_volume=False, '
                    f'got {self.mean_volume}'
                )
            if not math.isnan(self.std_volume):
                raise ValueError(
                    f'std_volume must be NaN when has_volume=False, '
                    f'got {self.std_volume}'
                )

        return self

    @model_validator(mode='after')
    def validate_available_volume_has_mean(self) -> Self:
        """
        Validate that mean is present when volume data is available.

        When has_volume=True, we must have at least computed a mean. The
        mean can only be NaN if there were no observations, which would
        contradict has_volume=True.

        Note:
            std_volume is allowed to be NaN even when has_volume=True,
            as there may be insufficient data (< 2 observations) to
            compute a meaningful standard deviation.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If has_volume=True but mean_volume is NaN.
        """
        if self.has_volume and math.isnan(self.mean_volume):
            raise ValueError(
                'mean_volume cannot be NaN when has_volume=True. '
                'If no volume data exists, set has_volume=False.'
            )

        return self

    # -------------------------------------------------------------------------
    # String Representation
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        """
        Return a compact string representation for debugging and logging.

        Shows all three fields in a readable format, with N/A displayed
        for NaN values.

        Returns:
            Compact string suitable for logs and REPL inspection.

        Example:
            >>> repr(stats)
            "VolumeStatistics(has_volume=True, mean=2450.50, std=890.20)"
        """
        mean_display: str = (
            f'{self.mean_volume:.2f}' if not math.isnan(self.mean_volume) else 'N/A'
        )
        std_display: str = (
            f'{self.std_volume:.2f}' if not math.isnan(self.std_volume) else 'N/A'
        )

        return (
            f'VolumeStatistics(has_volume={self.has_volume}, '
            f'mean={mean_display}, '
            f'std={std_display})'
        )
