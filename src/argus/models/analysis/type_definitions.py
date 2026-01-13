# argus/models/analysis/type_definitions.py

# This file contains type definitions used throughout the analysis models.

from typing import Literal

from argus.models.analysis.driver_risk import DriverRiskProfile
from argus.models.analysis.vehicle_risk import VehicleRiskProfile

__all__: list[str] = [
    'Direction',
    'EntityType',
    'RiskProfile',
]

# Valid entity types
EntityType = Literal['Driver', 'Vehicle']

# Valid direction values
Direction = Literal['higher', 'lower']

# Type aliases for convenience
RiskProfile = DriverRiskProfile | VehicleRiskProfile
"""Union type for any risk profile (Driver or Vehicle)"""

# THESE DON'T APPEAR TO BE USED ANYWHERE IN THE CODEBASE
# Composite type alias
# CompositeInterpType = (
#     TestInterpretationsCostDistributionSignificant
#     | TestInterpretationsCostDistributionNotSignificant
#     | TestInterpretationsRateComparisonSignificant
#     | TestInterpretationsRateComparisonNotSignificant
#     | None
# )
# CompositeTableHeadersType = (
#     DriverAnalysisTableHeaders
#     | VehicleAnalysisTableHeaders
#     | MultipleTestingCorrectionTableHeaders
#     | MultiFillupAnalysisTableHeaders
#     | GeographicAnalysisTableHeaders
#     | ReportFooterTestSummaryTableHeaders
# )
