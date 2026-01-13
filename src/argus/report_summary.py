# ARGUS/report_summary.py

import logging

import pandas as pd

from .output_formatter import ForensicReportWriter
from .models import StatisticalTest

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)


def generate_report_summary(
    report_writer: ForensicReportWriter,
    all_tests: dict[str, StatisticalTest],
    full_df: pd.DataFrame,
    target_location_df: pd.DataFrame,
    others_df: pd.DataFrame,
) -> None:
    """
    Generate the executive summary and footer sections of the forensic report.

    This function orchestrates the final report sections by collecting the necessary
    data and delegating formatting to the ForensicReportWriter.

    Args:
        report_writer: Instance of ForensicReportWriter for output
        all_tests: dictionary of all completed StatisticalTest objects
        full_df: Complete combined DataFrame before any time-based splitting
        target_location_df: DataFrame for target branch (potentially time-filtered)
        others_df: DataFrame for other branches (potentially time-filtered)
    """
    # Generate executive summary
    report_writer.write_executive_summary(all_tests)

    # Prepare data coverage statistics
    data_coverage: dict[str, int | float] = {
        'total_records': len(full_df),
        'analysis_records': len(target_location_df) + len(others_df),
        'target_records': len(target_location_df),
        'other_records': len(others_df),
        'eld_match_rate': (
            full_df['has_eld_activity'].mean()
            if 'has_eld_activity' in full_df.columns
            else 0.0
        ),
    }

    # Generate footer
    report_writer.write_report_footer(all_tests, data_coverage)
