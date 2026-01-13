# argus/suspicious_patterns.py

import logging
from datetime import timedelta

import numpy as np
import pandas as pd

from argus.models import StatisticalTest
from argus.models.context.context_model import AnalysisContext

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)

HIGH_SUSPICION_COUNT: int = 4
FRAUD_INDICATOR_THRESHOLD: int = 2

# Minimum transactions at a station to be eligible to be considered suspicious
SUSPICIOUS_STATION_MIN_COUNT: int = 5

FRAUD_INDICATOR_WEIGHT: int = 2
MISUSE_INDICATOR_WEIGHT: int = 1


def _identify_multi_fillup_events(
    df: pd.DataFrame, min_fillups: int = 2
) -> pd.DataFrame:
    """
    Identify all instances where a driver had multiple fillups on the same day.

    Args:
        df: DataFrame containing transaction data
        min_fillups: Minimum number of fillups to consider (default: 2)

    Returns:
        DataFrame containing only transactions from multi-fillup days
    """
    if df.empty or 'driver_name' not in df.columns or 'date_only' not in df.columns:
        return pd.DataFrame()

    # Calculate daily fillup counts per driver
    driver_daily_fillups: pd.Series[int] = df.groupby(
        ['driver_name', 'date_only']
    ).size()

    # Identify multi-fillup days
    multi_fillup_days: pd.Series[int] = driver_daily_fillups[
        driver_daily_fillups >= min_fillups
    ]

    if multi_fillup_days.empty:
        return pd.DataFrame()

    # Filter to only transactions from multi-fillup days
    multi_fillup_transactions: pd.DataFrame = df.merge(
        multi_fillup_days.reset_index()[['driver_name', 'date_only']],
        on=['driver_name', 'date_only'],
        how='inner',
    )

    return multi_fillup_transactions


def _analyze_multi_fillup_patterns(multi_fillup_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate and analyze patterns within multi-fillup days.

    Args:
        multi_fillup_df: DataFrame containing only multi-fillup transactions

    Returns:
        DataFrame with aggregated statistics per driver-date combination
    """
    if multi_fillup_df.empty:
        return pd.DataFrame()

    # Define the conditional aggregation for 'avg_volume'
    # It uses a real aggregation if 'volume' exists, or our
    # placeholder 'nan' function if it doesn't.
    avg_volume_agg: pd.NamedAgg = (
        pd.NamedAgg(column='fuel_volume_gallons', aggfunc='mean')
        if 'fuel_volume_gallons' in multi_fillup_df.columns
        else pd.NamedAgg(column='transaction_amount', aggfunc=_agg_return_nan)
    )

    # Aggregate patterns for each driver-date combination
    patterns: pd.DataFrame = (
        multi_fillup_df.groupby(['driver_name', 'date_only'])
        .agg(
            fillup_count=pd.NamedAgg(column='datetime_parsed', aggfunc='nunique'),
            products=pd.NamedAgg(
                column='product_clean', aggfunc=_agg_unique_sorted_products
            ),
            total_cost=pd.NamedAgg(column='transaction_amount', aggfunc='sum'),
            avg_cost=pd.NamedAgg(column='transaction_amount', aggfunc='mean'),
            avg_volume=avg_volume_agg,
            unique_stations=pd.NamedAgg(column='merchant_name', aggfunc='nunique'),
            time_span_hours=pd.NamedAgg(
                column='datetime_parsed',
                aggfunc=_agg_time_span_hours,
            ),
            has_eld_match=pd.NamedAgg(column='has_eld_activity', aggfunc='all'),
            diesel_count=pd.NamedAgg(column='is_diesel_def', aggfunc='sum'),
        )
        .reset_index()
    )

    # Calculate non-diesel rate
    patterns['non_diesel_rate'] = 1 - (
        patterns['diesel_count'] / patterns['fillup_count']
    )

    # Sort by fillup count (highest first), then by cost
    patterns = patterns.sort_values(
        ['fillup_count', 'total_cost'], ascending=[False, False]
    )

    return patterns


def _detect_suspicious_fillup_characteristics(
    patterns: pd.DataFrame,
    cost_threshold_percentile: float = 0.25,  # LOW cost is suspicious
    volume_threshold_percentile: float = 0.25,  # LOW volume is suspicious
) -> pd.DataFrame:
    """
    Flag multi-fillup events with characteristics suggesting passenger vehicle fraud.

    FRAUD PATTERN: Employees using fuel cards to fill personal passenger vehicles
    instead of company commercial trucks. Key indicators:
    - Lower volumes (passenger vehicle tanks are much smaller)
    - Lower costs (smaller fills)
    - Non-diesel purchases (passenger vehicles use regular gasoline)

    Args:
        patterns: DataFrame with aggregated multi-fillup patterns
        cost_threshold_percentile: Percentile below which cost is considered suspiciously low
        volume_threshold_percentile: Percentile below which volume is considered suspiciously low

    Returns:
        DataFrame with added 'red_flags' column listing suspicious indicators
    """
    if patterns.empty:
        return patterns

    patterns = patterns.copy()

    # Initialize columns to track different categories of suspicious behavior
    patterns['red_flags'] = ''  # Space-separated string of flag codes
    patterns['red_flags'] = patterns['red_flags'].astype(pd.StringDtype())
    patterns['fraud_indicators'] = 0  # Count of passenger vehicle fraud indicators
    patterns['misuse_indicators'] = 0  # Count of card misuse indicators

    # === PASSENGER VEHICLE FRAUD INDICATORS (Primary fraud pattern) ===
    # These indicators suggest someone is using a commercial fuel card to fill
    # a personal passenger vehicle instead of the intended commercial truck

    # Flag 1: Suspiciously low average cost per fillup
    # Lower costs typically indicate smaller tank capacities (passenger vehicles)
    # compared to commercial trucks which have much larger tanks
    cost_percentile_threshold: float = patterns['avg_cost'].quantile(
        cost_threshold_percentile
    )
    is_cost_suspiciously_low: pd.Series[bool] = (
        patterns['avg_cost'] <= cost_percentile_threshold
    )

    # Add 'LC' (Low Cost) flag to rows meeting this criterion
    patterns.loc[is_cost_suspiciously_low, 'red_flags'] = (
        patterns.loc[is_cost_suspiciously_low, 'red_flags'] + 'LC '
    )  # pyright: ignore[reportOperatorIssue]

    patterns.loc[is_cost_suspiciously_low, 'fraud_indicators'] += 1

    # Flag 2: Suspiciously low average volume per fillup
    # Small volumes are a strong indicator of passenger vehicle tanks vs commercial truck tanks
    # Commercial trucks typically have 100-300 gallon tanks; passenger vehicles have 12-20 gallon tanks
    if 'avg_volume' in patterns.columns and patterns['avg_volume'].notna().any():
        volume_percentile_threshold: float = patterns['avg_volume'].quantile(
            volume_threshold_percentile
        )
        is_volume_suspiciously_low: pd.Series = (
            patterns['avg_volume'] <= volume_percentile_threshold
        )

        # Add 'LV' (Low Volume) flag to rows meeting this criterion
        patterns.loc[is_volume_suspiciously_low, 'red_flags'] = (
            patterns.loc[is_volume_suspiciously_low, 'red_flags'] + 'LV '
        )  # pyright: ignore[reportOperatorIssue]
        patterns.loc[is_volume_suspiciously_low, 'fraud_indicators'] += 1

    # Flag 3: High rate of non-diesel fuel purchases
    # Commercial trucks almost exclusively use diesel fuel
    # Regular gasoline purchases suggest passenger vehicle use
    non_diesel_rate_threshold: float = (
        0.5  # 50% or more non-diesel purchases is highly suspicious
    )
    has_high_non_diesel_rate: pd.Series = (
        patterns['non_diesel_rate'] >= non_diesel_rate_threshold
    )

    # Add 'ND' (Non-Diesel) flag to rows meeting this criterion
    # This gets double weight (2 points) because it's a very strong fraud indicator
    patterns.loc[has_high_non_diesel_rate, 'red_flags'] = (
        patterns.loc[has_high_non_diesel_rate, 'red_flags'] + 'ND '
    )  # pyright: ignore[reportOperatorIssue]
    patterns.loc[has_high_non_diesel_rate, 'fraud_indicators'] += 2  # Double weight

    # === CARD MISUSE INDICATORS ===
    # These indicators suggest improper card usage patterns but don't necessarily
    # indicate passenger vehicle fraud specifically

    # Flag 4: Excessive number of fillups in a single day
    # Even with commercial vehicles, 4+ fillups in one day is highly unusual
    # This could indicate card sharing, unauthorized use, or fraudulent activity
    excessive_fillups_threshold: int = 4
    has_excessive_fillups: pd.Series = (
        patterns['fillup_count'] >= excessive_fillups_threshold
    )

    # Add 'MF' (Multiple Fillups) flag to rows meeting this criterion
    patterns.loc[has_excessive_fillups, 'red_flags'] = (
        patterns.loc[has_excessive_fillups, 'red_flags'] + 'MF '
    )  # pyright: ignore[reportOperatorIssue]
    patterns.loc[has_excessive_fillups, 'misuse_indicators'] += 1

    # Flag 5: Fillups occurring at multiple different stations on the same day
    # While legitimate for long-haul trucking, this can also indicate card sharing
    # or unauthorized card use by multiple people
    has_multiple_stations: pd.Series = patterns['unique_stations'] > 1

    # Add 'MS' (Multiple Stations) flag to rows meeting this criterion
    patterns.loc[has_multiple_stations, 'red_flags'] = (
        patterns.loc[has_multiple_stations, 'red_flags'] + 'MS '
    )  # pyright: ignore[reportOperatorIssue]
    patterns.loc[has_multiple_stations, 'misuse_indicators'] += 1

    # Flag 6: No ELD (Electronic Logging Device) match
    # ELD data provides verification that a truck was actually at the fueling location
    # Absence of ELD verification means we cannot confirm the vehicle's location
    has_no_eld_verification: pd.Series = ~patterns['has_eld_match']

    # Add 'NE' (No ELD) flag to rows meeting this criterion
    patterns.loc[has_no_eld_verification, 'red_flags'] = (
        patterns.loc[has_no_eld_verification, 'red_flags'] + 'NE '
    )  # pyright: ignore[reportOperatorIssue]
    patterns.loc[has_no_eld_verification, 'misuse_indicators'] += 1

    # Flag 7: Rapid succession of fillups in a very short time window
    # Three or more fillups within one hour is physically suspicious
    # This could indicate card fraud, skimming, or coordinated unauthorized use
    minimum_fillups_for_rapid_succession: int = 3
    maximum_hours_for_rapid_succession: float = 1.0
    has_rapid_succession_pattern: pd.Series = (
        patterns['fillup_count'] >= minimum_fillups_for_rapid_succession
    ) & (patterns['time_span_hours'] < maximum_hours_for_rapid_succession)

    # Add 'RS' (Rapid Succession) flag to rows meeting this criterion
    patterns.loc[has_rapid_succession_pattern, 'red_flags'] = (
        patterns.loc[has_rapid_succession_pattern, 'red_flags'] + 'RS '
    )  # pyright: ignore[reportOperatorIssue]
    patterns.loc[has_rapid_succession_pattern, 'misuse_indicators'] += 1

    # Remove trailing whitespace from all red_flags entries
    patterns['red_flags'] = patterns['red_flags'].str.rstrip()

    # Calculate combined suspicion score with fraud indicators weighted more heavily
    # Fraud indicators (suggesting passenger vehicle use) are more serious than
    # general misuse indicators, so they receive 2x weight
    patterns['suspicion_score'] = (
        patterns['fraud_indicators'] * FRAUD_INDICATOR_WEIGHT
        + patterns['misuse_indicators'] * MISUSE_INDICATOR_WEIGHT
    )

    return patterns


def run_multiple_fillup_analysis(
    context: AnalysisContext,
    all_tests: dict[str, StatisticalTest],
) -> None:
    """
    Perform deep-dive analysis into multiple same-day fillup events with focus
    on detecting passenger vehicle fraud.

    This analysis supplements the statistical test by identifying specific
    suspicious patterns, particularly those indicating employees filling
    personal passenger vehicles instead of company commercial trucks.

    Args:
        target_location: DataFrame for the target branch
        all_tests: dictionary containing all pre-calculated StatisticalTest objects
        report_writer: Instance of ForensicReportWriter
        top_n: Number of top suspicious events to display
    """
    # Check if the multi-fillup test was performed
    multi_fillup_test: StatisticalTest | None = all_tests.get(
        'Multiple Same-Day Fillups'
    )

    if not multi_fillup_test:
        # Test wasn't run, skip this analysis
        return

    # Step 1: Identify multi-fillup transactions
    multi_fillup_transactions: pd.DataFrame = _identify_multi_fillup_events(
        context.target_period_transactions.copy()
    )

    if multi_fillup_transactions.empty:
        # No multi-fillup events found
        return

    # Step 2: Analyze patterns
    patterns: pd.DataFrame = _analyze_multi_fillup_patterns(multi_fillup_transactions)

    if patterns.empty:
        return

    # Step 3: Detect suspicious characteristics (focused on passenger vehicle fraud)
    patterns = _detect_suspicious_fillup_characteristics(patterns)

    # Step 4: Calculate summary statistics
    summary_stats: dict[str, int | float] = {
        'total_events': len(patterns),
        'total_drivers': patterns['driver_name'].nunique(),
        'total_cost': patterns['total_cost'].sum(),
        'avg_fillups': patterns['fillup_count'].mean(),
        'high_suspicion_count': (
            patterns['suspicion_score'] >= HIGH_SUSPICION_COUNT
        ).sum(),  # Adjusted threshold
        'fraud_indicator_events': (
            patterns['fraud_indicators'] >= FRAUD_INDICATOR_THRESHOLD
        ).sum(),  # Passenger vehicle indicators
        'avg_suspicion_score': patterns['suspicion_score'].mean(),
    }

    # Step 5: Sort by suspicion score (fraud-weighted), then fillup count
    suspicious_events: pd.DataFrame = patterns.sort_values(
        ['suspicion_score', 'fraud_indicators', 'fillup_count'],
        ascending=[False, False, False],
    )

    # Step 6: Write report using ForensicReportWriter method
    context.report_writer.write_multi_fillup_analysis(
        test_result=multi_fillup_test,
        summary_stats=summary_stats,
        suspicious_events=suspicious_events,
        top_n=context.config.analysis.top_n_entities,
    )


def analyze_geographic_anomalies(
    context: AnalysisContext
) -> pd.DataFrame | None:
    """
    Identify suspicious geographic patterns, focusing on stations with high
    rates of passenger vehicle indicators (non-diesel, low cost).

    Args:
        target_location: DataFrame for the target branch
        report_writer: Instance of ForensicReportWriter
        top_n: Number of top patterns to display

    Returns:
        DataFrame with geographic anomaly analysis, or None if insufficient data
    """
    target_df: pd.DataFrame = context.target_period_transactions.copy()
    if target_df.empty:
        return None

    df_column_names: pd.Index[str] = target_df.columns
    if 'Station Name' not in df_column_names:
        return None

    avg_volume_agg: pd.NamedAgg = (
        pd.NamedAgg(column='fuel_volume_gallons', aggfunc='mean')
        if 'fuel_volume_gallons' in df_column_names
        else pd.NamedAgg(column='transaction_amount', aggfunc=_agg_return_nan)
    )

    # Analyze station usage patterns
    station_stats: pd.DataFrame = (
        target_df.groupby('Station Name')
        .agg(
            transaction_count=pd.NamedAgg(column='datetime_parsed', aggfunc='count'),
            unique_drivers=pd.NamedAgg(column='driver_name', aggfunc='nunique'),
            unique_vehicles=pd.NamedAgg(column='vehicle_id', aggfunc='nunique'),
            total_cost=pd.NamedAgg(column='transaction_amount', aggfunc='sum'),
            avg_cost=pd.NamedAgg(column='transaction_amount', aggfunc='mean'),
            no_eld_rate=pd.NamedAgg(column='has_eld_activity', aggfunc=_agg_false_mean),
            non_diesel_rate=pd.NamedAgg(
                column='is_diesel_def', aggfunc=_agg_false_mean
            ),
            avg_volume=avg_volume_agg,
        )
        .reset_index()
    )

    if station_stats.empty:
        return None

    # Calculate percentage of total activity
    total_transactions: int = station_stats['transaction_count'].sum()
    station_stats['pct_of_total'] = (
        station_stats['transaction_count'] / total_transactions
    )

    # Sort by transaction count
    station_stats = station_stats.sort_values('transaction_count', ascending=False)

    # Identify suspicious stations (passenger vehicle fraud indicators)
    suspicious_stations: pd.DataFrame = station_stats.copy()
    suspicious_stations['high_non_diesel'] = False
    suspicious_stations['high_no_eld'] = False
    suspicious_stations['low_avg_cost'] = False
    suspicious_stations['suspicion_flags'] = 0

    # Flag high non-diesel rate (primary indicator of passenger vehicle fills)
    non_diesel_threshold: float = station_stats['non_diesel_rate'].quantile(0.75)
    high_non_diesel_mask: pd.Series[bool] = (
        suspicious_stations['non_diesel_rate'] >= non_diesel_threshold
    )
    suspicious_stations.loc[high_non_diesel_mask, 'high_non_diesel'] = True
    suspicious_stations.loc[high_non_diesel_mask, 'suspicion_flags'] += (
        2  # Double weight
    )

    # Flag high no-ELD rate
    no_eld_threshold: float = station_stats['no_eld_rate'].quantile(0.75)
    high_no_eld_mask: pd.Series[bool] = (
        suspicious_stations['no_eld_rate'] >= no_eld_threshold
    )
    suspicious_stations.loc[high_no_eld_mask, 'high_no_eld'] = True
    suspicious_stations.loc[high_no_eld_mask, 'suspicion_flags'] += 1

    # Flag low average cost (suggests small passenger vehicle fills)
    low_cost_threshold: float = station_stats['avg_cost'].quantile(0.25)
    low_cost_mask: pd.Series[bool] = (
        suspicious_stations['avg_cost'] <= low_cost_threshold
    )
    suspicious_stations.loc[low_cost_mask, 'low_avg_cost'] = True
    suspicious_stations.loc[low_cost_mask, 'suspicion_flags'] += 1

    # Filter to only stations with at least one flag and minimum transaction volume
    suspicious_stations = (
        suspicious_stations[
            (suspicious_stations['suspicion_flags'] > 0)
            & (suspicious_stations['transaction_count'] >= SUSPICIOUS_STATION_MIN_COUNT)
        ]
        .sort_values('suspicion_flags', ascending=False)
        .head(10)
    )

    # Write report using ForensicReportWriter method
    context.report_writer.write_geographic_analysis(
        station_stats=station_stats,
        suspicious_stations=suspicious_stations,
        top_n=context.config.analysis.top_n_entities,
    )

    return station_stats


def run_suspicious_pattern_analysis(
    context: AnalysisContext,
    all_tests: dict[str, StatisticalTest],
) -> None:
    """
    Orchestrate all suspicious pattern detection analyses with focus on
    passenger vehicle fraud detection.

    This is a convenience function that runs all pattern detection modules,
    with emphasis on identifying employees filling personal vehicles instead
    of company commercial trucks.

    Args:
        target_location: DataFrame for the target branch
        all_tests: dictionary containing all pre-calculated StatisticalTest objects
        report_writer: Instance of ForensicReportWriter
        top_n: Number of top items to display in each analysis
    """
    # Run multi-fillup analysis (passenger vehicle fraud detection)
    run_multiple_fillup_analysis(
        context,
        all_tests=all_tests,
    )

    # Run geographic analysis (station-level fraud patterns)
    analyze_geographic_anomalies(
        context
    )


# ========================================================================
# Internal Helper Functions
# ========================================================================


def _agg_unique_sorted_products(product_series: pd.Series) -> str:
    """
    Aggregates unique, sorted product names into a single
    comma-separated string.
    """
    return ', '.join(sorted(product_series.unique()))


def _agg_time_span_hours(datetime_series: pd.Series) -> float:
    """
    Calculates the total time span of a datetime series in hours.
    Returns 0.0 if there is only one timestamp.
    """
    if len(datetime_series) > 1:
        time_delta: timedelta = datetime_series.max() - datetime_series.min()
        return time_delta.total_seconds() / 3600.0
    return 0.0


def _agg_return_nan(series: pd.Series) -> float:
    """
    An aggregator that ignores the input series and always returns np.nan.
    Used as a placeholder in conditional aggregations.
    """
    # The input series is intentionally unused
    return np.nan


def _agg_false_mean(bool_series: pd.Series) -> float:
    """
    Calculates the proportion (mean) of FALSE values in a boolean Series.

    This works by inverting the boolean Series (where False becomes True)
    and then calculating the mean of the result. The output is a float
    between 0.0 and 1.0 representing the rate of False values.

    Args:
        bool_series: A pandas Series containing boolean values.

    Returns:
        The proportion of False values (e.g., 0.75 for 3 False in 4 rows).
    """
    return (~bool_series).mean()
