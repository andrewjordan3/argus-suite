# argus/models/config/output.py
"""
This module defines the OutputConfig model for configuring output
generation and formatting in the ARGUS system.
"""

from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

__all__: list[str] = ['OutputConfig']

# =============================================================================
# OUTPUT CONFIGURATION
# =============================================================================
class OutputConfig(BaseModel):
    """
    Configuration for output generation and formatting.

    Controls what outputs are generated (reports, visualizations),
    where they are saved, and entity display settings.

    Attributes:
        output_directory: Directory path for saving outputs.
        output_width: Character width for console output formatting.
        display_report: Whether to print analysis report to console.
        save_report: Whether to save report to output directory.
        generate_visualizations: Whether to create visualization plots.
        save_visualizations: Whether to save plots to output directory.
        top_n_entities: Number of top entities (drivers/vehicles) to report.
        auto_analyze_top_drivers: Number of top drivers to auto-analyze in detail.
    """

    model_config = ConfigDict(extra='forbid')

    output_directory: Path = Field(
        Path('./output'),
        description='Directory path for saving all output files',
    )

    output_width: int = Field(
        100,
        description='Character width for console output formatting',
        ge=80,
        le=200,
    )

    display_report: bool = Field(
        True,
        description='Whether to print analysis report to console',
    )

    save_report: bool = Field(
        True,
        description='Whether to save report text to output directory',
    )

    generate_visualizations: bool = Field(
        True,
        description='Whether to create visualization plots',
    )

    save_visualizations: bool = Field(
        True,
        description='Whether to save visualization plots to output directory',
    )

    top_n_entities: int = Field(
        10,
        description='Number of top entities (drivers/vehicles) to report',
        ge=1,
        le=100,
    )

    auto_analyze_top_drivers: int = Field(
        3,
        description='Number of top drivers to automatically analyze in detail',
        ge=0,
        le=20,
    )

    @field_validator('output_directory', mode='before')
    @classmethod
    def convert_to_path(cls, value: str | Path) -> Path:
        """
        Convert string to Path object.

        Args:
            value: String or Path representing output directory.

        Returns:
            Path object for output directory.
        """
        return Path(value) if isinstance(value, str) else value

    @model_validator(mode='after')
    def validate_auto_analyze_subset(self) -> Self:
        """
        Ensure auto_analyze_top_drivers does not exceed top_n_entities.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If auto_analyze_top_drivers > top_n_entities.
        """
        if self.auto_analyze_top_drivers > self.top_n_entities:
            raise ValueError(
                f'auto_analyze_top_drivers ({self.auto_analyze_top_drivers}) cannot exceed '
                f'top_n_entities ({self.top_n_entities})'
            )
        return self

    def ensure_output_directory_exists(self) -> None:
        """
        Create output directory if it doesn't exist.

        Creates the output directory and any necessary parent directories.
        Safe to call multiple times - no error if directory already exists.

        Raises:
            OSError: If directory creation fails due to permissions or other OS error.
        """
        self.output_directory.mkdir(parents=True, exist_ok=True)
