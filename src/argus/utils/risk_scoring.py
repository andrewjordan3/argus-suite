# argus/utils/risk_scoring.py

import logging
from typing import Any

import numpy as np
import pandas as pd

from argus.config import AnomalyThresholds, RiskWeightsConfig
from argus.models.context.context_model import AnalysisContext
from argus.utils.stat_tools import wilson_ci
from argus.utils.tail_test import decide_log1p

logger: logging.Logger = logging.getLogger(__name__)


class RiskProfileCalculator:
    """
    Calculates comprehensive fraud risk profiles for entities using statistically rigorous methods.

    This calculator implements a multi-dimensional risk scoring system that combines:
    - Wilson confidence intervals for binomial rates (ELD compliance, fuel type, timing)
    - Percentile-based ranking for distribution-free risk quantification
    - Statistical significance testing for high-confidence fraud flags
    - Weighted composite scoring to prioritize different fraud indicators

    The approach is superior to Z-score methods because it:
    - Makes no assumptions about data normality
    - Provides interpretable percentile-based scores (0-100 scale)
    - Includes statistical confidence bounds via Wilson intervals
    - Handles small sample sizes appropriately

    Typical use case: Identify drivers or vehicles with suspicious transaction patterns
    across multiple risk dimensions (ELD compliance, fuel type, timing, cost).

    Attributes:
        context: Analysis context containing transactions, configuration, and thresholds
        entity_statistics: DataFrame containing aggregated entity-level risk metrics
        composite_score_weights: Weights for each risk dimension in final composite score
        rate_risk_thresholds: Maximum acceptable rates before flagging elevated risk
        minimum_transaction_count: Minimum transactions required for inclusion in analysis
        cost_column_for_ranking: Column name to use for cost percentile calculation
        log_transform_applied: Whether log transformation was applied to cost data
    """

    def __init__(self, context: AnalysisContext) -> None:
        """
        Initialize the risk profile calculator with analysis context and configuration.

        Args:
            context: Analysis context containing transaction data and configuration
        """
        self.context: AnalysisContext = context
        self.entity_statistics: pd.DataFrame = pd.DataFrame()

        # Extract configuration for convenience and performance
        weight_config: RiskWeightsConfig = context.config.risk_weights
        self.composite_score_weights: dict[str, float] = {
            'no_eld': weight_config.no_eld_match,
            'non_diesel': weight_config.non_diesel,
            'after_hours': weight_config.after_hours,
            'cost': weight_config.high_cost,
        }

        rate_config: AnomalyThresholds = context.config.anomaly_thresholds
        self.rate_risk_thresholds: dict[str, float] = {
            'no_eld': rate_config.high_no_eld_rate,
            'non_diesel': rate_config.high_non_diesel_rate,
            'after_hours': rate_config.high_after_hours_rate,
        }

        self.minimum_transaction_count: int = (
            context.config.statistics.min_transactions_risk
        )

        # State tracking for cost transformation decision
        self.cost_column_for_ranking: str = 'avg_cost_per_transaction'
        self.log_transform_applied: bool = False

    def calculate_risk_profiles(
        self,
        entity_column: str,
        aggregation_specification: dict[str, Any],
    ) -> pd.DataFrame:
        """
        Calculate comprehensive risk profiles for all entities in the target period.

        This is the main entry point that orchestrates the entire risk calculation pipeline.
        The process includes: aggregation, filtering, rate calculation, confidence intervals,
        percentile ranking, composite scoring, and statistical significance flagging.

        Args:
            entity_column: Column name to group by (e.g., 'Driver' or 'VIN')
            aggregation_specification: Dictionary defining aggregation operations.
                Example: {
                    'total_transactions': ('transaction_id', 'count'),
                    'no_eld_count': ('has_eld', lambda x: (~x).sum()),
                    'total_cost': ('cost', 'sum')
                }

        Returns:
            DataFrame with one row per entity containing:
            - Aggregated transaction statistics (counts, rates, costs)
            - Wilson confidence intervals for each binomial rate
            - Percentile ranks (0-100) for each risk dimension
            - Statistical significance flags for elevated rates
            - Composite risk score (0-100, weighted average of percentiles)
            Sorted by composite risk score descending (highest risk first)

        Raises:
            ValueError: If transaction data is empty or entity_column doesn't exist
        """
        logger.info(
            'Starting risk profile calculation for entity column: %r', entity_column
        )

        self._validate_transaction_data(entity_column)
        self._aggregate_transactions_by_entity(entity_column, aggregation_specification)
        self._filter_entities_by_minimum_transactions()

        if self.entity_statistics.empty:
            logger.warning(
                'No entities meet minimum transaction threshold (%d). '
                'Returning empty risk profile.',
                self.minimum_transaction_count,
            )
            return pd.DataFrame()

        self._calculate_base_risk_rates()
        self._calculate_wilson_confidence_intervals()
        self._apply_cost_transformation_if_warranted()
        self._calculate_percentile_rankings()
        self._calculate_composite_risk_score()
        self._flag_statistically_elevated_risks()

        return self._finalize_and_sort_results()

    def _validate_transaction_data(self, entity_column: str) -> None:
        """
        Validate that transaction data exists and contains the required entity column.

        Args:
            entity_column: Column name that should exist in transaction data

        Raises:
            ValueError: If transaction data is empty or entity_column is missing
        """
        transaction_data: pd.DataFrame = self.context.target_period_transactions

        if transaction_data.empty:
            logger.error('Transaction data is empty. Cannot calculate risk profiles.')
            raise ValueError(
                'Transaction data cannot be empty for risk profile calculation'
            )

        if entity_column not in transaction_data.columns:
            available_columns: list[str] = transaction_data.columns.tolist()
            logger.error(
                'Entity column %r not found in transaction data. Available columns: %r',
                entity_column,
                available_columns,
            )
            raise ValueError(
                f'Entity column "{entity_column}" does not exist in transaction data. '
                f'Available columns: {available_columns}'
            )

        logger.debug(
            'Validated transaction data: %d rows, entity column %r exists',
            len(transaction_data),
            entity_column,
        )

    def _aggregate_transactions_by_entity(
        self,
        entity_column: str,
        aggregation_specification: dict[str, Any],
    ) -> None:
        """
        Group transactions by entity and calculate summary statistics.

        This produces one row per entity (e.g., driver or vehicle) with aggregated metrics
        like total transaction count, fraud indicator counts, and cost totals.

        Args:
            entity_column: Column name to group by
            aggregation_specification: Dictionary defining aggregation operations
        """
        transaction_data: pd.DataFrame = self.context.target_period_transactions

        self.entity_statistics = (
            transaction_data.groupby(entity_column)
            .agg(**aggregation_specification)
            .reset_index()
        )

        entity_count: int = len(self.entity_statistics)
        logger.info('Aggregated transactions for %d unique entities', entity_count)

    def _filter_entities_by_minimum_transactions(self) -> None:
        """
        Remove entities with insufficient transaction history for reliable analysis.

        Entities with too few transactions produce unreliable statistical estimates.
        The minimum threshold ensures adequate sample size for meaningful risk assessment.
        """
        entities_before_filter: int = len(self.entity_statistics)

        self.entity_statistics = self.entity_statistics[
            self.entity_statistics['total_transactions']
            >= self.minimum_transaction_count
        ].copy()

        entities_after_filter: int = len(self.entity_statistics)
        entities_excluded: int = entities_before_filter - entities_after_filter

        if entities_excluded > 0:
            exclusion_percentage: float = (
                entities_excluded / entities_before_filter * 100
                if entities_before_filter > 0
                else 0.0
            )
            logger.info(
                'Filtered out %d entities (%.1f%%) with fewer than %d transactions. '
                '%d entities remain for analysis.',
                entities_excluded,
                exclusion_percentage,
                self.minimum_transaction_count,
                entities_after_filter,
            )

    def _calculate_base_risk_rates(self) -> None:
        """
        Calculate point estimates for all fraud risk rates.

        Computes the proportion of transactions exhibiting each risk behavior:
        - no_eld_rate: Missing Electronic Logging Device data (may indicate tampering)
        - non_diesel_rate: Using non-diesel fuel in diesel-only fleet (potential personal use)
        - after_hours_rate: Fueling outside business hours (possible unauthorized use)
        - avg_cost_per_transaction: Average transaction cost (detects price manipulation)

        These are point estimates that will later be supplemented with confidence intervals.
        """
        stats: pd.DataFrame = self.entity_statistics

        stats['no_eld_rate'] = stats['no_eld_count'] / stats['total_transactions']

        stats['non_diesel_rate'] = (
            stats['non_diesel_count'] / stats['total_transactions']
        )

        stats['after_hours_rate'] = (
            stats['after_hours_count'] / stats['total_transactions']
        )

        stats['avg_cost_per_transaction'] = (
            stats['total_cost'] / stats['total_transactions']
        )

        logger.debug('Calculated base risk rates for all entities')

    def _calculate_wilson_confidence_intervals(self) -> None:
        """
        Calculate Wilson confidence intervals for all binomial rates.

        Wilson intervals provide statistically rigorous bounds on true underlying rates,
        accounting for sampling uncertainty. This is especially important for entities
        with fewer transactions where point estimates are less reliable.

        The Wilson method is superior to normal approximation (Wald) for:
        - Small sample sizes (n < 30)
        - Extreme proportions (rates near 0 or 1)
        - Any situation requiring statistical rigor

        For each rate, we calculate both lower and upper bounds at 95% confidence level.
        """
        logger.debug('Calculating Wilson confidence intervals for binomial risk rates')

        self._add_wilson_interval(
            success_count_column='no_eld_count',
            rate_name='no_eld',
        )

        self._add_wilson_interval(
            success_count_column='non_diesel_count',
            rate_name='non_diesel',
        )

        self._add_wilson_interval(
            success_count_column='after_hours_count',
            rate_name='after_hours',
        )

        logger.debug('Wilson confidence intervals calculated for all risk rates')

    def _add_wilson_interval(
        self,
        success_count_column: str,
        rate_name: str,
    ) -> None:
        """
        Add Wilson confidence interval columns for a specific rate.

        Args:
            success_count_column: Column containing count of "successes" (e.g., 'no_eld_count')
            rate_name: Base name for the interval columns (e.g., 'no_eld')
        """
        lower_bound_column: str = f'{rate_name}_ci_lower'
        upper_bound_column: str = f'{rate_name}_ci_upper'

        lower_bounds: list[float] = []
        upper_bounds: list[float] = []

        for _, row_data in self.entity_statistics.iterrows():
            success_count: int = int(row_data[success_count_column])
            total_count: int = int(row_data['total_transactions'])

            ci_lower: float
            ci_upper: float
            ci_lower, ci_upper = wilson_ci(
                successes=success_count,
                total_observations=total_count,
                alpha=self.context.config.statistics.get_alpha(),
            )

            lower_bounds.append(ci_lower)
            upper_bounds.append(ci_upper)

        self.entity_statistics[lower_bound_column] = lower_bounds
        self.entity_statistics[upper_bound_column] = upper_bounds

    def _apply_cost_transformation_if_warranted(self) -> None:
        """
        Apply log1p transformation to cost data if it exhibits heavy right-tail characteristics.

        Financial metrics like transaction costs are often heavily right-skewed with outliers.
        Log transformation stabilizes variance and makes percentile-based comparisons more
        meaningful by reducing the influence of extreme outliers.

        Uses statistical heuristics (skewness, kurtosis, dispersion) to decide whether
        transformation is beneficial. If not warranted, uses original cost values.
        """
        cost_series: pd.Series = self.entity_statistics['avg_cost_per_transaction']

        should_transform: bool
        diagnostics: dict[str, Any]
        should_transform, diagnostics = decide_log1p(raw_input_series=cost_series)

        if should_transform:
            self.entity_statistics['avg_cost_transformed'] = np.log1p(cost_series)
            self.cost_column_for_ranking = 'avg_cost_transformed'
            self.log_transform_applied = True

            logger.info(
                'Applied log1p transformation to cost data. '
                'Dispersion reduced by %.1f%%. Rules triggered: %r',
                diagnostics['dispersion_reduction_pct'],
                diagnostics['rules_triggered'],
            )
        else:
            self.entity_statistics['avg_cost_transformed'] = cost_series
            self.cost_column_for_ranking = 'avg_cost_per_transaction'
            self.log_transform_applied = False

            logger.debug(
                'Skipped log1p transformation for cost data. '
                'Data does not exhibit sufficient right-skew or heavy tails.'
            )

    def _calculate_percentile_rankings(self) -> None:
        """
        Calculate percentile ranks (0-100 scale) for each risk dimension.

        Percentile ranks are distribution-free and highly interpretable:
        - 50th percentile = median (typical entity)
        - 90th percentile = riskier than 90% of entities
        - 99th percentile = extreme outlier

        Unlike Z-scores, percentiles make no assumptions about normality and are naturally
        bounded to [0, 100], making them ideal for composite risk scoring.

        Cost uses a two-tailed deviation score where both unusually high AND unusually
        low costs increase risk (may indicate fraud or data quality issues).
        """
        logger.debug('Calculating percentile rankings for all risk dimensions')

        self._add_percentile_rank('no_eld_rate', 'no_eld_percentile')
        self._add_percentile_rank('non_diesel_rate', 'non_diesel_percentile')
        self._add_percentile_rank('after_hours_rate', 'after_hours_percentile')
        self._add_percentile_rank(self.cost_column_for_ranking, 'cost_percentile')

        # Cost deviation: both high and low costs are risky (two-tailed)
        # Formula: abs(percentile - 50) * 2
        # - 50th percentile (median) → 0 risk (typical cost)
        # - 0th or 100th percentile → 100 risk (extreme outlier)
        # - 25th or 75th percentile → 50 risk (moderate deviation)
        self.entity_statistics['cost_deviation_score'] = (
            self.entity_statistics['cost_percentile'] - 50
        ).abs() * 2

        logger.debug('Percentile rankings calculated for all risk dimensions')

    def _add_percentile_rank(
        self,
        source_column: str,
        percentile_column: str,
    ) -> None:
        """
        Add percentile rank column for a specific metric.

        Args:
            source_column: Column to calculate percentiles for
            percentile_column: Name for new column containing percentile ranks
        """
        self.entity_statistics[percentile_column] = (
            self.entity_statistics[source_column].rank(pct=True, method='average') * 100
        )

    def _calculate_composite_risk_score(self) -> None:
        """
        Calculate weighted composite risk score combining all risk dimensions.

        The composite score is a weighted average of percentile ranks across all fraud
        indicators. This allows business priorities to be encoded (e.g., missing ELD data
        might be weighted more heavily than after-hours fueling).

        The result remains on a 0-100 scale where:
        - 0 = lowest risk across all dimensions
        - 100 = highest risk across all dimensions
        - 50 = median risk entity
        """
        weights: dict[str, float] = self.composite_score_weights

        self.entity_statistics['composite_risk_score'] = (
            self.entity_statistics['no_eld_percentile'] * weights['no_eld']
            + self.entity_statistics['non_diesel_percentile'] * weights['non_diesel']
            + self.entity_statistics['after_hours_percentile'] * weights['after_hours']
            + self.entity_statistics['cost_deviation_score'] * weights['cost']
        )

        min_score: float = self.entity_statistics['composite_risk_score'].min()
        max_score: float = self.entity_statistics['composite_risk_score'].max()

        logger.info(
            'Composite risk scores calculated using weights: %r. '
            'Score range: [%.2f, %.2f]',
            weights,
            min_score,
            max_score,
        )

    def _flag_statistically_elevated_risks(self) -> None:
        """
        Flag entities with statistically significant elevated risk rates.

        Uses Wilson confidence interval lower bounds to identify entities where we can be
        95% confident their true underlying rate exceeds the business-defined risk threshold.

        This approach is more rigorous than comparing point estimates because it accounts
        for sampling uncertainty. It reduces false positives and provides statistical backing
        for fraud investigation prioritization.
        """
        logger.debug('Flagging statistically significant elevated risk rates')

        self._add_risk_flag(
            rate_name='No-ELD',
            ci_lower_column='no_eld_ci_lower',
            threshold=self.rate_risk_thresholds['no_eld'],
            flag_column='no_eld_risk_flag',
        )

        self._add_risk_flag(
            rate_name='Non-diesel',
            ci_lower_column='non_diesel_ci_lower',
            threshold=self.rate_risk_thresholds['non_diesel'],
            flag_column='non_diesel_risk_flag',
        )

        self._add_risk_flag(
            rate_name='After-hours',
            ci_lower_column='after_hours_ci_lower',
            threshold=self.rate_risk_thresholds['after_hours'],
            flag_column='after_hours_risk_flag',
        )

        logger.debug('Statistical significance flagging complete')

    def _add_risk_flag(
        self,
        rate_name: str,
        ci_lower_column: str,
        threshold: float,
        flag_column: str,
    ) -> None:
        """
        Add boolean flag column indicating statistically significant elevated risk.

        Args:
            rate_name: Human-readable name of the rate being evaluated (for logging)
            ci_lower_column: Column containing Wilson CI lower bounds
            threshold: Minimum rate to be considered elevated risk
            flag_column: Name for new boolean flag column
        """
        self.entity_statistics[flag_column] = (
            self.entity_statistics[ci_lower_column] > threshold
        )

        flagged_count: int = self.entity_statistics[flag_column].sum()
        total_count: int = len(self.entity_statistics)
        flagged_percentage: float = (
            (flagged_count / total_count * 100) if total_count > 0 else 0.0
        )

        logger.info(
            '%s rate: %d of %d entities (%.1f%%) flagged with statistically '
            'significant rates above threshold %.1f%%',
            rate_name,
            flagged_count,
            total_count,
            flagged_percentage,
            threshold * 100,  # Convert to percentage for logging
        )

    def _finalize_and_sort_results(self) -> pd.DataFrame:
        """
        Sort results by composite risk score and return final DataFrame.

        Returns:
            Complete risk profile DataFrame sorted by risk score descending
        """
        self.entity_statistics = self.entity_statistics.sort_values(
            'composite_risk_score', ascending=False
        )

        if not self.entity_statistics.empty:
            highest_risk_entity: Any = self.entity_statistics.iloc[0][
                self.entity_statistics.columns[0]  # Entity column (first column)
            ]
            highest_risk_score: float = self.entity_statistics.iloc[0][
                'composite_risk_score'
            ]

            logger.info(
                'Risk profile calculation complete. %d entities analyzed. '
                'Highest risk entity: %s (score: %.2f)',
                len(self.entity_statistics),
                highest_risk_entity,
                highest_risk_score,
            )

        return self.entity_statistics
