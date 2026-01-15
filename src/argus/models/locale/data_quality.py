# argus/schemas/data_quality.py
"""
============================================================================
DATA PREPARATION AND QUALITY
============================================================================
Content for data preparation summary and quality assessment sections.
Includes labels, messages, and assessment criteria. These are used to generate
structured reports on data preparation and quality assessment.
============================================================================
"""

from pydantic import Field

from argus.models.common import FormatStr, FrozenModel, P

__all__: list[str] = [
    'DataPreparation',
    'DataPreparationLabels',
    'DataPreparationMessages',
    'DataQuality',
    'DataQualityAssessments',
    'DataQualityLabels',
    'DataQualityMessages',
    'DataQualitySubsections',
]


class DataPreparationLabels(FrozenModel):
    """
    Labels for data preparation statistics.

    These labels describe various stages of data cleaning and preparation.

    Attributes:
        initial_records: Label for raw input record count
        duplicates_removed: Label for duplicate removal count
        incomplete_removed: Label for incomplete record removal count
        final_records: Label for final cleaned record count
        retention_rate: Label for percentage of records retained
    """

    initial_records: str = Field(
        description='Label for initial raw record count before cleaning'
    )
    duplicates_removed: str = Field(
        description='Label for number of duplicate records removed'
    )
    incomplete_removed: str = Field(
        description='Label for number of incomplete records removed'
    )
    final_records: str = Field(description='Label for final cleaned record count')
    retention_rate: str = Field(description='Label for data retention percentage')


class DataPreparationMessages(FrozenModel):
    """
    Template messages for data preparation reporting.

    These message templates are used when specific data issues are found.

    Attributes:
        duplicates_found: Template for reporting duplicate removal
        incomplete_found: Template for reporting incomplete record removal
    """

    duplicates_found: FormatStr[P.DataPrepCountPercentage] = Field(
        description='Message template for reporting duplicate removal (includes placeholders)'
    )
    incomplete_found: FormatStr[P.DataPrepCountPercentage] = Field(
        description='Message template for reporting incomplete record removal'
    )


class DataPreparation(FrozenModel):
    """
    Complete data preparation section configuration.

    Defines all content for the data preparation summary that appears
    after the report header.

    Attributes:
        section_title: Title for this report section
        labels: Labels for all preparation statistics
        messages: Message templates for data issues found
    """

    section_title: str = Field(description='Title for the data preparation section')
    labels: DataPreparationLabels
    messages: DataPreparationMessages


class DataQualitySubsections(FrozenModel):
    """
    Subsection headers within data quality assessment.

    The data quality section is divided into three main areas of concern.

    Attributes:
        missing_values: Header for missing data analysis
        validity_issues: Header for data validation issues
        outliers: Header for statistical outlier detection
    """

    missing_values: str = Field(
        description='Subsection header for missing value analysis'
    )
    validity_issues: str = Field(
        description='Subsection header for data validity problems'
    )
    outliers: str = Field(description='Subsection header for outlier detection results')


class DataQualityLabels(FrozenModel):
    """
    Labels for data quality summary statistics.

    Attributes:
        total_after_cleaning: Label for final record count post-cleaning
        duplicates_removed: Label for duplicate removal confirmation
        remaining_duplicates: Warning label if duplicates still exist
    """

    total_after_cleaning: str = Field(
        description='Label for total records after cleaning operations'
    )
    duplicates_removed: str = Field(description='Label confirming duplicate removal')
    remaining_duplicates: FormatStr[P.DataQualityRemainingDuplicates] = Field(
        description='Warning label if duplicates remain after cleaning'
    )


class DataQualityMessages(FrozenModel):
    """
    Message templates for reporting data quality issues.

    These templates include placeholders for specific values discovered
    during quality assessment.

    Attributes:
        missing_value_item: Template for missing value report line
        validity_item: Template for validity issue report line
        outlier_item: Template for outlier report line
        outlier_bounds: Template for outlier boundary information
    """

    missing_value_item: FormatStr[P.DataQualityMissingValueItem] = Field(
        description='Template for reporting missing values in a column'
    )
    validity_item: FormatStr[P.DataQualityValidityItem] = Field(
        description='Template for reporting data validity issues'
    )
    outlier_item: FormatStr[P.DataQualityOutlierItem] = Field(
        description='Template for reporting outliers in a column'
    )
    outlier_bounds: FormatStr[P.DataQualityOutlierBounds] = Field(
        description='Template for showing valid range boundaries'
    )


class DataQualityAssessments(FrozenModel):
    """
    Overall data quality assessment messages.

    Based on the number and severity of issues found, one of these
    assessment messages is displayed as a summary.

    Attributes:
        excellent: Message when no critical issues found
        minor_issues: Message when minor issues detected
        multiple_issues: Message when multiple issues require review
    """

    excellent: str = Field(
        description='Assessment message when data quality is excellent'
    )
    minor_issues: str = Field(
        description='Assessment message when minor issues are detected'
    )
    multiple_issues: str = Field(
        description='Assessment message when multiple issues require thorough review'
    )


class DataQuality(FrozenModel):
    """
    Complete data quality assessment section configuration.

    Defines all content for the data quality section including subsection
    headers, labels, message templates, and assessment criteria.

    Attributes:
        section_title: Title for this report section
        subsections: Headers for quality assessment subsections
        labels: Labels for summary statistics
        messages: Templates for issue reporting
        assessments: Overall quality assessment messages
    """

    section_title: str = Field(
        description='Title for the data quality assessment section'
    )
    subsections: DataQualitySubsections
    labels: DataQualityLabels
    messages: DataQualityMessages
    assessments: DataQualityAssessments
