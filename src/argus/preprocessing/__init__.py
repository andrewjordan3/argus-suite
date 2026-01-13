# argus/preprocessing/__init__.py
"""
Data preprocessing pipeline for fuel card forensics analysis.

This package provides comprehensive data preparation and feature engineering
for fuel card transaction data, transforming raw vendor data into analysis-ready
datasets with enriched features and quality validation.

The preprocessing pipeline includes:
- Data cleaning and validation (duplicate removal, schema enforcement)
- Temporal feature engineering (business hours, weekdays, time categories)
- Transaction feature engineering (cost metrics, product standardization)
- Vehicle feature engineering (fuel efficiency, idle percentages)
- ELD data processing (handling both daily aggregates and granular data)
- Data quality assessment (missing values, outliers, validity checks)
- Data splitting (temporal and spatial stratification for analysis)

Public API:
    run_data_preparation: Main orchestrator function that executes the complete pipeline

Usage:
    from argus.preprocessing import run_data_preparation

    context = run_data_preparation(
        raw_dataframe=df,
        report_writer=writer,
        report_formatter=formatter,
        config=config
    )

The pipeline returns an AnalysisContext object containing:
- Complete unsplit transactions (all historical data)
- Target period transactions (focus period for target location)
- Peer period transactions (focus period for comparison locations)
- Target historical transactions (all-time target location data)
- Peer historical transactions (all-time peer location data)
- Analysis period label (human-readable date range)
- Configuration and reporting tools
"""

from argus.preprocessing.pipeline import run_data_preparation

__all__: list[str] = ['run_data_preparation']
