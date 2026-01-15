# argus/models/locale/report_metadata.py
"""
============================================================================
REPORT METADATA
============================================================================
System identification, versioning, and report-level information that
appears in report headers and footers. This schema ensures that all
report metadata is consistent and correctly formatted.
============================================================================
"""

from pydantic import Field

from argus.models.common import FrozenModel

__all__: list[str] = ['Metadata']


class Metadata(FrozenModel):
    """
    Complete report metadata with flat structure.

    This model contains all system identification, versioning, and report
    classification information in a flat structure matching the YAML format.

    Attributes:
        system_name: Short system acronym (e.g., "ARGUS")
        system_full_name: Full descriptive system name
        subtitle: Report type descriptor
        version: Software version string (e.g., "0.1.0")
        report_type: Type of report being generated
        classification: Security/confidentiality classification
    """

    system_name: str = Field(
        description="Short system identifier/acronym (e.g., 'ARGUS')"
    )
    system_full_name: str = Field(
        description='Complete system name for formal documentation'
    )
    subtitle: str = Field(description='Report type or component subtitle')
    version: str = Field(
        pattern=r'^\d+\.\d+\.\d+$',
        description='Software version in semantic versioning format (major.minor.patch)',
    )
    report_type: str = Field(
        description="Type of report being generated (e.g., 'Fuel Card Forensic Analysis Report')"
    )
    classification: str = Field(
        description="Security classification (e.g., 'Internal Use - Contains Sensitive Data')"
    )
