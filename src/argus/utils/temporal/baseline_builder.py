# argus/utils/temporal/baseline_builder.py
"""
Baseline distribution builder for entity behavioral comparison.

This module creates statistical baseline distributions from a population of
entities (drivers or vehicles). These baselines provide the context needed
to determine whether an individual entity's behavior is anomalous.

Typical Usage:
    from argus.utils.temporal.baseline_builder import build_entity_baselines

    baselines = build_entity_baselines(
        transaction_data=other_locations_df,
        minimum_months_per_entity=3,
    )

    # Access driver baseline for no_eld_rate
    driver_no_eld_stats = baselines.driver_name.no_eld_rate
    print(f"Fleet average: {driver_no_eld_stats.mean:.1f}%")
    print(f"95th percentile: {driver_no_eld_stats.q95:.1f}%")
"""

import logging

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from pandas._typing import Scalar
from pydantic import Field

from argus.models.common import FrozenModel
from argus.utils.temporal._constants import (
    BASELINE_DISTRIBUTION_METRICS,
    MINIMUM_MONTHS_FOR_BASELINE_INCLUSION,
)

__all__: list[str] = [
    'BaselineDistributions',
    'EntityTypeBaseline',
    'MetricDistributionStatistics',
    'build_entity_baselines',
]

# Set up module logger
logger: logging.Logger = logging.getLogger(__name__)


# =============================================================================
# PYDANTIC MODELS
# =============================================================================


class MetricDistributionStatistics(FrozenModel):
    """
    Statistical distribution summary for a single behavioral metric.

    This model captures the full distributional characteristics of a metric
    across all entity-month observations in the baseline population. These
    statistics enable z-score calculations and percentile rankings for
    individual entity comparisons.

    Attributes:
        mean: Arithmetic mean of the metric across all observations.
        std: Sample standard deviation (ddof=0 for population estimate).
        median: 50th percentile (robust central tendency measure).
        q25: 25th percentile (first quartile).
        q75: 75th percentile (third quartile).
        q90: 90th percentile (high but not extreme).
        q95: 95th percentile (typically used for outlier flagging).
        q99: 99th percentile (extreme values).
        min_value: Minimum observed value.
        max_value: Maximum observed value.
        observation_count: Number of entity-month observations in calculation.

    Example:
        >>> stats = MetricDistributionStatistics(
        ...     mean=15.2, std=8.4, median=12.5,
        ...     q25=9.1, q75=19.8, q90=26.3, q95=31.2, q99=42.7,
        ...     min_value=0.0, max_value=58.3, observation_count=1247
        ... )
        >>> z_score = (entity_value - stats.mean) / stats.std
    """

    mean: float = Field(description='Arithmetic mean of metric values')
    std: float = Field(ge=0.0, description='Standard deviation (population)')
    median: float = Field(description='50th percentile')
    q25: float = Field(description='25th percentile')
    q75: float = Field(description='75th percentile')
    q90: float = Field(description='90th percentile')
    q95: float = Field(description='95th percentile')
    q99: float = Field(description='99th percentile')
    min_value: float = Field(description='Minimum observed value')
    max_value: float = Field(description='Maximum observed value')
    observation_count: int = Field(
        ge=1, description='Number of entity-month observations'
    )

    def calculate_z_score(self, value: float) -> float:
        """
        Calculate z-score for a value against this baseline distribution.

        Args:
            value: The metric value to standardize.

        Returns:
            Z-score (number of standard deviations from mean).
            Returns 0.0 if std is zero to avoid division errors.
        """
        if self.std == 0:
            return 0.0
        return (value - self.mean) / self.std

    def calculate_percentile_rank(self, value: float) -> float:
        """
        Estimate percentile rank using linear interpolation between known quantiles.

        This provides a rough estimate without requiring the full distribution.
        For precise percentile calculations, store the raw values.

        Args:
            value: The metric value to rank.

        Returns:
            Estimated percentile (0-100 scale).
        """
        # Build interpolation points from known quantiles
        percentiles: list[float] = [0, 25, 50, 75, 90, 95, 99, 100]
        values: list[float] = [
            self.min_value,
            self.q25,
            self.median,
            self.q75,
            self.q90,
            self.q95,
            self.q99,
            self.max_value,
        ]

        # Handle edge cases
        if value <= self.min_value:
            return 0.0
        if value >= self.max_value:
            return 100.0

        # Linear interpolation between bracketing quantiles
        for index in range(len(values) - 1):
            if values[index] <= value <= values[index + 1]:
                # Avoid division by zero if quantiles are equal
                if values[index + 1] == values[index]:
                    return percentiles[index]

                fraction: float = (value - values[index]) / (
                    values[index + 1] - values[index]
                )
                return percentiles[index] + fraction * (
                    percentiles[index + 1] - percentiles[index]
                )

        return 50.0  # Fallback (shouldn't reach here)


class EntityTypeBaseline(FrozenModel):
    """
    Baseline distributions for all metrics of a single entity type.

    This model aggregates distribution statistics for each behavioral metric
    tracked for an entity type (driver or vehicle). Fields are optional because
    not all metrics may have sufficient data in every baseline calculation.

    Attributes:
        datetime_count: Distribution of unique transactions per entity-month.
        no_eld_rate: Distribution of percentage without ELD activity match.
        non_diesel_rate: Distribution of percentage non-diesel transactions.
        after_hours_rate: Distribution of percentage outside business hours.
        cost_mean: Distribution of mean transaction amounts per entity-month.
        cost_median: Distribution of median transaction amounts per entity-month.
        cost_sum: Distribution of total transaction amounts per entity-month.

    Example:
        >>> if baseline.no_eld_rate is not None:
        ...     z = baseline.no_eld_rate.calculate_z_score(entity_no_eld_rate)
        ...     if z > 2.0:
        ...         print("Entity no-ELD rate is significantly elevated")
    """

    datetime_count: MetricDistributionStatistics | None = Field(
        default=None,
        description='Distribution of unique transaction counts per entity-month',
    )
    no_eld_rate: MetricDistributionStatistics | None = Field(
        default=None,
        description='Distribution of no-ELD-activity rates (percentage)',
    )
    non_diesel_rate: MetricDistributionStatistics | None = Field(
        default=None,
        description='Distribution of non-diesel transaction rates (percentage)',
    )
    after_hours_rate: MetricDistributionStatistics | None = Field(
        default=None,
        description='Distribution of after-hours transaction rates (percentage)',
    )
    cost_mean: MetricDistributionStatistics | None = Field(
        default=None,
        description='Distribution of mean transaction amounts per entity-month',
    )
    cost_median: MetricDistributionStatistics | None = Field(
        default=None,
        description='Distribution of median transaction amounts per entity-month',
    )
    cost_sum: MetricDistributionStatistics | None = Field(
        default=None,
        description='Distribution of total transaction amounts per entity-month',
    )

    def get_metric_statistics(
        self, metric_name: str
    ) -> MetricDistributionStatistics | None:
        """
        Retrieve statistics for a metric by name.

        Args:
            metric_name: Name of the metric (must match a field name).

        Returns:
            MetricDistributionStatistics if available, None otherwise.

        Raises:
            AttributeError: If metric_name is not a valid field.
        """
        return getattr(self, metric_name, None)

    def available_metrics(self) -> list[str]:
        """
        List metrics that have baseline statistics available.

        Returns:
            List of metric field names that are not None.
        """
        return [
            field_name
            for field_name in self.get_field_definitions()
            if getattr(self, field_name) is not None
        ]


class BaselineDistributions(FrozenModel):
    """
    Complete baseline distributions for all entity types.

    This is the top-level model returned by build_entity_baselines(). It contains
    separate baseline distributions for drivers and vehicles, enabling entity-type
    specific behavioral comparisons.

    Attributes:
        driver_name: Baseline distributions for driver entities.
            None if insufficient driver data was available.
        vehicle_index: Baseline distributions for vehicle entities.
            None if insufficient vehicle data was available.

    Example:
        >>> baselines = build_entity_baselines(transaction_data)
        >>>
        >>> # Check if driver baseline is available
        >>> if baselines.driver_name is not None:
        ...     no_eld_stats = baselines.driver_name.no_eld_rate
        ...     if no_eld_stats is not None:
        ...         print(f"Driver fleet no-ELD rate: {no_eld_stats.mean:.1f}%")
        ...         print(f"Standard deviation: {no_eld_stats.std:.1f}%")
        >>>
        >>> # Get z-score for a specific driver
        >>> driver_no_eld = 45.2  # This driver's no-ELD rate
        >>> z_score = baselines.driver_name.no_eld_rate.calculate_z_score(driver_no_eld)
        >>> print(f"Driver z-score: {z_score:.2f}")
    """

    driver_name: EntityTypeBaseline | None = Field(
        default=None,
        description='Baseline distributions for driver entities',
    )
    vehicle_index: EntityTypeBaseline | None = Field(
        default=None,
        description='Baseline distributions for vehicle entities',
    )

    def get_entity_baseline(self, entity_type: str) -> EntityTypeBaseline | None:
        """
        Retrieve baseline for an entity type by name.

        Args:
            entity_type: Either 'driver_name' or 'vehicle_index'.

        Returns:
            EntityTypeBaseline if available, None otherwise.

        Raises:
            ValueError: If entity_type is not recognized.
        """
        if entity_type == 'driver_name':
            return self.driver_name
        elif entity_type == 'vehicle_index':
            return self.vehicle_index
        else:
            raise ValueError(
                f"Unknown entity type '{entity_type}'. "
                "Must be 'driver_name' or 'vehicle_index'."
            )

    def has_any_baselines(self) -> bool:
        """Check if at least one entity type has baseline data."""
        return self.driver_name is not None or self.vehicle_index is not None


# =============================================================================
# REQUIRED COLUMNS
# =============================================================================

REQUIRED_TRANSACTION_COLUMNS: tuple[str, ...] = (
    'month',
    'driver_name',
    'vehicle_index',
    'has_eld_activity',
    'is_diesel_def',
    'is_business_hours',
    'transaction_amount',
    'datetime_parsed',
)


# =============================================================================
# BASELINE BUILDER FUNCTION
# =============================================================================


def build_entity_baselines(
    transaction_data: pd.DataFrame,
    minimum_months_per_entity: int = MINIMUM_MONTHS_FOR_BASELINE_INCLUSION,
    metrics_to_baseline: tuple[str, ...] = BASELINE_DISTRIBUTION_METRICS,
) -> BaselineDistributions:
    """
    Create separate baseline distributions for drivers and vehicles.

    This function processes raw transaction data to create statistical baselines
    that characterize "normal" behavior for each entity type. These baselines
    include mean, standard deviation, and percentiles for key metrics.

    The process:
        1. Group transactions by entity (driver or vehicle)
        2. Aggregate metrics by month for each entity
        3. Combine monthly observations across all entities
        4. Calculate distribution statistics for each metric

    Args:
        transaction_data:
            DataFrame containing individual transactions with columns:
            - month: Period representing transaction month
            - driver_name: Driver identifier
            - vehicle_index: Vehicle identifier
            - has_eld_activity: Boolean, True if ELD matched
            - is_diesel_def: Boolean, True if diesel/DEF transaction
            - is_business_hours: Boolean, True if during business hours
            - transaction_amount: Transaction dollar amount
            - datetime_parsed: Transaction datetime

        minimum_months_per_entity:
            Minimum months of data required for an entity to be included
            in the baseline. Entities with fewer months are excluded to
            avoid skewing distributions with limited samples.

        metrics_to_baseline:
            Tuple of metric names to calculate distributions for.

    Returns:
        BaselineDistributions model with driver_name and vehicle_index
        EntityTypeBaseline objects. Either may be None if insufficient data.

    Raises:
        ValueError: If required columns are missing from transaction_data.

    Example:
        >>> baselines = build_entity_baselines(other_locations_df)
        >>> driver_baseline = baselines.driver_name
        >>> if driver_baseline and driver_baseline.no_eld_rate:
        ...     stats = driver_baseline.no_eld_rate
        ...     print(f"Fleet average no-ELD rate: {stats.mean:.1f}%")
        ...     print(f"95th percentile: {stats.q95:.1f}%")
    """
    # Validate required columns
    _validate_required_columns(transaction_data)

    # Process each entity type separately
    entity_monthly_observations: dict[str, list[dict[str, Scalar]]] = {
        'driver_name': [],
        'vehicle_index': [],
    }

    for entity_type in ['driver_name', 'vehicle_index']:
        logger.debug('Building baseline for %s entities...', entity_type)

        monthly_records: list[dict[str, Scalar]] = _collect_entity_monthly_records(
            transaction_data=transaction_data,
            entity_column=entity_type,
            minimum_months=minimum_months_per_entity,
        )

        entity_monthly_observations[entity_type] = monthly_records
        logger.debug(
            'Collected %d entity-month observations for %s',
            len(monthly_records),
            entity_type,
        )

    # Calculate distribution statistics and build models
    driver_baseline: EntityTypeBaseline | None = None
    vehicle_baseline: EntityTypeBaseline | None = None

    for entity_type in ['driver_name', 'vehicle_index']:
        observations_df = pd.DataFrame(entity_monthly_observations[entity_type])

        if observations_df.empty:
            logger.warning('No valid %s data for baseline - skipping', entity_type)
            continue

        entity_baseline: EntityTypeBaseline = _build_entity_type_baseline(
            observations_df=observations_df,
            metrics=metrics_to_baseline,
        )

        if entity_type == 'driver_name':
            driver_baseline = entity_baseline
        else:
            vehicle_baseline = entity_baseline

        available_metric_count: int = len(entity_baseline.available_metrics())
        logger.info(
            'Built %s baseline from %d entity-months across %d metrics',
            entity_type,
            len(observations_df),
            available_metric_count,
        )

    return BaselineDistributions(
        driver_name=driver_baseline,
        vehicle_index=vehicle_baseline,
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _validate_required_columns(data: pd.DataFrame) -> None:
    """
    Validate that all required columns are present.

    Args:
        data: DataFrame to validate.

    Raises:
        ValueError: If any required columns are missing.
    """
    missing_columns: list[str] = [
        col for col in REQUIRED_TRANSACTION_COLUMNS if col not in data.columns
    ]

    if missing_columns:
        raise ValueError(
            f'Missing required columns for baseline building: {missing_columns}'
        )


def _collect_entity_monthly_records(
    transaction_data: pd.DataFrame,
    entity_column: str,
    minimum_months: int,
) -> list[dict[str, Scalar]]:
    """
    Aggregate transactions by entity and month, filtering by data sufficiency.

    Args:
        transaction_data: Raw transaction DataFrame.
        entity_column: Column name for entity identifier ('driver_name' or 'vehicle_index').
        minimum_months: Minimum unique months required to include entity.

    Returns:
        List of dictionaries, each representing one entity-month observation
        with aggregated metrics.
    """
    monthly_records: list[dict[str, Scalar]] = []

    # Get unique entities, excluding null and 'Unknown'
    unique_entities_array: NDArray[np.str_ | np.int64] = (
        transaction_data[entity_column].dropna().unique()
    )
    unique_entities: list[str | int] = [
        entity for entity in unique_entities_array if entity and entity != 'Unknown'
    ]

    logger.debug(
        'Processing %d unique %s entities', len(unique_entities), entity_column
    )

    for entity_id in unique_entities:
        # Filter to this entity's transactions
        entity_transactions: pd.DataFrame = transaction_data[
            transaction_data[entity_column] == entity_id
        ].copy()

        # Check data sufficiency
        unique_months: int = entity_transactions['month'].nunique()
        total_transactions: int = len(entity_transactions)

        if total_transactions < minimum_months or unique_months < minimum_months:
            continue

        # Aggregate by month
        for month, month_group in entity_transactions.groupby('month'):
            monthly_record: dict[str, Scalar] = _calculate_monthly_metrics(
                entity_id=entity_id,
                month=month,
                transactions=month_group,
            )
            monthly_records.append(monthly_record)

    return monthly_records


def _calculate_monthly_metrics(
    entity_id: str | int,
    month: Scalar,
    transactions: pd.DataFrame,
) -> dict[str, Scalar]:
    """
    Calculate aggregated metrics for one entity-month.

    Args:
        entity_id: Identifier for the entity.
        month: Month period.
        transactions: DataFrame of transactions for this entity-month.

    Returns:
        Dictionary with entity_id, month, and calculated metrics.
    """
    # Count unique transactions (avoid duplicate counting)
    unique_transaction_count: int = (
        transactions['datetime_parsed'].nunique()
        if 'datetime_parsed' in transactions.columns
        else len(transactions)
    )

    return {
        'entity_id': entity_id,
        'month': month,
        'datetime_count': unique_transaction_count,
        'no_eld_rate': 100 * (~transactions['has_eld_activity']).mean(),
        'non_diesel_rate': 100 * (~transactions['is_diesel_def']).mean(),
        'after_hours_rate': 100 * (~transactions['is_business_hours']).mean(),
        'cost_mean': transactions['transaction_amount'].mean(),
        'cost_median': transactions['transaction_amount'].median(),
        'cost_sum': transactions['transaction_amount'].sum(),
    }


def _build_entity_type_baseline(
    observations_df: pd.DataFrame,
    metrics: tuple[str, ...],
) -> EntityTypeBaseline:
    """
    Build an EntityTypeBaseline model from observation data.

    Args:
        observations_df: DataFrame with one row per entity-month.
        metrics: Tuple of metric column names to process.

    Returns:
        EntityTypeBaseline with MetricDistributionStatistics for available metrics.
    """
    metric_statistics: dict[str, MetricDistributionStatistics | None] = {}

    for metric_name in metrics:
        if metric_name not in observations_df.columns:
            logger.debug('Metric %s not in observations - skipping', metric_name)
            metric_statistics[metric_name] = None
            continue

        metric_values: pd.Series[float | int] = observations_df[metric_name].dropna()

        if len(metric_values) == 0:
            logger.debug('No valid values for metric %s - skipping', metric_name)
            metric_statistics[metric_name] = None
            continue

        metric_statistics[metric_name] = MetricDistributionStatistics(
            mean=float(np.mean(metric_values)),
            std=float(np.std(metric_values)),
            median=float(np.median(metric_values)),
            q25=float(np.percentile(metric_values, 25)),
            q75=float(np.percentile(metric_values, 75)),
            q90=float(np.percentile(metric_values, 90)),
            q95=float(np.percentile(metric_values, 95)),
            q99=float(np.percentile(metric_values, 99)),
            min_value=float(np.min(metric_values)),
            max_value=float(np.max(metric_values)),
            observation_count=len(metric_values),
        )

    # Build the EntityTypeBaseline, only including metrics that exist as fields
    # Filter to only the fields that EntityTypeBaseline actually has
    valid_field_names: set[str] = set(EntityTypeBaseline.get_field_definitions().keys())
    filtered_statistics: dict[str, MetricDistributionStatistics | None] = {
        metric_name: stats
        for metric_name, stats in metric_statistics.items()
        if metric_name in valid_field_names
    }

    return EntityTypeBaseline(**filtered_statistics)
