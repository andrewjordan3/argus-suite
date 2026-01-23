# argus/models/user_config/analysis_target.py
"""
Configuration module for specifying analysis targets in the ARGUS system.
"""
from pydantic import Field

from argus.models.common import FrozenModel

__all__: list[str] = [
    'AnalysisConfig',
]

# =============================================================================
# ANALYSIS TARGET CONFIGURATION
# =============================================================================
class AnalysisConfig(FrozenModel):
    """
    Configuration for specifying the analysis target.

    Identifies which location/branch to analyze and compare against
    the baseline (all other branches).

    Attributes:
        target_location_number: Integer identifier of the location to analyze.
        target_location_name: Human-readable name of the target location for reports.
    """

    target_location_number: int = Field(
        ...,
        description='Integer identifier of the location to analyze',
        ge=0,
    )

    target_location_name: str = Field(
        ...,
        description='Human-readable name of the target location',
        min_length=1,
    )
