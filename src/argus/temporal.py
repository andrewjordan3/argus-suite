# argus/temporal.py

import logging
from collections.abc import Callable
from typing import Any, Literal

import numpy as np
import pandas as pd

from argus.models.analysis import TemporalRiskProfile
from argus.models.context.context_model import AnalysisContext
from argus.utils import (
    EntityAnalysisContext,
    EntityMetadata,
    autocorrelation_analysis,
    compare_temporal_risk_distributions,
    create_baseline_from_others,
    cusum_change_detection,
    detect_fraud_patterns,
    detect_multiple_changepoints,
    mann_kendall_trend_test,
    month_over_month_analysis,
    rolling_window_analysis,
    segment_comparison_test,
)

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)


def _analyze_entity_temporal_pattern(
    entity_context: EntityAnalysisContext,
) -> dict[str, Any] | None:
    """
    Analyze temporal patterns for a single driver or vehicle to detect potential fraud.

    This function performs comprehensive time-series analysis including:
    - Trend detection (Mann-Kendall test)
    - Change point detection (CUSUM and Bayesian methods)
    - Month-over-month comparison for sudden changes
    - Rolling window analysis for anomaly detection
    - Autocorrelation analysis for persistent patterns
    - Specific fraud pattern recognition

    Args:
        entity_df: Data for the specific entity (all transactions)
        entity_id: Internal ID (VINIndex for vehicles)
        entity_type: 'Driver' or 'Vehicle'
        display_id: Human-readable ID to display (VIN for vehicles)

    Returns:
        dictionary containing comprehensive temporal analysis results, or None if insufficient data
    """
    analysis_config: AnalysisConfig = entity_context.parent_context.config.analysis
    context: AnalysisContext = entity_context.parent_context

    # Metadata
    entity_metadata: EntityMetadata = entity_context.metadata
    entity_type: Literal['Driver'] | Literal['Vehicle'] = entity_metadata.type
    entity_id: str = entity_metadata.id
    display_id: str = entity_metadata.display_label
    truck_description: str | None = entity_metadata.description

    entity_df: pd.DataFrame = entity_context.data.copy()
    min_months_for_analysis: int = analysis_config.temporal_minimum_months
    min_trans_for_analysis: int = analysis_config.min_transactions_temporal
    format_name: Callable[..., str] = context.report_formatter.format_temporal_metric_name

    # Require minimum of 6 transactions for meaningful temporal analysis
    dataframe_length: int = len(entity_df)
    if dataframe_length < min_trans_for_analysis:
        logger.warning(
            '_analyze_entity_temporal_pattern requires a dataframe size greater than '
            '%d but received one with %d.',
            min_trans_for_analysis,
            dataframe_length,
        )
        return None

    if entity_df['datetime_parsed'].isna().all():
        raise ValueError(
            f'All datetime_parsed values are null for {entity_type} {display_id}'
        )

    # =====================================================================
    # STEP 1: AGGREGATE DATA BY MONTH
    # =====================================================================
    # Group transactions by month and calculate key metrics for each month
    monthly_data: list[dict[str, int | float | Any]] = []

    for month, group in entity_df.groupby('month'):
        # Count unique transactions (not total rows, since same transaction can appear multiple times)
        unique_transactions: int = (
            group['datetime_parsed'].nunique()
            if 'datetime_parsed' in group.columns
            else len(group)
        )

        monthly_data.append(
            {
                'month': month,
                'datetime_count': unique_transactions,
                'no_eld_rate': 100
                * (~group['has_eld_activity']).mean(),  # % without ELD activity
                'non_diesel_rate': 100
                * (~group['is_diesel_def']).mean(),  # % non-diesel purchases
                'after_hours_rate': 100
                * (~group['is_business_hours']).mean(),  # % outside business hours
                'cost_mean': group['cost'].mean(),
                'cost_median': group['cost'].median(),
                'cost_sum': group['cost'].sum(),
            }
        )

    monthly: pd.DataFrame = pd.DataFrame(monthly_data).set_index('month')

    # Require at least 3 months of data for temporal analysis
    if len(monthly) < min_months_for_analysis:
        return None

    # Initialize results dictionary with basic information
    results: dict[str, Any] = {
        'entity_id': entity_id,
        'display_id': display_id,
        'entity_type': entity_type,
        'truck_description': truck_description,
        'months_active': len(monthly),
        'total_transactions': int(monthly['datetime_count'].sum()),
        'trends': {},
        'change_points': {},
        'segment_comparison': {},
        'risk_indicators': [],
        'current_risk_factors': [],
    }

    # =====================================================================
    # STEP 2: TREND DETECTION (Mann-Kendall Test)
    # =====================================================================
    # Test for monotonic trends in key metrics over time
    # This catches gradual escalation or decline in suspicious behavior
    metrics_to_test: dict[str, pd.Series[Any]] = {
        'transaction_volume': monthly['datetime_count'],
        'no_eld_rate': monthly['no_eld_rate'],
        'non_diesel_rate': monthly['non_diesel_rate'],
        'after_hours_rate': monthly['after_hours_rate'],
        'avg_transaction_cost': monthly['cost_mean'],
    }

    for metric_name, metric_series in metrics_to_test.items():
        display_name: str = format_name(metric_name)
        metric_data: pd.Series = metric_series.sort_index()
        trend_result: tuple[str, float, float] = mann_kendall_trend_test(metric_series)
        trend: str = trend_result[0]
        tau: float = trend_result[1]
        p_value: float = trend_result[2]
        results['trends'][metric_name] = {
            'trend': trend,
            'tau': tau,
            'p_value': p_value,
        }

        # Flag concerning trends that indicate potential fraud
        # Increasing suspicious behavior or decreasing legitimate indicators
        if trend == 'increasing' and metric_name in [
            'transaction_volume',
            'no_eld_rate',
            'non_diesel_rate',
            'after_hours_rate',
        ]:
            results['risk_indicators'].append(f'INCREASING {display_name}')
        elif trend == 'decreasing' and metric_name == 'avg_transaction_cost':
            results['risk_indicators'].append(
                'DECREASING average cost (potential passenger vehicle use)'
            )

        # Detect change points in the time series using CUSUM method
        # This identifies when behavior shifted significantly
        change_point: pd.Period | None = cusum_change_detection(
            metric_series, k=0.5, h=3.5
        )
        if change_point is not None:
            results['change_points'][metric_name] = str(change_point)

    # =====================================================================
    # STEP 3: ADVANCED CHANGE POINT DETECTION (Multiple Change Points)
    # =====================================================================
    # Detect ALL significant change points using Bayesian method
    # This catches multiple behavioral shifts over the time period
    multiple_changepoints: dict[str, Any] = {}
    for metric_name, metric_series in metrics_to_test.items():
        metric_data = metric_series.sort_index()
        changepoints: list[pd.Period] = detect_multiple_changepoints(
            metric_series, min_segment_length=2
        )
        if changepoints:
            multiple_changepoints[metric_name] = [str(cp) for cp in changepoints]

    results['multiple_change_points'] = multiple_changepoints

    # =====================================================================
    # STEP 4: MONTH-OVER-MONTH ANALYSIS
    # =====================================================================
    # Compare consecutive months to detect sudden spikes or gradual escalation
    # This is critical for catching fraud as it develops
    mom_analysis: dict[str, Any] = month_over_month_analysis(
        monthly, entity_context.distributions
    )
    results['month_over_month'] = mom_analysis

    # Add risk indicators based on month-over-month findings
    if mom_analysis['sudden_spikes']:
        for spike in mom_analysis['sudden_spikes']:
            results['risk_indicators'].append(
                f'SUDDEN SPIKE in {format_name(spike["metric"])} (+{spike["percentile"]:.0f}th percentile)'
            )

    if mom_analysis['gradual_escalation']:
        for escalation in mom_analysis['gradual_escalation']:
            results['risk_indicators'].append(
                f'GRADUAL ESCALATION in {format_name(escalation["metric"])} '
                f'({escalation["consecutive_months"]} consecutive months)'
            )

    # =====================================================================
    # STEP 5: ROLLING WINDOW ANOMALY DETECTION
    # =====================================================================
    # Identify months where behavior deviates significantly from recent baseline
    # Uses 3-month rolling window to smooth noise while remaining responsive
    rolling_analysis: dict[str, dict[str, Any]] = rolling_window_analysis(
        monthly, window=3
    )
    results['rolling_anomalies'] = rolling_analysis

    # Flag outlier months in the risk indicators
    for metric, anomaly_data in rolling_analysis.items():
        if anomaly_data['outlier_months']:
            results['risk_indicators'].append(
                f'ANOMALOUS MONTHS in {format_name(metric)}: {", ".join(anomaly_data["outlier_months"])}'
            )

    # =====================================================================
    # STEP 6: AUTOCORRELATION ANALYSIS
    # =====================================================================
    # Detect if suspicious behavior is persistent (systematic) vs random (opportunistic)
    # High autocorrelation indicates someone has established a "new normal" of bad behavior
    autocorr_analysis: dict[str, dict[str, float | str]] = autocorrelation_analysis(
        monthly, max_lag=3
    )
    results['autocorrelation'] = autocorr_analysis

    # Flag persistent patterns - these are especially concerning
    for metric, autocorr_data in autocorr_analysis.items():
        if autocorr_data.get('risk_level') == 'HIGH':
            results['risk_indicators'].append(
                f'PERSISTENT PATTERN in {format_name(metric)} (autocorr={autocorr_data["lag1_correlation"]:.2f})'
            )

    # =====================================================================
    # STEP 7: FRAUD PATTERN RECOGNITION
    # =====================================================================
    # Look for specific patterns commonly associated with fuel card fraud
    fraud_patterns: dict[str, bool] = detect_fraud_patterns(monthly)
    results['fraud_patterns'] = fraud_patterns

    # Add specific fraud pattern indicators
    fraud_pattern_descriptions: dict[str, str] = {
        'off_hours_concentration': 'OFF-HOURS CONCENTRATION PATTERN (excessive non-business hour activity)',
        'spike_retreat': 'SPIKE-AND-RETREAT PATTERN (rapid escalation followed by sudden cessation)',
        'gradual_escalation': 'GRADUAL ESCALATION PATTERN (sustained increase over extended period)',
        'operational_anomaly': 'OPERATIONAL ANOMALY PATTERN (behavior inconsistent with business patterns)',
    }

    for pattern_name, detected in fraud_patterns.items():
        if detected:
            results['risk_indicators'].append(fraud_pattern_descriptions[pattern_name])

    # =====================================================================
    # STEP 8: SEGMENT COMPARISON (First Half vs Second Half)
    # =====================================================================
    # Compare first half vs second half of time period
    # This provides a high-level view of whether behavior has changed over time
    midpoint: int = len(monthly) // 2
    if midpoint >= 2:  # noqa: PLR2004
        for metric_name, metric_series in metrics_to_test.items():
            metric_data = metric_series.sort_index()
            early: pd.Series = metric_data.loc[:midpoint]
            late: pd.Series = metric_data.iloc[midpoint:]
            p_value: float
            interpretation: str
            p_value, interpretation = segment_comparison_test(early, late)
            results['segment_comparison'][metric_name] = interpretation

    # =====================================================================
    # STEP 9: CALCULATE COMPREHENSIVE TEMPORAL RISK SCORE (0-100)
    # =====================================================================
    risk_score = 0

    # Component 1: Concerning trends (max 20 points)
    # Weight: Lower because trends alone don't confirm fraud
    trend_risk_count: int = sum(
        1
        for indicator in results['risk_indicators']
        if 'INCREASING' in indicator or 'DECREASING' in indicator
    )
    if trend_risk_count > 0:
        risk_score += min(20, trend_risk_count * 10)

    # Component 2: Change points - single or multiple (max 25 points)
    # Weight: Medium-high because change points indicate behavioral shifts
    total_changepoints: int = len(results['change_points']) + sum(
        len(cp_list) for cp_list in results['multiple_change_points'].values()
    )
    if total_changepoints > 0:
        risk_score += min(25, total_changepoints * 8)

    # Component 3: Month-over-month sudden changes (max 25 points)
    # Weight: High because sudden spikes are strong fraud indicators
    if mom_analysis['sudden_spikes']:
        risk_score += min(25, len(mom_analysis['sudden_spikes']) * 12)

    # Component 4: Gradual escalation patterns (max 15 points)
    # Weight: Medium because gradual changes could be legitimate business changes
    if mom_analysis['gradual_escalation']:
        risk_score += min(15, len(mom_analysis['gradual_escalation']) * 8)

    # Component 5: Fraud pattern signatures (max 30 points)
    # Weight: Highest because these are specific known fraud patterns
    fraud_pattern_count: int = sum(
        1 for detected in fraud_patterns.values() if detected
    )
    if fraud_pattern_count > 0:
        risk_score += min(30, fraud_pattern_count * 15)

    # Component 6: Persistent autocorrelated behavior (max 15 points)
    # Weight: Medium-high because persistence indicates systematic misuse
    high_autocorr_count: int = sum(
        1 for data in autocorr_analysis.values() if data.get('risk_level') == 'HIGH'
    )
    if high_autocorr_count > 0:
        risk_score += min(15, high_autocorr_count * 8)

    # Component 7: Rolling window anomalies (max 15 points)
    # Weight: Medium because anomalies need context from other indicators
    total_outliers: int = sum(
        len(data['outlier_months']) for data in rolling_analysis.values()
    )
    if total_outliers > 0:
        risk_score += min(15, total_outliers * 5)

    # Component 8: Current state risk factors (max 20 points)
    # Weight: High because this shows current behavior, not just historical
    if len(monthly) > 0:
        latest_month: pd.Series = monthly.iloc[-1]

        rate_thresholds: RateThresholds = context.config.thresholds.rates
        # High no-ELD rate in most recent month
        if latest_month['no_eld_rate'] > rate_thresholds.high_no_eld:
            risk_score += 8
            results['current_risk_factors'].append(
                f'High No ELD Rate ({latest_month["no_eld_rate"]:.1f}%)'
            )

        # High non-diesel rate in most recent month
        if latest_month['non_diesel_rate'] > rate_thresholds.high_non_diesel:
            risk_score += 6
            results['current_risk_factors'].append(
                f'High Non-Diesel Rate ({latest_month["non_diesel_rate"]:.1f}%)'
            )

        # High after-hours rate in most recent month
        if latest_month['after_hours_rate'] > rate_thresholds.high_after_hours:
            risk_score += 6
            results['current_risk_factors'].append(
                f'High After Hours Rate ({latest_month["after_hours_rate"]:.1f}%)'
            )

    # Ensure score doesn't exceed 100
    results['temporal_risk_score'] = min(100, risk_score)

    # =====================================================================
    # STEP 10: ADD SUMMARY STATISTICS FOR REPORTING
    # =====================================================================
    results['summary'] = {
        'total_risk_factors': len(results['risk_indicators']),
        'total_change_points': total_changepoints,
        'has_fraud_patterns': fraud_pattern_count > 0,
        'volatility_score': mom_analysis.get('volatility_score', 0),
        'recent_behavior_score': sum(1 for _ in results['current_risk_factors']),
    }

    return results


def _analyze_branch_temporal_patterns(
    context: AnalysisContext,
    baseline_distributions: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Analyze temporal patterns for all drivers and vehicles in a branch.

    Args:
        branch_df: DataFrame containing branch transaction data
        min_transactions: Minimum transactions required for analysis

    Returns:
        list of dictionaries containing temporal analysis results
    """
    target_historical_df: pd.DataFrame = context.target_historical_transactions.copy()
    min_trans_for_analysis: int = context.config.analysis.min_transactions_temporal

    results: list[dict[str, Any]] = []
    driver_list: list[str] = target_historical_df['driver_name'].unique().tolist()

    # Analyze by driver
    for driver in driver_list:
        driver_data: pd.DataFrame = target_historical_df.loc[
            target_historical_df['driver_name'] == driver
        ]
        driver_distributions: dict[str, Any] = baseline_distributions['driver_name']
        if len(driver_data) >= min_trans_for_analysis:
            metadata = EntityMetadata(
                id=driver,
                type='Driver',
                display_label=driver,
            )
            entity_context = EntityAnalysisContext(
                metadata=metadata,
                data=driver_data,
                distributions=driver_distributions,
                parent_context=context,
            )
            result: dict[str, Any] | None = _analyze_entity_temporal_pattern(
                entity_context
            )
            if result is not None:
                results.append(result)

    # Analyze by vehicle
    vinindex_list: list[int] = target_historical_df['vehicle_index'].unique().tolist()
    for vin_index in vinindex_list:
        vehicle_distributions: dict[str, Any] = baseline_distributions['vehicle_index']
        vin_data: pd.DataFrame = target_historical_df.loc[
            target_historical_df['vehicle_index'] == vin_index
        ]
        if len(vin_data) >= min_trans_for_analysis:
            metadata = EntityMetadata(
                id=str(vin_index),
                type='Vehicle',
                display_label=vin_data['vehicle_id'].iloc[0],
                description=vin_data['vehicle_description'].iloc[0],
            )
            entity_context = EntityAnalysisContext(
                metadata=metadata,
                data=vin_data,
                distributions=vehicle_distributions,
                parent_context=context,
            )
            result = _analyze_entity_temporal_pattern(entity_context)
            if result is not None:
                results.append(result)

    return results


def _create_temporal_profiles(
    results: list[dict[str, Any]],
) -> list[TemporalRiskProfile]:
    """
    Convert raw temporal analysis results to TemporalRiskProfile objects.

    This function extracts all the analysis data from the temporal analysis
    dictionaries and creates structured TemporalRiskProfile objects with
    all fields properly populated.

    Args:
        results: list of dictionaries from _analyze_entity_temporal_pattern()

    Returns:
        list of TemporalRiskProfile objects sorted by risk score (highest first)
    """
    profiles: list[TemporalRiskProfile] = []

    for result in results:
        # Create profile with all fields from enhanced temporal analysis
        profile = TemporalRiskProfile(
            # Core identification fields
            display_id=result['display_id'],
            entity_type=result['entity_type'],
            truck_description=result['truck_description'],
            risk_score=int(result['temporal_risk_score']),
            months_active=result['months_active'],
            total_transactions=result['total_transactions'],
            # Original temporal analysis fields
            change_points=result.get('change_points', {}),
            risk_indicators=result.get('risk_indicators', []),
            segment_comparison=result.get('segment_comparison', {}),
            # Enhanced temporal analysis fields
            multiple_change_points=result.get('multiple_change_points', {}),
            month_over_month=result.get('month_over_month', {}),
            rolling_anomalies=result.get('rolling_anomalies', {}),
            autocorrelation=result.get('autocorrelation', {}),
            fraud_patterns=result.get('fraud_patterns', {}),
            current_risk_factors=result.get('current_risk_factors', []),
            summary=result.get('summary', {}),
        )
        profiles.append(profile)

    # Sort by risk score (highest first) for prioritized review
    profiles.sort(key=lambda p: p.risk_score, reverse=True)

    return profiles


def _calculate_summary_stats(
    profiles: list[TemporalRiskProfile], thresholds: ThresholdsConfig
) -> dict[str, int | float | dict[str, int | float] | None]:
    """
    Calculate comprehensive summary statistics from temporal profiles.

    This function aggregates statistics across all analyzed entities including:
    - Overall risk distribution counts and percentages
    - Change point detection statistics
    - Trend detection statistics
    - Fraud pattern detection statistics
    - Current risk factor statistics
    - Separate statistics for drivers vs vehicles

    Args:
        profiles: list of TemporalRiskProfile objects

    Returns:
        dictionary containing comprehensive summary statistics for report generation
    """
    # Handle empty profiles case
    if not profiles:
        return {
            'total_entities': 0,
            'high_risk_count': 0,
            'high_risk_pct': 0.0,
            'critical_count': 0,
            'critical_pct': 0.0,
            'with_change_points': 0,
            'with_change_points_pct': 0.0,
            'with_trends': 0,
            'with_trends_pct': 0.0,
            'with_fraud_patterns': 0,
            'with_fraud_patterns_pct': 0.0,
            'with_current_risks': 0,
            'with_current_risks_pct': 0.0,
            'driver_stats': None,
            'vehicle_stats': None,
        }

    # Calculate overall statistics
    total: int = len(profiles)

    # Risk level counts
    critical_count: int = sum(
        1 for p in profiles if p.risk_score >= thresholds.risk_score.critical
    )
    high_risk_count: int = sum(1 for p in profiles if p.risk_score >= thresholds.risk_score.high)

    # Analysis detection counts
    with_change_points: int = sum(1 for p in profiles if p.has_change_points())
    with_trends: int = sum(1 for p in profiles if p.has_risk_indicators())
    with_fraud_patterns: int = sum(1 for p in profiles if p.has_fraud_patterns())
    with_current_risks: int = sum(1 for p in profiles if p.has_current_risks())

    # Calculate percentages for all metrics
    critical_pct: float = critical_count / total if total > 0 else 0.0
    high_risk_pct: float = high_risk_count / total if total > 0 else 0.0
    with_change_points_pct: float = with_change_points / total if total > 0 else 0.0
    with_trends_pct: float = with_trends / total if total > 0 else 0.0
    with_fraud_patterns_pct: float = with_fraud_patterns / total if total > 0 else 0.0
    with_current_risks_pct: float = with_current_risks / total if total > 0 else 0.0

    # =========================================================================
    # DRIVER-SPECIFIC STATISTICS
    # =========================================================================
    driver_profiles: list[TemporalRiskProfile] = [
        p for p in profiles if p.entity_type == 'Driver'
    ]
    driver_stats: dict[str, int | float] | None = None

    if driver_profiles:
        driver_risks: list[int] = [p.risk_score for p in driver_profiles]
        driver_count: int = len(driver_profiles)

        driver_high_risk_count: int = sum(
            1 for r in driver_risks if r >= thresholds.risk_score.high
        )
        driver_critical_count: int = sum(
            1 for p in driver_profiles if p.risk_score >= thresholds.risk_score.critical
        )

        driver_stats = {
            'count': driver_count,
            'mean_risk': float(np.mean(driver_risks)),
            'median_risk': float(np.median(driver_risks)),
            'high_risk_count': driver_high_risk_count,
            'high_risk_pct': driver_high_risk_count / driver_count
            if driver_count > 0
            else 0.0,
            'critical_count': driver_critical_count,
            'critical_pct': driver_critical_count / driver_count
            if driver_count > 0
            else 0.0,
        }

    # =========================================================================
    # VEHICLE-SPECIFIC STATISTICS
    # =========================================================================
    vehicle_profiles: list[TemporalRiskProfile] = [
        p for p in profiles if p.entity_type == 'Vehicle'
    ]
    vehicle_stats: dict[str, int | float] | None = None

    if vehicle_profiles:
        vehicle_risks: list[int] = [p.risk_score for p in vehicle_profiles]
        vehicle_count: int = len(vehicle_profiles)

        vehicle_high_risk_count: int = sum(
            1 for r in vehicle_risks if r >= thresholds.risk_score.high
        )
        vehicle_critical_count: int = sum(
            1
            for p in vehicle_profiles
            if p.risk_score >= thresholds.risk_score.critical
        )

        vehicle_stats = {
            'count': vehicle_count,
            'mean_risk': float(np.mean(vehicle_risks)),
            'median_risk': float(np.median(vehicle_risks)),
            'high_risk_count': vehicle_high_risk_count,
            'high_risk_pct': vehicle_high_risk_count / vehicle_count
            if vehicle_count > 0
            else 0.0,
            'critical_count': vehicle_critical_count,
            'critical_pct': vehicle_critical_count / vehicle_count
            if vehicle_count > 0
            else 0.0,
        }

    # =========================================================================
    # RETURN COMPREHENSIVE STATISTICS dictIONARY
    # =========================================================================
    return {
        # Overall entity counts
        'total_entities': total,
        # High risk (≥50) statistics
        'high_risk_count': high_risk_count,
        'high_risk_pct': high_risk_pct,
        # Critical risk (≥75) statistics
        'critical_count': critical_count,
        'critical_pct': critical_pct,
        # Change point detection statistics
        'with_change_points': with_change_points,
        'with_change_points_pct': with_change_points_pct,
        # Trend detection statistics
        'with_trends': with_trends,
        'with_trends_pct': with_trends_pct,
        # Fraud pattern detection statistics
        'with_fraud_patterns': with_fraud_patterns,
        'with_fraud_patterns_pct': with_fraud_patterns_pct,
        # Current risk factor statistics (most important - shows active issues)
        'with_current_risks': with_current_risks,
        'with_current_risks_pct': with_current_risks_pct,
        # Entity-type specific statistics
        'driver_stats': driver_stats,
        'vehicle_stats': vehicle_stats,
    }


def _create_timeline_data(profiles: list[TemporalRiskProfile]) -> pd.DataFrame | None:
    """
    Create timeline DataFrame showing when changes occurred.

    Args:
        profiles: list of TemporalRiskProfile objects

    Returns:
        DataFrame with change point timeline, or None if no change points
    """
    all_change_points: list[dict[str, str | int]] = []

    for profile in profiles:
        if profile.change_points:
            for metric, month in profile.change_points.items():
                all_change_points.append(
                    {
                        'entity': profile.display_id,
                        'entity_type': profile.entity_type,
                        'month': month,
                        'metric': metric,
                    }
                )

    if not all_change_points:
        return None

    return pd.DataFrame(all_change_points)


def run_advanced_temporal_analysis(context: AnalysisContext) -> dict[str, Any]:
    """
    Execute comprehensive temporal analysis for fraud detection.

    This function:
    1. Analyzes temporal patterns for all drivers and vehicles
    2. Identifies concerning trends and change points
    3. Compares target location to other branches
    4. Generates comprehensive report via ForensicReportWriter

    Args:
        target_location: DataFrame for the target branch
        others: DataFrame for all other branches
        report_writer: Instance of ForensicReportWriter for output
        min_transactions: Minimum transactions required for analysis
        top_n: Number of top entities to display in report

    Returns:
        dictionary with temporal analysis results and high-risk entities
    """
    peers_historical_df: pd.DataFrame = context.peer_historical_transactions.copy()
    combined_df: pd.DataFrame = context.complete_unsplit_transactions.copy()
    date_min: pd.Timestamp = combined_df['datetime_parsed'].min()
    date_max: pd.Timestamp = combined_df['datetime_parsed'].max()

    # Create baseline distributions from non-target branches
    baselines: dict[str, dict[str, dict[str, float]]] = create_baseline_from_others(
        peers_historical_df
    )

    # Step 1: Analyze target branch temporal patterns
    target_results: list[dict[str, Any]] = _analyze_branch_temporal_patterns(
        context,
        baseline_distributions=baselines,
    )

    # Step 2: Create temporal profiles
    temporal_profiles: list[TemporalRiskProfile] = _create_temporal_profiles(
        target_results
    )

    # Step 3: Calculate summary statistics
    summary_stats: dict[str, int | float | dict[str, int | float] | None] = (
        _calculate_summary_stats(temporal_profiles, context.config.thresholds)
    )

    # Step 4: Create timeline data
    timeline_data: pd.DataFrame | None = _create_timeline_data(temporal_profiles)

    # Step 5: Optional comparative analysis with other branches
    comparative_stats = None
    if len(temporal_profiles) > 0 and len(peers_historical_df) > 0:
        others_results: list[dict[str, Any]] = _analyze_branch_temporal_patterns(
            context,
            baseline_distributions=baselines,
        )

        if others_results:
            others_profiles: list[TemporalRiskProfile] = _create_temporal_profiles(
                others_results
            )

            target_risks: list[float] = [p.risk_score for p in temporal_profiles]
            others_risks: list[float] = [p.risk_score for p in others_profiles]

            # Statistical comparison
            comparative_stats: dict[str, float | bool | str] | None = (
                compare_temporal_risk_distributions(target_risks, others_risks)
            )

    # Step 6: Write report using ForensicReportWriter
    context.report_writer.write_temporal_analysis(
        temporal_profiles=temporal_profiles,
        summary_stats=summary_stats,
        timeline_data=timeline_data,
        comparative_stats=comparative_stats,
        date_min=date_min,
        date_max=date_max,
        top_n=context.config.analysis.top_n_entities,
    )

    # Step 7: Return analysis results
    high_risk_profiles: list[TemporalRiskProfile] = [
        p
        for p in temporal_profiles
        if p.risk_score >= context.config.thresholds.risk_score.high
    ]

    return {
        'temporal_profiles': temporal_profiles,
        'target_mean_risk': (
            np.mean([p.risk_score for p in temporal_profiles])
            if temporal_profiles
            else np.nan
        ),
        'high_risk_entities': high_risk_profiles,
        'summary_stats': summary_stats,
    }
