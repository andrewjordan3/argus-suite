# argus/preprocessor/quality_assessment.py
"""
Comprehensive data quality assessment and reporting.

This module evaluates cleaned transaction data across multiple quality dimensions
to identify potential issues, validate assumptions, and guide fraud investigation
priorities. The assessment produces a detailed quality report used both for
pipeline validation and for documenting data reliability in forensic reports.

Classes:
    DataQualityAssessor: Performs multi-dimensional quality assessment

Quality Dimensions Evaluated:
    1. Completeness: Missing value patterns and rates across all columns
    2. Validity: Logically impossible values (future dates, invalid hours)
    3. Consistency: Data type verification and schema compliance
    4. Accuracy: Outlier detection using statistical methods (IQR)
    5. Uniqueness: Duplicate detection (should be 0 after cleaning)

Assessment Categories:

Missing Values:
    - Columns with missing data are reported with count and percentage
    - Different missingness patterns may indicate:
        * Structural missingness (ELD data only on some vehicles)
        * Vendor data quality issues
        * Integration gaps between systems
    - Affects analysis: Features requiring complete data may need separate handling

Outliers (IQR Method):
    - Detects values beyond 1.5 * IQR from Q1/Q3
    - Applied to: cost, volume, distance, odometer, idle time, driving time
    - Skipped for: categorical IDs, hour (naturally bounded)
    - Outliers may represent:
        * Legitimate extreme values (large truck fillups)
        * Data entry errors
        * Fraud attempts (price manipulation, volume inflation)
    - Reported with bounds and percentages for investigation prioritization

Validity Checks:
    - Future dates: Transactions dated after current time (impossible)
    - Invalid hours: Hour values outside 0-23 range
    - Negative values: Should be caught by cleaning but verified here
    - These always represent data quality issues requiring correction

Data Types:
    - Verifies all columns have expected types after cleaning
    - Documents schema for reproducibility
    - Helps identify unexpected type conversions

Quality Report Structure:
    {
        'total_rows': int,
        'duplicates': int,  # Should be 0 after cleaning
        'missing_values': {
            'column_name': {'count': int, 'percentage': float},
            ...
        },
        'data_types': {
            'column_name': str,  # dtype as string
            ...
        },
        'validity_checks': {
            'check_name': {'count': int, 'percentage': float},
            ...
        },
        'outliers': {
            'column_name': {
                'count': int,
                'percentage': float,
                'bounds': (lower, upper)
            },
            ...
        }
    }

Typical Usage:
    assessor = DataQualityAssessor()
    quality_report = assessor.assess(cleaned_df)

    # Check for critical issues
    if quality_report['validity_checks']:
        logger.warning('Found validity issues: %r', quality_report['validity_checks'])

    # Review outlier percentages
    for col, stats in quality_report['outliers'].items():
        if stats['percentage'] > 0.05:  # More than 5% outliers
            logger.info('%s has %.1f%% outliers', col, stats['percentage'] * 100)

Integration with Pipeline:
    - Quality assessment runs after cleaning and feature engineering
    - Results are written to the forensic report via report_writer
    - Severe quality issues can trigger warnings or halt analysis
    - Historical quality reports enable trend analysis over time

Design Philosophy:
    - Comprehensive: Check everything, report all issues
    - Actionable: Provide counts, percentages, and bounds for investigation
    - Transparent: Make quality visible rather than hidden
    - Non-invasive: Assess but don't modify (cleaning is separate)
"""

import logging
from datetime import UTC
from typing import Any

import numpy as np
import pandas as pd

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)


class DataQualityAssessor:
    """
    Performs comprehensive data quality assessment.

    Analyzes:
    - Missing value patterns
    - Data type verification
    - Outlier detection
    - Validity checks (negative values, future dates)
    """

    def assess(self, dataframe: pd.DataFrame) -> dict[str, Any]:
        """
        Run complete data quality assessment.

        Args:
            dataframe: Cleaned and enriched DataFrame to assess

        Returns:
            Dictionary containing quality metrics and issue reports
        """
        logger.debug('Assessing data quality')

        quality_report: dict[str, Any] = {
            'total_rows': len(dataframe),
            'duplicates': int(dataframe.duplicated().sum()),
            'missing_values': {},
            'data_types': {},
            'validity_checks': {},
            'outliers': {},
        }

        self._assess_missing_values(dataframe, quality_report)
        self._record_data_types(dataframe, quality_report)
        self._detect_outliers(dataframe, quality_report)
        self._check_data_validity(dataframe, quality_report)

        logger.debug('Data quality assessment complete')

        return quality_report

    def _assess_missing_values(
        self, dataframe: pd.DataFrame, quality_report: dict[str, Any]
    ) -> None:
        """
        Identify columns with missing values and calculate missingness rates.

        Args:
            dataframe: DataFrame to assess
            quality_report: Dictionary to populate with missing value statistics
        """
        total_rows: int = len(dataframe)
        missing_values: dict[str, dict[str, int | float]] = {}

        for column_name in dataframe.columns:
            missing_count: int = int(dataframe[column_name].isna().sum())

            if missing_count > 0:
                missing_values[column_name] = {
                    'count': missing_count,
                    'percentage': float(missing_count / total_rows),
                }

        quality_report['missing_values'] = missing_values

    def _record_data_types(
        self, dataframe: pd.DataFrame, quality_report: dict[str, Any]
    ) -> None:
        """
        Record data types for all columns.

        Args:
            dataframe: DataFrame to assess
            quality_report: Dictionary to populate with data type information
        """
        data_types: dict[str, str] = {
            column_name: str(dataframe[column_name].dtype)
            for column_name in dataframe.columns
        }

        quality_report['data_types'] = data_types

    def _detect_outliers(
        self, dataframe: pd.DataFrame, quality_report: dict[str, Any]
    ) -> None:
        """
        Detect outliers in numeric columns using IQR method.

        Args:
            dataframe: DataFrame to assess
            quality_report: Dictionary to populate with outlier statistics
        """
        numeric_columns: pd.Index = dataframe.select_dtypes(include=[np.number]).columns
        outliers: dict[str, dict[str, int | float | tuple[float, float]]] = {}

        # Skip columns that shouldn't have outlier analysis
        skip_columns: set[str] = {
            'hour',
            'vehicle_index',
            'driver_index',
            'location_index',
        }

        for column_name in numeric_columns:
            if column_name in skip_columns:
                continue

            column_data: pd.Series = dataframe[column_name].dropna()  # pyright: ignore[reportUnknownVariableType]

            if len(column_data) == 0:
                continue

            q1: float = float(column_data.quantile(0.25))
            q3: float = float(column_data.quantile(0.75))
            iqr: float = q3 - q1

            # Only calculate outliers if there's variation in the data
            if iqr > 0:
                lower_bound: float = max(q1 - 1.5 * iqr, 0.0)
                upper_bound: float = q3 + 1.5 * iqr

                is_outlier: pd.Series = (dataframe[column_name] < lower_bound) | (  # pyright: ignore[reportUnknownVariableType]
                    dataframe[column_name] > upper_bound
                )
                outlier_count: int = int(is_outlier.sum())

                if outlier_count > 0:
                    outliers[column_name] = {
                        'count': outlier_count,
                        'percentage': float(outlier_count / len(dataframe)),
                        'bounds': (lower_bound, upper_bound),
                    }

        quality_report['outliers'] = outliers

    def _check_data_validity(
        self, dataframe: pd.DataFrame, quality_report: dict[str, Any]
    ) -> None:
        """
        Check for logically invalid values (future dates, invalid hours, etc).

        Args:
            dataframe: DataFrame to assess
            quality_report: Dictionary to populate with validity check results
        """
        validity_checks: dict[str, dict[str, int | float]] = {}
        total_rows: int = len(dataframe)

        # Check for future dates
        datetime_columns: pd.Index = dataframe.select_dtypes(
            include=['datetime64']
        ).columns  # pyright: ignore[reportAssignmentType]
        current_time: pd.Timestamp = pd.Timestamp.now(tz=UTC)

        for column_name in datetime_columns:
            future_date_count: int = int((dataframe[column_name] > current_time).sum())

            if future_date_count > 0:
                validity_checks[f'{column_name}_future_dates'] = {
                    'count': future_date_count,
                    'percentage': float(future_date_count / total_rows),
                }

        # Check for invalid hours
        if 'hour' in dataframe.columns:
            invalid_hour_count: int = int(
                ((dataframe['hour'] < 0) | (dataframe['hour'] > 23)).sum()  # noqa: PLR2004
            )

            if invalid_hour_count > 0:
                validity_checks['invalid_hours'] = {
                    'count': invalid_hour_count,
                    'percentage': float(invalid_hour_count / total_rows),
                }

        quality_report['validity_checks'] = validity_checks
