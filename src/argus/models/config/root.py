# argus/models/config/root.py
"""Root configuration model for ARGUS."""

from pathlib import Path
from typing import Any, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field

from argus.models.config.analysis_target import AnalysisConfig
from argus.models.config.column_mapping import ColumnMappingConfig
from argus.models.config.data_sources import DataSourcesConfig
from argus.models.config.logging import LoggingConfig
from argus.models.config.output import OutputConfig
from argus.models.config.performance import PerformanceConfig


class FuelCardForensicsUserConfig(BaseModel):
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
        >>> config = FuelCardForensicsUserConfig.from_yaml("config.yaml")
        >>> config.analysis.target_location_name
        'Philadelphia Branch'
    """

    model_config = ConfigDict(extra='forbid')

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

    @classmethod
    def from_yaml(cls, config_path: str | Path) -> Self:
        """
        Load configuration from a YAML file.

        Args:
            config_path: Path to YAML configuration file.

        Returns:
            Validated configuration instance.

        Raises:
            FileNotFoundError: If config file doesn't exist.
            ValidationError: If config content is invalid.
        """
        config_path = Path(config_path)
        with config_path.open('r', encoding='utf-8') as file_handle:
            raw_config: dict[str, Any] = yaml.safe_load(file_handle)

        return cls.model_validate(raw_config)
