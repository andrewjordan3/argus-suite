# argus/models/user_config/root.py
"""Root configuration model for ARGUS."""

from pathlib import Path

from pydantic import Field

from argus.models.common import RootConfigModel
from argus.models.user_config.analysis_target import AnalysisConfig
from argus.models.user_config.column_mapping import ColumnMappingConfig
from argus.models.user_config.data_sources import DataSourcesConfig
from argus.models.user_config.logging import LoggingConfig
from argus.models.user_config.output import OutputConfig
from argus.models.user_config.performance import PerformanceConfig

__all__: list[str] = ['UserConfig']


class UserConfig(RootConfigModel):
    """
    Root configuration for ARGUS Fuel Card Forensics.

    Aggregates all user-configurable settings for a forensic analysis run.
    Typically loaded from a YAML configuration file (config.yaml).

    Attributes:
        sources: Input data file paths (fuel transactions, ELD telemetry).
        column_mapping: Maps dataset column names to ARGUS field names.
        analysis: Target location and analysis parameters.
        output: Report generation and file output settings.
        logging: Log levels and file destinations.
        performance: Tuning parameters for computational operations.

    Example:
        >>> config = UserConfig.from_yaml("config.yaml")
        >>> config.analysis.target_location_name
        'Philadelphia Branch'
    """

    analysis: AnalysisConfig = Field(
        description='Target location and analysis scope settings.',
    )

    column_mapping: ColumnMappingConfig = Field(
        description='Maps your column names to ARGUS expected field names.',
    )

    sources: DataSourcesConfig = Field(
        description='Input data file paths for fuel and ELD data.',
    )

    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description='Logging levels and destinations.',
    )

    output: OutputConfig = Field(
        description='Report generation and output file settings.',
    )

    performance: PerformanceConfig = Field(
        default_factory=PerformanceConfig,
        description='Performance tuning configuration.',
    )

    locale_file: Path | None = Field(
        default=None,
        description='Path to locale file for report text and formatting.',
    )

    policy_file: Path | None = Field(
        default=None,
        description='Path to policy file for organizational thresholds.',
    )
