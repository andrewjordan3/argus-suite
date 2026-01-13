# argus/models/config/performance.py

from pydantic import BaseModel, ConfigDict, Field

__all__: list[str] = [
    'PerformanceConfig',
]


class PerformanceConfig(BaseModel):
    """
    Configuration for performance tuning of the ARGUS system.

    Attributes:
        n_bootstrap: Number of bootstrap iterations for confidence interval estimation.
    """

    model_config = ConfigDict(extra='forbid')

    n_bootstrap: int = Field(
        default=10000,
        description='Number of bootstrap iterations for confidence interval estimation',
        ge=500,
        le=100000,
    )
