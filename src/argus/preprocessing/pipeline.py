# argus/preprocessor/pipeline.py
"""
Main orchestrator for the complete data preprocessing pipeline.

This module provides the primary entry point for transforming raw fuel card
transaction data into analysis-ready datasets. It coordinates all preprocessing
stages in the correct sequence, handles error propagation, manages logging,
and packages results into a standardized AnalysisContext object.

Functions:
    run_data_preparation: Execute complete preprocessing pipeline

Pipeline Stages (in execution order):
    1. Data Cleaning (DataCleaner)
       - Standardize column names
       - Validate schema
       - Remove duplicates
       - Filter incomplete months
       - Enforce data constraints

    2. Temporal Feature Engineering (TemporalFeatureEngineer)
       - Extract date/time components
       - Create business hours flags
       - Generate rush hour indicators
       - Categorize time periods

    3. Transaction Feature Engineering (TransactionFeatureEngineer)
       - Standardize product categories
       - Calculate cost per gallon
       - Categorize transaction sizes
       - Count fillups per day
       - Create location groupings

    4. Vehicle Feature Engineering (VehicleFeatureEngineer)
       - Calculate fuel efficiency (MPG)
       - Compute idle percentages
       - Compute driving percentages

    5. ELD Processing (ELDDataHandler)
       - Detect aggregation type (daily vs granular)
       - Create ELD activity flags
       - Handle duplicate distances appropriately

    6. Quality Assessment (DataQualityAssessor)
       - Evaluate completeness
       - Detect outliers
       - Validate data integrity
       - Document quality metrics

    7. Data Splitting (DataSplitter)
       - Determine analysis period
       - Split by location (target vs peers)
       - Split by time (recent vs historical)
       - Generate split metadata

    8. Report Generation
       - Document preparation steps
       - Report quality metrics
       - Describe analysis scope
       - Record pipeline decisions

Pipeline Output (AnalysisContext):
    The pipeline returns a single AnalysisContext object containing:

    Datasets:
        - complete_unsplit_transactions: All cleaned and enriched data
        - target_period_transactions: Recent data at target location
        - peer_period_transactions: Recent data at peer locations
        - target_historical_transactions: All-time target location data
        - peer_historical_transactions: All-time peer location data

    Metadata:
        - analysis_period_label: Human-readable date range
        - target_location_number: Integer ID of target location
        - target_location_name: Human-readable location name

    Tools:
        - report_writer: For writing forensic report sections
        - report_formatter: For formatting output consistently
        - config: Complete configuration object

Error Handling:
    - Validation errors raise immediately (fail fast)
    - Quality issues log warnings but continue
    - Empty datasets after splitting log warnings
    - All errors include context for debugging

Logging Strategy:
    - INFO: Pipeline milestones and summary statistics
    - DEBUG: Detailed operation progress
    - WARNING: Quality issues and empty datasets
    - ERROR: Validation failures and critical issues

Usage Example:
    from argus.preprocessing import run_data_preparation
    from argus.config import FuelCardForensicsConfig
    from argus.output_formatter import ForensicReportWriter
    from argus.utils import ReportFormatter

    # Load configuration
    config = FuelCardForensicsConfig.from_yaml('config.yaml')

    # Initialize reporting tools
    writer = ForensicReportWriter()
    formatter = ReportFormatter()

    # Load raw data
    raw_df = pd.read_csv('fuel_transactions.csv')

    # Execute pipeline
    context = run_data_preparation(
        raw_dataframe=raw_df,
        report_writer=writer,
        report_formatter=formatter,
        config=config
    )

    # Access prepared data
    print(f"Target period: {len(context.target_period_transactions)} transactions")
    print(f"Analysis period: {context.analysis_period_label}")

    # Proceed to fraud detection analysis
    from argus.risk_analysis import run_risk_identification_analysis
    driver_profiles, volume_profiles = run_risk_identification_analysis(context)

Performance Considerations:
    - Pipeline processes entire dataset in memory
    - Feature engineering is vectorized (pandas operations)
    - Typical runtime: 1-5 seconds per 100K transactions
    - Memory usage: ~5-10x raw data size (due to feature columns)

Data Requirements:
    - Input must have all required columns (validated during cleaning)
    - Timestamps must be parseable to datetime
    - Numeric columns should be numeric types or coercible
    - Missing data is acceptable and handled appropriately

Configuration Dependencies:
    - Column mapping: Required for standardization
    - Business hours: Required for temporal features
    - Target location: Required for spatial splitting
    - Analysis parameters: Control splitting and filtering behavior
"""
import logging
from typing import Any

import pandas as pd

from argus.config import FuelCardForensicsConfig
from argus.output_formatter import ForensicReportWriter
from argus.preprocessing.cleaning import DataCleaner
from argus.preprocessing.data_splitter import DataSplitter
from argus.preprocessing.eld_processing import ELDDataHandler
from argus.preprocessing.feature_engineering import (
    TemporalFeatureEngineer,
    TransactionFeatureEngineer,
    VehicleFeatureEngineer,
)
from argus.preprocessing.quality_assessment import DataQualityAssessor
from argus.utils import AnalysisContext, ReportFormatter

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)


def run_data_preparation(
    raw_dataframe: pd.DataFrame,
    report_writer: ForensicReportWriter,
    report_formatter: ReportFormatter,
    config: FuelCardForensicsConfig,
) -> AnalysisContext:
    """
    Orchestrate the complete data preparation and feature engineering pipeline.

    This function coordinates all preprocessing steps:
    1. Data cleaning (deduplication, validation, filtering)
    2. Feature engineering (temporal, transaction, vehicle)
    3. ELD data processing
    4. Data quality assessment
    5. Data splitting for analysis
    6. Report generation

    Args:
        raw_dataframe: Raw input DataFrame with user-specific column names
        report_writer: Report writer for documenting preparation steps
        report_formatter: Formatter for creating readable output
        config: Complete configuration object

    Returns:
        AnalysisContext containing all prepared datasets and metadata
    """
    logger.info('Starting data preparation pipeline')

    # Clean raw data
    cleaner: DataCleaner = DataCleaner(config)
    cleaned_df: pd.DataFrame
    cleaning_stats: dict[str, int]
    cleaned_df, cleaning_stats = cleaner.clean(raw_dataframe)

    report_writer.write_data_preparation_summary(
        initial_rows=cleaning_stats['initial_rows'],
        final_rows=cleaning_stats['final_rows'],
        duplicates_removed=cleaning_stats['duplicates_removed'],
        incomplete_records_removed=cleaning_stats['incomplete_removed'],
    )

    # Engineer temporal features
    temporal_engineer: TemporalFeatureEngineer = TemporalFeatureEngineer(config)
    enriched_df: pd.DataFrame = temporal_engineer.engineer_features(cleaned_df)

    # Engineer transaction features
    transaction_engineer: TransactionFeatureEngineer = TransactionFeatureEngineer(
        config
    )
    enriched_df = transaction_engineer.engineer_features(enriched_df)

    # Engineer vehicle features
    vehicle_engineer: VehicleFeatureEngineer = VehicleFeatureEngineer()
    enriched_df = vehicle_engineer.engineer_features(enriched_df)

    # Process ELD data
    eld_handler: ELDDataHandler = ELDDataHandler()
    enriched_df = eld_handler.process_eld_data(enriched_df)

    # Assess data quality
    quality_assessor: DataQualityAssessor = DataQualityAssessor()
    quality_report: dict[str, Any] = quality_assessor.assess(enriched_df)

    report_writer.write_data_quality_summary(
        quality_report=quality_report,
        duplicates_removed=cleaning_stats['duplicates_removed'],
        total_records=cleaning_stats['final_rows'],
    )

    # Create full historical datasets by location
    target_location_name: str = config.analysis.target_location_name

    full_target_location: pd.DataFrame = enriched_df[
        enriched_df['branch_group'] == target_location_name
    ].copy()

    full_peer_locations: pd.DataFrame = enriched_df[
        enriched_df['branch_group'] == 'Other Branches'
    ].copy()

    # Split data for focused analysis period
    splitter: DataSplitter = DataSplitter(config.analysis)
    target_period: pd.DataFrame
    peer_period: pd.DataFrame
    split_info: dict[str, Any]
    target_period, peer_period, split_info = splitter.split(enriched_df)

    report_writer.write_data_split_summary(
        split_status=split_info['split_status'],
        min_year=split_info['min_year'],
        current_year=split_info['current_year'],
        num_months_current_year=split_info['num_months_current_year'],
    )

    # Calculate analysis period label
    combined_period_df: pd.DataFrame = pd.concat([target_period, peer_period])
    date_min: pd.Timestamp = combined_period_df['datetime_parsed'].min()
    date_max: pd.Timestamp = combined_period_df['datetime_parsed'].max()

    analysis_period: str = report_formatter.calculate_analysis_period_label(
        date_min, date_max
    )

    report_writer.set_analysis_period(analysis_period)

    # Write analysis scope summary
    report_writer.write_analysis_scope_details(
        target_location=target_location_name,
        num_other_branches=int(peer_period['location_index'].nunique()),
        date_min=date_min,
        date_max=date_max,
        total_transactions=len(combined_period_df),
    )

    # Validate that we have data to analyze
    if target_period.empty or peer_period.empty:
        logger.warning(
            'Insufficient data for analysis. Target: %d rows, Peers: %d rows',
            len(target_period),
            len(peer_period),
        )

    logger.info(
        'Data preparation complete. Target period: %d rows, Peer period: %d rows',
        len(target_period),
        len(peer_period),
    )

    return AnalysisContext(
        complete_unsplit_transactions=enriched_df,
        target_period_transactions=target_period,
        peer_period_transactions=peer_period,
        target_historical_transactions=full_target_location,
        peer_historical_transactions=full_peer_locations,
        analysis_period_label=analysis_period,
        target_location_number=config.analysis.target_location_number,
        target_location_name=target_location_name,
        report_writer=report_writer,
        report_formatter=report_formatter,
        config=config,
    )
