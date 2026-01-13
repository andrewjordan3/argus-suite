# argus/formatting/report_sections.py

############################################################################
# NOTE: This will be moved to the user_config yaml file in the future.
############################################################################
from enum import Enum


class ReportSection(Enum):
    """
    Enum for report sections that controls rendering order.

    IMPORTANT: The order defined here determines the sequence in which
    sections appear in the final report. The section names should correspond
    to keys in the report_config.yaml file.

    Order Philosophy:
    - Executive Summary comes early (after header) for busy stakeholders
    - Methodology establishes credibility before presenting findings
    - Data quality/scope show the analysis is sound
    - Statistical findings flow from general to specific
    - Footer contains disclaimers and metadata
    """

    HEADER = 1  # Report title, dates, metadata
    EXECUTIVE_SUMMARY = 2  # Key findings upfront (moved up for executives)
    METHODOLOGY = 3  # Statistical approach and interpretation guide
    DATA_QUALITY = 4  # Data preparation and quality assessment
    ANALYSIS_SCOPE = 5  # What data is being analyzed
    KEY_METRICS = 6  # Main statistical tests and findings
    MULTIPLE_TESTING_CORRECTION = 7  # FDR correction details
    FINANCIAL_IMPACT = 8  # Quantified risk and exposure
    DRIVER_ANALYSIS = 9  # Driver-level deep dives
    VEHICLE_ANALYSIS = 10  # Vehicle-level deep dives
    TEMPORAL_ANALYSIS = 11  # Time-based pattern analysis
    FOOTER = 12  # Disclaimers, coverage, metadata
