# argus/models/context/target_analysis_data.py
"""
Runtime data container for a single target location analysis.

This module defines TargetAnalysisData, which encapsulates all datasets
and metadata required to analyze one target location. A new instance is
created for each location analyzed.

Lifecycle:
    1. Raw data loaded from source
    2. Data split by target vs peers, period vs historical
    3. TargetAnalysisData created with prepared DataFrames
    4. Passed through analysis pipeline
    5. Discarded after analysis completes

Note:
    This model is frozen (immutable) to ensure data integrity throughout
    the analysis pipeline. The same DataFrames are referenced by all
    analysis functions without risk of modification.
"""

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

__all__: list[str] = ['TargetAnalysisData']


class TargetAnalysisData(BaseModel):
    """
    Runtime data for a single target location analysis.

    Contains prepared DataFrames and metadata for one analysis run.
    Created after data preparation and consumed by analysis functions.

    This model uses arbitrary_types_allowed to support pandas DataFrames.
    It is frozen to prevent accidental mutation during analysis.

    Attributes:
        complete_unsplit_transactions: Full dataset before target/peer split.
        target_period_transactions: Target location data within analysis period.
        peer_period_transactions: Peer locations data within analysis period.
        target_historical_transactions: Target location full history.
        peer_historical_transactions: Peer locations full history.
        analysis_period_label: Human-readable period description.
        target_location_number: Numeric identifier for the target.
        target_location_name: Display name for the target.

    Example:
        >>> data = TargetAnalysisData(
        ...     target_location_number=14,
        ...     target_location_name='Philadelphia Branch',
        ...     analysis_period_label='2025 YTD (Jan-Jun)',
        ...     complete_unsplit_transactions=df_all,
        ...     target_period_transactions=df_target,
        ...     peer_period_transactions=df_peers,
        ...     target_historical_transactions=df_target_hist,
        ...     peer_historical_transactions=df_peer_hist,
        ... )
        >>> logger.info('Analyzing %s', data)
        Analyzing Loc #14 (Philadelphia Branch)
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True, extra='forbid')

    # =========================================================================
    # Datasets
    # =========================================================================

    complete_unsplit_transactions: pd.DataFrame = Field(
        ...,
        description='Full dataset before target/peer split (for reference).',
    )

    target_period_transactions: pd.DataFrame = Field(
        ...,
        description='Target location transactions within analysis period.',
    )

    peer_period_transactions: pd.DataFrame = Field(
        ...,
        description='Peer locations transactions within analysis period.',
    )

    target_historical_transactions: pd.DataFrame = Field(
        ...,
        description='Target location full history (for trending, Z-scores).',
    )

    peer_historical_transactions: pd.DataFrame = Field(
        ...,
        description='Peer locations full history (for baseline statistics).',
    )

    # =========================================================================
    # Metadata
    # =========================================================================

    analysis_period_label: str = Field(
        ...,
        min_length=1,
        description="Human-readable period label (e.g., '2025 YTD (Jan-Jun)').",
    )

    target_location_number: int = Field(
        ...,
        ge=0,
        description='Numeric identifier for the target location.',
    )

    target_location_name: str = Field(
        ...,
        min_length=1,
        description='Display name for the target location.',
    )

    # =========================================================================
    # Dunder Methods
    # =========================================================================

    def __str__(self) -> str:
        """Human-readable description for logging."""
        return f'Loc #{self.target_location_number} ({self.target_location_name})'

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (
            f'TargetAnalysisData('
            f'target={self.target_location_number}, '
            f'period={self.analysis_period_label!r}, '
            f'target_rows={len(self.target_period_transactions)}, '
            f'peer_rows={len(self.peer_period_transactions)})'
        )
