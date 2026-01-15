# argus/models/locale/header_content.py
"""
============================================================================
REPORT HEADER CONTENT
============================================================================
Text content and labels for report header section, including title,
metadata labels, and key analysis parameters.
============================================================================
"""

from pydantic import Field

from argus.models.common import FrozenModel

__all__: list[str] = ['ReportHeader', 'ReportHeaderLabels']


class ReportHeaderLabels(FrozenModel):
    """
    Labels for report metadata fields displayed in header.

    These labels appear as field names in the report header's metadata section.

    Attributes:
        report_date: Label for report generation date
        analysis_period: Label for temporal scope of analysis
        confidence_level: Label for statistical confidence parameter
        target_location: Label for branch being analyzed
        location_id: Label for numeric location identifier
    """

    report_date: str = Field(description='Label for report generation date field')
    analysis_period: str = Field(
        description='Label for analysis period description field'
    )
    confidence_level: str = Field(
        description='Label for statistical confidence level field'
    )
    target_location: str = Field(description='Label for target branch name field')
    location_id: str = Field(description='Label for numeric location ID field')


class ReportHeader(FrozenModel):
    """
    Complete report header configuration.

    Defines the title block and metadata that appears at the top of every report.

    Attributes:
        main_title: Primary report title (typically system name)
        subtitle: Secondary title describing report type
        labels: Labels for all metadata fields
    """

    main_title: str = Field(
        description='Primary report title, typically the system acronym/name'
    )
    subtitle: str = Field(
        description='Secondary title describing the specific report type'
    )
    labels: ReportHeaderLabels
