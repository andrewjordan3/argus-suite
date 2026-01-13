# argus/models/locale/vehicle_analysis.py
"""
============================================================================
VEHICLE ANALYSIS
============================================================================
Content for vehicle-level risk analysis summary table. (Note: Deep dive profiles
are not currently implemented for vehicles but could be added following the driver
analysis pattern.)
============================================================================
"""

from pydantic import Field

from argus.models.common import BaseConfigModel

__all__: list[str] = ['VehicleAnalysis', 'VehicleAnalysisTableHeaders']


class VehicleAnalysisTableHeaders(BaseConfigModel):
    """
    Column headers for vehicle risk summary table.

    Similar to driver analysis but focused on vehicle assets.

    Attributes:
        vehicle: Header for vehicle identifier (VIN) column
        primary_driver: Header for primary driver column
        risk_score: Header for risk score column
        transactions: Header for transaction count column
        no_eld_pct: Header for no-ELD-match percentage column
        avg_cost: Header for average transaction cost column
    """

    vehicle: str = Field(
        description='Column header for vehicle identifier (typically VIN)'
    )
    primary_driver: str = Field(
        description='Column header for most frequent driver of this vehicle'
    )
    risk_score: str = Field(
        description='Column header for calculated risk score (0-100)'
    )
    transactions: str = Field(description='Column header for total transaction count')
    no_eld_pct: str = Field(
        description='Column header for percentage without ELD match'
    )
    avg_cost: str = Field(description='Column header for average transaction cost')


class VehicleAnalysis(BaseConfigModel):
    """
    Complete vehicle analysis section configuration.

    Provides summary table of high-risk vehicles. (Note: Deep dive profiles
    are not currently implemented for vehicles but could be added following
    the driver analysis pattern.)

    Attributes:
        table_title: Title for vehicle risk summary table
        table_headers: Column headers for summary table
    """

    table_title: str = Field(description='Title for the vehicle risk summary table')
    table_headers: VehicleAnalysisTableHeaders
