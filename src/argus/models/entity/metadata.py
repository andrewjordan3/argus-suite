# argus/models/entity/metadata.py
"""
Identity metadata for analysis subjects (drivers, vehicles).
"""

from typing import Literal

from pydantic import Field

from argus.models.common import FrozenModel

__all__: list[str] = ['EntityMetadata']


class EntityMetadata(FrozenModel):
    """
    Identity information for a single analysis subject.

    Bundles identifiers and descriptions needed to label charts
    and reports for a driver or vehicle.

    Attributes:
        id: Internal unique identifier.
        type: Entity category ('Driver' or 'Vehicle').
        display_label: Human-readable name (driver name or VIN).
        description: Optional context (e.g., vehicle make/model).
    """

    id: str = Field(..., description='Internal unique identifier.')

    type: Literal['Driver', 'Vehicle'] = Field(..., description='Entity category.')

    display_label: str = Field(..., description='Human-readable identifier.')

    description: str | None = Field(
        default=None, description='Optional context (e.g., vehicle make/model).'
    )

    def __str__(self) -> str:
        """Logging-friendly label."""
        return f'{self.type} {self.id}: {self.display_label}'
