# argus/models/entity/__init__.py
"""
Entity models for driver and vehicle analysis.
"""

from argus.models.entity.analysis_input import EntityAnalysisInput
from argus.models.entity.metadata import EntityMetadata

__all__: list[str] = [
    'EntityAnalysisInput',
    'EntityMetadata',
]
