# argus/schemas/geographic.py
"""
============================================================================
GEOGRAPHIC ANALYSIS
============================================================================
Content for analyzing station usage patterns and identifying geographic
anomalies that may indicate fraud. This includes identifying stations with
suspicious transaction patterns that may indicate fraudulent activity.
============================================================================
"""

from pydantic import Field

from argus.models.common import BaseConfigModel, FormatStr, P

__all__: list[str] = [
    'GeographicAnalysis',
    'GeographicAnalysisSuspiciousFlagFormats',
    'GeographicAnalysisSuspiciousStations',
    'GeographicAnalysisTableHeaders',
]

class GeographicAnalysisTableHeaders(BaseConfigModel):
    """
    Column headers for station usage table.

    Shows most-used stations with suspicious pattern indicators.

    Attributes:
        station_name: Header for station name column
        transactions: Header for transaction count column
        pct_total: Header for percentage of total transactions column
        drivers: Header for number of unique drivers column
        non_diesel_pct: Header for non-diesel percentage column
        no_eld_pct: Header for no-ELD-match percentage column
        avg_cost: Header for average cost column
    """

    station_name: str = Field(description='Column header for fuel station name')
    transactions: str = Field(
        description='Column header for transaction count (abbreviated)'
    )
    pct_total: str = Field(
        description="Column header for percentage of location's total transactions"
    )
    drivers: str = Field(
        description='Column header for number of unique drivers using this station'
    )
    non_diesel_pct: str = Field(
        description='Column header for percentage of non-diesel purchases'
    )
    no_eld_pct: str = Field(
        description='Column header for percentage without ELD match'
    )
    avg_cost: str = Field(description='Column header for average transaction cost')


class GeographicAnalysisSuspiciousFlagFormats(BaseConfigModel):
    """
    Format strings for suspicious station characteristics.

    Templates for displaying specific suspicious patterns found at stations.

    Attributes:
        high_non_diesel: Format for high non-diesel rate
        high_no_eld: Format for high no-ELD rate
        low_avg_cost: Format for suspiciously low average cost
    """

    high_non_diesel: FormatStr[P.GeoFlagRate] = Field(
        description='Format string for displaying high non-diesel rate'
    )
    high_no_eld: FormatStr[P.GeoFlagRate] = Field(
        description='Format string for displaying high no-ELD rate'
    )
    low_avg_cost: FormatStr[P.GeoFlagCost] = Field(
        description='Format string for displaying low average cost'
    )


class GeographicAnalysisSuspiciousStations(BaseConfigModel):
    """
    Configuration for suspicious stations subsection.

    Highlights stations with concerning patterns that warrant investigation.

    Attributes:
        title: Subsection title
        format: Format string for station line items
        flag_separator: Separator between multiple flags
        flag_formats: Format strings for individual flag types
    """

    title: str = Field(description='Title for suspicious stations subsection')
    format: FormatStr[P.GeoSuspiciousStationFormat] = Field(
        description='Format string for station line items (includes placeholders)'
    )
    flag_separator: str = Field(
        description="Character(s) to separate multiple flags (typically ' | ')"
    )
    flag_formats: GeographicAnalysisSuspiciousFlagFormats


class GeographicAnalysis(BaseConfigModel):
    """
    Complete geographic analysis section configuration.

    Analyzes which fuel stations are used most frequently and identifies
    stations with suspicious transaction patterns.

    Attributes:
        section_title: Title for geographic analysis section
        introduction: Introductory paragraph about the analysis
        table_title: Title for station usage table
        table_headers: Column headers for usage table
        suspicious_stations: Configuration for suspicious stations subsection
    """

    section_title: str = Field(description='Title for the geographic analysis section')
    introduction: str = Field(
        description='Introduction explaining the purpose of geographic analysis'
    )
    table_title: FormatStr[P.GeoTableTitle] = Field(
        description='Title for station usage table (includes top_n placeholder)'
    )
    table_headers: GeographicAnalysisTableHeaders
    suspicious_stations: GeographicAnalysisSuspiciousStations
