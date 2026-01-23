# argus/models/entity/analysis_input.py
"""
Input container for entity-level temporal analysis.
"""

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from argus.models.entity.metadata import EntityMetadata

__all__: list[str] = ['EntityAnalysisInput']


class EntityAnalysisInput(BaseModel):
    """
    Bundled input for analyzing a single entity's temporal patterns.

    Packages the entity's identity, transaction data, and reference
    distributions needed for statistical comparison into one object,
    avoiding argument explosion in analysis functions.

    Attributes:
        metadata: Identity and display labels for the entity.
        data: Transactions for this entity (filtered from target data).
        distributions: Reference distributions for statistical comparison.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    metadata: EntityMetadata = Field(
        ..., description='Identity and display labels for the entity.'
    )

    data: pd.DataFrame = Field(..., description='Transactions for this entity.')

    distributions: dict[str, dict[str, float]] = Field(
        ..., description='Reference distributions for statistical comparison.'
    )

    def __str__(self) -> str:
        """Logging-friendly description."""
        return (
            f'[{self.metadata.type} {self.metadata.id}] {self.metadata.display_label}'
        )

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (
            f'EntityAnalysisInput('
            f'type={self.metadata.type!r}, '
            f'id={self.metadata.id!r}, '
            f'rows={len(self.data)})'
        )
