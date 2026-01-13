# argus/preprocessor/feature_engineering.py
"""
Feature engineering for temporal, transaction, and vehicle attributes.

This module creates derived features that enrich raw transaction data with
calculated metrics, categorical encodings, and statistical indicators. These
features enable sophisticated fraud detection, pattern analysis, and anomaly
identification that would not be possible with raw vendor data alone.

Classes:
    TemporalFeatureEngineer: Creates time-based derived features
    TransactionFeatureEngineer: Creates transaction-level derived features
    VehicleFeatureEngineer: Creates vehicle telemetry-based derived features

Temporal Features:
    - Date components: year, month, week_number, day_of_month, weekday
    - Time components: hour, minute
    - Normalized timestamps: date_only (midnight), datetime_parsed (backward compat)
    - Business context: is_business_hours, is_weekend, is_rush_hour
    - Time categories: time_of_day_category (Early Morning/Morning/Afternoon/Evening)
    - Rush hour flags: is_morning_rush, is_evening_rush

Transaction Features:
    - Product standardization: product_clean (lowercase/trimmed)
    - Product categorization: is_diesel_def flag
    - Cost metrics: cost_per_gallon
    - Size categorization: transaction_size_category (Small/Medium/Large)
    - Frequency metrics: fillups_per_day
    - Location grouping: branch_group (target vs peers)

Vehicle Features:
    - Fuel efficiency: mpg (miles per gallon)
    - Usage patterns: idle_percentage, driving_percentage
    - Derived from: distance_miles, fuel_volume_gallons, engine_runtime_minutes

Feature Engineering Principles:
    1. Domain Knowledge: Features encode fleet management and fraud detection expertise
    2. Interpretability: All features have clear business meaning
    3. Robustness: Handle edge cases (division by zero, missing data) gracefully
    4. Composability: Features build on each other (e.g., rush hour requires hour)

Fraud Detection Applications:
    - After-hours transactions may indicate unauthorized personal use
    - Multiple fillups per day can signal fuel card sharing
    - Unusual cost per gallon suggests price manipulation
    - Abnormal MPG indicates potential odometer tampering or fuel theft
    - High idle percentages combined with low mileage suggest waste

Typical Usage:
    # Apply temporal features
    temporal_engineer = TemporalFeatureEngineer(config)
    enriched_df = temporal_engineer.engineer_features(cleaned_df)

    # Apply transaction features
    transaction_engineer = TransactionFeatureEngineer(config)
    enriched_df = transaction_engineer.engineer_features(enriched_df)

    # Apply vehicle features
    vehicle_engineer = VehicleFeatureEngineer()
    enriched_df = vehicle_engineer.engineer_features(enriched_df)

All engineers are designed to be idempotent - running them multiple times
produces the same result. They also handle missing data gracefully by
computing features only where sufficient input data exists.
"""
import logging

import numpy as np
import pandas as pd

from argus.config import FuelCardForensicsConfig

# pyright: reportAttributeAccessIssue=false

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)

class TemporalFeatureEngineer:
    """
    Creates time-based derived features.

    Generates features related to:
    - Date components (year, month, week, day)
    - Time components (hour, minute)
    - Business hours vs after-hours
    - Weekday vs weekend
    - Rush hour periods
    - Time of day categories
    """

    def __init__(self, config: FuelCardForensicsConfig) -> None:
        """
        Initialize temporal feature engineer with configuration.

        Args:
            config: Configuration containing business hours and temporal rules
        """
        self.config: FuelCardForensicsConfig = config

    def engineer_features(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Generate all temporal features.

        Args:
            dataframe: DataFrame with parsed transaction_timestamp column

        Returns:
            DataFrame with additional temporal feature columns
        """
        logger.debug('Engineering temporal features')

        enriched_df: pd.DataFrame = dataframe.copy()

        enriched_df = self._extract_date_components(enriched_df)
        enriched_df = self._extract_time_components(enriched_df)
        enriched_df = self._create_business_hours_flags(enriched_df)
        enriched_df = self._create_rush_hour_flags(enriched_df)
        enriched_df = self._create_time_of_day_categories(enriched_df)

        logger.debug('Temporal feature engineering complete')

        return enriched_df

    def _extract_date_components(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Extract date-related components from transaction timestamp.

        Args:
            dataframe: DataFrame with transaction_timestamp

        Returns:
            DataFrame with date component columns
        """
        timestamp: pd.Series = dataframe['transaction_timestamp']

        # Backward compatibility: Keep datetime_parsed for legacy code
        dataframe['datetime_parsed'] = timestamp

        # Normalized date (midnight) for daily aggregations
        dataframe['date_only'] = timestamp.dt.normalize()

        # Date components
        dataframe['year'] = timestamp.dt.isocalendar().year
        dataframe['month'] = timestamp.dt.to_period('M')
        dataframe['week_number'] = timestamp.dt.isocalendar().week
        dataframe['weekday'] = timestamp.dt.weekday
        dataframe['day_of_month'] = timestamp.dt.day

        # Weekend flag
        business_days: list[int] = self.config.business_hours.days_of_week
        dataframe['is_weekend'] = ~dataframe['weekday'].isin(business_days)

        return dataframe

    def _extract_time_components(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Extract time-related components from transaction timestamp.

        Args:
            dataframe: DataFrame with transaction_timestamp

        Returns:
            DataFrame with time component columns
        """
        timestamp: pd.Series = dataframe['transaction_timestamp']

        dataframe['hour'] = timestamp.dt.hour
        dataframe['minute'] = timestamp.dt.minute

        return dataframe

    def _create_business_hours_flags(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Create flags indicating whether transaction occurred during business hours.

        Handles both standard day schedules (e.g., 6am-4pm) and overnight
        shifts (e.g., 10pm-6am).

        Args:
            dataframe: DataFrame with hour and is_weekend columns

        Returns:
            DataFrame with is_business_hours flag
        """
        start_hour: int = self.config.business_hours.start_hour
        end_hour: int = self.config.business_hours.end_hour

        hour_series: pd.Series = dataframe['hour']

        if start_hour < end_hour:
            # Standard day (e.g., 6am to 4pm)
            is_business_time: pd.Series = (
                (hour_series >= start_hour) & (hour_series < end_hour)
            )
        else:
            # Overnight shift (e.g., 10pm to 6am)
            is_business_time = (hour_series >= start_hour) | (hour_series < end_hour)

        # Business hours = correct time AND not weekend
        dataframe['is_business_hours'] = is_business_time & (~dataframe['is_weekend'])

        return dataframe

    def _create_rush_hour_flags(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Flag transactions occurring during typical rush hour periods.

        Rush hours are defined as:
        - Morning: 7am-9am (hour 7, 8)
        - Evening: 4pm-7pm (hour 16, 17, 18)

        These periods may indicate commuter fraud patterns.

        Args:
            dataframe: DataFrame with hour column

        Returns:
            DataFrame with rush hour flags
        """
        hour_series: pd.Series = dataframe['hour']

        morning_rush_hours: list[int] = [7, 8]
        evening_rush_hours: list[int] = [16, 17, 18]

        dataframe['is_morning_rush'] = hour_series.isin(morning_rush_hours)
        dataframe['is_evening_rush'] = hour_series.isin(evening_rush_hours)
        dataframe['is_rush_hour'] = (
            dataframe['is_morning_rush'] | dataframe['is_evening_rush']
        )

        return dataframe

    def _create_time_of_day_categories(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Categorize transactions by broad time-of-day periods.

        Categories:
        - Early Morning: 12am-6am (0-5)
        - Morning: 6am-12pm (6-11)
        - Afternoon: 12pm-6pm (12-17)
        - Evening: 6pm-12am (18-23)

        Args:
            dataframe: DataFrame with hour column

        Returns:
            DataFrame with time_of_day_category column
        """
        hour_series: pd.Series = dataframe['hour']

        conditions: list[pd.Series] = [
            hour_series < 6,  # noqa: PLR2004
            (hour_series >= 6) & (hour_series < 12),  # noqa: PLR2004
            (hour_series >= 12) & (hour_series < 18),  # noqa: PLR2004
            hour_series >= 18,  # noqa: PLR2004
        ]

        categories: list[str] = [
            'Early Morning',
            'Morning',
            'Afternoon',
            'Evening',
        ]

        dataframe['time_of_day_category'] = np.select(
            conditions, categories, default='Unknown'
        )

        return dataframe


class TransactionFeatureEngineer:
    """
    Creates transaction-level derived features.

    Generates features related to:
    - Cost per gallon calculations
    - Transaction size categorization
    - Fillups per day counting
    - Product type standardization
    """

    def __init__(self, config: FuelCardForensicsConfig) -> None:
        """
        Initialize transaction feature engineer with configuration.

        Args:
            config: Configuration containing analysis parameters
        """
        self.config: FuelCardForensicsConfig = config

    def engineer_features(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Generate all transaction-level features.

        Args:
            dataframe: DataFrame with transaction data

        Returns:
            DataFrame with additional transaction feature columns
        """
        logger.debug('Engineering transaction features')

        enriched_df: pd.DataFrame = dataframe.copy()

        enriched_df = self._standardize_product_categories(enriched_df)
        enriched_df = self._calculate_cost_per_gallon(enriched_df)
        enriched_df = self._categorize_transaction_sizes(enriched_df)
        enriched_df = self._calculate_fillups_per_day(enriched_df)
        enriched_df = self._add_branch_grouping(enriched_df)

        logger.debug('Transaction feature engineering complete')

        return enriched_df

    def _standardize_product_categories(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize product category names and create diesel/DEF flag.

        Args:
            dataframe: DataFrame with product_category column

        Returns:
            DataFrame with product_clean and is_diesel_def columns
        """
        dataframe['product_clean'] = (
            dataframe['product_category'].fillna('unknown').str.lower().str.strip()
        )

        diesel_products: list[str] = ['diesel', 'def']
        dataframe['is_diesel_def'] = dataframe['product_clean'].isin(diesel_products)

        return dataframe

    def _calculate_cost_per_gallon(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate cost per gallon for each transaction.

        This metric helps identify:
        - Unusually expensive purchases (potential premium fuel fraud)
        - Unusually cheap purchases (potential data quality issues)
        - Price outliers by region or merchant

        Args:
            dataframe: DataFrame with transaction_amount and fuel_volume_gallons

        Returns:
            DataFrame with cost_per_gallon column
        """
        dataframe['cost_per_gallon'] = (
            dataframe['transaction_amount'] / dataframe['fuel_volume_gallons']
        )

        # Replace inf values (division by zero) with NaN
        dataframe['cost_per_gallon'] = dataframe['cost_per_gallon'].replace(
            [np.inf, -np.inf], np.nan
        )

        return dataframe

    def _categorize_transaction_sizes(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Categorize transactions by cost into small/medium/large buckets.

        Small: < $50
        Medium: $50-$150
        Large: > $150

        Args:
            dataframe: DataFrame with transaction_amount column

        Returns:
            DataFrame with transaction_size_category column
        """
        cost_series: pd.Series = dataframe['transaction_amount']

        conditions: list[pd.Series] = [
            cost_series < 50.0,  # noqa: PLR2004
            (cost_series >= 50.0) & (cost_series <= 150.0),  # noqa: PLR2004
            cost_series > 150.0,  # noqa: PLR2004
        ]

        categories: list[str] = ['Small', 'Medium', 'Large']

        dataframe['transaction_size_category'] = np.select(
            conditions, categories, default='Unknown'
        )

        return dataframe

    def _calculate_fillups_per_day(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Count number of fuel transactions per vehicle per day.

        Multiple fillups in a single day can indicate:
        - Fuel card sharing
        - Fraudulent repeated purchases
        - High-intensity vehicle usage

        Args:
            dataframe: DataFrame with vehicle_index, date_only, and timestamp

        Returns:
            DataFrame with fillups_per_day column
        """
        dataframe['fillups_per_day'] = dataframe.groupby(
            ['vehicle_index', 'date_only']
        )['transaction_timestamp'].transform('nunique')

        return dataframe

    def _add_branch_grouping(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Create branch grouping to separate target location from peer locations.

        Args:
            dataframe: DataFrame with location_index column

        Returns:
            DataFrame with branch_group column
        """
        target_location_number: int = self.config.analysis.target_location_number
        target_location_name: str = self.config.analysis.target_location_name

        dataframe['branch_group'] = np.where(
            dataframe['location_index'] == target_location_number,
            target_location_name,
            'Other Branches',
        )

        dataframe['branch_group'] = dataframe['branch_group'].astype(pd.StringDtype())

        return dataframe


class VehicleFeatureEngineer:
    """
    Creates vehicle-level derived features.

    Generates features related to:
    - Fuel efficiency (MPG)
    - Idle percentages
    - Driving percentages
    - Odometer validation
    """

    def engineer_features(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Generate all vehicle-level features.

        Args:
            dataframe: DataFrame with vehicle telemetry data

        Returns:
            DataFrame with additional vehicle feature columns
        """
        logger.debug('Engineering vehicle features')

        enriched_df: pd.DataFrame = dataframe.copy()

        enriched_df = self._calculate_fuel_efficiency(enriched_df)
        enriched_df = self._calculate_idle_percentage(enriched_df)
        enriched_df = self._calculate_driving_percentage(enriched_df)

        logger.debug('Vehicle feature engineering complete')

        return enriched_df

    def _calculate_fuel_efficiency(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate miles per gallon (MPG) for transactions with both distance and volume.

        This metric helps identify:
        - Unusually low MPG (potential fuel theft or siphoning)
        - Unusually high MPG (potential odometer tampering)
        - Vehicle performance issues

        Args:
            dataframe: DataFrame with distance_miles and fuel_volume_gallons

        Returns:
            DataFrame with mpg column
        """
        dataframe['mpg'] = (
            dataframe['distance_miles'] / dataframe['fuel_volume_gallons']
        )

        # Replace inf values (division by zero) with NaN
        dataframe['mpg'] = dataframe['mpg'].replace([np.inf, -np.inf], np.nan)

        return dataframe

    def _calculate_idle_percentage(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate percentage of engine runtime spent idling.

        High idle percentages may indicate:
        - Excessive idling (inefficient fuel use)
        - Personal use (idling at non-work locations)
        - Vehicle left running unnecessarily

        Args:
            dataframe: DataFrame with idle_duration_minutes and engine_runtime_minutes

        Returns:
            DataFrame with idle_percentage column
        """
        dataframe['idle_percentage'] = (
            dataframe['idle_duration_minutes'] / dataframe['engine_runtime_minutes']
        ) * 100.0

        # Replace inf values and cap at 100%
        dataframe['idle_percentage'] = dataframe['idle_percentage'].replace(
            [np.inf, -np.inf], np.nan
        )
        dataframe['idle_percentage'] = dataframe['idle_percentage'].clip(upper=100.0)

        return dataframe

    def _calculate_driving_percentage(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate percentage of engine runtime spent driving.

        Low driving percentages combined with high engine runtime may indicate
        excessive idling or non-productive vehicle use.

        Args:
            dataframe: DataFrame with driving_duration_minutes and engine_runtime_minutes

        Returns:
            DataFrame with driving_percentage column
        """
        dataframe['driving_percentage'] = (
            dataframe['driving_duration_minutes'] / dataframe['engine_runtime_minutes']
        ) * 100.0

        # Replace inf values and cap at 100%
        dataframe['driving_percentage'] = dataframe['driving_percentage'].replace(
            [np.inf, -np.inf], np.nan
        )
        dataframe['driving_percentage'] = dataframe['driving_percentage'].clip(
            upper=100.0
        )

        return dataframe
