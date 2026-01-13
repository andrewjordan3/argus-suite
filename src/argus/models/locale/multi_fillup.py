# argus/models/locale/multi_fillup.py
"""
============================================================================
MULTI-FILLUP ANALYSIS
============================================================================
Content for analyzing multiple same-day fillup events, which are highly
suspicious for commercial fleet operations. This section identifies and analyzes
these suspicious events, providing a detailed analysis of the multi-fillup
events, including statistical significance and summary statistics.
============================================================================
"""

from pydantic import Field

from argus.models.common import BaseConfigModel, FormatStr, FormatStrList, P

__all__: list[str] = [
    'MultiFillupAnalysis',
    'MultiFillupAnalysisNotSignificant',
    'MultiFillupAnalysisSignificanceContext',
    'MultiFillupAnalysisSignificant',
    'MultiFillupAnalysisTableHeaders',
]


class MultiFillupAnalysisSignificant(BaseConfigModel):
    """
    Content for one significance outcome (significant or not significant).

    Different messages are shown depending on whether the multi-fillup test
    passed FDR correction.

    Attributes:
        marker: Visual marker (✓ or ✗)
        title: Statement of significance outcome
        details: Statistical details (p-value, q-value)
        interpretation: Explanation of what the result means
    """

    marker: str = Field(
        description="Visual marker indicating result (e.g., '✓' or '✗')"
    )
    title: str = Field(description='Statement of statistical significance outcome')
    details: FormatStr[P.MultiFillupSignificanceDetails] = Field(
        description='Statistical details template (p and q values)'
    )
    interpretation: FormatStr[P.MultiFillupSignificanceInterpretation] = Field(
        description='Interpretation of what this result means for the analysis'
    )


class MultiFillupAnalysisNotSignificant(BaseConfigModel):
    """
    Content for one significance outcome (significant or not significant).

    Different messages are shown depending on whether the multi-fillup test
    passed FDR correction.

    Attributes:
        marker: Visual marker (✓ or ✗)
        title: Statement of significance outcome
        details: Statistical details (p-value, q-value)
        interpretation: Explanation of what the result means
    """

    marker: str = Field(
        description="Visual marker indicating result (e.g., '✓' or '✗')"
    )
    title: str = Field(description='Statement of statistical significance outcome')
    details: FormatStr[P.MultiFillupSignificanceDetails] = Field(
        description='Statistical details template (p and q values)'
    )
    interpretation: str = Field(
        description='Interpretation of what this result means for the analysis'
    )


class MultiFillupAnalysisSignificanceContext(BaseConfigModel):
    """
    Significance context for multi-fillup analysis.

    Provides appropriate messaging based on whether the statistical test
    for multi-fillup rate was significant.

    Attributes:
        significant: Content when test is significant
        not_significant: Content when test is not significant
    """

    significant: MultiFillupAnalysisSignificant
    not_significant: MultiFillupAnalysisNotSignificant


class MultiFillupAnalysisTableHeaders(BaseConfigModel):
    """
    Column headers for multi-fillup events table.

    Shows the most suspicious multi-fillup events with their characteristics.

    Attributes:
        driver: Header for driver name column
        date: Header for event date column
        fills: Header for number of fillups column
        sites: Header for number of unique stations column
        hours: Header for time span column
        avg_vol: Header for average volume column
        avg_cost: Header for average cost column
        red_flags: Header for red flags column
    """

    driver: str = Field(description='Column header for driver name')
    date: str = Field(description='Column header for event date')
    fills: str = Field(description='Column header for number of fillups in event')
    sites: str = Field(
        description='Column header for number of unique stations visited'
    )
    hours: str = Field(description='Column header for time span of event')
    avg_vol: str = Field(description='Column header for average volume per fillup')
    avg_cost: str = Field(description='Column header for average cost per fillup')
    red_flags: str = Field(description='Column header for red flags detected')


class MultiFillupAnalysis(BaseConfigModel):
    """
    Complete multi-fillup analysis section configuration.

    Multiple same-day fillups are highly unusual for legitimate commercial
    operations. This section identifies and analyzes these suspicious events.

    Attributes:
        section_title: Title for multi-fillup deep dive section
        significance_context: Context based on statistical significance
        summary_title: Title for summary statistics subsection
        summary_items: list of summary statistic line items
        events_table_title: Title for suspicious events table
        table_headers: Column headers for events table
        legend_title: Title for red flag legend
    """

    section_title: str = Field(
        description='Title for the multi-fillup analysis section'
    )
    significance_context: MultiFillupAnalysisSignificanceContext
    summary_title: str = Field(description='Title for summary statistics subsection')
    summary_items: FormatStrList[P.MultiFillupSummaryItems] = Field(
        description='list of summary statistic line items (with placeholders)'
    )
    events_table_title: FormatStr[P.MultiFillupTopN] = Field(
        description='Title for suspicious events table (includes top_n placeholder)'
    )
    table_headers: MultiFillupAnalysisTableHeaders
    legend_title: str = Field(description='Title for red flag legend section')
