# argus/models/locale/driver_analysis.py
"""
============================================================================
DRIVER ANALYSIS
============================================================================
Content for driver-level risk analysis including summary tables and
detailed driver profiles. The summary table highlights high-risk drivers with
key metrics, while the detailed driver profiles offer a comprehensive analysis
of their transaction patterns.
============================================================================
"""

from pydantic import Field

from argus.models.common import FormatStr, FormatStrList, FrozenModel, P

__all__: list[str] = [
    'DriverAnalysis',
    'DriverAnalysisDeepDive',
    'DriverAnalysisDeepDiveSections',
    'DriverAnalysisTableHeaders',
]


class DriverAnalysisTableHeaders(FrozenModel):
    """
    Column headers for driver risk summary table.

    The summary table shows high-risk drivers with key metrics.

    Attributes:
        driver: Header for driver name column
        risk_score: Header for risk score column
        transactions: Header for transaction count column
        no_eld_pct: Header for no-ELD-match percentage column
        non_diesel_pct: Header for non-diesel purchase percentage column
        after_hours_pct: Header for after-hours transaction percentage column
        avg_cost: Header for average transaction cost column
    """

    driver: str = Field(description='Column header for driver name')
    risk_score: str = Field(
        description='Column header for calculated risk score (0-100)'
    )
    transactions: str = Field(description='Column header for total transaction count')
    no_eld_pct: str = Field(
        description='Column header for percentage without ELD match'
    )
    non_diesel_pct: str = Field(
        description='Column header for percentage of non-diesel purchases'
    )
    after_hours_pct: str = Field(
        description='Column header for percentage of after-hours transactions'
    )
    avg_cost: str = Field(description='Column header for average transaction cost')


class DriverAnalysisDeepDiveSections(FrozenModel):
    """
    Section content for detailed driver profile deep dive.

    Each high-risk driver gets a detailed analysis with multiple subsections.

    Attributes:
        risk_score: Template for risk score display
        transaction_summary: Header for transaction summary subsection
        transaction_items: list of transaction summary line items
        risk_indicators: Header for risk indicators subsection
        risk_items: list of risk indicator line items
        product_breakdown: Header for product breakdown subsection
        product_format: Format string for product line items
        multi_fillup: Header for multi-fillup analysis subsection
        multi_fillup_items: list of multi-fillup statistic line items
    """

    risk_score: FormatStr[P.DriverRiskScore] = Field(
        description='Format string for risk score display with category'
    )
    transaction_summary: str = Field(
        description='Header for transaction summary subsection'
    )
    transaction_items: FormatStrList[P.DriverTransactionItems] = Field(
        description='list of transaction summary line items (with placeholders)'
    )
    risk_indicators: str = Field(
        description='Header for key risk indicators subsection'
    )
    risk_items: FormatStrList[P.DriverRiskItems] = Field(
        description='list of risk indicator line items (with placeholders)'
    )
    product_breakdown: str = Field(
        description='Header for product purchase breakdown subsection'
    )
    product_format: FormatStr[P.DriverProductBreakdown] = Field(
        description='Format string for individual product line items'
    )
    multi_fillup: str = Field(
        description='Header for multiple fillup analysis subsection'
    )
    multi_fillup_items: FormatStrList[P.DriverMultiFillupItems] = Field(
        description='list of multi-fillup statistic line items (with placeholders)'
    )


class DriverAnalysisDeepDive(FrozenModel):
    """
    Configuration for detailed driver profile section.

    After the summary table, high-risk drivers receive detailed profiles
    with comprehensive analysis of their transaction patterns.

    Attributes:
        title: Title template for driver profile (includes driver name)
        sections: All section headers and content for the profile
    """

    title: FormatStr[P.DriverDeepDiveTitle] = Field(
        description='Title template for driver profile (includes driver name placeholder)'
    )
    sections: DriverAnalysisDeepDiveSections


class DriverAnalysis(FrozenModel):
    """
    Complete driver analysis section configuration.

    Includes both summary table of high-risk drivers and detailed
    profile configurations.

    Attributes:
        table_title: Title for driver risk summary table
        table_headers: Column headers for summary table
        deep_dive: Configuration for detailed driver profiles
    """

    table_title: str = Field(description='Title for the driver risk summary table')
    table_headers: DriverAnalysisTableHeaders
    deep_dive: DriverAnalysisDeepDive
