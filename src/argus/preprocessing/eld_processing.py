# argus/preprocessor/eld_processing.py
"""
Electronic Logging Device (ELD) data processing and standardization.

This module handles the complex task of processing ELD distance data, which
can arrive in two fundamentally different formats depending on the vendor:
1. Daily aggregates (same distance value repeated for all transactions on a vehicle-day)
2. Granular trip-level data (unique distance per transaction)

The ELDDataHandler automatically detects which format is present and applies
appropriate processing to avoid double-counting while preserving all available
information for fraud detection and efficiency analysis.

Classes:
    ELDDataHandler: Detects ELD format and processes accordingly

ELD Data Challenges:
    Problem: Some ELD vendors provide daily distance totals that appear on every
    transaction for that vehicle on that day. Summing these values naively would
    count the same miles multiple times.

    Solution: Detect aggregation type by checking if distance values vary within
    vehicle-days. If constant (daily aggregate), preserve distance only on the
    first transaction of each vehicle-day while maintaining an activity flag on
    all transactions.

Output Columns:
    has_eld_activity: Boolean flag indicating ELD data exists for this vehicle-day
    is_first_transaction_of_day: Boolean flag marking first transaction per vehicle-day
    distance_miles: Distance value (NaN on non-first transactions if daily aggregate)

Detection Logic:
    - Group transactions by (vehicle_index, date_only)
    - Count unique distance values per group
    - If all groups have exactly 1 unique distance → Daily aggregate
    - If any groups have >1 unique distance → Granular data

Processing Strategy by Type:
    Daily Aggregate:
        - Keep distance_miles only on first transaction per vehicle-day
        - Set subsequent transactions' distance_miles to NaN
        - Mark all transactions on ELD days with has_eld_activity=True
        - Prevents double-counting in daily/weekly/monthly aggregations

    Granular:
        - Preserve all distance_miles values (they represent trip segments)
        - Mark all transactions with has_eld_activity where distance exists
        - Allows natural summation of trip segments

Fraud Detection Applications:
    - Transactions without ELD activity (has_eld_activity=False) may indicate:
        * Device tampering or disconnection
        * Personal vehicle use with company fuel card
        * Test transactions or data quality issues
    - Unusual distance patterns combined with fuel volume suggest odometer fraud

Typical Usage:
    eld_handler = ELDDataHandler()
    processed_df = eld_handler.process_eld_data(dataframe)

    # Safe aggregation pattern:
    daily_distance = processed_df.groupby('date_only')['distance_miles'].sum()
    # This correctly handles both daily aggregate and granular formats

Data Quality Considerations:
    - ELD data is optional - not all transactions will have distance information
    - Missing ELD data is normal and expected, especially for:
        * Older vehicles without ELD devices
        * Non-fleet personal vehicles
        * Transactions at locations without telemetry integration
    - The has_eld_activity flag allows analysis of ELD coverage patterns
"""
import logging

import numpy as np
import pandas as pd

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)


class ELDDataHandler:
    """
    Handles Electronic Logging Device (ELD) data processing.

    Responsibilities:
    - Detecting whether ELD distance is daily aggregate vs transaction-level
    - Creating ELD activity flags
    - Handling duplicate distance values appropriately
    """

    def process_eld_data(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Process ELD data and create appropriate flags.

        Args:
            dataframe: DataFrame with distance_miles and vehicle/date columns

        Returns:
            DataFrame with ELD-related flag columns
        """
        logger.debug('Processing ELD data')

        # Sort by vehicle and timestamp for consistent processing
        sorted_df: pd.DataFrame = dataframe.sort_values(
            ['vehicle_index', 'date_only', 'transaction_timestamp']
        )

        is_daily_aggregate: bool = self._detect_eld_aggregation_type(sorted_df)

        if is_daily_aggregate:
            processed_df: pd.DataFrame = self._process_daily_aggregate_eld(sorted_df)
        else:
            processed_df = self._process_granular_eld(sorted_df)

        logger.debug('ELD data processing complete')

        return processed_df

    def _detect_eld_aggregation_type(self, dataframe: pd.DataFrame) -> bool:
        """
        Determine if ELD distance values are daily aggregates or per-transaction.

        Daily aggregate: Same distance value repeated for all transactions on a given
                        vehicle-day (common with some ELD vendors)
        Granular: Different distance values per transaction (trip-level data)

        Args:
            dataframe: DataFrame with distance_miles, vehicle_index, and date_only

        Returns:
            True if ELD data is daily aggregate, False if granular
        """
        # Filter to records with distance data and multiple transactions per day
        eld_records: pd.DataFrame = dataframe.dropna(subset=['distance_miles'])

        if eld_records.empty:
            return True  # Default assumption if no ELD data

        # Group by vehicle/date and count unique distance values
        # If unique distance count > 1, values vary (granular data)
        # If unique distance count == 1, values repeat (daily aggregate)
        distance_variance: pd.Series = (
            eld_records.groupby(['vehicle_index', 'date_only'])[
                'distance_miles'
            ].nunique()
        )

        varying_days_count: int = int((distance_variance > 1).sum())

        if varying_days_count == 0:
            logger.debug(
                'ELD data is daily aggregate (consistent distance per vehicle-day)'
            )
            return True
        else:
            logger.warning(
                'ELD data is granular (%d vehicle-days have varying distances). '
                'Treating as transaction-level data.',
                varying_days_count,
            )
            return False

    def _process_daily_aggregate_eld(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Process ELD data when distance values are daily aggregates.

        Strategy: Keep distance only on the first transaction of each vehicle-day
        to avoid double-counting. Set subsequent transactions' distance to NaN.
        All transactions on ELD days get has_eld_activity=True.

        Args:
            dataframe: DataFrame with distance_miles column

        Returns:
            DataFrame with ELD flags and adjusted distance values
        """
        # Flag whether ELD activity exists for this vehicle-day
        dataframe['has_eld_activity'] = dataframe['distance_miles'].notna()

        # Mark first transaction of each vehicle-day
        dataframe['is_first_transaction_of_day'] = ~dataframe.duplicated(
            subset=['vehicle_index', 'date_only'], keep='first'
        )

        # Set distance to NaN for non-first transactions to avoid double-counting
        # but keep has_eld_activity True for all transactions on ELD days
        dataframe.loc[~dataframe['is_first_transaction_of_day'], 'distance_miles'] = (
            np.nan
        )

        logger.debug(
            'Processed daily aggregate ELD data: distance preserved only on first '
            'transaction per vehicle-day'
        )

        return dataframe

    def _process_granular_eld(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Process ELD data when distance values are transaction-level (granular).

        Strategy: Keep all distance values as they represent distinct trip segments.
        Create consistent flag columns for schema compatibility.

        Args:
            dataframe: DataFrame with distance_miles column

        Returns:
            DataFrame with ELD flags (distance values unchanged)
        """
        # Flag whether ELD activity exists for this transaction
        dataframe['has_eld_activity'] = dataframe['distance_miles'].notna()

        # Mark first transaction for schema consistency
        dataframe['is_first_transaction_of_day'] = ~dataframe.duplicated(
            subset=['vehicle_index', 'date_only'], keep='first'
        )

        # Do NOT nullify subsequent distance values since they're distinct

        logger.debug(
            'Processed granular ELD data: all distance values preserved '
            '(transaction-level segments)'
        )

        return dataframe
