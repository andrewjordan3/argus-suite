# argus/risk_analysis.py

import logging
import math

import pandas as pd

from argus.models import DriverRiskProfile, ReportSection, VolumeStatistics
from argus.utils import AnalysisContext, RiskProfileCalculator

logger: logging.Logger = logging.getLogger(__name__)

__all__: list[str] = ['DriverAnalyzer', 'run_risk_identification_analysis']

class DriverAnalyzer:
    """
    Encapsulates driver-level fraud risk analysis and reporting.

    This class handles all aspects of driver risk identification including:
    - Comprehensive risk profiling using statistical methods
    - Volume-based analysis for high-consumption detection
    - Focused deep-dive analysis for specific drivers
    - Statistical calculations (z-scores, rates, aggregations)

    The analyzer separates calculation logic from report writing, making it easier
    to test and maintain each component independently.

    Attributes:
        context: Analysis context containing transactions, config, and reporting tools
        driver_aggregation_specification: Standardized aggregation spec for driver metrics
    """

    def __init__(self, context: AnalysisContext) -> None:
        """
        Initialize the driver analyzer with analysis context.

        Args:
            context: Analysis context containing configuration and transaction data
        """
        self.context: AnalysisContext = context

        # Define standard driver aggregation specification used across multiple analyses
        # This ensures consistency in how driver metrics are calculated
        self.driver_aggregation_specification: dict[str, pd.NamedAgg] = {
            'total_transactions': pd.NamedAgg(
                column='datetime_parsed', aggfunc='count'
            ),
            'no_eld_count': pd.NamedAgg(
                column='has_eld_activity', aggfunc=self._count_false_values
            ),
            'non_diesel_count': pd.NamedAgg(
                column='is_diesel_def', aggfunc=self._count_false_values
            ),
            'after_hours_count': pd.NamedAgg(
                column='is_business_hours', aggfunc=self._count_false_values
            ),
            'total_cost': pd.NamedAgg(column='transaction_amount', aggfunc='sum'),
        }

    @staticmethod
    def _count_false_values(boolean_series: pd.Series) -> int:
        """
        Count the number of False values in a boolean pandas Series.

        This is a more explicit replacement for the lambda: lambda x: (~x).sum()
        used in pandas aggregation specifications.

        Args:
            boolean_series: Series containing boolean values

        Returns:
            Total count of False values in the series
        """
        return int((~boolean_series).sum())

    def analyze_driver_risk_profiles(self) -> pd.DataFrame:
        """
        Calculate comprehensive risk profiles for all drivers meeting minimum criteria.

        This method orchestrates the full risk profiling pipeline:
        1. Aggregates transactions by driver
        2. Calculates Wilson confidence intervals for rates
        3. Computes percentile-based risk scores
        4. Flags statistically significant elevated risks
        5. Generates report table for top-risk drivers

        Returns:
            DataFrame containing risk profiles for all qualifying drivers,
            sorted by composite risk score descending. Empty DataFrame if
            no drivers meet minimum transaction threshold.
        """
        logger.info('Starting comprehensive driver risk profile analysis')

        calculator: RiskProfileCalculator = RiskProfileCalculator(self.context)
        driver_profiles: pd.DataFrame = calculator.calculate_risk_profiles(
            entity_column='driver_name',
            aggregation_specification=self.driver_aggregation_specification,
        )

        if driver_profiles.empty:
            self._report_insufficient_driver_data()
            return driver_profiles

        self._generate_driver_risk_table(driver_profiles)

        logger.info(
            'Driver risk profile analysis complete. %d drivers analyzed.',
            len(driver_profiles),
        )

        return driver_profiles

    def _report_insufficient_driver_data(self) -> None:
        """
        Add warning message to report when no drivers meet minimum transaction criteria.
        """
        minimum_transactions: int = self.context.config.analysis.min_transactions_risk

        warning_message: str = (
            f'\n⚠ No drivers at the target location met the minimum criteria '
            f'({minimum_transactions}+ transactions) for risk analysis.'
        )

        self.context.report_writer.add_to_section(
            ReportSection.DRIVER_ANALYSIS, warning_message
        )

        logger.warning(
            'No drivers meet minimum transaction threshold (%d) for risk analysis',
            minimum_transactions,
        )

    def _generate_driver_risk_table(self, driver_profiles: pd.DataFrame) -> None:
        """
        Generate and write the driver risk summary table to the report.

        Args:
            driver_profiles: DataFrame containing all driver risk profiles
        """
        top_driver_count: int = self.context.config.analysis.top_n_entities
        top_drivers: pd.DataFrame = driver_profiles.head(top_driver_count)

        driver_risk_profiles: list[DriverRiskProfile] = []

        for rank, (_, row_data) in enumerate(top_drivers.iterrows(), start=1):
            driver_risk_profiles.append(
                DriverRiskProfile(
                    driver_name=str(row_data['driver_name']),
                    risk_score=float(row_data['composite_risk_score']),
                    transaction_count=int(row_data['total_transactions']),
                    no_eld_rate=float(row_data['no_eld_rate']),
                    non_diesel_rate=float(row_data['non_diesel_rate']),
                    after_hours_rate=float(row_data['after_hours_rate']),
                    avg_cost=float(row_data['avg_cost_per_transaction']),
                    total_cost=float(row_data['total_cost']),
                    rank=rank,
                )
            )

        self.context.report_writer.write_driver_table(driver_risk_profiles)

        logger.debug(
            'Generated risk table for top %d drivers', len(driver_risk_profiles)
        )

    def analyze_top_volume_drivers(self) -> list[DriverRiskProfile]:
        """
        Identify and analyze drivers with the highest total fuel volume.

        This analysis is independent from risk scoring and can identify high-volume
        drivers even if they don't meet risk analysis transaction thresholds.
        High volume without corresponding risk flags may indicate legitimate heavy
        use, while high volume WITH risk flags warrants immediate investigation.

        Returns:
            List of DriverRiskProfile objects for top volume drivers,
            sorted by total volume descending. Empty list if insufficient data.
        """
        logger.info('Starting top volume driver analysis')

        transaction_data: pd.DataFrame = self.context.target_period_transactions

        if not self._validate_volume_analysis_data(transaction_data):
            return []

        volume_statistics: pd.DataFrame = self._aggregate_driver_volume_statistics(
            transaction_data
        )

        if volume_statistics.empty:
            logger.warning(
                'No drivers meet minimum transaction threshold for volume analysis'
            )
            return []

        volume_statistics = self._calculate_driver_risk_rates(volume_statistics)
        volume_statistics = self._calculate_volume_z_scores(volume_statistics)
        volume_statistics = self._sort_and_limit_by_volume(volume_statistics)

        volume_profiles: list[DriverRiskProfile] = self._create_volume_driver_profiles(
            volume_statistics
        )

        logger.info(
            'Top volume driver analysis complete. %d drivers identified.',
            len(volume_profiles),
        )

        return volume_profiles

    def _validate_volume_analysis_data(self, transaction_data: pd.DataFrame) -> bool:
        """
        Validate that transaction data contains required columns for volume analysis.

        Args:
            transaction_data: Raw transaction DataFrame

        Returns:
            True if data is valid for volume analysis, False otherwise
        """
        if transaction_data.empty:
            logger.warning('Transaction data is empty for volume analysis')
            return False

        if 'driver_name' not in transaction_data.columns:
            logger.warning('Transaction data missing required column: driver_name')
            return False

        if 'fuel_volume_gallons' not in transaction_data.columns:
            logger.warning(
                'Transaction data missing required column: fuel_volume_gallons'
            )
            return False

        return True

    def _aggregate_driver_volume_statistics(
        self, transaction_data: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Aggregate transaction data to calculate per-driver volume and fraud metrics.

        Args:
            transaction_data: Raw transaction DataFrame

        Returns:
            DataFrame with one row per driver containing aggregated statistics
        """
        aggregation_with_volume: dict[str, pd.NamedAgg] = {
            **self.driver_aggregation_specification,
            'total_volume': pd.NamedAgg(column='fuel_volume_gallons', aggfunc='sum'),
        }

        driver_statistics: pd.DataFrame = (
            transaction_data.groupby('driver_name')
            .agg(**aggregation_with_volume)
            .reset_index()
        )

        minimum_transactions: int = self.context.config.analysis.min_transactions_risk
        driver_statistics = driver_statistics[
            driver_statistics['total_transactions'] >= minimum_transactions
        ].copy()

        logger.debug(
            'Aggregated volume statistics for %d drivers (minimum %d transactions)',
            len(driver_statistics),
            minimum_transactions,
        )

        return driver_statistics

    def _calculate_driver_risk_rates(
        self, driver_statistics: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate fraud risk rates (proportions) for each driver.

        Args:
            driver_statistics: DataFrame with aggregated driver counts

        Returns:
            DataFrame with additional rate columns added
        """
        total_transactions: pd.Series = driver_statistics['total_transactions']

        driver_statistics['no_eld_rate'] = (
            driver_statistics['no_eld_count'] / total_transactions
        )

        driver_statistics['non_diesel_rate'] = (
            driver_statistics['non_diesel_count'] / total_transactions
        )

        driver_statistics['after_hours_rate'] = (
            driver_statistics['after_hours_count'] / total_transactions
        )

        driver_statistics['avg_cost'] = (
            driver_statistics['total_cost'] / total_transactions
        )

        return driver_statistics

    def _calculate_volume_z_scores(
        self, driver_statistics: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate standardized z-scores for driver fuel volumes.

        Z-scores indicate how many standard deviations each driver's volume
        is from the fleet average. High positive z-scores (>2.0) indicate
        unusually high consumption that may warrant investigation.

        If standard deviation is zero or invalid (cannot calculate meaningful
        z-scores), all z-scores are set to NaN to indicate missing data.

        Args:
            driver_statistics: DataFrame containing total_volume column

        Returns:
            DataFrame with volume_z_score column added
        """
        volume_series: pd.Series = driver_statistics['total_volume']

        mean_volume: float = float(volume_series.mean())
        std_volume: float = float(volume_series.std())

        if pd.isna(std_volume) or std_volume <= 0.0:
            logger.debug(
                'Volume standard deviation is zero or invalid. '
                'Setting all z-scores to NaN (cannot calculate)'
            )
            driver_statistics['volume_z_score'] = math.nan
        else:
            driver_statistics['volume_z_score'] = (
                volume_series - mean_volume
            ) / std_volume

            logger.debug(
                'Calculated volume z-scores. Mean: %.2f gallons, Std: %.2f gallons',
                mean_volume,
                std_volume,
            )

        return driver_statistics

    def _sort_and_limit_by_volume(
        self, driver_statistics: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Sort drivers by total volume descending and limit to top N.

        Args:
            driver_statistics: DataFrame containing driver volume statistics

        Returns:
            DataFrame sorted by volume, limited to configured top N drivers
        """
        top_driver_count: int = self.context.config.analysis.top_n_entities

        sorted_statistics: pd.DataFrame = driver_statistics.sort_values(
            'total_volume', ascending=False
        ).head(top_driver_count)

        return sorted_statistics

    def _create_volume_driver_profiles(
        self, volume_statistics: pd.DataFrame
    ) -> list[DriverRiskProfile]:
        """
        Create DriverRiskProfile objects from volume statistics.

        Note: These profiles have risk_score set to 0.0 since this is purely
        volume-based analysis, not comprehensive risk scoring. This is an
        intentional zero, not missing data.

        Args:
            volume_statistics: DataFrame with driver volume and risk metrics

        Returns:
            List of DriverRiskProfile objects sorted by volume
        """
        volume_profiles: list[DriverRiskProfile] = []

        for rank, (_, row_data) in enumerate(volume_statistics.iterrows(), start=1):
            volume_profiles.append(
                DriverRiskProfile(
                    driver_name=str(row_data['driver_name']),
                    risk_score=0.0,  # Intentional: volume analysis doesn't compute risk scores
                    transaction_count=int(row_data['total_transactions']),
                    no_eld_rate=float(row_data['no_eld_rate']),
                    non_diesel_rate=float(row_data['non_diesel_rate']),
                    after_hours_rate=float(row_data['after_hours_rate']),
                    avg_cost=float(row_data['avg_cost']),
                    total_cost=float(row_data['total_cost']),
                    total_volume=float(row_data['total_volume']),
                    volume_z_score=float(row_data['volume_z_score']),
                    rank=rank,
                )
            )

        return volume_profiles

    def run_focused_driver_analysis(
        self,
        driver_names_to_analyze: list[str],
        driver_risk_profiles: pd.DataFrame,
    ) -> list[DriverRiskProfile]:
        """
        Perform comprehensive deep-dive analysis on specific drivers.

        This method generates detailed driver profiles including:
        - Complete risk metrics and rates
        - Volume statistics and z-scores
        - Product breakdown (fuel types purchased)
        - Multi-fillup day analysis
        - Vehicle usage patterns

        Args:
            driver_names_to_analyze: List of driver names to analyze in detail
            driver_risk_profiles: Pre-calculated risk profiles for all drivers

        Returns:
            List of DriverRiskProfile objects for the analyzed drivers
        """
        if not driver_names_to_analyze:
            logger.debug('No drivers specified for focused analysis')
            return []

        if driver_risk_profiles.empty:
            logger.warning('Driver risk profiles DataFrame is empty')
            return []

        logger.info(
            'Starting focused analysis for %d drivers', len(driver_names_to_analyze)
        )

        volume_statistics: VolumeStatistics = self._calculate_fleet_volume_statistics()
        focused_profiles: list[DriverRiskProfile] = []

        for driver_name in driver_names_to_analyze:
            driver_profile: DriverRiskProfile | None = self._analyze_single_driver(
                driver_name=driver_name,
                driver_risk_profiles=driver_risk_profiles,
                volume_statistics=volume_statistics,
            )

            if driver_profile is not None:
                focused_profiles.append(driver_profile)

        logger.info(
            'Focused driver analysis complete. %d drivers analyzed.',
            len(focused_profiles),
        )

        return focused_profiles

    def _calculate_fleet_volume_statistics(self) -> VolumeStatistics:
        """
        Calculate fleet-wide volume statistics for z-score computation.

        Returns:
            VolumeStatistics object containing mean, std, and availability flag.
            When volume data is unavailable, mean and std are set to NaN.
        """
        transaction_data: pd.DataFrame = self.context.target_period_transactions

        has_volume_column: bool = 'fuel_volume_gallons' in transaction_data.columns

        if not has_volume_column:
            return VolumeStatistics(
                has_volume=False,
                mean_volume=math.nan,
                std_volume=math.nan,
            )

        driver_volumes: pd.Series = (
            transaction_data.groupby('driver_name')['fuel_volume_gallons'].sum(
                min_count=1
            )
        )

        mean_volume: float = float(driver_volumes.mean())

        # Standard deviation requires at least 2 non-null values
        std_volume: float = (
            float(driver_volumes.std())
            if len(driver_volumes.dropna()) > 1
            else math.nan
        )

        logger.debug(
            'Fleet volume statistics: Mean=%.2f gallons, Std=%.2f gallons',
            mean_volume,
            std_volume,
        )

        return VolumeStatistics(
            has_volume=True,
            mean_volume=mean_volume,
            std_volume=std_volume,
        )

    def _analyze_single_driver(
        self,
        driver_name: str,
        driver_risk_profiles: pd.DataFrame,
        volume_statistics: VolumeStatistics,
    ) -> DriverRiskProfile | None:
        """
        Perform complete analysis for a single driver and generate report section.

        Args:
            driver_name: Name of driver to analyze
            driver_risk_profiles: Pre-calculated risk profiles for all drivers
            volume_statistics: Fleet-wide volume statistics for z-score calculation

        Returns:
            DriverRiskProfile object if analysis successful, None otherwise
        """
        # Extract driver's risk statistics
        driver_stats_row: pd.DataFrame = driver_risk_profiles[
            driver_risk_profiles['driver_name'] == driver_name
        ]

        if driver_stats_row.empty:
            logger.warning(
                'Driver %r not found in risk profiles. Skipping analysis.', driver_name
            )
            return None

        driver_statistics: pd.Series = driver_stats_row.iloc[0]

        # Extract driver's transaction data
        transaction_data: pd.DataFrame = self.context.target_period_transactions
        driver_transactions: pd.DataFrame = transaction_data[
            transaction_data['driver_name'] == driver_name
        ]

        if driver_transactions.empty:
            logger.warning(
                'No transactions found for driver %r. Skipping analysis.', driver_name
            )
            return None

        # Calculate volume metrics if available
        total_volume: float = math.nan
        volume_z_score: float = math.nan

        if volume_statistics.has_volume:
            total_volume = float(driver_transactions['fuel_volume_gallons'].sum())

            if (
                not math.isnan(volume_statistics.std_volume)
                and volume_statistics.std_volume > 0.0
            ):
                volume_z_score = (
                    total_volume - volume_statistics.mean_volume
                ) / volume_statistics.std_volume

        # Create driver profile
        driver_profile: DriverRiskProfile = DriverRiskProfile(
            driver_name=driver_name,
            risk_score=float(driver_statistics.get('composite_risk_score', 0.0)),
            transaction_count=int(driver_statistics.get('total_transactions', 0)),
            no_eld_rate=float(driver_statistics.get('no_eld_rate', 0.0)),
            non_diesel_rate=float(driver_statistics.get('non_diesel_rate', 0.0)),
            after_hours_rate=float(driver_statistics.get('after_hours_rate', 0.0)),
            avg_cost=float(driver_statistics.get('avg_cost_per_transaction', 0.0)),
            total_cost=float(driver_statistics.get('total_cost', 0.0)),
            total_volume=total_volume,
            volume_z_score=volume_z_score,
        )

        # Extract detailed transaction patterns
        deep_dive_details: dict[str, int | float | pd.DataFrame] = (
            self._extract_driver_deep_dive_details(driver_transactions)
        )

        # Write focused profile section to report
        self.context.report_writer.write_focused_driver_profile(
            driver_profile, deep_dive_details
        )

        logger.debug(
            'Completed focused analysis for driver: %s '
            '(Risk Score: %.2f, Transactions: %d)',
            driver_name,
            driver_profile.risk_score,
            driver_profile.transaction_count,
        )

        return driver_profile

    def _extract_driver_deep_dive_details(
        self,
        driver_transactions: pd.DataFrame,
    ) -> dict[str, int | float | pd.DataFrame]:
        """
        Extract detailed transaction patterns for deep-dive driver analysis.

        This includes:
        - Number of unique vehicles used
        - Product type breakdown (fuel types and quantities)
        - Multi-fillup day analysis (days with multiple transactions)
        - Maximum fillups in a single day
        - Average cost on multi-fillup days

        Note: Default values of 0 represent legitimate counts (e.g., zero vehicles,
        zero multi-fillup days) rather than missing data.

        Args:
            driver_transactions: DataFrame filtered to single driver's transactions

        Returns:
            Dictionary containing detailed driver statistics and breakdowns
        """
        details: dict[str, int | float | pd.DataFrame] = {
            'unique_vehicles': (
                driver_transactions['VIN'].nunique()
                if 'VIN' in driver_transactions.columns
                else 0
            ),
            'product_breakdown': pd.DataFrame(),
            'multi_fillup_days': 0,
            'max_fillups_one_day': 0,
            'avg_cost_multi_fillup_days': 0.0,
        }

        if driver_transactions.empty:
            return details

        # Product breakdown analysis
        if 'product_clean' in driver_transactions.columns:
            details['product_breakdown'] = self._calculate_product_breakdown(
                driver_transactions
            )

        # Multi-fillup day analysis
        if 'fillups_per_day' in driver_transactions.columns:
            multi_fillup_metrics: dict[str, int | float] = (
                self._calculate_multi_fillup_metrics(driver_transactions)
            )
            details.update(multi_fillup_metrics)

        return details

    def _calculate_product_breakdown(
        self,
        driver_transactions: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Calculate detailed breakdown of fuel products purchased by driver.

        Args:
            driver_transactions: Transactions for a single driver

        Returns:
            DataFrame with columns: count, percentage, total_cost per product type
        """
        product_counts: pd.Series = driver_transactions['product_clean'].value_counts()

        product_costs: pd.Series = (
            driver_transactions.groupby('product_clean')['transaction_amount'].sum()
        )

        total_transactions: int = len(driver_transactions)

        product_breakdown: pd.DataFrame = pd.DataFrame(
            {
                'count': product_counts,
                'percentage': product_counts / total_transactions,
                'total_cost': product_costs,
            }
        )

        return product_breakdown

    def _calculate_multi_fillup_metrics(
        self,
        driver_transactions: pd.DataFrame,
    ) -> dict[str, int | float]:
        """
        Calculate metrics related to days with multiple fillups.

        Multiple fillups in a single day can indicate:
        - Fuel card sharing between drivers
        - Fleet vehicle usage by multiple people
        - Potential fraud through repeated small purchases

        Args:
            driver_transactions: Transactions for a single driver

        Returns:
            Dictionary containing multi-fillup metrics
        """
        multi_fillup_mask: pd.Series = (
            driver_transactions['fillups_per_day'] > 1
        )
        multi_fillup_transactions: pd.DataFrame = driver_transactions[multi_fillup_mask]

        if multi_fillup_transactions.empty:
            return {
                'multi_fillup_days': 0,
                'max_fillups_one_day': 0,
                'avg_cost_multi_fillup_days': 0.0,
            }

        multi_fillup_day_count: int = (
            multi_fillup_transactions['date_only'].nunique()
            if 'date_only' in multi_fillup_transactions.columns
            else 0
        )

        max_fillups_single_day: int = int(driver_transactions['fillups_per_day'].max())

        average_multi_fillup_cost: float = float(
            multi_fillup_transactions['transaction_amount'].mean()
        )

        return {
            'multi_fillup_days': multi_fillup_day_count,
            'max_fillups_one_day': max_fillups_single_day,
            'avg_cost_multi_fillup_days': average_multi_fillup_cost,
        }


def run_risk_identification_analysis(
    context: AnalysisContext,
    highlight_drivers: list[str] | None = None,
) -> tuple[list[DriverRiskProfile], list[DriverRiskProfile]]:
    """
    Orchestrate the complete driver risk identification and analysis process.

    This function coordinates:
    1. Comprehensive risk profiling for all drivers using statistical methods
    2. Volume-based analysis to identify high-consumption drivers
    3. Focused deep-dive analysis on specified or top-risk drivers
    4. Report generation for all analysis components

    The function separates high-risk identification from high-volume identification
    because these represent different fraud patterns:
    - High risk + normal volume: Potential fraud through manipulation
    - High risk + high volume: Most urgent investigation priority
    - Normal risk + high volume: Legitimate heavy use, low priority

    Args:
        context: Analysis context containing configuration, data, and reporting tools
        highlight_drivers: Optional list of specific driver names to analyze in detail.
                          If None, automatically analyzes top N high-risk drivers
                          based on configuration.

    Returns:
        Tuple of (focused_driver_profiles, volume_driver_profiles):
        - focused_driver_profiles: Detailed profiles for analyzed drivers
        - volume_driver_profiles: Profiles for highest-volume drivers
    """
    logger.info(
        'Starting comprehensive risk identification analysis. Highlight drivers: %s',
        highlight_drivers if highlight_drivers else 'Auto-select top risk',
    )

    analyzer: DriverAnalyzer = DriverAnalyzer(context)

    # Perform comprehensive risk profiling
    driver_risk_profiles: pd.DataFrame = analyzer.analyze_driver_risk_profiles()

    # Determine which drivers to analyze in depth
    focused_driver_profiles: list[DriverRiskProfile] = []

    if not driver_risk_profiles.empty:
        drivers_to_analyze: list[str]
        analysis_type_label: str

        if highlight_drivers:
            drivers_to_analyze = highlight_drivers
            analysis_type_label = 'User-Specified'

            logger.info(
                'Using user-specified drivers for focused analysis: %r',
                highlight_drivers,
            )
        else:
            top_driver_count: int = context.config.analysis.auto_analyze_top_drivers
            top_risk_drivers: pd.DataFrame = driver_risk_profiles.head(top_driver_count)
            drivers_to_analyze = top_risk_drivers['driver_name'].tolist()
            analysis_type_label = f'Top {top_driver_count} High-Risk'

            logger.info(
                'Auto-selected top %d high-risk drivers for focused analysis',
                top_driver_count,
            )

        if drivers_to_analyze:
            _add_focused_analysis_section_header(
                context=context,
                driver_count=len(drivers_to_analyze),
                analysis_type=analysis_type_label,
            )

            focused_driver_profiles = analyzer.run_focused_driver_analysis(
                driver_names_to_analyze=drivers_to_analyze,
                driver_risk_profiles=driver_risk_profiles,
            )

    # Perform volume-based analysis
    volume_driver_profiles: list[DriverRiskProfile] = (
        analyzer.analyze_top_volume_drivers()
    )

    logger.info(
        'Risk identification analysis complete. '
        'Focused profiles: %d, Volume profiles: %d',
        len(focused_driver_profiles),
        len(volume_driver_profiles),
    )

    return focused_driver_profiles, volume_driver_profiles


def _add_focused_analysis_section_header(
    context: AnalysisContext,
    driver_count: int,
    analysis_type: str,
) -> None:
    """
    Add formatted section header for focused driver analysis to report.

    Args:
        context: Analysis context containing report writer and formatter
        driver_count: Number of drivers being analyzed in detail
        analysis_type: Description of how drivers were selected (e.g., "User-Specified")
    """
    separator: str = context.report_formatter.separator('=')

    header_lines: list[str] = [
        '',
        separator,
        f'FOCUSED DRIVER ANALYSIS — {analysis_type.upper()} DRIVERS',
        separator,
        f'\nDetailed examination of {driver_count} driver(s) '
        f'showing elevated risk indicators.\n',
    ]

    header_content: str = '\n'.join(header_lines)

    context.report_writer.add_to_section(ReportSection.DRIVER_ANALYSIS, header_content)

    logger.debug(
        'Added focused analysis section header: %s analysis, %d drivers',
        analysis_type,
        driver_count,
    )
