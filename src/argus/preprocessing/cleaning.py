# argus/preprocessor/cleaning.py
"""
Data cleaning operations for fuel card transaction data.

This module handles initial data quality and standardization operations that
prepare raw vendor data for feature engineering and analysis. The DataCleaner
class applies a series of transformations to ensure data consistency, completeness,
and validity before downstream processing.

Classes:
    DataCleaner: Orchestrates all data cleaning operations

Cleaning Operations:
    1. Column Standardization: Maps vendor-specific column names to standard schema
    2. Schema Validation: Verifies all required columns exist after renaming
    3. Column Filtering: Retains only columns needed for analysis
    4. Whitespace Normalization: Converts empty strings and whitespace to NaN
    5. Duplicate Removal: Eliminates exact duplicate rows
    6. Timestamp Parsing: Converts timestamps to timezone-aware datetime objects
    7. Incomplete Month Filtering: Removes partial trailing months to avoid bias
    8. Positive Value Enforcement: Converts negative values to positive for certain columns

The cleaning process is conservative and defensive - it removes problematic records
rather than attempting complex imputation, ensuring that analysis is based on
reliable data rather than inferred values.

Typical Usage:
    cleaner = DataCleaner(config)
    cleaned_df, stats = cleaner.clean(raw_dataframe)

    # stats contains:
    # - initial_rows: Starting record count
    # - duplicates_removed: Count of duplicate rows eliminated
    # - incomplete_removed: Records from incomplete trailing month
    # - final_rows: Ending record count after all cleaning

Design Philosophy:
    - Fail fast: Raise errors immediately if required data is missing
    - Be explicit: Log all transformations and their impacts
    - Preserve history: Track and report all modifications via statistics
    - Minimize inference: Remove bad data rather than guess corrections
"""
import logging
from typing import ClassVar

import numpy as np
import pandas as pd

from argus.config import FuelCardForensicsConfig

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)

# Type definition for allowed column types in our schema
# Using a union of specific Pandas Dtypes for strict typing
type column_types = pd.StringDtype | pd.Float64Dtype | pd.Int64Dtype | pd.DatetimeTZDtype

class DataCleaner:
    """
    Handles initial data cleaning operations.

    Responsibilities:
    - Column renaming and validation
    - Duplicate removal
    - Missing value handling
    - Incomplete month filtering
    - Data type enforcement
    """

    # Type specifications for all columns (defined once at class level)
    TYPE_SPECIFICATIONS: ClassVar[dict[str, column_types]] = {
        'vehicle_id': pd.StringDtype(),
        'transaction_timestamp': pd.DatetimeTZDtype(unit='ns', tz='UTC'),
        'driver_name': pd.StringDtype(),
        'merchant_name': pd.StringDtype(),
        'merchant_address': pd.StringDtype(),
        'assigned_location': pd.StringDtype(),
        'transaction_amount': pd.Float64Dtype(),
        'fuel_volume_gallons': pd.Float64Dtype(),
        'product_category': pd.StringDtype(),
        'odometer_miles': pd.Int64Dtype(),
        'vehicle_index': pd.Int64Dtype(),
        'driver_index': pd.Int64Dtype(),
        'location_index': pd.Int64Dtype(),
        'vehicle_description': pd.StringDtype(),
        'driver_pin': pd.Int64Dtype(),
        'geographic_region': pd.StringDtype(),
        'distance_miles': pd.Float64Dtype(),
        'idle_duration_minutes': pd.Float64Dtype(),
        'driving_duration_minutes': pd.Float64Dtype(),
        'engine_runtime_minutes': pd.Float64Dtype(),
    }

    def __init__(self, config: FuelCardForensicsConfig) -> None:
        """
        Initialize data cleaner with configuration.

        Args:
            config: Full configuration object containing mapping and business rules
        """
        self.config: FuelCardForensicsConfig = config

    def clean(self, raw_dataframe: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
        """
        Execute complete data cleaning pipeline.

        Args:
            raw_dataframe: Raw input DataFrame with user-specific column names

        Returns:
            Tuple of (cleaned_df, cleaning_statistics)

        Raises:
            ValueError: If required columns are missing after renaming
        """
        logger.info('Starting data cleaning pipeline')

        initial_row_count: int = len(raw_dataframe)

        cleaned_df: pd.DataFrame = self._standardize_column_names(raw_dataframe)
        self._validate_required_columns(cleaned_df)

        cleaned_df = self._filter_to_required_columns(cleaned_df)
        cleaned_df = self._normalize_whitespace_and_nulls(cleaned_df)

        duplicates_removed: int
        cleaned_df, duplicates_removed = self._remove_duplicates(cleaned_df)

        cleaned_df = self._parse_timestamps(cleaned_df)
        cleaned_df = self._enforce_types(cleaned_df)

        incomplete_removed: int
        cleaned_df, incomplete_removed = self._filter_incomplete_months(cleaned_df)

        cleaned_df = self._enforce_positive_values(cleaned_df)

        final_row_count: int = len(cleaned_df)

        cleaning_statistics: dict[str, int] = {
            'initial_rows': initial_row_count,
            'duplicates_removed': duplicates_removed,
            'incomplete_removed': incomplete_removed,
            'final_rows': final_row_count,
        }

        logger.info(
            'Data cleaning complete. Rows: %d -> %d (-%d duplicates, -%d incomplete)',
            initial_row_count,
            final_row_count,
            duplicates_removed,
            incomplete_removed,
        )

        return cleaned_df, cleaning_statistics

    def _standardize_column_names(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Apply user-provided column name mapping to standardize column names.

        Args:
            dataframe: DataFrame with original column names

        Returns:
            DataFrame with standardized column names
        """
        rename_mapping: dict[str, str] = self.config.column_mapping.get_rename_mapping()
        standardized_df: pd.DataFrame = dataframe.rename(columns=rename_mapping)

        logger.debug('Standardized column names using provided mapping')

        return standardized_df

    def _validate_required_columns(self, dataframe: pd.DataFrame) -> None:
        """
        Verify that all required columns exist after renaming.

        Args:
            dataframe: DataFrame to validate

        Raises:
            ValueError: If required columns are missing
        """
        is_valid: bool
        missing_columns: list[str]
        is_valid, missing_columns = (
            self.config.column_mapping.validate_dataframe_columns(dataframe.columns)
        )

        if not is_valid:
            error_message: str = (
                f'DataFrame is missing required columns: {missing_columns}'
            )
            logger.error(error_message)
            raise ValueError(error_message)

        logger.debug('All required columns present after renaming')

    def _filter_to_required_columns(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Retain only the columns required for analysis.

        Args:
            dataframe: DataFrame with all columns

        Returns:
            DataFrame with only required columns
        """
        required_columns: list[str] = self.config.column_mapping.get_required_columns()
        filtered_df: pd.DataFrame = dataframe[required_columns].copy()

        logger.debug('Filtered to %d required columns', len(required_columns))

        return filtered_df

    def _normalize_whitespace_and_nulls(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Replace whitespace-only strings with NaN and standardize null handling.

        Args:
            dataframe: DataFrame to normalize

        Returns:
            DataFrame with normalized null values
        """
        normalized_df: pd.DataFrame = dataframe.replace(
            to_replace=r'^\s*$', value=np.nan, regex=True
        ).fillna(np.nan)

        return normalized_df

    def _remove_duplicates(self, dataframe: pd.DataFrame) -> tuple[pd.DataFrame, int]:
        """
        Remove duplicate rows from the DataFrame.

        Args:
            dataframe: DataFrame potentially containing duplicates

        Returns:
            Tuple of (deduplicated_df, count_of_duplicates_removed)
        """
        initial_count: int = len(dataframe)
        deduplicated_df: pd.DataFrame = dataframe.drop_duplicates()
        final_count: int = len(deduplicated_df)
        duplicates_removed: int = initial_count - final_count

        if duplicates_removed > 0:
            logger.info('Removed %d duplicate rows', duplicates_removed)

        return deduplicated_df, duplicates_removed

    def _parse_timestamps(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Parse transaction timestamps to timezone-aware datetime objects.

        Args:
            dataframe: DataFrame with timestamp column

        Returns:
            DataFrame with parsed timestamps
        """
        dataframe['transaction_timestamp'] = pd.to_datetime(
            dataframe['transaction_timestamp'], errors='coerce', utc=True
        )

        return dataframe

    def _filter_incomplete_months(
        self, dataframe: pd.DataFrame
    ) -> tuple[pd.DataFrame, int]:
        """
        Remove transactions from incomplete trailing months.

        If the last date in the dataset is more than N days before month-end
        (where N is configured threshold), remove all transactions from that month
        to avoid biased analysis of partial periods.

        Args:
            dataframe: DataFrame with parsed timestamps

        Returns:
            Tuple of (filtered_df, count_of_rows_removed)
        """
        timestamp_series: pd.Series = dataframe['transaction_timestamp']
        last_date: pd.Timestamp = timestamp_series.max()

        incomplete_removed: int = 0
        filtered_df: pd.DataFrame = dataframe

        if pd.notna(last_date):
            last_day_of_month: pd.Timestamp = last_date + pd.offsets.MonthEnd(0)
            days_until_month_end: int = (last_day_of_month - last_date).days
            threshold_days: int = self.config.analysis.monthend_threshold

            if days_until_month_end > threshold_days:
                logger.info(
                    'Filtering incomplete month. Last date: %s (%d days until month-end)',
                    last_date.date(),
                    days_until_month_end,
                )

                incomplete_month: pd.Period = last_date.to_period('M')
                date_mask: pd.Series = (  # pyright: ignore[reportUnknownVariableType]
                    timestamp_series.dt.to_period('M') != incomplete_month  # pyright: ignore[reportAttributeAccessIssue]
                )

                filtered_df = dataframe[date_mask].copy()
                incomplete_removed = len(dataframe) - len(filtered_df)

        return filtered_df, incomplete_removed

    def _enforce_positive_values(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Convert negative values to positive for columns that should always be positive.

        Negative values in columns like odometer, volume, and distance are likely
        data quality issues and should be treated as their absolute values.

        Args:
            dataframe: DataFrame potentially containing negative values

        Returns:
            DataFrame with enforced positive values
        """
        positive_only_columns: list[str] = [
            'odometer_miles',
            'fuel_volume_gallons',
            'distance_miles',
        ]

        for column_name in positive_only_columns:
            if column_name in dataframe.columns:
                dataframe[column_name] = dataframe[column_name].abs()

        return dataframe

    def _enforce_types(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Explicitly cast all columns to their expected data types.

        This ensures consistent data types across different data sources and
        prevents type-related issues in downstream analysis. Uses pandas nullable
        types (Int64Dtype, Float64Dtype, StringDtype) which properly handle
        missing values while maintaining semantic clarity.

        Object dtype columns are always converted to their proper types rather
        than being left as the generic object dtype, which is less efficient
        and less semantically clear.

        Type coercion errors are logged and handled gracefully - columns that
        cannot be converted retain their current type rather than failing the
        entire pipeline.

        Args:
            dataframe: DataFrame with columns to type-cast

        Returns:
            DataFrame with enforced types
        """
        logger.debug('Enforcing explicit data types for all columns')

        type_enforcement_failures: list[str] = []

        for column_name, target_dtype in self.TYPE_SPECIFICATIONS.items():
            if column_name not in dataframe.columns:
                logger.debug(
                    'Skipping type enforcement for %r (column not present)',
                    column_name
                )
                continue

            current_dtype = dataframe[column_name].dtype

            # Skip if already correct type (but never skip 'object' dtype)
            if self._is_correct_dtype(dataframe[column_name], target_dtype):
                logger.debug(
                    'Column %r already has correct type: %s',
                    column_name,
                    current_dtype
                )
                continue

            try:
                # Track original non-null count to detect unexpected NaN introduction
                original_non_null_count: int = dataframe[column_name].notna().sum()

                # Perform type conversion
                dataframe[column_name] = dataframe[column_name].astype(target_dtype)

                # Verify conversion didn't introduce unexpected NaNs
                new_non_null_count: int = dataframe[column_name].notna().sum()
                if new_non_null_count < original_non_null_count:
                    nan_introduced: int = original_non_null_count - new_non_null_count
                    logger.warning(
                        'Type conversion for %r introduced %d NaN values '
                        '(from %s to %s)',
                        column_name,
                        nan_introduced,
                        current_dtype,
                        target_dtype
                    )

                logger.debug(
                    'Converted %r from %s to %s',
                    column_name,
                    current_dtype,
                    target_dtype
                )

            except (ValueError, TypeError) as conversion_error:
                # Log failure but continue with other columns
                logger.error(
                    'Failed to cast column %r from %s to %s: %s. '
                    'Column will retain original type.',
                    column_name,
                    current_dtype,
                    target_dtype,
                    str(conversion_error)
                )
                type_enforcement_failures.append(column_name)

        if type_enforcement_failures:
            logger.warning(
                'Type enforcement failed for %d columns: %r',
                len(type_enforcement_failures),
                type_enforcement_failures
            )
        else:
            logger.debug('All column types successfully enforced')

        return dataframe

    def _is_correct_dtype(
        self,
        series: pd.Series,
        target_dtype: column_types
    ) -> bool:
        """
        Check if a series already has the target data type.

        Note: Object dtype is never considered "correct" - it should always
        be converted to a more specific type (typically StringDtype for strings).

        Standard Numpy types (int64, float64) are also NOT considered correct
        if the target is a Nullable type (Int64, Float64). This strictness
        ensures we have consistent behavior regarding NaNs across the pipeline.

        Args:
            series: Pandas series to check
            target_dtype: Target dtype object

        Returns:
            True if series already has correct type, False otherwise
        """
        current_dtype = series.dtype

        # Object dtype should always be converted, never considered correct
        if current_dtype == np.dtype('object'):
            is_correct_type: bool = False
        # Direct dtype comparison (handles most cases cleanly)
        elif current_dtype == target_dtype:
            is_correct_type = True
        else:
            # Pattern match on target dtype for special compatibility cases
            match target_dtype:
                case pd.DatetimeTZDtype():
                    # DatetimeTZ requires matching both unit and timezone
                    if isinstance(current_dtype, pd.DatetimeTZDtype):
                        is_correct_type = (
                            current_dtype.unit == target_dtype.unit
                            and current_dtype.tz == target_dtype.tz
                        )
                    else:
                        is_correct_type = False

                case pd.Float64Dtype():
                    # STRICT: We reject numpy 'float64' to enforce Nullable 'Float64'
                    # This ensures consistent NaN handling in downstream logic.
                    is_correct_type = isinstance(current_dtype, pd.Float64Dtype)

                case pd.Int64Dtype():
                    # STRICT: We reject numpy 'int64' to enforce Nullable 'Int64'
                    # This protects against crashes if NaNs are introduced later.
                    is_correct_type = isinstance(current_dtype, pd.Int64Dtype)

                case _:
                    # No special compatibility rules apply
                    is_correct_type = False

        return is_correct_type
