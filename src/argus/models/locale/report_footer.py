# argus/models/locale/report_footer.py
"""
============================================================================
REPORT FOOTER
============================================================================
Content for report footer including data coverage, statistical rigor
summary, test summary table, and disclaimers. Each section is defined by
a Pydantic model to ensure data integrity and consistency.
============================================================================
"""

from pydantic import Field

from argus.models.common import FrozenModel
from argus.models.locale.placeholder_registry import P
from argus.models.locale.placeholder_validators import FormatStr, FormatStrList

__all__: list[str] = [
    'ReportFooter',
    'ReportFooterClosing',
    'ReportFooterDataCoverage',
    'ReportFooterDisclaimer',
    'ReportFooterReportMetadata',
    'ReportFooterStatisticalRigor',
    'ReportFooterTestSummary',
    'ReportFooterTestSummaryHeaders',
]


class ReportFooterDataCoverage(FrozenModel):
    """
    Data coverage statistics for footer.

    Summarizes what data was included in the analysis.

    Attributes:
        title: Data coverage section title
        items: list of coverage statistic items (with placeholders)
    """

    title: str
    items: FormatStrList[P.FooterDataCoverageItems] = Field(
        description='list of data coverage statistic line items (with placeholders)'
    )


class ReportFooterStatisticalRigor(FrozenModel):
    """
    Statistical rigor summary for footer.

    Summarizes statistical approach and findings.

    Attributes:
        title: Statistical rigor section title
        items: list of rigor statistic items (with placeholders)
    """

    title: str
    items: FormatStrList[P.FooterStatisticalRigorItems] = Field(
        description='list of statistical rigor statistic line items (with placeholders)'
    )


class ReportFooterTestSummaryHeaders(FrozenModel):
    """
    Column headers for test summary table in footer.

    Attributes:
        test_name: Header for test name column
        raw_p_value: Header for raw p-value column
        q_value: Header for FDR q-value column
        significant: Header for significance column
    """

    test_name: str
    raw_p_value: str
    q_value: str
    significant: str


class ReportFooterTestSummary(FrozenModel):
    """
    Test summary table configuration for footer.

    Compact summary of all statistical tests performed.

    Attributes:
        title: Test summary section title
        headers: Column headers for summary table
    """

    title: str
    headers: ReportFooterTestSummaryHeaders


class ReportFooterReportMetadata(FrozenModel):
    """
    Report metadata for footer.

    Basic information about when and what was analyzed.

    Attributes:
        title: Report metadata section title
        items: list of metadata items (with placeholders)
    """

    title: str
    items: FormatStrList[P.FooterReportMetadata] = Field(
        description='list of report metadata line items (with placeholders)'
    )


class ReportFooterDisclaimer(FrozenModel):
    """
    Important disclaimer for footer.

    Legal/professional disclaimer about interpretation of findings.

    Attributes:
        title: Disclaimer section title
        paragraphs: list of disclaimer paragraphs
    """

    title: str
    paragraphs: list[str] = Field(description='list of disclaimer paragraphs')


class ReportFooterClosing(FrozenModel):
    """
    Closing text for report footer.

    Final sign-off message.

    Attributes:
        main: Main closing statement
        subtitle: System identification subtitle
    """

    main: str
    subtitle: FormatStr[P.FooterClosing] = Field(
        description='System identification subtitle (with placeholders)'
    )


class ReportFooter(FrozenModel):
    """
    Complete report footer configuration.

    The footer provides comprehensive summary of data coverage, statistical
    approach, and important disclaimers.

    Attributes:
        section_title: Footer section title
        data_coverage: Data coverage statistics configuration
        statistical_rigor: Statistical rigor summary configuration
        test_summary: Test summary table configuration
        report_metadata: Report metadata configuration
        disclaimer: Disclaimer configuration
        closing: Closing statement configuration
    """

    section_title: str
    data_coverage: ReportFooterDataCoverage
    statistical_rigor: ReportFooterStatisticalRigor
    test_summary: ReportFooterTestSummary
    report_metadata: ReportFooterReportMetadata
    disclaimer: ReportFooterDisclaimer
    closing: ReportFooterClosing
