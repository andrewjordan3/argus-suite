# argus/models/common/placeholders.py
"""
Central registry of placeholder sets for ARGUS format strings.

This module defines all valid placeholder combinations used in locale files.
Each placeholder set corresponds to a specific format string pattern and maps
directly to the kwargs passed to str.format() in the application code.

Organization:
    Placeholder sets are organized by report section, matching the YAML structure.
    Names use PascalCase and describe the specific message/template they validate.

Naming Convention:
    {Section}{Subsection}{Purpose}
    Examples:
        - DataQualityMissingValueItem
        - ExecSummaryFindingTitle
        - TemporalEntityHeader

Usage in Models:
    >>> from argus.models.common.placeholders import Placeholders as P
    >>> from argus.models.common.placeholder_validation import FormatStr
    >>>
    >>> class DataQualityMessages(FrozenModel):
    ...     missing_value_item: FormatStr[P.DataQualityMissingValueItem]
    ...     outlier_item: FormatStr[P.DataQualityOutlierItem]

Usage in Application Code:
    >>> # The kwargs must match the placeholder names in the registry
    >>> message = locale.data_quality.messages.missing_value_item.format(
    ...     column="driver_id",
    ...     count=42,
    ...     percentage="3.2%",
    ... )

Translator Reference:
    Each placeholder set includes:
    - Docstring explaining the template's purpose
    - Inline comments documenting each placeholder's meaning and example values
"""

from typing import Final

__all__: list[str] = ['P']


class Placeholders:
    """
    Central registry of named placeholder sets for format string validation.

    All placeholder sets are defined as frozenset[str] class attributes.
    Use these directly in FormatStr type annotations.

    Placeholder sets are organized by report section for easy navigation.
    """

    # =========================================================================
    # GENERIC / SHARED PLACEHOLDERS
    # =========================================================================

    CountPercentage: Final[frozenset[str]] = frozenset(
        {
            'count',  # int: Number of items
            'percentage',  # str: Formatted percentage (e.g., "12.3%")
        }
    )
    """Generic count with percentage - used for various summary items."""

    LabelValue: Final[frozenset[str]] = frozenset(
        {
            'label',  # str: Descriptive label text
            'value',  # str: The value to display
        }
    )
    """Generic label-value pair for formatted output lines."""

    TopN: Final[frozenset[str]] = frozenset(
        {
            'top_n',  # int: Number of items to display (e.g., 10)
        }
    )
    """Template requiring only a count of items to display."""

    # =========================================================================
    # RED FLAGS SECTION
    # =========================================================================

    RedFlagSuspicionFormula: Final[frozenset[str]] = frozenset(
        {
            'passenger_weight',  # float: Weight multiplier for passenger indicators (from policy)
            'misuse_weight',  # float: Weight multiplier for misuse indicators (from policy)
        }
    )
    """
    Formula explanation for suspicion score calculation.
    Example: "Suspicion Score = (Passenger indicators * {policy.passenger_weight}) + ..."
    Note: policy. prefix is stripped during validation.
    """

    # =========================================================================
    # DATA PREPARATION SECTION
    # =========================================================================

    DataPrepCountPercentage: Final[frozenset[str]] = frozenset(
        {
            'count',  # int: Number of records affected
            'percentage',  # str: Percentage of total (e.g., "2.1%")
        }
    )
    """
    Data preparation messages showing record counts.
    Used for: duplicates_found, incomplete_found
    Example: "Duplicate records removed: {count} ({percentage})"
    """

    # =========================================================================
    # DATA QUALITY SECTION
    # =========================================================================

    DataQualityMissingValueItem: Final[frozenset[str]] = frozenset(
        {
            'column',  # str: Name of the column with missing values
            'count',  # int: Number of missing values
            'percentage',  # str: Percentage of total rows (e.g., "5.2%")
        }
    )
    """
    Individual line item for missing value report.
    Example: "   • {column}: {count} missing ({percentage})"
    """

    DataQualityValidityItem: Final[frozenset[str]] = frozenset(
        {
            'check_name',  # str: Name of the validity check that failed
            'count',  # int: Number of invalid instances
            'percentage',  # str: Percentage of total rows
        }
    )
    """
    Individual line item for validity check failures.
    Example: "   • {check_name}: {count} instances ({percentage})"
    """

    DataQualityOutlierItem: Final[frozenset[str]] = frozenset(
        {
            'column',  # str: Name of the column with outliers
            'count',  # int: Number of outlier values detected
            'percentage',  # str: Percentage of values that are outliers
            'bounds',  # str: Optional bounds info string (may be empty)
        }
    )
    """
    Individual line item for outlier detection.
    Example: "   • {column}: {count} outliers ({percentage}){bounds}"
    """

    DataQualityOutlierBounds: Final[frozenset[str]] = frozenset(
        {
            'lower',  # float/str: Lower bound of valid range
            'upper',  # float/str: Upper bound of valid range
        }
    )
    """
    Bounds suffix for outlier items.
    Example: " | Valid range: [{lower}, {upper}]"
    """

    DataQualityRemainingDuplicates: Final[frozenset[str]] = frozenset(
        {
            'count',  # int: Number of remaining duplicate records
        }
    )
    """
    Warning message for remaining duplicates after cleaning.
    Example: "⚠ Warning: {count} duplicates still present"
    """

    # =========================================================================
    # ANALYSIS SCOPE SECTION
    # =========================================================================

    ScopeSplitScenario: Final[frozenset[str]] = frozenset(
        {
            'min_year',  # int: First year in the dataset (e.g., 2021)
            'current_year',  # int: Most recent year (e.g., 2024)
            'num_months_current_year',  # int: Months available in current year (1-12)
        }
    )
    """
    Explanation for split analysis scenario (multi-year with sufficient current data).
    Example: "Data spans multiple years ({min_year}-{current_year}) with sufficient
             current-year data ({num_months_current_year} months)."
    """

    ScopeInsufficientScenario: Final[frozenset[str]] = frozenset(
        {
            'num_months_current_year',  # int: Number of months (insufficient, e.g., 2)
        }
    )
    """
    Explanation when current year has too few months for separate analysis.
    Example: "current year has insufficient data ({num_months_current_year} months)"
    """

    # Note: single scenario has no placeholders - use plain str

    # =========================================================================
    # STATISTICAL METHODOLOGY SECTION
    # =========================================================================

    MethodologyTargetLocation: Final[frozenset[str]] = frozenset(
        {
            'target_location',  # str: Branch name being analyzed
        }
    )
    """
    Methodology descriptions referencing the target location.
    Example: "How many times more likely the event is to happen in {target_location}..."
    """

    MethodologyRiskRatioThresholds: Final[frozenset[str]] = frozenset(
        {
            'risk_ratio_substantial',  # float: Threshold for substantial (e.g., 2.0)
            'risk_ratio_major',  # float: Threshold for major concern (e.g., 3.0)
        }
    )
    """
    Risk ratio interpretation thresholds (from policy).
    Example: "RR > {policy.risk_ratio_substantial}: Substantial difference"
    """

    MethodologyOddsRatioThresholds: Final[frozenset[str]] = frozenset(
        {
            'odds_ratio_strong',  # float: Threshold for strong (e.g., 3.0)
            'odds_ratio_very_strong',  # float: Threshold for very strong (e.g., 10.0)
        }
    )
    """
    Odds ratio interpretation thresholds (from policy).
    Example: "OR > {policy.odds_ratio_strong}: Strong association"
    """

    MethodologyRiskDiffThresholds: Final[frozenset[str]] = frozenset(
        {
            'risk_diff_practical',  # float: Practical significance threshold (e.g., 0.10)
            'risk_diff_practical_pct',  # str: As percentage (e.g., "10%")
            'risk_diff_major',  # float: Major threshold (e.g., 0.20)
            'risk_diff_major_pct',  # str: As percentage (e.g., "20%")
        }
    )
    """
    Risk difference interpretation thresholds (from policy).
    Example: "RD > {policy.risk_diff_practical} ({policy.risk_diff_practical_pct}): Practically significant"
    """

    MethodologyPValueThresholds: Final[frozenset[str]] = frozenset(
        {
            'p_significant',  # float: Threshold for significant (e.g., 0.05)
            'confidence_pct',  # str: Confidence level as percentage (e.g., "95%")
            'p_very_significant',  # float: Threshold for very significant (e.g., 0.01)
            'very_significant_confidence_pct',  # str: e.g., "99%"
            'p_highly_significant',  # float: Threshold for highly significant (e.g., 0.001)
            'highly_significant_confidence_pct',  # str: e.g., "99.9%"
        }
    )
    """
    P-value significance thresholds and confidence levels (from policy).
    Example: "p < {policy.p_significant}: Statistically significant* ({policy.confidence_pct} confidence)"
    """

    MethodologySignificanceNote: Final[frozenset[str]] = frozenset(
        {
            'alpha',  # float: Significance threshold (e.g., 0.05)
            'confidence_level',  # float: Confidence level (e.g., 0.95)
        }
    )
    """
    Note explaining significance threshold.
    Example: "Significance threshold: α = {alpha:.2f} (confidence level = {confidence_level:.2f})."
    """  # noqa: RUF001

    MethodologyCliffsDeltaThresholds: Final[frozenset[str]] = frozenset(
        {
            'cliffs_delta_negligible',  # float: Negligible threshold (e.g., 0.15)
            'cliffs_delta_small',  # float: Small threshold (e.g., 0.33)
            'cliffs_delta_medium',  # float: Medium threshold (e.g., 0.47)
        }
    )
    """
    Cliff's delta effect size thresholds (from policy).
    Example: "|δ| < {policy.cliffs_delta_negligible}: Negligible"
    """

    MethodologyCohensDThresholds: Final[frozenset[str]] = frozenset(
        {
            'cohens_d_negligible',  # float: Negligible threshold (e.g., 0.2)
            'cohens_d_small',  # float: Small threshold (e.g., 0.5)
            'cohens_d_medium',  # float: Medium threshold (e.g., 0.8)
        }
    )
    """
    Cohen's d effect size thresholds (from policy).
    Example: "|d| < {policy.cohens_d_negligible}: Negligible"
    """

    MethodologyAlpha: Final[frozenset[str]] = frozenset(
        {
            'alpha',  # float: Significance threshold (e.g., 0.05)
        }
    )
    """
    Templates requiring only alpha value.
    Example: "q-values and deems a result significant if q < α (= {alpha:.2f})"
    """  # noqa: RUF001

    # =========================================================================
    # MULTIPLE TESTING CORRECTION SECTION
    # =========================================================================

    # Uses MethodologyAlpha - same placeholder set

    # =========================================================================
    # TEST INTERPRETATIONS SECTION
    # =========================================================================

    TestInterpCostDirection: Final[frozenset[str]] = frozenset(
        {
            'target_location',  # str: Branch name being analyzed
            'direction',  # str: "higher" or "lower"
        }
    )
    """
    Cost distribution significant finding - direction statement.
    Example: "→ {target_location} transaction costs are {direction} than other branches."
    """

    TestInterpCostDifference: Final[frozenset[str]] = frozenset(
        {
            'mean_difference',  # str: Formatted currency difference (e.g., "$12.34")
        }
    )
    """
    Cost distribution significant finding - difference amount.
    Example: "→ Mean difference: {mean_difference} per transaction"
    """

    TestInterpRateSignificant: Final[frozenset[str]] = frozenset(
        {
            'target_location',  # str: Branch name being analyzed
            'risk_ratio',  # float: Ratio of target rate to baseline rate
        }
    )
    """
    Rate comparison significant finding - interpretation line.
    Example: "→ Interpretation: {target_location} is {risk_ratio:.1f} times more likely"
    """

    TestInterpRateContext: Final[frozenset[str]] = frozenset(
        {
            'test_name',  # str: Name of the statistical test
        }
    )
    """
    Rate comparison significant finding - context line.
    Example: "to have {test_name}. This result is unlikely under the null hypothesis..."
    """

    TestInterpEffectSize: Final[frozenset[str]] = frozenset(
        {
            'magnitude',  # str: Effect size label (negligible/small/medium/large)
            'target_location',  # str: Branch name being analyzed
            'direction',  # str: "higher" or "lower"
        }
    )
    """
    Effect size interpretation format (Cliff's delta or Cohen's d).
    Example: "({magnitude} effect, {target_location} costs are {direction})"
    """

    TestInterpPValueHighlySignificant: Final[frozenset[str]] = frozenset(
        {
            'p_highly_significant',  # float: Threshold (e.g., 0.001)
        }
    )
    """
    P-value interpretation - highly significant.
    Example: "highly significant (p < {policy.p_highly_significant})"
    """

    TestInterpPValueFormatted: Final[frozenset[str]] = frozenset(
        {
            'clean_p_value',  # float: P-value for display
        }
    )
    """
    P-value interpretation with formatted value.
    Example: "significant (p = {clean_p_value:.3f})"
    """

    # =========================================================================
    # FINANCIAL IMPACT SECTION
    # =========================================================================

    FinancialTargetLocation: Final[frozenset[str]] = frozenset(
        {
            'target_location',  # str: Branch name being analyzed
        }
    )
    """
    Labels that include target location name.
    Example: "{target_location}" as a label
    """

    FinancialExposureItems: Final[frozenset[str]] = frozenset(
        {
            'excess_count',  # int: Count of excess unverified transactions
            'avg_cost',  # str: Average cost formatted as currency
            'total_exposure',  # str: Total exposure formatted as currency
            'confidence_pct',  # str: Confidence level (e.g., "95%")
            'ci_low',  # str: Lower bound formatted as currency
            'ci_high',  # str: Upper bound formatted as currency
        }
    )
    """
    Exposure item:
        excess unverified transaction count
        average cost of unverified transactions
        estimated total financial exposure
        confidence interval (confidence level, lower bound, upper bound)
    Example:
        - "• Excess unverified transactions: {excess_count}"
        - "• Average cost of unverified: {avg_cost}"
        - "• Estimated exposure: {total_exposure}"
        - "• {policy.confidence_pct} Confidence Interval: [{ci_low}, {ci_high}]"
    """

    # =========================================================================
    # EXECUTIVE SUMMARY SECTION
    # =========================================================================

    ExecSummaryNoFindings: Final[frozenset[str]] = frozenset(
        {
            'target_location',  # str: Branch name being analyzed
        }
    )
    """
    No findings paragraphs - referencing target location.
    Example: "...differences may exist between {target_location} and other branches..."
    """

    ExecSummaryFindingsHeader: Final[frozenset[str]] = frozenset(
        {
            'count',  # int: Number of significant findings
        }
    )
    """
    Findings section header with count.
    Example: "{count} STATISTICALLY SIGNIFICANT FINDING(S) IDENTIFIED:"
    """

    ExecSummaryFindingTitle: Final[frozenset[str]] = frozenset(
        {
            'index',  # int: 1-indexed finding number
            'test_name',  # str: Name of the statistical test
        }
    )
    """
    Individual finding title.
    Example: "FINDING #{index}: {test_name}"
    """

    ExecSummaryRateComparisonMain: Final[frozenset[str]] = frozenset(
        {
            'target_location',  # str: Branch name being analyzed
        }
    )
    """
    Rate comparison finding - main line.
    Example: "→ {target_location} has a statistically significant,"
    """

    ExecSummaryRateComparisonDetail: Final[frozenset[str]] = frozenset(
        {
            'risk_ratio',  # float: Ratio of target rate to baseline
            'direction',  # str: "higher" or "lower"
            'test_name',  # str: Name of the test/metric
        }
    )
    """
    Rate comparison finding - detail line.
    Example: "  {risk_ratio:.2f}x {direction} rate of '{test_name}' events."
    """

    ExecSummaryRateComparisonRates: Final[frozenset[str]] = frozenset(
        {
            'target_rate',  # str: Event rate in target location
            'baseline_rate',  # str: Event rate in baseline
        }
    )
    """
    Rate comparison finding - rates display.
    Example: "   Target: {target_rate} vs. Other Branches: {baseline_rate}"
    """

    ExecSummaryRateComparisonOddsRatio: Final[frozenset[str]] = frozenset(
        {
            'odds_ratio',  # float: Odds ratio value
        }
    )
    """
    Rate comparison finding - odds ratio.
    Example: "   Odds Ratio: {odds_ratio:.2f}x (indicates strength of association)"
    """

    ExecSummaryCostComparisonMain: Final[frozenset[str]] = frozenset(
        {
            'test_name',  # str: Name of the statistical test
        }
    )
    """
    Cost comparison finding - main.
    Example: "→ {test_name} shows a statistically significant difference."
    """

    ExecSummaryCostComparisonAverages: Final[frozenset[str]] = frozenset(
        {
            'target_avg',  # str: Mean value in target (formatted currency)
            'baseline_avg',  # str: Mean value in baseline (formatted currency)
        }
    )
    """
    Cost comparison finding - averages.
    Example: "   Target avg: {target_avg} vs. Other branches avg: {baseline_avg}"
    """

    ExecSummaryCostComparisonEffect: Final[frozenset[str]] = frozenset(
        {
            'effect_size',  # float: Standardized effect size
            'direction',  # str: "higher" or "lower"
        }
    )
    """
    Cost comparison finding - effect size.
    Example: "   Effect size (Cliff's Delta): {effect_size:.3f} ({direction} in target location)"
    """

    ExecSummaryStatisticalStrength: Final[frozenset[str]] = frozenset(
        {
            'p_value',  # str: P-value description (e.g., "p < 0.001")
            'q_value',  # float: FDR-adjusted q-value
        }
    )
    """
    Statistical strength statement.
    Example: "→ Statistical strength: {p_value}, FDR-adjusted q-value: {q_value:.4f}"
    """

    ExecSummaryRiskDifference: Final[frozenset[str]] = frozenset(
        {
            'risk_diff',  # str: Absolute difference formatted
            'direction',  # str: "higher" or "lower"
        }
    )
    """
    Risk difference finding.
    Example: "→ Absolute difference: {risk_diff} {direction} in event rate"
    """

    # =========================================================================
    # DRIVER ANALYSIS SECTION
    # =========================================================================

    DriverDeepDiveTitle: Final[frozenset[str]] = frozenset(
        {
            'driver_name',  # str: Driver's full name
        }
    )
    """
    Driver deep dive section title.
    Example: "DEEP DIVE: DRIVER PROFILE - {driver_name}"
    """

    DriverRiskScore: Final[frozenset[str]] = frozenset(
        {
            'risk_score',  # float: Composite risk score (0-100)
            'risk_category',  # str: Category label (Critical/High/Medium/Low)
        }
    )
    """
    Driver risk score display.
    Example: "Overall Risk Score: {risk_score:.1f}/100 ({risk_category} Risk)"
    """

    # List placeholder sets (union of all required placeholders)
    DriverTransactionItems: Final[frozenset[str]] = frozenset(
        {
            'transaction_count',  # int: Number of transactions
            'total_cost',  # str: Sum formatted as currency
            'avg_cost',  # str: Mean formatted as currency
            'unique_vehicles',  # int: Count of unique vehicles used
        }
    )
    """
    Driver transaction summary line items (rendered as list).
    All placeholders must appear somewhere across the list items.
    """

    DriverRiskItems: Final[frozenset[str]] = frozenset(
        {
            'no_eld_rate',  # str: Rate formatted as percentage
            'non_diesel_rate',  # str: Rate formatted as percentage
            'after_hours_rate',  # str: Rate formatted as percentage
        }
    )
    """
    Driver risk indicator line items (rendered as list).
    All placeholders must appear somewhere across the list items.
    """

    DriverProductBreakdown: Final[frozenset[str]] = frozenset(
        {
            'product',  # str: Product type name
            'count',  # int: Number of purchases
            'percentage',  # str: Percentage of total
            'total_cost',  # str: Total cost formatted as currency
        }
    )
    """
    Driver product breakdown line item.
    Example: "  • {product}: {count} ({percentage}) - {total_cost}"
    """

    DriverMultiFillupItems: Final[frozenset[str]] = frozenset(
        {
            'multi_fillup_days',  # int: Days with multiple fillups
            'max_fillups_one_day',  # int: Maximum fillups in single day
            'avg_cost_multi_fillup_days',  # str: Average cost formatted
        }
    )
    """
    Driver multi-fillup statistic line items (rendered as list).
    All placeholders must appear somewhere across the list items.
    """

    # =========================================================================
    # MULTI-FILLUP ANALYSIS SECTION
    # =========================================================================

    MultiFillupSignificanceDetails: Final[frozenset[str]] = frozenset(
        {
            'p_value',  # str: P-value description
            'q_value',  # float: FDR-adjusted q-value
        }
    )
    """
    Multi-fillup significance context details.
    Example: "({p_value}, q = {q_value:.4f})"
    """

    MultiFillupSignificanceInterpretation: Final[frozenset[str]] = frozenset(
        {
            'target_location',  # str: Branch name being analyzed
        }
    )
    """
    Multi-fillup significant interpretation.
    Example: "This indicates {target_location} has a statistically higher rate..."
    """

    MultiFillupSummaryItems: Final[frozenset[str]] = frozenset(
        {
            'total_events',  # int: Total multi-fillup events
            'total_drivers',  # int: Unique drivers involved
            'avg_fillups',  # float: Average fillups per event
            'total_cost',  # str: Total cost formatted as currency
            'high_suspicion_count',  # int: Count of high-suspicion events
        }
    )
    """Multi-fillup summary - all metrics."""

    MultiFillupTopN: Final[frozenset[str]] = frozenset(
        {
            'top_n',  # int: Number of top items to display
        }
    )
    """Multi-fillup top N - same as TopN placeholder set."""

    # =========================================================================
    # GEOGRAPHIC ANALYSIS SECTION
    # =========================================================================

    GeoTableTitle: Final[frozenset[str]] = frozenset(
        {
            'top_n',  # int: Number of items to display
            'target_location',  # str: Branch name being analyzed
        }
    )
    """
    Geographic analysis table title.
    Example: "TOP {top_n} MOST USED FUEL STATIONS ({target_location}):"
    """

    GeoSuspiciousStationFormat: Final[frozenset[str]] = frozenset(
        {
            'station_name',  # str: Fuel station name
            'transaction_count',  # int: Number of transactions
            'flags',  # str: Concatenated flag indicators
        }
    )
    """
    Suspicious station line item.
    Example: "  • {station_name}: {transaction_count} trans - {flags}"
    """

    GeoFlagRate: Final[frozenset[str]] = frozenset(
        {
            'rate',  # str: Rate formatted as percentage
        }
    )
    """
    Geographic flag format with rate.
    Example: "Non-diesel: {rate}"
    """

    GeoFlagCost: Final[frozenset[str]] = frozenset(
        {
            'cost',  # str: Cost formatted as currency
        }
    )
    """
    Geographic flag format with cost.
    Example: "Low avg cost: {cost}"
    """

    # =========================================================================
    # TEMPORAL ANALYSIS SECTION - INTRODUCTION
    # =========================================================================

    TemporalIntroTargetLocation: Final[frozenset[str]] = frozenset(
        {
            'target_location',  # str: Branch name being analyzed
        }
    )
    """
    Temporal analysis introduction - target location reference.
    Example: "...identifies when suspicious patterns emerged in {target_location}..."
    """

    TemporalIntroSpikeThreshold: Final[frozenset[str]] = frozenset(
        {
            'spike_threshold_pct',  # str: Spike percentage threshold (e.g., "50")
        }
    )
    """
    Temporal intro - spike threshold reference.
    Example: "Sudden spikes (25 pts) - Month-over-month jumps >{policy.spike_threshold_pct}%"
    """

    TemporalIntroAll: Final[frozenset[str]] = frozenset(
        {
            'target_location',  # str: Branch name being analyzed
            'spike_threshold_pct',  # str: Spike percentage threshold (e.g., "50")
        }
    )
    """
    Temporal intro - all thresholds reference.
    Example: "Sudden spikes (25 pts) - Month-over-month jumps >{policy.spike_threshold_pct}%...
             Target location: {target_location}"
    """

    TemporalBusinessHoursRange: Final[frozenset[str]] = frozenset(
        {
            'business_hours_range',  # str: Business hours (e.g., "M-F, 6am-4pm")
        }
    )
    """
    Metric definition - after hours rate.
    Example: "...OUTSIDE business hours ({policy.business_hours_range})"
    """

    TemporalTopN: Final[frozenset[str]] = frozenset(
        {
            'top_n',  # int: Number of top items to display
        }
    )
    """Temporal analysis top N - same as TopN placeholder set."""

    # =========================================================================
    # TEMPORAL ANALYSIS - THRESHOLDS (from policy)
    # =========================================================================

    TemporalSpikeThresholds: Final[frozenset[str]] = frozenset(
        {
            'spike_threshold_pct',  # str: Spike percentage (e.g., "50")
            'spike_percentile',  # str: Percentile threshold (e.g., "95")
            'consecutive_months',  # str: Number of consecutive months (e.g., "3")
        }
    )
    """
    Spike detection thresholds.
    Example: "Sudden Spike: >{policy.spike_threshold_pct}% increase...or >{policy.spike_percentile}th percentile"
    """

    TemporalAutocorrelationThreshold: Final[frozenset[str]] = frozenset(
        {
            'autocorrelation_threshold',  # float: Correlation threshold (e.g., 0.6)
        }
    )
    """
    Autocorrelation significance threshold.
    Example: "High lag-1 correlation (>{policy.autocorrelation_threshold}) indicates systematic pattern"
    """

    TemporalFraudPatternThresholdsOffHours: Final[frozenset[str]] = frozenset(
        {
            'off_hours_threshold_pct',  # str: Off-hours percentage (e.g., "60")
        }
    )
    """
    Fraud pattern recognition thresholds.
    Example: "off_hours_concentration: Excessive non-business hour activity (>{policy.off_hours_threshold_pct}%...)"
    """

    TemporalFraudPatternThresholdsSpikeRetreat: Final[frozenset[str]] = frozenset(
        {
            'spike_threshold_pct',  # str: Spike percentage (e.g., "50")
            'retreat_drop_pct',  # str: Retreat drop percentage (e.g., "40")
        }
    )
    """
    Fraud pattern recognition thresholds.
    Example: "spike_retreat: Repeated sudden spikes (>{policy.spike_threshold_pct}%...)"
    """

    TemporalFraudPatternThresholdsGradualEscalation: Final[frozenset[str]] = frozenset(
        {
            'period_change_pct',  # str: Period comparison change (e.g., "30")
        }
    )
    """
    Fraud pattern recognition thresholds.
    Example: "gradual_escalation: Gradual increase over periods (>{policy.period_change_pct}%...)"
    """

    TemporalPSignificant: Final[frozenset[str]] = frozenset(
        {
            'p_significant',  # float: P-value threshold (e.g., 0.05)
        }
    )
    """
    Period comparison significance threshold.
    Example: "INCREASED: Statistically significant rise (p < {policy.p_significant})"
    """

    # =========================================================================
    # TEMPORAL ANALYSIS - INSUFFICIENT DATA
    # =========================================================================

    TemporalInsufficientDataThresholds: Final[frozenset[str]] = frozenset(
        {
            'min_transactions_temporal',  # int: Min transactions needed (e.g., 20)
            'min_months_temporal',  # int: Min months needed (e.g., 3)
        }
    )
    """
    Insufficient data warning details.
    Example: "Entities need at least {policy.min_transactions_temporal} transactions across {policy.min_months_temporal}+ months."
    """

    # =========================================================================
    # TEMPORAL ANALYSIS - SUMMARY STATISTICS
    # =========================================================================

    TemporalSummaryItems: Final[frozenset[str]] = frozenset(
        {
            'date_min',  # str: Analysis period start date
            'date_max',  # str: Analysis period end date
            'total_entities',  # int: Total entities analyzed
            'risk_critical',  # int: Critical risk threshold
            'critical_count',  # int: Count of critical-risk entities
            'critical_pct',  # str: Percentage formatted
            'risk_high',  # int: High risk lower threshold
            'risk_critical_minus_one',  # int: Critical - 1 for range
            'high_risk_count',  # int: Count of high-risk entities
            'high_risk_pct',  # str: Percentage formatted
            'with_change_points',  # int: Count with change points
            'with_change_points_pct',  # str: Percentage formatted
            'with_trends',  # int: Count with trends
            'with_trends_pct',  # str: Percentage formatted
            'with_fraud_patterns',  # int: Count with fraud patterns
            'with_fraud_patterns_pct',  # str: Percentage formatted
            'with_current_risks',  # int: Count with current active risks
            'with_current_risks_pct',  # str: Percentage formatted
        }
    )
    """
    Temporal summary - analysis period, total entities, risk category counts,
    change point/trend/fraud pattern/current risk counts and percentages.
    Example:
        - "Analysis Period: {date_min} to {date_max}"
        - "Total Entities Analyzed: {total_entities}"
        - "Critical Risk (>{risk_critical}): {critical_count} ({critical_pct})"
        - "High Risk ({risk_high}-{risk_critical_minus_one}): {high_risk_count} ({high_risk_pct})"
        - "Entities with Change Points: {with_change_points} ({with_change_points_pct})"
        - "Entities with Trends: {with_trends} ({with_trends_pct})"
        - "Entities with Fraud Patterns: {with_fraud_patterns} ({with_fraud_patterns_pct})"
        - "Entities with Current Active Risks: {with_current_risks} ({with_current_risks_pct})"
    """

    # =========================================================================
    # TEMPORAL ANALYSIS - ENTITY DISPLAY
    # =========================================================================

    TemporalEntityTitle: Final[frozenset[str]] = frozenset(
        {
            'entity_type',  # str: Type of entity (Driver/Vehicle)
            'display_id',  # str: Display identifier
        }
    )
    """
    Entity section title (without truck description).
    Example: "{entity_type}: {display_id}"
    """

    TemporalEntityTitleWithTruck: Final[frozenset[str]] = frozenset(
        {
            'entity_type',  # str: Type of entity
            'display_id',  # str: Display identifier
            'truck_description',  # str: Vehicle year/make/model
        }
    )
    """
    Entity section title with truck description.
    Example: "{entity_type}: {display_id} ({truck_description})"
    """

    TemporalEntityRiskLine: Final[frozenset[str]] = frozenset(
        {
            'risk_score',  # float: Risk score (0-100)
            'risk_category',  # str: Category label
        }
    )
    """
    Entity risk score line.
    Example: "  Risk Score: {risk_score}/100 [{risk_category}]"
    """

    TemporalEntityActivityLine: Final[frozenset[str]] = frozenset(
        {
            'months_active',  # int: Number of months with activity
            'total_transactions',  # int: Total transactions for entity
        }
    )
    """
    Entity activity line.
    Example: "  Active: {months_active} months | Transactions: {total_transactions}"
    """

    TemporalEntityFlagsLine: Final[frozenset[str]] = frozenset(
        {
            'flags',  # str: Comma-separated analysis flags
        }
    )
    """
    Entity analysis flags line.
    Example: "  Analysis Flags: {flags}"
    """

    TemporalCurrentRiskFactor: Final[frozenset[str]] = frozenset(
        {
            'factor',  # str: Risk factor description
        }
    )
    """
    Current risk factor line item.
    Example: "    • {factor}"
    """

    # =========================================================================
    # TEMPORAL ANALYSIS - MONTH-OVER-MONTH
    # =========================================================================

    TemporalSuddenSpike: Final[frozenset[str]] = frozenset(
        {
            'metric',  # str: Metric name
            'percentile',  # float: Percentile value
            'count',  # int: Number of months
            'months',  # str: Month labels (comma-separated)
        }
    )
    """
    Sudden spike detection format.
    Example: "      • {metric}: Max {percentile:.1f}th percentile across {count} months ({months})"
    """

    TemporalGradualEscalation: Final[frozenset[str]] = frozenset(
        {
            'metric',  # str: Metric name
            'consecutive',  # int: Count of consecutive months
        }
    )
    """
    Gradual escalation format.
    Example: "      • {metric}: {consecutive} consecutive months of increases"
    """

    TemporalVolatilityScore: Final[frozenset[str]] = frozenset(
        {
            'volatility_score',  # str: Volatility score value
        }
    )
    """
    Volatility score display.
    Example: "    Volatility Score: {volatility_score}"
    """

    # =========================================================================
    # TEMPORAL ANALYSIS - CHANGE POINTS
    # =========================================================================

    TemporalChangePointSingle: Final[frozenset[str]] = frozenset(
        {
            'metric',  # str: Metric name
            'month',  # str: Month label
        }
    )
    """
    Single change point format.
    Example: "    • {metric}: Changed around {month}"
    """

    TemporalChangePointMultipleIntro: Final[frozenset[str]] = frozenset(
        {
            'metric',  # str: Metric name
        }
    )
    """
    Multiple change points intro.
    Example: "    • {metric}: Multiple changes detected"
    """

    TemporalChangePointDate: Final[frozenset[str]] = frozenset(
        {
            'metric',  # str: Metric name
            'date',  # str: Date string
        }
    )
    """
    Change point with date.
    Example: "  • {metric}: {date}"
    """

    TemporalChangePointMultipleDates: Final[frozenset[str]] = frozenset(
        {
            'metric',  # str: Metric name
            'dates',  # str: Multiple dates (comma-separated)
        }
    )
    """
    Multiple change points with dates.
    Example: "  • {metric}: Multiple changes ({dates})"
    """

    # =========================================================================
    # TEMPORAL ANALYSIS - AUTOCORRELATION
    # =========================================================================

    TemporalAutocorrelation: Final[frozenset[str]] = frozenset(
        {
            'metric',  # str: Metric name
            'correlation',  # float/str: Autocorrelation coefficient
            'level',  # str: Persistence level label
        }
    )
    """
    Autocorrelation pattern format.
    Example: "  • {metric}: Correlation = {correlation} (Persistently {level})"
    """

    # =========================================================================
    # TEMPORAL ANALYSIS - ROLLING ANOMALIES
    # =========================================================================

    TemporalRollingAnomaly: Final[frozenset[str]] = frozenset(
        {
            'metric',  # str: Metric name
            'months',  # str: Month labels with anomalies
            'z_score',  # float/str: Z-score value
        }
    )
    """
    Rolling window anomaly format.
    Example: "  • {metric}: Outliers in {months} (Max Z-score: {z_score})"
    """

    TemporalMaxZScore: Final[frozenset[str]] = frozenset(
        {
            'max_z_score',  # float/str: Maximum z-score
        }
    )
    """
    Max z-score line.
    Example: "      (Max z-score: {max_z_score})"
    """

    # =========================================================================
    # TEMPORAL ANALYSIS - TRENDS
    # =========================================================================

    TemporalTrendIndicator: Final[frozenset[str]] = frozenset(
        {
            'indicator',  # str: Trend indicator description
        }
    )
    """
    Trend indicator line item.
    Example: "    • {indicator}"
    """

    # =========================================================================
    # TEMPORAL ANALYSIS - PERIOD COMPARISON
    # =========================================================================

    TemporalPeriodComparison: Final[frozenset[str]] = frozenset(
        {
            'metric',  # str: Metric name
            'result',  # str: Comparison result (INCREASED/DECREASED/NO CHANGE)
        }
    )
    """
    Period comparison result.
    Example: "  • {metric}: {result}"
    """

    # =========================================================================
    # TEMPORAL ANALYSIS - ENTITY SUMMARY
    # =========================================================================

    TemporalEntitySummaryRisk: Final[frozenset[str]] = frozenset(
        {
            'risk_category',  # str: Risk category label
            'risk_score',  # float: Risk score value
        }
    )
    """
    Entity summary risk format.
    Example: "  Risk Level: {risk_category} (Score: {risk_score}/100)"
    """

    # =========================================================================
    # TEMPORAL ANALYSIS - RISK DISTRIBUTION
    # =========================================================================

    TemporalRiskDistCritical: Final[frozenset[str]] = frozenset(
        {
            'risk_critical',  # int: Critical threshold
            'critical_count',  # int: Count in this category
        }
    )
    """
    Risk distribution - critical category.
    Example: "  Critical ({policy.risk_critical}-100): {critical_count} entities"
    """

    TemporalRiskDistHigh: Final[frozenset[str]] = frozenset(
        {
            'risk_high',  # int: High threshold
            'risk_critical_minus_one',  # int: Critical - 1
            'high_count',  # int: Count in this category
        }
    )
    """
    Risk distribution - high category.
    Example: "  High ({policy.risk_high}-{policy.risk_critical_minus_one}): {high_count} entities"
    """

    TemporalRiskDistMedium: Final[frozenset[str]] = frozenset(
        {
            'risk_medium',  # int: Medium threshold
            'risk_high_minus_one',  # int: High - 1
            'medium_count',  # int: Count in this category
        }
    )
    """
    Risk distribution - medium category.
    Example: "  Medium ({policy.risk_medium}-{policy.risk_high_minus_one}): {medium_count} entities"
    """

    TemporalRiskDistLow: Final[frozenset[str]] = frozenset(
        {
            'risk_medium_minus_one',  # int: Medium - 1
            'low_count',  # int: Count in this category
        }
    )
    """
    Risk distribution - low category.
    Example: "  Low (0-{policy.risk_medium_minus_one}): {low_count} entities"
    """

    TemporalRiskDistEntityType: Final[frozenset[str]] = frozenset(
        {
            'count',  # int: Number of entities of this type
        }
    )
    """
    Entity type header with count.
    Example: "Drivers (n={count}):"
    """

    TemporalRiskDistEntityStats: Final[frozenset[str]] = frozenset(
        {
            'mean_risk',  # float: Mean risk score
            'median_risk',  # float: Median risk score
            'risk_critical',  # int: Critical threshold
            'critical_count',  # int: Critical count
            'critical_pct',  # float: Critical percentage
            'risk_high',  # int: High threshold
            'risk_critical_minus_one',  # int: Critical - 1
            'high_risk_count',  # int: High risk count
            'high_risk_pct',  # float: High risk percentage
        }
    )
    """
    Entity type detailed statistics.
    Used for driver/vehicle risk distribution items.
    """

    # =========================================================================
    # TEMPORAL ANALYSIS - FRAUD TIMELINE
    # =========================================================================

    TemporalTimelineMonthFormat: Final[frozenset[str]] = frozenset(
        {
            'month',  # str: Month label
            'count',  # int: Number of changes
            'label',  # str: Visual indicator (e.g., bar chart characters)
        }
    )
    """
    Timeline month entry.
    Example: "  {month}: {count} {label}"
    """

    TemporalTimelinePeakSingle: Final[frozenset[str]] = frozenset(
        {
            'peak_month',  # str: Month with peak activity
            'peak_count',  # int: Count at peak
        }
    )
    """
    Single peak insight.
    Example: "  Peak change activity occurred in {peak_month} ({peak_count} entities)."
    """

    TemporalTimelinePeakMultiple: Final[frozenset[str]] = frozenset(
        {
            'peak_months',  # str: Multiple peak months (comma-separated)
        }
    )
    """
    Multiple peaks insight.
    Example: "  Multiple peaks detected: {peak_months}"
    """

    TemporalTimelinePatternsEarlyPct: Final[frozenset[str]] = frozenset(
        {
            'early_pct',  # str: Percentage of early changes
        }
    )
    """
    Temporal pattern insights.
    Example: "    • Early changes ({early_pct}% in first third): Possible long-term misuse"
    """

    TemporalTimelinePatternsLatePct: Final[frozenset[str]] = frozenset(
        {
            'late_pct',  # str: Percentage of late changes
        }
    )
    """
    Temporal pattern insights.
    Example: "    • Late changes ({late_pct}% in last third): Recent/emerging issues"
    """

    # =========================================================================
    # TEMPORAL ANALYSIS - FRAUD PATTERN SUMMARY
    # =========================================================================

    TemporalFraudPatternCount: Final[frozenset[str]] = frozenset(
        {
            'count',  # int: Number of entities with this pattern
        }
    )
    """
    Fraud pattern entity count.
    Example: "    Detected in: {count} entities"
    """

    TemporalFraudPatternOffHours: Final[frozenset[str]] = frozenset(
        {
            'off_hours_threshold_pct',  # str: Off-hours percentage threshold
        }
    )
    """
    Off-hours concentration pattern description.
    Example: "    Excessive non-business hour activity (>{policy.off_hours_threshold_pct}% of transactions)"
    """

    TemporalFraudPatternSpikeRetreat: Final[frozenset[str]] = frozenset(
        {
            'spike_threshold_pct',  # str: Spike percentage
            'retreat_drop_pct',  # str: Retreat drop percentage
        }
    )
    """
    Spike-and-retreat pattern description.
    Example: "    Rapid escalation...>(>{policy.spike_threshold_pct}% spike, then >{policy.retreat_drop_pct}% drop)"
    """

    TemporalFraudPatternGradualEscalation: Final[frozenset[str]] = frozenset(
        {
            'period_change_pct',  # str: Period comparison change percentage
        }
    )
    """
    Gradual escalation pattern description.
    Example: "    Sustained increase...(second half >{policy.period_change_pct}% higher than first)"
    """

    # =========================================================================
    # TEMPORAL ANALYSIS - COMPARATIVE ANALYSIS
    # =========================================================================

    TemporalComparativeIntro: Final[frozenset[str]] = frozenset(
        {
            'target_location',  # str: Branch name being analyzed
        }
    )
    """
    Comparative analysis introduction.
    Example: "Comparing temporal risk patterns: {target_location} vs Other Branches"
    """

    TemporalComparativeTargetStats: Final[frozenset[str]] = frozenset(
        {
            'target_mean',  # float: Mean risk score for target
            'target_median',  # float: Median risk score for target
        }
    )
    """
    Target location statistics.
    Example: "    Mean = {target_mean:.2f}, Median = {target_median:.2f}"
    """

    TemporalComparativeOthersStats: Final[frozenset[str]] = frozenset(
        {
            'others_mean',  # float: Mean risk score for others
            'others_median',  # float: Median risk score for others
        }
    )
    """
    Other branches statistics.
    Example: "    Mean = {others_mean:.2f}, Median = {others_median:.2f}"
    """

    TemporalComparativeTestLine: Final[frozenset[str]] = frozenset(
        {
            'p_value',  # float: P-value from test
        }
    )
    """
    Statistical test result line.
    Example: "  Statistical Test: Mann-Whitney U, p = {p_value:.4f}"
    """

    TemporalComparativeIQR: Final[frozenset[str]] = frozenset(
        {
            'p25',  # float/str: 25th percentile
            'p75',  # float/str: 75th percentile
        }
    )
    """
    Interquartile range display.
    Example: "  25th-75th percentile: {p25} - {p75}"
    """

    TemporalComparativeSampleSize: Final[frozenset[str]] = frozenset(
        {
            'n',  # int: Sample size
        }
    )
    """
    Sample size line.
    Example: "  Sample size: {n} entities"
    """

    TemporalComparativeEffectSize: Final[frozenset[str]] = frozenset(
        {
            'delta',  # float/str: Cliff's delta value
            'interpretation',  # str: Effect size interpretation
        }
    )
    """
    Effect size (Cliff's delta) line.
    Example: "  Effect Size (Cliff's Delta): δ = {delta} ({interpretation})"
    """

    TemporalComparativeEffectSizeNegligible: Final[frozenset[str]] = frozenset(
        {
            'cliffs_delta_negligible',  # float/str: Cliff's delta value
        }
    )
    """
    Effect size (Cliff's delta) line.
    Example: "Negligible (|δ| < {policy.cliffs_delta_negligible}) - Minimal practical difference between locations"
    """

    TemporalComparativeEffectSizeSmall: Final[frozenset[str]] = frozenset(
        {
            'cliffs_delta_small',  # float/str: Cliff's delta value
        }
    )
    """
    Effect size (Cliff's delta) line.
    Example: "Small (|δ| < {policy.cliffs_delta_small}) - Small practical difference between locations"
    """

    TemporalComparativeEffectSizeMedium: Final[frozenset[str]] = frozenset(
        {
            'cliffs_delta_medium',  # float/str: Cliff's delta value
        }
    )
    """
    Effect size (Cliff's delta) line.
    Example: "Medium (|δ| < {policy.cliffs_delta_medium}) - Medium practical difference between locations"
    """

    TemporalComparativeSignificant: Final[frozenset[str]] = frozenset(
        {
            'target_location',  # str: Branch name
            'p_significant',  # float: Significance threshold
        }
    )
    """
    Significant difference interpretation paragraphs.
    Example: "  ⚠ STATISTICALLY SIGNIFICANT DIFFERENCE (p < {policy.p_significant})"
    """

    TemporalComparativeProbability: Final[frozenset[str]] = frozenset(
        {
            'target_location',  # str: Branch name
            'probability',  # str: Probability value
            'comparison_entity',  # str: "target" or "other"
        }
    )
    """
    Effect size probability explanation.
    Example: "    ...there's a {probability} chance the {comparison_entity} entity has a higher risk score."
    """

    # =========================================================================
    # TEMPORAL ANALYSIS - INTERPRETATION GUIDE
    # =========================================================================

    TemporalInterpCriticalThreshold: Final[frozenset[str]] = frozenset(
        {
            'risk_critical',  # int: Critical threshold value
        }
    )
    """
    Interpretation guide - critical threshold reference.
    Example: "  ✓ Risk score ≥{policy.risk_critical} (Critical category)"
    """

    TemporalInterpHighRange: Final[frozenset[str]] = frozenset(
        {
            'risk_high',  # int: High threshold
            'risk_critical_minus_one',  # int: Critical - 1
        }
    )
    """
    Interpretation guide - high range reference.
    Example: "  • Risk score {policy.risk_high}-{policy.risk_critical_minus_one} (High category)"
    """

    TemporalInterpLowPriority: Final[frozenset[str]] = frozenset(
        {
            'risk_medium',  # int: Medium threshold
            'risk_high_minus_one',  # int: High - 1
            'min_months_temporal',  # int: Minimum months
            'min_transactions_risk',  # int: Minimum transactions
        }
    )
    """
    Interpretation guide - low priority reference.
    Example: "  • Risk score {policy.risk_medium}-{policy.risk_high_minus_one} (Medium category)"
    """

    # =========================================================================
    # REPORT FOOTER SECTION
    # =========================================================================

    FooterDataCoverageItems: Final[frozenset[str]] = frozenset(
        {
            'total_records',  # int: Total records in full dataset
            'analysis_records',  # int: Records in analysis period
            'target_location',  # str: Branch name
            'target_records',  # int: Records for target
            'target_pct',  # str: Percentage of total
            'other_records',  # int: Records for other branches
            'other_pct',  # str: Percentage of total
            'eld_match_rate',  # str: Overall ELD match rate
        }
    )
    """Footer data coverage - all items."""

    FooterStatisticalRigorItems: Final[frozenset[str]] = frozenset(
        {
            'total_tests',  # int: Total statistical tests performed
            'significant_count',  # int: Count of significant tests
            'significant_pct',  # str: Percentage significant
            'confidence_level',  # str: Statistical confidence level
            'alpha',  # float: FDR control level
        }
    )
    """Footer statistical rigor - all items."""

    FooterReportMetadata: Final[frozenset[str]] = frozenset(
        {
            'report_date',  # str: YYYY-MM-DD generation date
            'analysis_period',  # str: Human-readable period
            'target_location',  # str: Branch name
            'target_location_number',  # str/int: Numeric ID
            'system_name',  # str: System name (ARGUS)
            'version',  # str: System version
        }
    )
    """
    Footer report metadata section.
    Example: "• Report Generated: {report_date}
             • Target Location: {target_location} (ID: {target_location_number})"
    """

    FooterClosing: Final[frozenset[str]] = frozenset(
        {
            'system_name',  # str: System name (ARGUS)
            'system_full_name',  # str: Full system name
        }
    )
    """
    Footer closing line.
    Example: "Generated by {system_name}: {system_full_name}"
    """


# =============================================================================
# CONVENIENCE ALIAS
# =============================================================================
# Short alias for cleaner model definitions
P = Placeholders
