# argus/pipeline.py

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self

import pandas as pd

from argus.categoricals import run_key_metric_analysis
from argus.formatting import format_duration_between_times, slugify
from argus.generate_visualizations import generate_executive_visualizations
from argus.models.analysis import DriverRiskProfile
from argus.models.context import ArgusConfig, ArgusServices
from argus.preprocessing import run_data_preparation
from argus.report_summary import generate_report_summary
from argus.risk_analysis import run_risk_identification_analysis
from argus.suspicious_patterns import run_suspicious_pattern_analysis
from argus.temporal import run_advanced_temporal_analysis
from argus.utils.builders import build_dependencies_from_paths

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)


class ArgusPipeline:
    """
    Orchestrate a complete ARGUS forensic analysis run.

    The pipeline coordinates the full analysis workflow for one or more targets
    (typically locations) and produces one or more forensic reports containing
    statistical tests, risk profiles, pattern detection, and temporal analysis.

    Design:
        - Configuration (ArgusConfig) is pure, validated data loaded from YAML.
        - Services (ArgusServices) are side-effectful dependencies (writer, formatter, clock).
        - This class focuses on orchestration, not dependency construction.

    Typical usage:
        >>> pipeline = ArgusPipeline.from_paths('user.yaml', 'policy.yaml', 'en_US.yaml')
        >>> pipeline.run()

    Testing usage:
        >>> pipeline = ArgusPipeline(config=config, services=fake_services)
        >>> pipeline.run()
    """

    def __init__(
        self,
        *,
        config: ArgusConfig,
        services: ArgusServices,
    ) -> None:
        """
        Initialize the forensic analysis pipeline.

        """
        self._config: ArgusConfig = config
        self._services: ArgusServices = services

    @classmethod
    def from_paths(
        cls,
        user_config_path: str | Path,
        policy_path: str | Path | None = None,
        locale_path: str | Path | None = None,
    ) -> Self:
        """Factory that loads configs and performs setup side effects."""
        config: ArgusConfig
        services: ArgusServices
        config, services = build_dependencies_from_paths(
            user_config_path=user_config_path,
            policy_path=policy_path,
            locale_path=locale_path,
        )
        return cls(config=config, services=services)

    @property
    def config(self) -> ArgusConfig:
        return self._config

    @property
    def services(self) -> ArgusServices:
        return self._services

    @property
    def target_location(self) -> str:
        return self.config.user.analysis.target_location_name

    @property
    def target_number(self) -> int:
        return self.config.user.analysis.target_location_number

    @property
    def output_directory(self) -> Path:
        return self.config.user.output.output_directory

    def run(
        self, df: pd.DataFrame, highlight_drivers: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Execute the complete forensic analysis pipeline.

        Args:
            df: Raw DataFrame containing fuel card and ELD data
            highlight_drivers: Optional list of specific drivers to analyze in detail

        Returns:
            dictionary containing all analysis results and artifacts
        """
        logger.info('ARGUS (Analytics & Risk Governance Utility Suite)')
        logger.info('Target Location: %r', self.target_location)
        start_time: datetime = datetime.now(tz=UTC)

        # Verify the provided dataframe has all the required columns
        is_valid: bool
        missing_columns: list[str]
        is_valid, missing_columns = (
            self.config.user.column_mapping.validate_dataframe_columns(df.columns)
        )
        if not is_valid:
            raise ValueError(
                f'The provided dataframe is missing these required columns: {missing_columns}'
            )

        # Standardize the column names using the user provided mapping
        renamed_df: pd.DataFrame = df.rename(
            columns=self.config.user.column_mapping.get_rename_mapping()
        )

        try:
            # Stage 1: Data Preparation
            self._stage_data_preparation(renamed_df)

            # Stage 2: Statistical Analysis
            self._stage_statistical_analysis()

            # Stage 3: Risk Identification
            high_volume_drivers: list[DriverRiskProfile] = (
                self._stage_risk_identification(highlight_drivers)
            )

            # Stage 4: Suspicious Pattern Detection
            self._stage_pattern_detection()

            # Stage 5: Temporal Analysis
            self._stage_temporal_analysis()

            # Stage 6: Generate Report Summary
            self._stage_report_summary()

            # Stage 7: Generate Visualizations
            if self.config.user.output.generate_visualizations:
                self._stage_visualizations(high_volume_drivers)

            # Stage 8: Output Report
            self._stage_output_report()

            end_time: datetime = datetime.now(tz=UTC)
            run_time: str = format_duration_between_times(start_time, end_time)
            logger.info('Analysis Completed in %s', run_time)

            return self.results

        except Exception as e:
            logger.warning('ANALYSIS FAILED')
            logger.error('Error: %r', e)
            raise

    def _stage_data_preparation(self, df: pd.DataFrame) -> None:
        """Stage 1: Data preparation and quality assessment."""
        logger.info('STAGE 1: DATA PREPARATION & QUALITY ASSESSMENT')

        # Run data preparation
        self.context: AnalysisContext = run_data_preparation(
            raw_dataframe=df,
            report_writer=self.report_writer,
            report_formatter=self.report_formatter,
            config=self.config,
        )

        # Write the methodology section
        self.report_writer.write_methodology()

        logger.debug('\n✓ Data preparation complete')
        logger.debug(
            '  - Target location: %d:, transactions',
            len(self.context.target_period_transactions),
        )
        logger.debug(
            '  - Other branches: %d:, transactions',
            len(self.context.peer_period_transactions),
        )
        logger.debug('  - Analysis period: %s', self.context.analysis_period_label)

    def _stage_statistical_analysis(self) -> None:
        """Stage 2: Key metric statistical analysis."""
        logger.info('STAGE 2: KEY METRIC STATISTICAL ANALYSIS')

        self.all_tests = run_key_metric_analysis(self.context)

        significant_count: int = sum(
            1 for test in self.all_tests.values() if test.is_significant
        )
        logger.debug('\n✓ Statistical analysis complete')
        logger.debug('  - Tests performed: %d', len(self.all_tests))
        logger.debug('  - Significant findings: %d', significant_count)

        self.results['statistical_tests'] = self.all_tests

    def _stage_risk_identification(
        self, highlight_drivers: list[str] | None
    ) -> list[DriverRiskProfile]:
        """Stage 3: High-risk driver and vehicle identification."""
        logger.debug('STAGE 3: RISK IDENTIFICATION ANALYSIS')

        # Run analysis and capture driver profiles
        self.driver_profiles: list[DriverRiskProfile]
        high_volume_drivers: list[DriverRiskProfile]
        self.driver_profiles, high_volume_drivers = run_risk_identification_analysis(
            self.context,
            highlight_drivers=highlight_drivers,
        )

        logger.debug('\n✓ Risk identification complete')
        logger.debug(
            '  - Analyzed %d entities for high-risk behavior',
            len(self.driver_profiles),
        )
        if highlight_drivers:
            logger.debug(
                '  - Performed deep dive analysis on %d specific drivers',
                len(highlight_drivers),
            )
        else:
            logger.debug(
                '  - Auto-analyzed top %d drivers',
                self.config.analysis.auto_analyze_top_drivers,
            )

        return high_volume_drivers

    def _stage_pattern_detection(self) -> None:
        """Stage 4: Suspicious pattern detection."""
        logger.debug('STAGE 4: SUSPICIOUS PATTERN DETECTION')

        run_suspicious_pattern_analysis(
            self.context,
            all_tests=self.all_tests,
        )

        logger.debug('\n✓ Pattern detection complete')
        logger.debug('  - Multi-fillup patterns analyzed')
        logger.debug('  - Geographic anomalies identified')

    def _stage_temporal_analysis(self) -> None:
        """Stage 5: Advanced temporal analysis."""
        logger.debug('STAGE 5: ADVANCED TEMPORAL ANALYSIS')

        temporal_results: dict[str, Any] = run_advanced_temporal_analysis(self.context)

        self.results['temporal_analysis'] = temporal_results

        logger.debug('\n✓ Temporal analysis complete')
        if temporal_results.get('temporal_profiles'):
            logger.debug(
                '  - Entities analyzed: %d', len(temporal_results['temporal_profiles'])
            )
            logger.debug(
                '  - High-risk entities: %d',
                len(temporal_results.get('high_risk_entities', [])),
            )
            logger.debug(
                '  - Mean risk score: %.1f',
                temporal_results.get('target_mean_risk', 0.0),
            )

    def _stage_report_summary(self) -> None:
        """Stage 6: Generate executive summary and footer."""
        logger.debug('STAGE 6: GENERATING REPORT SUMMARY')

        generate_report_summary(
            report_writer=self.report_writer,
            all_tests=self.all_tests,
            full_df=self.results['full_df'],
            target_location_df=self.results['target_location'],
            others_df=self.results['others'],
        )

        logger.debug('\n✓ Report summary generated')

    def _stage_visualizations(
        self, high_volume_drivers: list[DriverRiskProfile]
    ) -> None:
        """Stage 7: Generate executive visualizations."""
        logger.debug('STAGE 7: GENERATING VISUALIZATIONS')

        save_path: Path | None = None
        if self.config.output.save_visualizations:
            date_string: str = datetime.now(tz=UTC).strftime('%Y%m%d')
            clean_location: str = slugify(self.target_location)
            save_path: Path | None = (
                self.output_dir / f'Dashboard_{clean_location}_{date_string}.png'
            )

        try:
            generate_executive_visualizations(
                self.context,
                all_tests=self.all_tests,
                driver_profiles=self.driver_profiles,
                high_volume_drivers=high_volume_drivers,
                save_path=str(save_path) if save_path else None,
            )

            logger.debug('\n✓ Visualizations generated')
            if save_path:
                logger.debug('  - Saved to: %r', save_path)
        except Exception as e:
            logger.warning('\n⚠ Warning: Visualization generation failed: %r', e)
            logger.warning('  Continuing with text report only...')

    def _stage_output_report(self) -> None:
        """Stage 8: Output and save the final report."""
        logger.debug('STAGE 8: OUTPUTTING FINAL REPORT')

        # Render to console
        if self.config.output.display_report:
            logger.info('=' * 100)
            logger.info('FORENSIC ANALYSIS REPORT')
            logger.info('=' * 100)

            self.report_writer.render_report()

        # Save to file if requested
        if self.config.output.save_report:
            date_string: str = datetime.now(tz=UTC).strftime('%Y%m%d')
            clean_location: str = slugify(self.target_location)
            report_path: Path = (
                self.output_dir / f'ARGUS_Report_{clean_location}_{date_string}.txt'
            )
            self.report_writer.save_report(str(report_path))
            logger.info('Report saved to: %r', report_path)

        self.results['report_writer'] = self.report_writer
