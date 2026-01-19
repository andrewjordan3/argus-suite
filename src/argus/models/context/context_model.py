# argus/utils/context_model.py
"""
Analysis Context definition for the Argus pipeline.

This module defines the container object used to pass execution state,
data, and configuration tools through the analysis functions.
"""

from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from argus.formatting.report_formatter import ReportFormatter
from argus.models.config import UserConfig
from argus.output_formatter import ForensicReportWriter

__all__: list[str] = [
    'AnalysisContext',
    'EntityAnalysisContext',
    'EntityMetadata',
]

class AnalysisContext(BaseModel):
    """
    Encapsulates the state and tools required for a forensic analysis run.

    This context object is passed through the pipeline, avoiding "argument explosion"
    in function signatures. It is frozen (immutable) to ensure that the context
    remains stable throughout the execution of a single target analysis.
    """

    # arbitrary_types_allowed=True is REQUIRED because pandas DataFrame
    # and the custom Writer/Formatter classes are not standard Pydantic types.
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    # =========================================================================
    # DATASETS (The "Prepared Data")
    # =========================================================================

    complete_unsplit_transactions: pd.DataFrame = Field(
        ...,
        description='The full, raw dataset containing all locations and history before any splitting occurred.',
    )

    target_period_transactions: pd.DataFrame = Field(
        ...,
        description='Transactions for the target location strictly within the analysis period.',
    )

    peer_period_transactions: pd.DataFrame = Field(
        ...,
        description='Transactions for the comparison cohort (peer locations) strictly within the analysis period.',
    )

    target_historical_transactions: pd.DataFrame = Field(
        ...,
        description='Complete historical transactions for the target location (used for trending/z-score history).',
    )

    peer_historical_transactions: pd.DataFrame = Field(
        ...,
        description='Complete historical transactions for the comparison cohort (used for global baseline stats).',
    )

    analysis_period_label: str = Field(
        ...,
        description="Label defining the time range of the analysis (e.g., '2023-Q4' or 'Nov 2024').",
    )

    # =========================================================================
    # TARGET METADATA
    # =========================================================================

    target_location_number: int = Field(
        ..., description='The integer identifier for the location being analyzed.'
    )

    target_location_name: str = Field(
        ..., description='The human-readable name of the location.'
    )

    # =========================================================================
    # TOOLS & SERVICES
    # =========================================================================

    report_writer: ForensicReportWriter = Field(
        ..., description='Service for writing the final forensic report.'
    )

    report_formatter: ReportFormatter = Field(
        ...,
        description='Service for formatting report cells (Excel styles, currency, etc).',
    )

    # =========================================================================
    # CONFIGURATION
    # =========================================================================

    config: UserConfig = Field(
        ...,
        description='Main configuration object for the current run.',
    )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def get_context_description(self) -> str:
        """
        Returns a formatted string describing the current analysis target.
        Useful for logging.
        """
        return f'Loc #{self.target_location_number} ({self.target_location_name})'


# =============================================================================
# ENTITY ANALYSIS MODELS
# =============================================================================


class EntityMetadata(BaseModel):
    """
    Identity information for a specific analysis subject (Driver or Vehicle).

    Bundles the various identifiers and descriptions needed to label
    charts and reports for a single entity.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(
        ..., description='Internal unique identifier (e.g., driver_index as string)'
    )
    type: Literal['Driver', 'Vehicle'] = Field(
        ..., description='Category of the entity'
    )
    display_label: str = Field(
        ..., description='Human-readable identifier (e.g., Driver Name or VIN)'
    )
    description: str | None = Field(
        default=None, description="Optional context (e.g., '2018 Ford F-150')"
    )


class EntityAnalysisContext(BaseModel):
    """
    Context packet for analyzing a single entity's temporal patterns.

    This replaces the 7+ arguments passed to _analyze_entity_temporal_pattern.
    It bundles the subject's data, identity, and the reference distributions
    needed for statistical comparison.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    # The Subject
    metadata: EntityMetadata = Field(
        ..., description='Identity and descriptive labels for the entity.'
    )

    # The Data
    data: pd.DataFrame = Field(
        ..., description='Transactions specific to this entity (filtered view).'
    )

    # The Context
    distributions: dict[str, dict[str, float]] = Field(
        ...,
        description='Reference distributions (benchmarks) for statistical comparison.',
    )

    # Reference to the main analysis context (access to config, writer, formatter)
    parent_context: AnalysisContext = Field(
        ...,
        description='Reference to the main analysis context (access to config, writer, formatter).',
    )

    def get_log_header(self) -> str:
        """Helper to formatting logging prefixes."""
        return (
            f'[{self.metadata.type} {self.metadata.id}] {self.metadata.display_label}'
        )
