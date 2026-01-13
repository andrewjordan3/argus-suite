# argus/preprocessor/data_splitter.py
"""
Data splitting for temporal and spatial analysis stratification.

This module partitions cleaned and enriched data into appropriate subsets for
comparative fraud detection analysis. It handles both temporal splitting (isolating
recent periods from historical baselines) and spatial splitting (separating target
locations from peer comparison groups).

Classes:
    DataSplitter: Determines analysis periods and splits data accordingly

Splitting Strategies:

Temporal Splitting (Time-Based):
    Goal: Focus analysis on recent data while retaining historical context

    Decision Logic:
        1. If all data is from single year → Use complete dataset
        2. If multi-year data exists:
           a. Count months in current (most recent) year
           b. If current year has sufficient months (configurable threshold) → Split
           c. Otherwise → Use complete dataset to avoid insufficient sample sizes

    Rationale:
        - Recent data is more relevant for current fraud patterns
        - Historical data provides baseline but may include outdated patterns
        - Splitting requires minimum data volume to ensure statistical validity
        - Year-over-year changes in operations make older data less comparable

Spatial Splitting (Location-Based):
    Goal: Isolate target location from peer locations for comparative analysis

    Strategy:
        - Target: Transactions at location under investigation
        - Peers: Transactions at all other locations (comparison baseline)

    Rationale:
        - Target location analyzed for anomalies
        - Peer locations provide "normal" baseline behavior
        - Differences between target and peers highlight location-specific issues
        - Peer aggregation smooths individual location noise

Split Types Generated:
    1. Target Period: Recent data at target location (primary analysis focus)
    2. Peer Period: Recent data at peer locations (comparison baseline)
    3. Target Historical: All-time data at target location (trend analysis)
    4. Peer Historical: All-time data at peer locations (historical baseline)
    5. Complete Unsplit: All data from all locations/times (reference)

Split Status Values:
    'single': Using complete dataset (no temporal split)
        - Reason: Single year of data OR insufficient current year data

    'split': Using current year only
        - Reason: Multi-year data available AND current year meets threshold

    'insufficient': Would split but current year lacks sufficient data
        - Reason: Current year exists but below minimum month requirement

Configuration Parameters:
    current_year_minimum_months: Minimum months required in current year to enable split
        - Default: 3 months
        - Rationale: Need sufficient sample size for statistical validity
        - Too low: Unstable estimates from small samples
        - Too high: May never split, losing recency benefits

Split Metadata Returned:
    {
        'min_year': int,              # Earliest year in dataset
        'current_year': int,          # Most recent year in dataset
        'num_months_current_year': int | None,  # Months available in current year
        'split_status': str,          # 'single', 'split', or 'insufficient'
    }

Typical Usage:
    splitter = DataSplitter(config.analysis)
    target_period, peer_period, split_info = splitter.split(complete_df)

    logger.info('Split status: %s', split_info['split_status'])
    if split_info['split_status'] == 'split':
        logger.info('Analyzing year %d only', split_info['current_year'])

Analysis Implications:

When Split:
    - More relevant: Recent patterns vs old data
    - Faster: Smaller datasets process quicker
    - Sharper: Better detection of emerging fraud patterns
    - Risk: Historical context lost, seasonal patterns may be incomplete

When Not Split:
    - More context: Full historical perspective
    - Stable: Larger samples, more reliable statistics
    - Comprehensive: Can detect long-term trends
    - Risk: Old patterns may dilute recent signal

Best Practices:
    - Review split_status before interpreting results
    - Consider seasonality when setting minimum month threshold
    - Compare split vs unsplit results when possible
    - Document split decision in forensic report
"""
import logging
from typing import Any

import pandas as pd

from argus.config import AnalysisConfig

# pyright: reportAttributeAccessIssue=false, reportUnknownVariableType=false

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)


class DataSplitter:
    """
    Splits data into analysis periods based on configuration.

    Handles:
    - Determining appropriate analysis timeframe
    - Splitting by location (target vs peer)
    - Splitting by time period (current year vs historical)
    """

    def __init__(self, config: AnalysisConfig) -> None:
        """
        Initialize data splitter with configuration.

        Args:
            config: Analysis configuration containing splitting rules
        """
        self.config: AnalysisConfig = config

    def split(
        self, dataframe: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
        """
        Split data for analysis based on time period and location.

        Args:
            dataframe: Complete cleaned and enriched DataFrame

        Returns:
            Tuple of (target_location_df, peer_locations_df, split_info)
        """
        logger.debug('Splitting data for analysis')

        target_location_name: str = self.config.target_location_name

        # Split by location first
        target_all_time: pd.DataFrame = dataframe[
            dataframe['branch_group'] == target_location_name
        ].copy()

        peers_all_time: pd.DataFrame = dataframe[
            dataframe['branch_group'] != target_location_name
        ].copy()

        # Determine if temporal split is appropriate
        split_info: dict[str, Any] = self._determine_analysis_period(dataframe)

        # Apply temporal split if indicated
        if split_info['split_status'] == 'split':
            current_year: int = split_info['current_year']

            target_period: pd.DataFrame = target_all_time[
                target_all_time['datetime_parsed'].dt.year == current_year
            ].copy()

            peers_period: pd.DataFrame = peers_all_time[
                peers_all_time['datetime_parsed'].dt.year == current_year
            ].copy()

            logger.info(
                'Split data to current year (%d). Target: %d rows, Peers: %d rows',
                current_year,
                len(target_period),
                len(peers_period),
            )
        else:
            target_period = target_all_time
            peers_period = peers_all_time

            logger.info(
                'Using full dataset. Target: %d rows, Peers: %d rows',
                len(target_period),
                len(peers_period),
            )

        return target_period, peers_period, split_info

    def _determine_analysis_period(self, dataframe: pd.DataFrame) -> dict[str, Any]:
        """
        Determine whether to analyze current year only or full dataset.

        Args:
            dataframe: Complete DataFrame

        Returns:
            Dictionary containing split decision and metadata
        """
        min_year: int = int(dataframe['datetime_parsed'].dt.year.min())
        current_year: int = int(dataframe['datetime_parsed'].dt.year.max())

        split_info: dict[str, Any] = {
            'min_year': min_year,
            'current_year': current_year,
            'num_months_current_year': None,
            'split_status': 'single',
        }

        # Only consider splitting if we have multiple years of data
        if min_year >= current_year:
            return split_info

        # Check if current year has enough data
        min_months_required: int = self.config.current_year_minimum_months
        total_unique_months: int = dataframe['month'].nunique()

        if total_unique_months <= min_months_required:
            return split_info

        # Count months in current year
        current_year_data: pd.DataFrame = dataframe[
            dataframe['datetime_parsed'].dt.year == current_year
        ]
        current_year_months: int = current_year_data['month'].nunique()
        split_info['num_months_current_year'] = current_year_months

        if current_year_months > min_months_required:
            split_info['split_status'] = 'split'
        else:
            split_info['split_status'] = 'insufficient'

        return split_info
