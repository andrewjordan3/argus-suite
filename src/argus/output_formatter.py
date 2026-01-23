# argus/output_formatter.py

import logging
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

import pandas as pd

from argus.models.user_config.root import UserConfig
from argus.models.locale import LocaleConfig
from argus.models.policy.root import PolicyConfig
from argus.utils import (
    ReportFormatter,
)

# Set up a logger for this module
logger: logging.Logger = logging.getLogger(__name__)

CRITICAL_RISK_SCORE: int = 75
MEDIUM_RISK_SCORE: int = 50
LOW_RISK_SCORE: int = 25
MINIMUM_MONTHS: int = 3
MIN_MONTHS_PCT_THRESHOLD: int = 30
EFFECT_MAGNITUDE_THRESHOLD_NEGLIGIBLE: float = 0.147
EFFECT_MAGNITUDE_THRESHOLD_SMALL: float = 0.33
EFFECT_MAGNITUDE_THRESHOLD_MEDIUM: float = 0.474
ODDS_RISK_RATIO_DIFFERENCE_THRESHOLD: float = 0.5


class ForensicReportWriter:
    """
    Handles all output formatting for the Fuel Card Forensic Analysis.
    Separates presentation logic from analysis logic.

    This class is responsible for:
    - Organizing report sections
    - Applying formatted values to templates
    - Managing report output

    All formatting is delegated to ReportFormatter.
    All templates and text content are accessed via ConfigLoader.
    """

    def __init__(
        self,
        user_config: UserConfig,
        policy_config: PolicyConfig,
        locale_config: LocaleConfig,
        formatter: ReportFormatter | None = None,
    ) -> None:
        """
        Initialize the report writer.

        Args:
            target_location: Name of the target branch
            target_location_number: ID of the target branch
            analysis_period: Period being analyzed (e.g., "2025 YTD")
            confidence_level: Statistical confidence level (default 0.95)
            output_width: Width for separator lines (default from config)
            use_logging: If True, use logging instead of print (default False)
            config: Optional pre-loaded ConfigLoader instance
            formatter: Optional pre-loaded ReportFormatter instance
        """
        self.target_location: str = config.analysis.target_location_name
        self.target_location_number: int = config.analysis.target_location_number
        self.analysis_period: str = analysis_period
        self.confidence_level: float = config.analysis.confidence_level
        self.report_date: str = datetime.now(tz=UTC).strftime('%Y-%m-%d')

        # Load configuration
        self.template: TemplateLoader = (
            output_template if output_template is not None else load_template()
        )
        self.new_config: ReportConfig = self.template.pydantic_config

        # Create or use provided formatter
        self.formatter: ReportFormatter = (
            formatter if formatter is not None else ReportFormatter(self.template)
        )

        # Set output width from config or parameter
        self.output_width: int = config.output.output_width

        # Storage for report sections
        self.sections: dict[ReportSection, list[str]] = {
            section: [] for section in ReportSection
        }

    def set_analysis_period(self, analysis_period: str) -> None:
        """Update the analysis period after initialization and refresh header."""
        self.analysis_period = analysis_period
        self.write_header()

    def add_to_section(self, section: ReportSection, content: str) -> None:
        """Add content to a specific section."""
        self.sections[section].append(content)

    # ========================================================================
    # Helper Methods
    # ========================================================================
    def _write_section_header(
        self,
        content: list[str],
        section_key: str | None = None,
        separator_char: str = '=',
        include_newline: bool = True,
        literal_text: str | None = None,
    ) -> None:
        """
        Write a standardized section header with separators.

        This consolidates the extremely common pattern of:
            content.append("\n" + self.formatter.separator("="))
            content.append(self.template.get_section_title('section_name'))
            content.append(self.formatter.separator("="))

        Args:
            content: list to append formatted lines to
            section_key: Configuration key for the section title
            separator_char: Character for separator lines (default "=")
            include_newline: Whether to include newline before first separator (default True)

        Example usage:
            # OLD CODE (3 lines):
            content.append("\n" + self.formatter.separator("="))
            content.append(self.template.get_section_title('data_quality'))
            content.append(self.formatter.separator("="))

            # NEW CODE (1 line):
            self._write_section_header(content, 'data_quality')
        """
        if not section_key and not literal_text:
            logger.warning(
                'ForensicReportWriter._write_section_header was called without anything to write'
            )
            return
        if include_newline:
            content.append('\n' + self.formatter.separator(separator_char))
        else:
            content.append(self.formatter.separator(separator_char))

        if literal_text:
            content.append(literal_text)
        elif section_key:
            content.append(self.template.get_section_title(section_key))
        content.append(self.formatter.separator(separator_char))

    def _write_subsection_header(
        self,
        content: list[str],
        title: str,
        separator_char: str = '-',
        include_newline: bool = True,
    ) -> None:
        """
        Write a subsection header with separators (for titles not from config).

        Similar to _write_section_header but takes a direct title string.

        Args:
            content: list to append formatted lines to
            title: The title text to display
            separator_char: Character for separator lines (default "-")
            include_newline: Whether to include newline before separator (default True)

        Example usage:
            # OLD CODE:
            content.append("\n" + self.formatter.separator("-"))
            content.append(f"{test.name.upper()}")
            content.append(self.formatter.separator("-"))

            # NEW CODE:
            self._write_subsection_header(content, test.name.upper())
        """
        if include_newline:
            content.append('\n' + self.formatter.separator(separator_char))
        else:
            content.append(self.formatter.separator(separator_char))

        content.append(title)
        content.append(self.formatter.separator(separator_char))

    def _create_table(
        self,
        headers: dict[str, str],
        rows: list[dict[str, str | int | float]],
        column_specs: dict[str, dict[str, Any]],
        separator_char: str = '-',
    ) -> list[str]:
        """
        Create a formatted table with headers and rows.

        This consolidates the common table creation pattern that appears
        throughout the code.

        Args:
            headers: dictionary mapping column keys to header labels
            rows: list of dictionaries containing row data
            column_specs: dictionary mapping column keys to formatting specs:
                {
                    'column_key': {
                        'width': int,           # Column width for alignment
                        'format': str,          # 'currency', 'percent', 'integer', 'number', 'string'
                        'decimals': int,        # For number formatting (optional)
                        'truncate': int,        # Max length before truncation (optional)
                        'truncate_suffix': str  # Suffix when truncated (optional, default '...')
                    }
                }
            separator_char: Character for separator lines (default "-")

        Returns:
            list of formatted table lines (including header and separator)

        Example usage:
            # Define your table structure
            headers = {
                'test_name': 'Test Name',
                'p_value': 'Raw p-value',
                'q_value': 'FDR q-value',
                'significant': 'Significant'
            }

            column_specs = {
                'test_name': {'width': 35, 'format': 'string', 'truncate': 35},
                'p_value': {'width': 15, 'format': 'number', 'decimals': 4},
                'q_value': {'width': 15, 'format': 'number', 'decimals': 4},
                'significant': {'width': 12, 'format': 'string'}
            }

            # Prepare your row data
            rows = []
            for test in sorted_tests:
                rows.append({
                    'test_name': test.name,
                    'p_value': test.p_value,
                    'q_value': test.q_value if test.q_value is not None else 'N/A',
                    'significant': "✓ YES" if test.is_significant else "✗ NO"
                })

            # Generate the table
            table_lines = self._create_table(headers, rows, column_specs)
            content.extend(table_lines)
        """
        table_lines: list[str] = []

        # Build header line
        header_parts: list[str] = []
        for col_key in column_specs:
            width: int = column_specs[col_key]['width']
            header_label: str = headers.get(col_key, col_key)
            header_parts.append(f'{header_label:<{width}}')

        table_lines.append(' '.join(header_parts))
        table_lines.append(self.formatter.separator(separator_char))

        # Build data rows
        for row_data in rows:
            row_parts: list[str] = []
            for col_key, spec in column_specs.items():
                width = spec['width']
                format_type: str = spec.get('format', 'string')
                value: str | float | int = row_data.get(col_key, '')

                # Format the value based on type
                if isinstance(value, str) and self.formatter.is_missing_like(value):
                    logger.debug(
                        'Found N/A (%r) when building table for %r.',
                        value,
                        row_data.get('test_name', 'statistical test'),
                    )
                    formatted_value: str = 'N/A'
                elif not isinstance(value, str) and math.isnan(value):
                    logger.debug(
                        'Found NaN (%r) when building table for %r.',
                        value,
                        row_data.get('test_name', 'statistical test'),
                    )
                    formatted_value = 'N/A'
                elif format_type == 'currency':
                    formatted_value = self.formatter.format_currency(value)
                elif format_type == 'percent':
                    formatted_value = self.formatter.format_percent(value)
                elif format_type == 'integer':
                    formatted_value = self.formatter.format_integer(value)
                elif format_type == 'number':
                    decimals: int = spec.get('decimals', 2)
                    formatted_value = self.formatter.format_number(
                        value, decimals=decimals
                    )
                else:  # string
                    formatted_value = str(value)

                    # Handle truncation if specified
                    if 'truncate' in spec:
                        max_len: int = spec['truncate']
                        if len(formatted_value) > max_len:
                            suffix: str = spec.get('truncate_suffix', '...')
                            formatted_value = (
                                formatted_value[: max_len - len(suffix)] + suffix
                            )

                row_parts.append(f'{formatted_value:<{width}}')

            table_lines.append(' '.join(row_parts))

        # Bottom separator
        table_lines.append(self.formatter.separator(separator_char))

        return table_lines

    def _format_significance_marker(self, is_significant: bool) -> str:
        """
        Return formatted significance marker (✓ YES or ✗ NO).

        This consolidates the pattern:
            sig_marker = "✓ YES" if test.is_significant else "✗ NO"

        Args:
            is_significant: Boolean indicating significance

        Returns:
            Formatted marker string

        Example usage:
            # OLD CODE:
            sig_marker = "✓ YES" if test.is_significant else "✗ NO"

            # NEW CODE:
            sig_marker = self._format_significance_marker(test.is_significant)
        """
        return '✓ YES' if is_significant else '✗ NO'

    def _format_significance_text(self, is_significant: bool) -> str:
        """
        Return formatted significance text (SIGNIFICANT or NOT SIGNIFICANT).

        This consolidates the pattern:
            significance_result = 'SIGNIFICANT' if test.is_significant else 'NOT SIGNIFICANT'

        Args:
            is_significant: Boolean indicating significance

        Returns:
            Formatted text string

        Example usage:
            # OLD CODE:
            significance_result = 'SIGNIFICANT' if test.is_significant else 'NOT SIGNIFICANT'

            # NEW CODE:
            significance_result = self._format_significance_text(test.is_significant)
        """
        return 'SIGNIFICANT' if is_significant else 'NOT SIGNIFICANT'

    def _write_config_items(
        self,
        content: list[str],
        items: list[str],
        formatter_kwargs: dict[str, Any] | None = None,
        prefix: str = '',
    ) -> None:
        """
        Write a list of items from config with optional template formatting.

        This consolidates the extremely common pattern:
            for item_template in config.get('some.path.items', []):
                formatted_item = self.formatter.format_template(
                    item_template,
                    key1=value1,
                    key2=value2
                )
                content.append(formatted_item)

        Args:
            content: list to append formatted lines to
            items: Config items list
            formatter_kwargs: Optional dictionary of kwargs for format_template
            prefix: Optional prefix to add before each item (e.g., "  • ")

        Example usage:
            # OLD CODE (6 lines):
            for item_template in statistic_items:
                formatted_statistic = self.formatter.format_template(
                    item_template,
                    date_min=date_min,
                    total_entities=total_entities
                )
                content.append(formatted_statistic)

            # NEW CODE (1 line):
            self._write_config_items(
                content,
                'temporal_analysis.summary_statistics.items',
                formatter_kwargs={'date_min': date_min, 'total_entities': total_entities}
            )
        """
        formatter_kwargs = formatter_kwargs or {}

        for item_template in items:
            formatted_item: str = self.formatter.format_template(
                item_template, **formatter_kwargs
            )
            content.append(prefix + formatted_item)

    def _write_labeled_value(
        self,
        content: list[str],
        label: str,
        value: Any,
        format_type: str = 'string',
        decimals: int = 2,
        separator: str = ': ',
    ) -> None:
        """
        Write a labeled value line with appropriate formatting.

        This consolidates patterns like:
            content.append(f"{label}: {self.formatter.format_number(value)}")

        Args:
            content: list to append formatted lines to
            label: The label text
            value: The value to format
            format_type: Type of formatting ('string', 'number', 'integer', 'currency', 'percent')
            decimals: Number of decimal places for number formatting
            separator: Separator between label and value (default ": ")

        Example usage:
            # OLD CODE:
            content.append(f"Total records: {self.formatter.format_number(total_records)}")

            # NEW CODE:
            self._write_labeled_value(content, "Total records", total_records, format_type='number')
        """
        if format_type == 'currency':
            formatted_value: str = self.formatter.format_currency(value)
        elif format_type == 'percent':
            formatted_value = self.formatter.format_percent(value)
        elif format_type == 'integer':
            formatted_value = self.formatter.format_integer(value)
        elif format_type == 'number':
            formatted_value = self.formatter.format_number(value, decimals=decimals)
        else:  # string
            formatted_value = str(value)

        content.append(f'{label}{separator}{formatted_value}')

    def _write_statistics_block(
        self,
        content: list[str],
        title: str,
        stats: dict[str, tuple[Any, str]],
        indent: str = '   ',
    ) -> None:
        """
        Write a block of statistics with consistent formatting.

        This consolidates the pattern of writing multiple stat lines for
        target vs baseline comparisons.

        Args:
            content: list to append formatted lines to
            title: Block title (e.g., location name)
            stats: dictionary mapping stat labels to (value, format_type) tuples
                format_type can be: 'currency', 'percent', 'integer', 'number'
            indent: Indentation for stat lines (default "   ")

        Example usage:
            # OLD CODE (9 lines):
            content.append(f"   {self.target_location}:")
            content.append(f"      Mean:   {self.formatter.format_currency(test.target_avg)}")
            content.append(f"      Median: {self.formatter.format_currency(test.target_median)}")
            content.append(f"      IQR:    {self.formatter.format_currency(test.target_p25)} - "
                        f"{self.formatter.format_currency(test.target_p75)}")

            # NEW CODE (1 call):
            self._write_statistics_block(
                content,
                self.target_location,
                {
                    'Mean': (test.target_avg, 'currency'),
                    'Median': (test.target_median, 'currency'),
                    'IQR': (f"{self.formatter.format_currency(test.target_p25)} - "
                            f"{self.formatter.format_currency(test.target_p75)}", 'string')
                }
            )
        """
        content.append(f'{indent}{title}:')

        for stat_label, (value, format_type) in stats.items():
            if format_type == 'currency':
                formatted_value: str = self.formatter.format_currency(value)
            elif format_type == 'percent':
                formatted_value = self.formatter.format_percent(value)
            elif format_type == 'integer':
                formatted_value = self.formatter.format_integer(value)
            elif format_type == 'number':
                formatted_value = self.formatter.format_number(value)
            else:  # string - already formatted
                formatted_value = str(value)

            content.append(f'{indent}   {stat_label:<8}{formatted_value}')

    # ========================================================================
    # Report Writing Methods
    # ========================================================================

    def write_analysis_scope_details(
        self,
        target_location: str,
        num_other_branches: int,
        date_min: pd.Timestamp,
        date_max: pd.Timestamp,
        total_transactions: int,
    ) -> None:
        """Write the final analysis scope details."""
        content: list[str] = []
        content.append('\n' + self.formatter.separator('-'))
        content.append(self.template.get_section_title('analysis_scope'))
        content.append(self.formatter.separator('-'))

        # Get labels from config
        labels: AnalysisScopeFinalScopeLabels = (
            self.new_config.analysis_scope.final_scope_labels
        )

        # Format values using formatter
        num_branches_formatted: str = self.formatter.format_number(num_other_branches)
        date_range_formatted: str = (
            f'{date_min.strftime("%Y-%m-%d")} to {date_max.strftime("%Y-%m-%d")}'
        )
        total_trans_formatted: str = self.formatter.format_number(total_transactions)

        content.append(
            f'  • {labels.branches}: {target_location} vs. {num_branches_formatted} others'
        )
        content.append(f'  • {labels.date_range}: {date_range_formatted}')
        content.append(f'  • {labels.total_transactions}: {total_trans_formatted}')
        content.append(self.formatter.separator('-'))

        self.add_to_section(ReportSection.ANALYSIS_SCOPE, '\n'.join(content))

    def write_data_preparation_summary(
        self,
        initial_rows: int,
        final_rows: int,
        duplicates_removed: int,
        incomplete_records_removed: int = 0,
    ) -> None:
        """
        Write the data preparation summary section.

        This method reports on the data cleaning process, including the initial
        dataset size, any duplicates or incomplete records removed, and the final
        cleaned dataset size.

        Args:
            initial_rows: Number of records in the initial dataset
            final_rows: Number of records after cleaning
            duplicates_removed: Count of duplicate records removed
            incomplete_records_removed: Count of incomplete records removed (default 0)

        Responsibility:
            - Retrieve content templates from ConfigLoader
            - Delegate formatting to ReportFormatter
            - Organize the prepared content into the report section
        """
        content: list[str] = []

        # Create section header using formatter for separator
        self._write_section_header(content, 'data_preparation')

        # Get label templates from configuration
        labels: DataPreparationLabels = self.new_config.data_preparation.labels

        # Format and add initial records count
        initial_label: str = labels.initial_records
        initial_count_formatted: str = self.formatter.format_number(initial_rows)
        content.append(f'\n{initial_label}: {initial_count_formatted}')

        # Add duplicate removal details if any duplicates were found
        if duplicates_removed > 0:
            duplicates_template: str = (
                self.new_config.data_preparation.messages.duplicates_found
            )
            duplicates_message: str = self.formatter.format_template(
                duplicates_template,
                count=self.formatter.format_number(duplicates_removed),
                percentage=self.formatter.format_percent(
                    duplicates_removed / initial_rows
                ),
            )
            content.append(duplicates_message)

        # Add incomplete records removal details if any were found
        if incomplete_records_removed > 0:
            incomplete_template: str = (
                self.new_config.data_preparation.messages.incomplete_found
            )
            incomplete_message: str = self.formatter.format_template(
                incomplete_template,
                count=self.formatter.format_number(incomplete_records_removed),
                percentage=self.formatter.format_percent(
                    incomplete_records_removed / initial_rows
                ),
            )
            content.append(incomplete_message)

        # Format and add final records count
        final_label: str = labels.final_records
        final_count_formatted: str = self.formatter.format_number(final_rows)
        content.append(f'\n{final_label}: {final_count_formatted}')

        # Add the completed section to the report
        self.add_to_section(ReportSection.DATA_QUALITY, '\n'.join(content))

    def write_header(self, subtitle: str | None = None) -> None:
        """
        Write the report header section with title, metadata, and analysis information.

        The header includes:
        - Main title and subtitle
        - Report generation date
        - Analysis period being examined
        - Statistical confidence level being used

        Args:
            subtitle: Optional custom subtitle. If None, uses default from config

        Responsibility:
            - Retrieve header templates and labels from ConfigLoader
            - Delegate text centering and formatting to ReportFormatter
            - Organize header content in proper order
        """
        content: list[str] = []

        # Create top separator
        content.append('\n' + self.formatter.separator('='))

        # Get title content from configuration
        main_title: str = self.new_config.report_header.main_title
        default_subtitle: str = self.new_config.report_header.subtitle

        # Center and add titles using formatter
        content.append(self.formatter.center_text(main_title))
        content.append(self.formatter.center_text(subtitle or default_subtitle))
        content.append(self.formatter.separator('='))

        # Get metadata labels from configuration
        metadata_labels: ReportHeaderMetadataLabels = (
            self.new_config.report_header.metadata_labels
        )

        # Format confidence level as percentage
        confidence_level_percent = int(self.confidence_level * 100)

        # Add metadata lines
        report_date_label: str = metadata_labels.report_date
        content.append(f'{report_date_label}: {self.report_date}')

        analysis_period_label: str = metadata_labels.analysis_period
        content.append(f'{analysis_period_label}: {self.analysis_period}')

        confidence_level_label: str = metadata_labels.confidence_level
        content.append(f'{confidence_level_label}: {confidence_level_percent}%')

        # Close header with bottom separator
        content.append(self.formatter.separator('='))

        # Add the completed header to the report
        self.add_to_section(ReportSection.HEADER, '\n'.join(content))

    def write_data_split_summary(
        self,
        split_status: str,
        min_year: int | None = None,
        current_year: int | None = None,
        num_months_current_year: int | None = None,
    ) -> None:
        """
        Write a summary of the data scope and how it was split for analysis.

        This method describes which data was included in the analysis and how
        it was divided (e.g., single year vs. multi-year analysis).

        Args:
            split_status: Status identifier for the split scenario (e.g., 'single_year')
            min_year: Optional earliest year in the dataset
            current_year: Optional current/latest year in the dataset
            num_months_current_year: Optional number of months included from current year

        Responsibility:
            - Retrieve scenario descriptions from ConfigLoader
            - Delegate template formatting to ReportFormatter
            - Organize the scope information for the report
        """
        content: list[str] = []

        # Create section header
        self._write_section_header(content, 'analysis_scope')

        # Get the scenario-specific description from configuration
        scenario: AnalysisScopeScenariosItem = getattr(
            self.new_config.analysis_scope.scenarios, split_status
        )
        scenario_description: str = scenario.description

        # Format the description with provided variables if available
        if scenario_description:
            formatted_description: str = self.formatter.format_template(
                scenario_description,
                min_year=min_year,
                current_year=current_year,
                num_months_current_year=num_months_current_year,
            )
            content.append(formatted_description)

        # Add the completed section to the report
        self.add_to_section(ReportSection.ANALYSIS_SCOPE, '\n'.join(content))

    def write_methodology(self) -> None:
        """
        Write the statistical methodology section with legally defensible language.

        This orchestrator method coordinates the methodology section, which provides
        comprehensive documentation of all statistical methods used in the analysis.
        This section is critical for legal defensibility and technical transparency.

        The methodology covers:
        - Effect size measures (Risk Ratio, Odds Ratio, Risk Difference)
        - Statistical significance testing (p-values, confidence intervals)
        - Non-parametric tests (Mann-Whitney U, Cliff's Delta)
        - Independence tests (Chi-Square, Fisher's Exact, Cramér's V)
        - Multiple testing corrections (Benjamini-Hochberg procedure)
        - Statistical assumptions and limitations

        Responsibility:
            - Coordinate the flow of methodology sections
            - Calculate alpha threshold for significance
            - Delegate section writing to specialized helper methods
            - Assemble complete methodology documentation
        """
        content: list[str] = []

        # ====================================================================
        # Section Header and Introduction
        # ====================================================================
        content.append('\n' + self.formatter.separator('-'))
        content.append(self.template.get_section_title('statistical_methodology'))
        content.append(self.formatter.separator('-'))

        # Calculate alpha value for significance threshold (used in multiple sections)
        alpha: float = 1 - self.confidence_level

        # Introduction
        methodology_intro: str = self.new_config.statistical_methodology.introduction
        content.append(f'\n{methodology_intro}')

        # ====================================================================
        # Section 1: Effect Size Measures
        # ====================================================================
        self._write_methodology_effect_sizes(content)

        # ====================================================================
        # Section 2: Statistical Significance
        # ====================================================================
        self._write_methodology_significance(content, alpha)

        # ====================================================================
        # Section 3: Non-Parametric Tests
        # ====================================================================
        self._write_methodology_non_parametric(content)

        # ====================================================================
        # Section 4: Independence Tests
        # ====================================================================
        self._write_methodology_independence(content)

        # ====================================================================
        # Section 5: Multiple Testing Correction
        # ====================================================================
        self._write_methodology_multiple_testing(content, alpha)

        # ====================================================================
        # Section 6: Assumptions and Limitations
        # ====================================================================
        self._write_methodology_assumptions(content)

        # Add the completed methodology section to the report
        self.add_to_section(ReportSection.METHODOLOGY, '\n'.join(content))

    def _write_methodology_effect_sizes(self, content: list[str]) -> None:
        """
        Write effect size measures section.

        Documents all effect size measures used in the analysis including
        Risk Ratio, Odds Ratio, and Risk Difference with their interpretations.

        Args:
            content: list to append formatted lines to

        Responsibility:
            - Retrieve effect size configurations
            - Format each measure with description
            - Display interpretation guidelines
        """
        effect_sizes: StatisticalMethodologyEffectSizes = (
            self.new_config.statistical_methodology.effect_sizes
        )

        # Section header
        effect_sizes_header: str = effect_sizes.section_header
        content.append(f'\n{effect_sizes_header}')

        # Document each effect size measure
        for measure_name in ['risk_ratio', 'odds_ratio', 'risk_difference']:
            measure_data: StatisticalMethodologyEffectItem = getattr(
                effect_sizes, measure_name
            )

            # Format measure label
            measure_label: str = measure_data.label

            # Format description with location name substitution
            measure_description_template: str = measure_data.description
            measure_description: str = self.formatter.format_template(
                measure_description_template, target_location=self.target_location
            )

            content.append(f'   • {measure_label}: {measure_description}')

            # Add interpretation points
            interpretation_points: list[str] | None = measure_data.interpretation
            if interpretation_points:
                for interpretation_point in interpretation_points:
                    content.append(f'     - {interpretation_point}')

    def _write_methodology_significance(self, content: list[str], alpha: float) -> None:
        """
        Write statistical significance section.

        Documents p-values, confidence intervals, and significance thresholds
        used throughout the analysis.

        Args:
            content: list to append formatted lines to
            alpha: Significance threshold (e.g., 0.05 for 95% confidence)

        Responsibility:
            - Explain p-value interpretation
            - Document confidence interval methodology
            - Display significance threshold
        """
        significance: StatisticalMethodologySignificance = (
            self.new_config.statistical_methodology.significance
        )

        # Section header
        significance_header: str = significance.section_header
        content.append(f'\n{significance_header}')

        # ====================================================================
        # P-value Explanation
        # ====================================================================
        p_value_data: StatisticalMethodologySignificancePValue = significance.p_value
        p_value_label: str = p_value_data.label
        p_value_description: str = p_value_data.description

        content.append(f'   • {p_value_label}: {p_value_description}')

        # Add p-value interpretation points
        p_value_interpretation: list[str] = p_value_data.interpretation
        for interpretation_point in p_value_interpretation:
            content.append(f'     - {interpretation_point}')

        # Add note about significance threshold with formatted alpha
        p_value_note_template: str = p_value_data.note
        p_value_note: str = self.formatter.format_template(
            p_value_note_template,
            alpha=self.formatter.format_number(alpha, decimals=2),
            confidence_level=self.formatter.format_percent(
                self.confidence_level, decimals=0
            ),
        )
        content.append(f'   • {p_value_note}')

        # ====================================================================
        # Confidence Intervals Explanation
        # ====================================================================
        confidence_intervals: StatisticalMethodologySignificanceConfidenceIntervals = (
            significance.confidence_intervals
        )
        ci_label: str = confidence_intervals.label
        ci_description: str = confidence_intervals.description
        ci_interpretation: str = confidence_intervals.interpretation

        content.append(f'   • {ci_label}: {ci_description}')
        content.append(f'     - {ci_interpretation}')

    def _write_methodology_non_parametric(self, content: list[str]) -> None:
        """
        Write non-parametric tests section.

        Documents Mann-Whitney U test and Cliff's Delta effect size,
        which are used for cost distribution comparisons.

        Args:
            content: list to append formatted lines to

        Responsibility:
            - Explain Mann-Whitney U test
            - Explain Cliff's Delta effect size
            - Provide interpretation guidelines
        """
        non_parametric: StatisticalMethodologyNonParametricTests = (
            self.new_config.statistical_methodology.non_parametric_tests
        )

        # Section header
        non_parametric_header: str = non_parametric.section_header
        content.append(f'\n{non_parametric_header}')

        # Document each non-parametric test
        for test_name in ['mann_whitney_u', 'cliffs_delta']:
            test_data: StatisticalMethodologyNonParametricItem = getattr(
                non_parametric, test_name
            )
            test_label: str = test_data.label
            test_description: str = test_data.description

            content.append(f'   • {test_label}: {test_description}')

            # Add interpretation points
            test_interpretation: list[str] | None = test_data.interpretation
            if test_interpretation:
                for interpretation_point in test_interpretation:
                    content.append(f'     - {interpretation_point}')

    def _write_methodology_independence(self, content: list[str]) -> None:
        """
        Write independence tests section.

        Documents Chi-Square test, Fisher's Exact test, and Cramér's V,
        which are used for categorical data and rate comparisons.

        Args:
            content: list to append formatted lines to

        Responsibility:
            - Explain Chi-Square test
            - Explain Fisher's Exact test
            - Explain Cramér's V effect size
        """
        independence: StatisticalMethodologyIndependenceTests = (
            self.new_config.statistical_methodology.independence_tests
        )

        # Section header
        independence_header = independence.section_header
        content.append(f'\n{independence_header}')

        # Document each independence test
        for test_name in ['chi_square', 'fishers_exact', 'cramers_v']:
            test_data: StatisticalMethodologyNonParametricItem = getattr(
                independence, test_name
            )

            test_label: str = test_data.label
            test_description: str = test_data.description

            content.append(f'   • {test_label}: {test_description}')

    def _write_methodology_multiple_testing(
        self, content: list[str], alpha: float
    ) -> None:
        """
        Write multiple testing correction section.

        Documents the Benjamini-Hochberg procedure used to control
        the False Discovery Rate when performing multiple statistical tests.

        Args:
            content: list to append formatted lines to
            alpha: Significance threshold used in FDR correction

        Responsibility:
            - Explain Benjamini-Hochberg procedure
            - Document FDR control methodology
            - Display correction procedure with alpha
        """
        multiple_testing: StatisticalMethodologyMultipleTesting = (
            self.new_config.statistical_methodology.multiple_testing
        )

        # Section header
        multiple_testing_header: str = multiple_testing.section_header
        content.append(f'\n{multiple_testing_header}')

        # Benjamini-Hochberg procedure description
        bh_label: str = multiple_testing.label
        bh_description: str = multiple_testing.description

        content.append(f'   • {bh_label}: {bh_description}')

        # Add procedure details with formatted alpha value
        bh_procedure_template: str = multiple_testing.procedure
        bh_procedure: str = self.formatter.format_template(
            bh_procedure_template, alpha=self.formatter.format_number(alpha, decimals=2)
        )

        content.append(f'   • {bh_procedure}')

    def _write_methodology_assumptions(self, content: list[str]) -> None:
        """
        Write assumptions and limitations section.

        Documents important assumptions made in the statistical analysis
        and acknowledges methodological limitations.

        Args:
            content: list to append formatted lines to

        Responsibility:
            - Display all statistical assumptions
            - Document known limitations
            - Provide context for interpretation
        """
        assumptions_text: str = self.new_config.statistical_methodology.assumptions
        content.append(f'\n{assumptions_text}')

    def write_statistical_test(
        self, test: StatisticalTest, detailed: bool = True
    ) -> None:
        """
        Write formatted output for a statistical test result.

        This orchestrator method presents statistical test results in a standardized format
        appropriate for executive review and legal documentation.

        Args:
            test: StatisticalTest object containing all test results and metadata
            detailed: If True, include all statistical details (effect sizes, p-values, etc.)
                    If False, show only summary interpretation (default True)

        Responsibility:
            - Coordinate the flow of test result presentation
            - Determine test type (cost distribution vs. rate comparison)
            - Delegate section writing to specialized helper methods
            - Assemble complete test output
        """
        content: list[str] = []

        # ====================================================================
        # Section 1: Test Header
        # ====================================================================
        self._write_subsection_header(content, test.name.upper())

        # Determine test type for appropriate formatting
        is_cost_distribution_test: bool = (
            'cost' in test.name.lower() or 'distribution' in test.name.lower()
        )

        # ====================================================================
        # Section 2: Descriptive Statistics
        # ====================================================================
        if is_cost_distribution_test:
            self._write_cost_distribution_descriptive_stats(content, test)
        else:
            self._write_rate_comparison_descriptive_stats(content, test)

        # ====================================================================
        # Section 3: Detailed Statistical Results (Optional)
        # ====================================================================
        if detailed:
            self._write_test_detailed_results(content, test)

        content.append(self.formatter.separator('-'))

        # ====================================================================
        # Section 4: Executive Interpretation
        # ====================================================================
        if is_cost_distribution_test:
            self._write_cost_distribution_interpretation(content, test)
        else:
            self._write_rate_comparison_interpretation(content, test)

        content.append(self.formatter.separator('-'))

        # Add the completed test results to the report
        self.add_to_section(ReportSection.KEY_METRICS, '\n'.join(content))

    def _write_cost_distribution_descriptive_stats(
        self, content: list[str], test: StatisticalTest
    ) -> None:
        """
        Write descriptive statistics for cost distribution tests.

        Displays mean, median, IQR, and total costs for both target
        location and baseline locations.

        Args:
            content: list to append formatted lines to
            test: StatisticalTest object with cost distribution results

        Responsibility:
            - Format target location cost statistics
            - Format baseline location cost statistics
            - Calculate and display differences
        """
        if math.isnan(test.target_median):
            return  # Cannot display cost stats without median

        # ====================================================================
        # Target Location Statistics
        # ====================================================================
        content.append(f'   {self.target_location}:')
        content.append(
            f'      Mean:   {self.formatter.format_currency(test.target_avg)}'
        )
        content.append(
            f'      Median: {self.formatter.format_currency(test.target_median)}'
        )
        content.append(
            f'      IQR:    {self.formatter.format_currency(test.target_p25)} - '
            f'{self.formatter.format_currency(test.target_p75)}'
        )
        content.append(
            f'      Total:  {self.formatter.format_currency(test.target_total)}'
        )

        # ====================================================================
        # Baseline (Other Branches) Statistics
        # ====================================================================
        content.append('\n   Other Branches:')
        content.append(
            f'      Mean:   {self.formatter.format_currency(test.baseline_avg)}'
        )
        content.append(
            f'      Median: {self.formatter.format_currency(test.baseline_median)}'
        )
        content.append(
            f'      IQR:    {self.formatter.format_currency(test.baseline_p25)} - '
            f'{self.formatter.format_currency(test.baseline_p75)}'
        )
        content.append(
            f'      Total:  {self.formatter.format_currency(test.baseline_total)}'
        )

        # ====================================================================
        # Difference Calculations
        # ====================================================================
        content.append('\n   DIFFERENCE:')
        difference_sign: Literal['+'] | Literal[''] = (
            '+' if test.mean_difference and test.mean_difference > 0 else ''
        )

        content.append(
            f'      Mean Difference:   {difference_sign}'
            f'{self.formatter.format_currency(test.mean_difference)} '
            f'({difference_sign}{test.percent_difference:.1f}%)'
        )
        content.append(
            f'      Median Difference: {difference_sign}'
            f'{self.formatter.format_currency(test.median_difference)}'
        )

    def _write_rate_comparison_descriptive_stats(
        self, content: list[str], test: StatisticalTest
    ) -> None:
        """
        Write descriptive statistics for rate comparison tests.

        Displays counts and rates for both target location and
        baseline locations.

        Args:
            content: list to append formatted lines to
            test: StatisticalTest object with rate comparison results

        Responsibility:
            - Format target location rates (count/n = rate)
            - Format baseline location rates
        """
        if math.isnan(test.target_rate) or math.isnan(test.baseline_rate):
            return  # Cannot display rate stats without rates

        # ====================================================================
        # Target Location Rate
        # ====================================================================
        target_count_formatted: str = self.formatter.format_integer(test.target_count)
        target_n_formatted: str = self.formatter.format_integer(test.target_n)
        target_rate_formatted: str = self.formatter.format_percent(test.target_rate)

        content.append(
            f'   {self.target_location}:    '
            f'{target_count_formatted} / {target_n_formatted} = '
            f'{target_rate_formatted}'
        )

        # ====================================================================
        # Baseline (Other Branches) Rate
        # ====================================================================
        baseline_count_formatted: str = self.formatter.format_integer(
            test.baseline_count
        )
        baseline_n_formatted: str = self.formatter.format_integer(test.baseline_n)
        baseline_rate_formatted: str = self.formatter.format_percent(test.baseline_rate)

        content.append(
            f'   Other Branches:  '
            f'{baseline_count_formatted} / {baseline_n_formatted} = '
            f'{baseline_rate_formatted}'
        )

    def _write_test_detailed_results(
        self, content: list[str], test: StatisticalTest
    ) -> None:
        """
        Write detailed statistical results including effect sizes and test statistics.

        This section provides all technical statistical details including
        risk ratios, odds ratios, effect sizes, and significance tests.

        Args:
            content: list to append formatted lines to
            test: StatisticalTest object with detailed results

        Responsibility:
            - Display all effect sizes with confidence intervals
            - Display statistical test results (p-values, q-values)
            - Show final significance determination
        """
        # ====================================================================
        # Effect Sizes Section
        # ====================================================================
        content.append('\n   EFFECT SIZES:')

        # Risk Ratio with confidence interval
        if not math.isnan(test.risk_ratio) and test.risk_ratio_ci is not None:
            risk_ratio_ci_formatted: str = self.formatter.format_confidence_interval(
                test.risk_ratio_ci[0], test.risk_ratio_ci[1], decimals=2
            )
            content.append(
                f'   • Risk Ratio:      {test.risk_ratio:.2f}x {risk_ratio_ci_formatted}'
            )

        # Odds Ratio with confidence interval
        if not math.isnan(test.odds_ratio) and test.odds_ratio_ci is not None:
            odds_ratio_ci_formatted: str = self.formatter.format_confidence_interval(
                test.odds_ratio_ci[0], test.odds_ratio_ci[1], decimals=2
            )
            content.append(
                f'   • Odds Ratio:      {test.odds_ratio:.2f}x {odds_ratio_ci_formatted}'
            )

        # Generic effect size (e.g., Cliff's Delta)
        if not math.isnan(test.effect_size):
            effect_size_label: str = test.effect_size_name or 'Effect Size'
            content.append(
                f'   • {effect_size_label}:      '
                f'{self.formatter.format_number(test.effect_size, decimals=3)}'
            )

            # Add interpretation for Cliff's Delta specifically
            if effect_size_label == "Cliff's Delta":
                self._write_cliffs_delta_interpretation(content, test)

        # ====================================================================
        # Statistical Tests Section
        # ====================================================================
        content.append('\n   STATISTICAL TESTS:')
        content.append(
            f'   • Raw p-value:     {self.formatter.format_p_value(test.p_value)}'
        )

        if not math.isnan(test.q_value):
            q_value_formatted: str = self.formatter.format_number(
                test.q_value, decimals=4
            )
            content.append(f'   • q-value (BH/FDR):   {q_value_formatted}')

        significance_result: str = self._format_significance_text(test.is_significant)
        content.append(f'   • Final Result:   {significance_result}')

    def _write_cliffs_delta_interpretation(
        self, content: list[str], test: StatisticalTest
    ) -> None:
        """
        Write interpretation text for Cliff's Delta effect size.

        Provides human-readable interpretation of the Cliff's Delta
        magnitude and direction.

        Args:
            content: list to append formatted lines to
            test: StatisticalTest object with Cliff's Delta effect size

        Responsibility:
            - Categorize effect magnitude (negligible/small/medium/large)
            - Determine direction (higher/lower)
            - Format interpretation template
        """
        cliffs_delta_magnitude: str = self.formatter.interpret_cliffs_delta(
            test.effect_size
        )
        direction_text: Literal['higher'] | Literal['lower'] = (
            'higher' if test.effect_size and test.effect_size > 0 else 'lower'
        )

        # Get and format interpretation template
        interpretation_template: str = (
            self.new_config.test_interpretations.cliffs_delta.interpretation_format
        )

        interpretation_text: str = self.formatter.format_template(
            interpretation_template,
            magnitude=cliffs_delta_magnitude,
            target_location=self.target_location,
            direction=direction_text,
        )

        content.append(f'     {interpretation_text}')

    def _write_cost_distribution_interpretation(
        self, content: list[str], test: StatisticalTest
    ) -> None:
        """
        Write executive interpretation for cost distribution test.

        Provides high-level interpretation appropriate for executive
        and legal audiences, emphasizing practical significance.

        Args:
            content: list to append formatted lines to
            test: StatisticalTest object with cost distribution results

        Responsibility:
            - Retrieve appropriate interpretation template
            - Determine direction of cost difference
            - Format executive-level findings
        """
        # Get interpretation configuration
        interpretation: CompositeInterpType = self.template.get_interpretation(
            'cost_distribution', test.is_significant
        )

        if isinstance(interpretation, TestInterpretationsCostDistributionSignificant):
            # ====================================================================
            # Significant Cost Distribution Finding
            # ====================================================================
            interpretation_title: str = interpretation.title
            content.append(f'   {interpretation_title}')

            # Describe direction of difference
            direction_text: str = (
                ''
                if not test.effect_size
                else 'HIGHER'
                if test.effect_size > 0
                else 'LOWER'
            )
            direction_message_template: str = interpretation.direction_message
            direction_message: str = self.formatter.format_template(
                direction_message_template,
                target_location=self.target_location,
                direction=direction_text,
            )
            content.append(f'   {direction_message}')

            # Quantify the difference
            difference_message_template: str = interpretation.difference_message
            mean_diff: float | None = (
                abs(test.mean_difference) if test.mean_difference else None
            )
            difference_message: str = self.formatter.format_template(
                difference_message_template,
                mean_difference=self.formatter.format_currency(mean_diff),
            )
            content.append(f'   {difference_message}')

        elif isinstance(
            interpretation, TestInterpretationsCostDistributionNotSignificant
        ):
            # ====================================================================
            # Not Significant Cost Distribution
            # ====================================================================
            interpretation_title = interpretation.title
            interpretation_message: str = interpretation.message

            content.append(f'   {interpretation_title}')
            content.append(f'   {interpretation_message}')

    def _write_rate_comparison_interpretation(
        self, content: list[str], test: StatisticalTest
    ) -> None:
        """
        Write executive interpretation for rate comparison test.

        Provides high-level interpretation appropriate for executive
        and legal audiences, emphasizing risk ratios and practical implications.

        Args:
            content: list to append formatted lines to
            test: StatisticalTest object with rate comparison results

        Responsibility:
            - Retrieve appropriate interpretation template
            - Format risk ratio interpretation
            - Provide contextual information
        """
        # Get interpretation configuration
        interpretation: CompositeInterpType = self.template.get_interpretation(
            'rate_comparison', test.is_significant
        )

        if isinstance(interpretation, TestInterpretationsRateComparisonSignificant):
            # ====================================================================
            # Significant Rate Comparison Finding
            # ====================================================================
            interpretation_title: str = interpretation.title
            content.append(f'   {interpretation_title}')

            if test.risk_ratio and test.risk_ratio > 1:
                # Format main interpretation with risk ratio
                main_interpretation_template: str = interpretation.interpretation
                main_interpretation: str = self.formatter.format_template(
                    main_interpretation_template,
                    target_location=self.target_location,
                    risk_ratio=self.formatter.format_number(
                        test.risk_ratio, decimals=2
                    ),
                )

                # Add contextual information
                context_template: str = interpretation.context
                context_text: str = self.formatter.format_template(
                    context_template, test_name=test.name.lower()
                )

                content.append(f'   {main_interpretation}')
                content.append(f'   {context_text}')

        elif isinstance(
            interpretation, TestInterpretationsRateComparisonNotSignificant
        ):
            # ====================================================================
            # Not Significant Rate Comparison
            # ====================================================================
            interpretation_title = interpretation.title
            interpretation_message: str = interpretation.message

            content.append(f'   {interpretation_title}')
            content.append(f'   {interpretation_message}')

    def write_driver_table(
        self, drivers: list[DriverRiskProfile], table_title: str | None = None
    ) -> None:
        """
        Write a formatted table displaying driver risk profiles.

        This method creates a tabular display of driver risk information, including
        risk scores, transaction counts, and various behavioral metrics that indicate
        potential misuse or policy violations.

        Args:
            drivers: list of DriverRiskProfile objects containing driver metrics
            title: Optional custom table title. If None, uses default from config

        Responsibility:
            - Retrieve table structure and labels from ConfigLoader
            - Delegate all formatting to ReportFormatter
            - Organize driver data in a readable table format
        """
        content: list[str] = []

        # Get table title from config or use provided title
        if table_title is None:
            title: str = self.new_config.driver_analysis.table_title
        else:
            title = table_title

        # Create table header
        self._write_subsection_header(content, title)

        # 1. Define Headers
        # Get column headers from configuration
        config_headers: CompositeTableHeadersType = self.template.get_table_headers(
            'driver_analysis'
        )
        if isinstance(config_headers, DriverAnalysisTableHeaders):
            headers: dict[str, str] = {
                'driver': config_headers.driver,
                'risk_score': config_headers.risk_score,
                'transactions': config_headers.transactions,
                'no_eld_pct': config_headers.no_eld_pct,
                'non_diesel_pct': config_headers.non_diesel_pct,
                'after_hours_pct': config_headers.after_hours_pct,
                'avg_cost': config_headers.avg_cost,
            }

            # 2. Define Column Specifications
            # Widths are based on the old f-string padding
            column_specs: dict[str, dict[str, str | int]] = {
                'driver': {'width': 25, 'format': 'string', 'truncate': 25},
                'risk_score': {'width': 12, 'format': 'number', 'decimals': 1},
                'transactions': {'width': 15, 'format': 'number', 'decimals': 0},
                'no_eld_pct': {'width': 12, 'format': 'percent'},
                'non_diesel_pct': {'width': 15, 'format': 'percent'},
                'after_hours_pct': {'width': 15, 'format': 'percent'},
                'avg_cost': {'width': 12, 'format': 'currency'},
            }

            # 3. Prepare Row Data
            # Create a list of dictionaries, passing raw data.
            # _create_table will handle all formatting (percent, currency, etc.)
            rows_data: list[dict[str, Any]] = []
            for driver in drivers:
                rows_data.append(
                    {
                        'driver': driver.driver_name,
                        'risk_score': driver.risk_score,
                        'transactions': driver.transaction_count,
                        'no_eld_pct': driver.no_eld_rate,
                        'non_diesel_pct': driver.non_diesel_rate,
                        'after_hours_pct': driver.after_hours_rate,
                        'avg_cost': driver.avg_cost,
                    }
                )

            # 4. Generate Table
            # Delegate all table line creation to the helper method
            table_lines: list[str] = self._create_table(
                headers, rows_data, column_specs, separator_char='-'
            )
            content.extend(table_lines)

            # 5. Add the completed table to the report
            self.add_to_section(ReportSection.DRIVER_ANALYSIS, '\n'.join(content))

    def write_vehicle_table(
        self, vehicles: list[VehicleRiskProfile], table_title: str | None = None
    ) -> None:
        """
        Write a formatted table displaying vehicle risk profiles.

        This method creates a tabular display of vehicle risk information, including
        Vehicle Identification Numbers (VINs), primary drivers, risk scores, and
        behavioral metrics that may indicate unauthorized use or policy violations.

        Args:
            vehicles: list of VehicleRiskProfile objects containing vehicle metrics
            title: Optional custom table title. If None, uses default from config

        Responsibility:
            - Retrieve table structure and labels from ConfigLoader
            - Delegate all formatting to ReportFormatter
            - Organize vehicle data in a readable table format
        """
        content: list[str] = []

        # Get table title from config or use provided title
        if table_title is None:
            title: str = self.new_config.vehicle_analysis.table_title
        else:
            title = table_title

        # Create table header
        self._write_subsection_header(content, title)

        # 1. Define Headers
        # Get column headers from configuration
        config_headers: CompositeTableHeadersType = self.template.get_table_headers(
            'vehicle_analysis'
        )
        if isinstance(config_headers, VehicleAnalysisTableHeaders):
            headers: dict[str, str] = {
                'vehicle': config_headers.vehicle,
                'primary_driver': config_headers.primary_driver,
                'risk_score': config_headers.risk_score,
                'transactions': config_headers.transactions,
                'no_eld_pct': config_headers.no_eld_pct,
                'avg_cost': config_headers.avg_cost,
            }

            # 2. Define Column Specifications
            # Widths are based on the old f-string padding
            column_specs: dict[str, dict[str, str | int]] = {
                'vehicle': {'width': 25, 'format': 'string', 'truncate': 25},
                'primary_driver': {'width': 25, 'format': 'string', 'truncate': 25},
                'risk_score': {'width': 12, 'format': 'number', 'decimals': 1},
                'transactions': {'width': 15, 'format': 'number', 'decimals': 0},
                'no_eld_pct': {'width': 12, 'format': 'percent'},
                'avg_cost': {'width': 12, 'format': 'currency'},
            }

            # 3. Prepare Row Data
            # Create a list of dictionaries, passing raw data.
            rows_data: list[dict[str, Any]] = []
            for vehicle in vehicles:
                rows_data.append(
                    {
                        'vehicle': vehicle.vin,
                        'primary_driver': vehicle.primary_driver,
                        'risk_score': vehicle.risk_score,
                        'transactions': vehicle.transaction_count,
                        'no_eld_pct': vehicle.no_eld_rate,
                        'avg_cost': vehicle.avg_cost,
                    }
                )

            # 4. Generate Table
            # Delegate all table line creation to the helper method
            table_lines: list[str] = self._create_table(
                headers, rows_data, column_specs, separator_char='-'
            )
            content.extend(table_lines)

            # 5. Add the completed table to the report
            self.add_to_section(ReportSection.VEHICLE_ANALYSIS, '\n'.join(content))

    def write_focused_driver_profile(
        self,
        driver_profile: DriverRiskProfile,
        details: dict[str, int | float | pd.DataFrame],
    ) -> None:
        """
        Write a comprehensive, detailed analysis for a single high-risk driver.

        This "deep dive" section provides extensive information about a driver's
        behavior, transaction patterns, and risk indicators. It's typically used
        for drivers who exceed risk thresholds and require further investigation.

        The deep dive includes:
        - Overall risk assessment
        - Transaction summary (count, total cost, average cost, vehicles used)
        - Key risk indicators (no ELD usage, non-diesel purchases, after-hours activity)
        - Product purchase breakdown showing what was purchased
        - Multiple same-day fillup analysis (potential indicator of fraud)

        Args:
            driver_profile: DriverRiskProfile object containing aggregate driver metrics
            details: dictionary containing detailed analysis data including:
                    - unique_vehicles: Number of different vehicles used
                    - product_breakdown: DataFrame of products purchased
                    - multi_fillup_days: Number of days with multiple fillups
                    - max_fillups_one_day: Maximum fillups on a single day
                    - avg_cost_multi_fillup_days: Average cost on multi-fillup days

        Responsibility:
            - Retrieve section templates and structure from ConfigLoader
            - Delegate all formatting to ReportFormatter
            - Organize detailed driver information in a logical flow
        """
        driver_name: str = driver_profile.driver_name

        # Get deep dive configuration from YAML
        deep_dive_config: DriverAnalysisDeepDive = (
            self.new_config.driver_analysis.deep_dive
        )

        # Get section templates
        sections: DriverAnalysisDeepDiveSections = deep_dive_config.sections

        # Format title with driver name
        title_template: str = deep_dive_config.title
        title_formatted: str = self.formatter.format_template(
            title_template, driver_name=driver_name.upper()
        )

        # Create header for deep dive section
        content: list[str] = [
            '\n' + self.formatter.separator('='),
            title_formatted,
            self.formatter.separator('='),
        ]

        # ====================================================================
        # Risk Score Section
        # ====================================================================
        risk_score: float = driver_profile.risk_score
        risk_category: str = self.formatter.format_risk_level(risk_score)

        risk_score_template: str = sections.risk_score
        risk_score_text: str = self.formatter.format_template(
            risk_score_template, risk_score=risk_score, risk_category=risk_category
        )
        content.append(f'\n{risk_score_text}')

        # ====================================================================
        # Transaction Summary Section
        # ====================================================================
        transaction_summary_header: str = sections.transaction_summary
        content.append(f'\n{transaction_summary_header}')

        # Get transaction summary item templates from config
        transaction_items: list[str] = sections.transaction_items
        unique_trucks: int | float | str | pd.DataFrame = details.get(
            'unique_vehicles', 0
        )

        # Format each transaction summary item
        if isinstance(unique_trucks, int):
            for item_template in transaction_items:
                formatted_item = self.formatter.format_template(
                    item_template,
                    transaction_count=self.formatter.format_number(
                        driver_profile.transaction_count
                    ),
                    total_cost=self.formatter.format_currency(
                        driver_profile.total_cost
                    ),
                    avg_cost=self.formatter.format_currency(driver_profile.avg_cost),
                    unique_vehicles=self.formatter.format_number(unique_trucks),
                )
                content.append(formatted_item)

        # ====================================================================
        # Risk Indicators Section
        # ====================================================================
        risk_indicators_header: str = sections.risk_indicators
        content.append(f'\n{risk_indicators_header}')

        # Get risk indicator item templates from config
        risk_indicator_items: list[str] = sections.risk_items

        # Format each risk indicator item
        for item_template in risk_indicator_items:
            formatted_item: str = self.formatter.format_template(
                item_template,
                no_eld_rate=self.formatter.format_percent(driver_profile.no_eld_rate),
                non_diesel_rate=self.formatter.format_percent(
                    driver_profile.non_diesel_rate
                ),
                after_hours_rate=self.formatter.format_percent(
                    driver_profile.after_hours_rate
                ),
            )
            content.append(formatted_item)

        # ====================================================================
        # Product Breakdown Section
        # ====================================================================
        get_prod_breakdown: int | float | str | pd.DataFrame | None = details.get(
            'product_breakdown'
        )
        product_breakdown_data: pd.DataFrame = (
            get_prod_breakdown
            if isinstance(get_prod_breakdown, pd.DataFrame)
            else pd.DataFrame()
        )

        product_breakdown_header: str = sections.product_breakdown
        content.append(f'\n{product_breakdown_header}')

        # Get product item format template
        product_item_template: str = sections.product_item_format

        # Format top 5 products
        for product, row in product_breakdown_data.head(5).iterrows():
            formatted_product_item: str = self.formatter.format_template(
                product_item_template,
                product=str(product).title(),
                count=self.formatter.format_number(row['count']),
                percentage=self.formatter.format_percent(row['percentage']),
                total_cost=self.formatter.format_currency(row['total_cost']),
            )
            content.append(formatted_product_item)

        # ====================================================================
        # Multiple Same-Day Fillups Section
        # ====================================================================
        # Only show this section if driver has multiple fillup days
        get_multi_fillup_measure: int | float | str | pd.DataFrame = details.get(
            'multi_fillup_days', 0
        )
        if isinstance(get_multi_fillup_measure, int) and get_multi_fillup_measure > 0:
            multi_fillup_header: str = sections.multi_fillup
            content.append(f'\n{multi_fillup_header}')

            # Get multi-fillup item templates
            multi_fillup_items: list[str] = sections.multi_fillup_items
            single_day_fillups: int | float | pd.DataFrame = details[
                'max_fillups_one_day'
            ]
            avg_multi_fillup_cost: int | float | pd.DataFrame = details[
                'avg_cost_multi_fillup_days'
            ]

            # Format each multi-fillup item
            if isinstance(single_day_fillups, int) and isinstance(
                avg_multi_fillup_cost, float
            ):
                for item_template in multi_fillup_items:
                    formatted_item = self.formatter.format_template(
                        item_template,
                        multi_fillup_days=self.formatter.format_number(
                            get_multi_fillup_measure
                        ),
                        max_fillups_one_day=self.formatter.format_number(
                            single_day_fillups
                        ),
                        avg_cost_multi_fillup_days=self.formatter.format_currency(
                            avg_multi_fillup_cost
                        ),
                    )
                    content.append(formatted_item)

        # Add the completed deep dive section to the report
        self.add_to_section(ReportSection.DRIVER_ANALYSIS, '\n'.join(content))

    def write_data_quality_summary(
        self,
        quality_report: dict[
            str,
            int
            | dict[str, str]
            | dict[str, dict[str, int | float]]
            | dict[str, dict[str, int | float | tuple[float, float]]],
        ],
        duplicates_removed: int,
        total_records: int,
    ) -> None:
        """
        Write a comprehensive data quality assessment summary.

        This method reports on the overall quality of the dataset, identifying:
        - Successfully cleaned records
        - Duplicate records removed
        - Missing values in critical fields
        - Data validity issues (out-of-range values, invalid formats)
        - Statistical outliers that may indicate data entry errors

        The quality assessment helps establish the reliability of the forensic analysis
        and identifies any data limitations that should be considered.

        Args:
            quality_report: dictionary containing data quality metrics including:
                        - duplicates: Count of remaining duplicates
                        - missing_values: dict of columns with missing data
                        - validity_checks: dict of validation failures
                        - outliers: dict of columns with outlier values
            duplicates_removed: Number of duplicate records removed during cleaning
            total_records: Total number of records after cleaning

        Responsibility:
            - Retrieve quality assessment templates from ConfigLoader
            - Delegate all formatting to ReportFormatter
            - Organize quality metrics in a logical order
            - Provide an overall assessment of data quality
        """
        content: list[str] = []

        # Create section header
        self._write_section_header(content, 'data_quality')

        # Get label templates from configuration
        labels: DataQualityLabels = self.new_config.data_quality.labels

        # ====================================================================
        # Summary Statistics Section
        # ====================================================================
        total_records_label: str = labels.total_after_cleaning
        total_records_formatted: str = self.formatter.format_number(total_records)
        content.append(f'\n{total_records_label}: {total_records_formatted}')

        duplicates_removed_label: str = labels.duplicates_removed
        duplicates_removed_formatted: str = self.formatter.format_number(
            duplicates_removed
        )
        content.append(f'{duplicates_removed_label}: {duplicates_removed_formatted}')

        # Report any remaining duplicates (data quality issue)
        verified_remaining_duplicates_count: int = 0
        remaining_duplicates_count: (
            int
            | dict[str, str]
            | dict[str, dict[str, int | float]]
            | dict[str, dict[str, int | float | tuple[float, float]]]
        ) = quality_report.get('duplicates', 0)
        if (
            isinstance(remaining_duplicates_count, int)
            and remaining_duplicates_count > 0
        ):
            remaining_duplicates_template: str = labels.remaining_duplicates
            remaining_duplicates_message: str = self.formatter.format_template(
                remaining_duplicates_template,
                count=self.formatter.format_number(remaining_duplicates_count),
            )
            content.append(remaining_duplicates_message)
            verified_remaining_duplicates_count = remaining_duplicates_count

        # ====================================================================
        # Missing Values Section
        # ====================================================================
        missing_values_data: (
            int
            | dict[str, str]
            | dict[str, dict[str, int | float]]
            | dict[str, dict[str, int | float | tuple[float, float]]]
            | None
        ) = quality_report.get('missing_values')

        if missing_values_data and isinstance(missing_values_data, dict):
            # Get subsection headers from config
            subsections: DataQualitySubsections = (
                self.new_config.data_quality.subsections
            )
            missing_values_header: str = subsections.missing_values
            content.append(f'\n{missing_values_header}')

            # Helper to prevent type errors
            def retrieve_percentage(item: tuple[str, Any]) -> float:
                item_dict: Any = item[1]
                if isinstance(item_dict, dict):
                    if isinstance(item_dict['percentage'], float):
                        return item_dict['percentage']
                    else:
                        return 0.0
                else:
                    return 0.0

            # Sort by percentage of missing values (highest first)
            top_missing_columns: list[
                tuple[str, str]
                | tuple[str, dict[str, int | float]]
                | tuple[str, dict[str, int | float | tuple[float, float]]]
            ] = sorted(
                missing_values_data.items(), key=retrieve_percentage, reverse=True
            )

            # Get item template for missing values
            missing_value_item_template: str = (
                self.new_config.data_quality.messages.missing_value_item
            )

            # Format top 5 columns with missing values
            for column_name, missing_info in top_missing_columns[:5]:
                if isinstance(missing_info, dict):
                    count_missing: int | float | tuple[float, float] = missing_info[
                        'count'
                    ]
                    percentage_missing: int | float | tuple[float, float] = (
                        missing_info['percentage']
                    )
                    if isinstance(count_missing, float) and isinstance(
                        percentage_missing, float
                    ):
                        formatted_missing_item: str = self.formatter.format_template(
                            missing_value_item_template,
                            column=column_name,
                            count=self.formatter.format_number(count_missing),
                            percentage=self.formatter.format_percent(
                                percentage_missing
                            ),
                        )
                        content.append(formatted_missing_item)

        # ====================================================================
        # Data Validity Issues Section
        # ====================================================================
        validity_checks_data: (
            int
            | dict[str, str]
            | dict[str, dict[str, int | float]]
            | dict[str, dict[str, int | float | tuple[float, float]]]
            | None
        ) = quality_report.get('validity_checks')

        if validity_checks_data:
            # Get subsection header
            subsections: DataQualitySubsections = (
                self.new_config.data_quality.subsections
            )
            validity_issues_header: str = subsections.validity_issues
            content.append(f'\n{validity_issues_header}')

            # Get item template for validity issues
            validity_item_template: str = (
                self.new_config.data_quality.messages.validity_item
            )

            # Format each validity check that found issues
            if isinstance(validity_checks_data, dict):
                for check_key, check_info in validity_checks_data.items():
                    if isinstance(check_info, dict):
                        check_count: str | int | float | tuple[float, float] = (
                            check_info['count']
                        )
                        check_percentage: str | int | float | tuple[float, float] = (
                            check_info['percentage']
                        )
                        if isinstance(check_count, int) and isinstance(
                            check_percentage, float
                        ):
                            # Convert check key to human-readable name
                            check_name: str = self.formatter.format_display_name(
                                check_key
                            )

                            formatted_validity_item: str = (
                                self.formatter.format_template(
                                    validity_item_template,
                                    check_name=check_name,
                                    count=self.formatter.format_number(check_count),
                                    percentage=self.formatter.format_percent(
                                        check_percentage
                                    ),
                                )
                            )
                            content.append(formatted_validity_item)

        # ====================================================================
        # Outliers Section
        # ====================================================================
        outliers_data: Any | None = quality_report.get('outliers')

        if outliers_data:
            # Get subsection header
            subsections = self.new_config.data_quality.subsections
            outliers_header: str = subsections.outliers
            content.append(f'\n{outliers_header}')

            # Sort by count of outliers (highest first)
            top_outlier_columns: list[
                tuple[str, dict[str, int | float | tuple[float, float]]]
            ] = sorted(
                outliers_data.items(), key=lambda item: item[1]['count'], reverse=True
            )

            # Get item templates
            outlier_item_template: str = (
                self.new_config.data_quality.messages.outlier_item
            )
            outlier_bounds_template: str = (
                self.new_config.data_quality.messages.outlier_bounds
            )

            # Format top 5 columns with outliers
            for column_name, outlier_info in top_outlier_columns[:5]:
                # Format bounds if available
                bounds_text: str = ''
                if 'bounds' in outlier_info and isinstance(
                    outlier_info['bounds'], tuple
                ):
                    lower_bound: float
                    upper_bound: float
                    lower_bound, upper_bound = outlier_info['bounds']
                    bounds_text = self.formatter.format_template(
                        outlier_bounds_template,
                        lower=self.formatter.format_number(lower_bound, decimals=2),
                        upper=self.formatter.format_number(upper_bound, decimals=2),
                    )

                # Format the outlier item
                outlier_count: int | float | tuple[float, float] = outlier_info['count']
                outlier_percentage: int | float | tuple[float, float] = outlier_info[
                    'percentage'
                ]
                if isinstance(outlier_count, int) and isinstance(
                    outlier_percentage, float
                ):
                    formatted_outlier_item: str = self.formatter.format_template(
                        outlier_item_template,
                        column=column_name,
                        count=self.formatter.format_number(outlier_count),
                        percentage=self.formatter.format_percent(outlier_percentage),
                        bounds=bounds_text,
                    )
                    content.append(formatted_outlier_item)

        # ====================================================================
        # Overall Assessment Section
        # ====================================================================
        content.append('\n' + self.formatter.separator('-'))

        # Count total issues to determine assessment level
        if isinstance(validity_checks_data, dict):
            validity_checks_count: int = len(validity_checks_data)
        else:
            validity_checks_count = 0
        total_issues: int = validity_checks_count + (
            1 if verified_remaining_duplicates_count > 0 else 0
        )

        # Get assessment messages from config
        assessments: DataQualityAssessments = self.new_config.data_quality.assessments

        # Get quality thresholds from config
        quality_thresholds: ConfigurationDataQuality = (
            self.new_config.configuration.data_quality
        )
        minor_issues_threshold: int = quality_thresholds.minor_issues_threshold

        # Determine and display appropriate assessment
        if total_issues == 0:
            assessment_message: str = assessments.excellent
            content.append(assessment_message)
        elif total_issues <= minor_issues_threshold:
            assessment_message = assessments.minor_issues
            content.append(assessment_message)
        else:
            assessment_message = assessments.multiple_issues
            content.append(assessment_message)

        content.append(self.formatter.separator('-'))

        # Add the completed quality assessment to the report
        self.add_to_section(ReportSection.DATA_QUALITY, '\n'.join(content))

    def write_multiple_testing_correction(
        self, corrected_p_values: dict[str, tuple[float, bool, float]]
    ) -> None:
        """
        Write the multiple testing correction results section.

        When performing multiple statistical tests simultaneously, the probability of
        finding at least one false positive increases. This section reports the results
        of the Benjamini-Hochberg procedure, which controls the False Discovery Rate (FDR)
        to maintain the integrity of our statistical conclusions.

        For each test, this shows:
        - Original (raw) p-value
        - Adjusted q-value (corrected for multiple comparisons)
        - Whether the test remains significant after correction

        Args:
            corrected_p_values: dictionary mapping test names to tuples of:
                            (raw_p_value, is_significant, q_value)

        Responsibility:
            - Retrieve correction methodology text from ConfigLoader
            - Delegate all formatting to ReportFormatter
            - Present correction results in a clear tabular format
        """
        content: list[str] = []
        mtc_config: MultipleTestingCorrection = (
            self.new_config.multiple_testing_correction
        )

        # Create section header
        self._write_section_header(content, literal_text=mtc_config.section_title)

        # Calculate alpha threshold for significance
        alpha: float = self.formatter.get_alpha(self.confidence_level)

        # Get and format introduction explaining the correction procedure
        introduction_template: str = mtc_config.introduction
        introduction_text: str = self.formatter.format_template(
            introduction_template, alpha=alpha
        )
        content.append(f'\n{introduction_text}')

        # ====================================================================
        # Correction Results Table
        # ====================================================================

        # 1. Get column headers from configuration
        config_headers: CompositeTableHeadersType = self.template.get_table_headers(
            'multiple_testing_correction'
        )
        if isinstance(config_headers, MultipleTestingCorrectionTableHeaders):
            headers: dict[str, str] = {
                'test_name': config_headers.test_name,
                'raw_p_value': config_headers.raw_p_value,
                'q_value': config_headers.q_value,
                'significant': config_headers.significant,
            }

            # 2. Define column specifications
            column_specs: dict[str, dict[str, int | str]] = {
                'test_name': {'width': 25, 'format': 'string'},
                'raw_p_value': {'width': 15, 'format': 'number', 'decimals': 4},
                'q_value': {'width': 15, 'format': 'number', 'decimals': 4},
                'significant': {'width': 15, 'format': 'string'},
            }

            # 3. Get significance markers from configuration
            markers: MultipleTestingCorrectionSignificanceMarkers = (
                mtc_config.significance_markers
            )
            yes_marker: str = markers.yes_marker
            no_marker: str = markers.no_marker

            # 4. Prepare row data
            rows_data: list[dict[str, str | float]] = []
            for test_name, (
                raw_p_value,
                is_significant,
                q_value,
            ) in corrected_p_values.items():
                rows_data.append(
                    {
                        'test_name': test_name,
                        'raw_p_value': raw_p_value,
                        'q_value': q_value,
                        'significant': yes_marker if is_significant else no_marker,
                    }
                )

            # 5. Generate and append table
            content.append('')  # Blank line before table
            table_lines: list[str] = self._create_table(
                headers, rows_data, column_specs
            )
            content.extend(table_lines)

            # Add the completed correction results to the report
            self.add_to_section(
                ReportSection.MULTIPLE_TESTING_CORRECTION, '\n'.join(content)
            )

    def write_financial_impact(
        self,
        target_total: float | None,
        baseline_total: float | None,
        target_avg: float | None,
        baseline_avg: float | None,
        exposure_estimate: dict[str, Any] | None = None,
    ) -> None:
        """
        Write the financial impact analysis section.

        This critical section quantifies the financial implications of the forensic findings,
        providing executives and stakeholders with concrete dollar amounts for decision-making.

        The financial impact analysis includes:
        - Total spending comparison between target location and baseline
        - Per-transaction cost metrics showing average spending patterns
        - Potential financial exposure from unverified or suspicious transactions
        - Confidence intervals for exposure estimates (when available)

        This information is essential for:
        - Assessing the materiality of findings
        - Prioritizing investigation resources
        - Justifying policy changes or corrective actions
        - Supporting legal or disciplinary proceedings

        Args:
            target_total: Total spending at the target location
            baseline_total: Total spending at all other (baseline) locations
            target_avg: Average cost per transaction at target location
            baseline_avg: Average cost per transaction at baseline locations
            exposure_estimate: Optional dictionary containing potential financial exposure data:
                            - excess_count: Number of suspicious transactions
                            - avg_cost: Average cost of suspicious transactions
                            - total_exposure: Total estimated financial exposure
                            - confidence_interval: Optional (lower, upper) bounds

        Responsibility:
            - Retrieve financial impact templates from ConfigLoader
            - Delegate all formatting to ReportFormatter
            - Present financial data in executive-friendly format
            - Calculate and display proportions and differences
        """
        content: list[str] = []

        # Create section header
        self._write_section_header(content, 'financial_impact')

        # Get section structure from configuration
        subsections: FinancialImpactSubsections = (
            self.new_config.financial_impact.subsections
        )
        labels: FinancialImpactLabels = self.new_config.financial_impact.labels

        # ====================================================================
        # Total Spend Section
        # ====================================================================
        total_spend_header: str = subsections.total_spend
        content.append(f'\n{total_spend_header}')

        if target_total and baseline_total:
            # Calculate total combined spending for percentage calculations
            total_combined: float = target_total + baseline_total

            # Format target location total with percentage of overall spend
            target_total_label_template: str = labels.target_total
            target_total_label: str = self.formatter.format_template(
                target_total_label_template, target_location=self.target_location
            )
            target_total_formatted: str = self.formatter.format_currency(target_total)
            target_total_percentage: str = self.formatter.format_percent(
                target_total / total_combined
            )
            content.append(
                f'   {target_total_label}:    {target_total_formatted} '
                f'({target_total_percentage} of total)'
            )

            # Format baseline (other branches) total with percentage
            baseline_total_label: str = labels.baseline_total
            baseline_total_formatted: str = self.formatter.format_currency(
                baseline_total
            )
            baseline_total_percentage: str = self.formatter.format_percent(
                baseline_total / total_combined
            )
            content.append(
                f'   {baseline_total_label}:  {baseline_total_formatted} '
                f'({baseline_total_percentage} of total)'
            )

        # ====================================================================
        # Per-Transaction Metrics Section
        # ====================================================================
        per_transaction_header: str = subsections.per_transaction
        content.append(f'\n{per_transaction_header}')

        # Format target location average cost
        target_mean_label_template: str = labels.target_mean
        target_mean_label: str = self.formatter.format_template(
            target_mean_label_template, target_location=self.target_location
        )
        target_avg_formatted: str = self.formatter.format_currency(target_avg)
        content.append(f'   {target_mean_label}:    Mean = {target_avg_formatted}')

        # Format baseline average cost
        baseline_mean_label: str = labels.baseline_mean
        baseline_avg_formatted: str = self.formatter.format_currency(baseline_avg)
        content.append(f'   {baseline_mean_label}:  Mean = {baseline_avg_formatted}')

        if target_avg and baseline_avg:
            # Calculate and format the mean difference
            mean_difference: float = target_avg - baseline_avg
            mean_difference_label: str = labels.mean_difference
            mean_difference_formatted: str = self.formatter.format_currency(
                mean_difference
            )
            content.append(f'   {mean_difference_label}: {mean_difference_formatted}')

        # ====================================================================
        # Potential Financial Exposure Section (Optional)
        # ====================================================================
        # Only include this section if exposure estimate data is provided
        if exposure_estimate:
            exposure_header: str = subsections.exposure
            content.append(f'\n{exposure_header}')

            # Get exposure item templates from configuration
            exposure_items: list[str] = self.new_config.financial_impact.exposure_items

            # Format each exposure item
            for item_template in exposure_items:
                # Check if this item requires confidence interval data
                requires_confidence_interval: bool = (
                    '{ci_low}' in item_template or '{ci_high}' in item_template
                )
                has_confidence_interval: bool = (
                    'confidence_interval' in exposure_estimate
                )

                # Skip confidence interval items if CI data not available
                if requires_confidence_interval and not has_confidence_interval:
                    continue

                # Format the exposure item with available data
                formatted_exposure_item: str = self.formatter.format_template(
                    item_template,
                    excess_count=self.formatter.format_number(
                        exposure_estimate['excess_count']
                    ),
                    avg_cost=self.formatter.format_currency(
                        exposure_estimate['avg_cost']
                    ),
                    total_exposure=self.formatter.format_currency(
                        exposure_estimate['total_exposure']
                    ),
                    ci_low=self.formatter.format_currency(
                        exposure_estimate.get('confidence_interval', (0, 0))[0]
                    ),
                    ci_high=self.formatter.format_currency(
                        exposure_estimate.get('confidence_interval', (0, 0))[1]
                    ),
                )
                content.append(f'   {formatted_exposure_item}')

            # Add disclaimer note about exposure estimates
            exposure_note: str = self.new_config.financial_impact.exposure_note
            if exposure_note:
                content.append(f'   {exposure_note}')

        # Add the completed financial impact section to the report
        self.add_to_section(ReportSection.FINANCIAL_IMPACT, '\n'.join(content))

    def write_temporal_analysis(
        self,
        temporal_profiles: list['TemporalRiskProfile'],
        summary_stats: dict[str, Any],
        timeline_data: pd.DataFrame | None = None,
        comparative_stats: dict[str, Any] | None = None,
        date_min: pd.Timestamp | None = None,
        date_max: pd.Timestamp | None = None,
        top_n: int = 10,
    ) -> None:
        """
        Write comprehensive temporal analysis report with fraud emergence detection.

        This is the main orchestrator method that coordinates all temporal analysis sections.
        It delegates each major section to specialized helper methods for better maintainability.

        The temporal analysis includes:
        - Trend detection and change point identification
        - Month-over-month volatility analysis
        - Fraud pattern recognition and signatures
        - Current risk factors assessment
        - Statistical correlation analysis
        - Rolling window anomaly detection
        - Investigation prioritization guidance

        Args:
            temporal_profiles: list of TemporalRiskProfile objects sorted by risk score
            summary_stats: dictionary containing aggregate summary statistics
            timeline_data: Optional DataFrame with change point timeline data
            comparative_stats: Optional dictionary comparing target to baseline locations
            date_min: Start date of analysis period
            date_max: End date of analysis period
            top_n: Number of top high-risk entities to display in detail (default 10)

        Responsibility:
            - Coordinate the flow of temporal analysis sections
            - Delegate section writing to specialized helper methods
            - Handle early return for insufficient data
            - Assemble all sections into cohesive report
        """
        content: list[str] = []

        # ====================================================================
        # Section 1: Header and Introduction
        # ====================================================================
        self._write_section_header(content, 'temporal_analysis')

        self._write_temporal_introduction(content)

        # ====================================================================
        # Section 2: Metric Definitions
        # ====================================================================
        self._write_temporal_metric_definitions(content)

        # ====================================================================
        # Section 3: Check for Insufficient Data (Early Return)
        # ====================================================================
        if len(temporal_profiles) == 0:
            self._write_temporal_insufficient_data(content)
            self.add_to_section(ReportSection.TEMPORAL_ANALYSIS, '\n'.join(content))
            return  # Early exit - no data to analyze

        # ====================================================================
        # Section 4: Summary Statistics
        # ====================================================================
        self._write_temporal_summary_statistics(
            content, temporal_profiles, summary_stats, date_min, date_max
        )

        # ====================================================================
        # Section 5: Top High-Risk Entities (Detailed Analysis)
        # ====================================================================
        self._write_temporal_top_entities(content, temporal_profiles, top_n)

        # ====================================================================
        # Section 6: Fraud Pattern Summary (Branch-Wide)
        # ====================================================================
        self._write_temporal_fraud_pattern_summary(content, temporal_profiles)

        # ====================================================================
        # Section 7: Risk Distribution by Entity Type
        # ====================================================================
        self._write_temporal_risk_distribution(
            content, temporal_profiles, summary_stats
        )

        # ====================================================================
        # Section 8: Fraud Emergence Timeline
        # ====================================================================
        self._write_temporal_fraud_timeline(content, timeline_data)

        # ====================================================================
        # Section 9: Comparative Statistics (Optional)
        # ====================================================================
        if comparative_stats:
            self._write_temporal_comparative_statistics(content, comparative_stats)

        # ====================================================================
        # Section 10: Interpretation Guide for Investigators
        # ====================================================================
        self._write_temporal_interpretation_guide(content)

        # ====================================================================
        # Section 11: Caveats and Limitations
        # ====================================================================
        self._write_temporal_caveats(content)

        # Final separator
        content.append('\n' + self.formatter.separator('='))

        # Add the completed temporal analysis to the report
        self.add_to_section(ReportSection.TEMPORAL_ANALYSIS, '\n'.join(content))

    def _write_temporal_introduction(self, content: list[str]) -> None:
        """
        Write the temporal analysis introduction paragraphs.

        Args:
            content: list to append formatted lines to

        Responsibility:
            - Retrieve introduction paragraphs from ConfigLoader
            - Format with target location name
            - Append to content list
        """
        introduction_paragraphs: list[str] = (
            self.new_config.temporal_analysis.introduction.paragraphs
        )

        for paragraph in introduction_paragraphs:
            formatted_paragraph: str = self.formatter.format_template(
                paragraph, target_location=self.target_location
            )
            content.append(f'{formatted_paragraph}')

    def _write_temporal_metric_definitions(self, content: list[str]) -> None:
        """
        Write the metric definitions section explaining all temporal metrics and analysis methods.

        This section provides investigators with clear definitions of:
        - Basic temporal metrics (transaction rates, cost metrics, behavioral flags)
        - Analysis methods (change point detection, trend analysis, fraud patterns)
        - Period comparison methodology

        Args:
            content: list to append formatted lines to

        Responsibility:
            - Retrieve metric and analysis definitions from ConfigLoader
            - Format definitions with proper structure
            - Append to content list
        """
        # Section header
        content.append('\n' + self.formatter.separator('-'))
        content.append(
            self.new_config.temporal_analysis.metric_definitions.section_title
        )
        content.append(self.formatter.separator('-'))

        # ====================================================================
        # Basic Metric Definitions
        # ====================================================================
        metrics: TemporalAnalysisMetricDefinitionsMetrics = (
            self.new_config.temporal_analysis.metric_definitions.metrics
        )

        for _, metric_data in metrics:
            label: str = metric_data.label
            definition: str = metric_data.definition
            risk_explanation: str | None = metric_data.risk
            note: str | None = metric_data.note

            content.append(f'  • {label}: {definition}')

            if risk_explanation:
                content.append(f'    {risk_explanation}')

            if note:
                content.append(f'    {note}')

        # ====================================================================
        # Analysis Types/Methods
        # ====================================================================
        analysis_types: TemporalAnalysisMetricDefinitionsAnalysisTypes = (
            self.new_config.temporal_analysis.metric_definitions.analysis_types
        )

        if analysis_types:
            analysis_title: str = analysis_types.title
            content.append(f'\n{analysis_title}')

            for analysis_key, analysis_data in analysis_types:
                # Skip the title key
                if analysis_key == 'title':
                    continue

                label: str = analysis_data.label
                description: str = analysis_data.description
                note = analysis_data.note

                if label:
                    content.append(f'\n  {label}:')

                if description:
                    content.append(f'    {description}')

                if note:
                    content.append(f'    {note}')

                # Handle special structures like thresholds
                if 'thresholds' in analysis_data:
                    for threshold in analysis_data['thresholds']:
                        content.append(f'      {threshold}')

                # Handle pattern dictionaries
                if 'patterns' in analysis_data and analysis_data.patterns is not None:
                    for (
                        pattern_name,
                        pattern_description,
                    ) in analysis_data.patterns.items():
                        display_name: str = self.formatter.format_display_name(
                            pattern_name
                        )
                        content.append(f'      • {display_name}: {pattern_description}')

        # ====================================================================
        # Period Comparison Explanation
        # ====================================================================
        period_comparison: TemporalAnalysisMetricDefinitionsPeriodComparison = (
            self.new_config.temporal_analysis.metric_definitions.period_comparison
        )

        if period_comparison:
            comparison_title: str = period_comparison.title
            content.append(f'\n{comparison_title}')

            for item in period_comparison.items:
                content.append(f'  {item}')

    def _write_temporal_insufficient_data(self, content: list[str]) -> None:
        """
        Write warning message when temporal data is insufficient for analysis.

        This occurs when there aren't enough transactions or time periods to
        perform meaningful temporal analysis. The method explains minimum
        requirements and provides recommendations.

        Args:
            content: list to append formatted lines to

        Responsibility:
            - Retrieve insufficient data messages from ConfigLoader
            - Format with minimum requirement values
            - Append warning to content list
        """
        content.append('\n' + self.formatter.separator('-'))

        # Get insufficient data configuration
        insufficient_data_config: TemporalAnalysisInsufficientData = (
            self.new_config.temporal_analysis.insufficient_data
        )

        # Get minimum thresholds from configuration
        minimum_transactions: int = (
            self.new_config.configuration.temporal.minimum_transactions
        )
        minimum_months: int = self.new_config.configuration.temporal.minimum_months

        # Warning message
        warning_message: str = insufficient_data_config.warning
        content.append(warning_message)

        # Details about requirements
        details_template: str = insufficient_data_config.details
        details_message: str = self.formatter.format_template(
            details_template,
            min_transactions=minimum_transactions,
            min_months=minimum_months,
        )
        content.append(details_message)

        # Recommendation
        recommendation: str = insufficient_data_config.recommendation
        if recommendation:
            content.append(recommendation)

        content.append(self.formatter.separator('-'))

    def _write_temporal_summary_statistics(
        self,
        content: list[str],
        temporal_profiles: list['TemporalRiskProfile'],
        summary_stats: dict[str, Any],
        date_min: pd.Timestamp | None,
        date_max: pd.Timestamp | None,
    ) -> None:
        """
        Write enhanced temporal summary statistics section.

        This section provides high-level overview of temporal analysis results,
        including entity counts, risk distributions, and detection rates for
        various risk indicators.

        Args:
            content: list to append formatted lines to
            temporal_profiles: All temporal risk profiles
            summary_stats: dictionary of summary statistics
            date_min: Analysis start date
            date_max: Analysis end date

        Responsibility:
            - Calculate additional statistics from profiles
            - Retrieve stat templates from ConfigLoader
            - Format all statistics using ReportFormatter
            - Append to content list
        """
        content.append('\n' + self.formatter.separator('-'))
        temporal_summary_stats: dict[str, list[str] | str] = (
            self.new_config.temporal_analysis.summary_statistics
        )
        temporal_summary_stats_title: list[str] | str | None = (
            temporal_summary_stats.get('title')
        )
        display_title: str
        if isinstance(temporal_summary_stats_title, str):
            display_title = temporal_summary_stats_title
        else:
            display_title = 'TEMPORAL SUMMARY STATISTICS:'
        content.append(display_title)
        content.append(self.formatter.separator('-'))

        # ====================================================================
        # Calculate Enhanced Statistics
        # ====================================================================
        total_entities: int = len(temporal_profiles)

        # Critical risk entities (risk score >= 75)
        critical_count: int = sum(
            1 for p in temporal_profiles if p.risk_score >= CRITICAL_RISK_SCORE
        )
        critical_percentage: float = (
            critical_count / total_entities if total_entities else 0.0
        )

        # Entities with fraud patterns
        entities_with_fraud_patterns: int = sum(
            1 for p in temporal_profiles if p.has_fraud_patterns()
        )
        fraud_patterns_percentage: float = (
            entities_with_fraud_patterns / total_entities if total_entities else 0.0
        )

        # Entities with current (recent) risks
        entities_with_current_risks: int = sum(
            1 for p in temporal_profiles if p.has_current_risks()
        )
        current_risks_percentage: float = (
            entities_with_current_risks / total_entities if total_entities else 0.0
        )

        # ====================================================================
        # Format and Display Statistics
        # ====================================================================
        statistic_items: list[str] | str | None = temporal_summary_stats.get('items')

        if isinstance(statistic_items, list):
            for item_template in statistic_items:
                formatted_statistic: str = self.formatter.format_template(
                    item_template,
                    date_min=date_min.strftime('%Y-%m-%d') if date_min else 'N/A',
                    date_max=date_max.strftime('%Y-%m-%d') if date_max else 'N/A',
                    total_entities=self.formatter.format_number(
                        summary_stats['total_entities']
                    ),
                    critical_count=self.formatter.format_number(critical_count),
                    critical_pct=self.formatter.format_percent(critical_percentage),
                    high_risk_count=self.formatter.format_number(
                        summary_stats['high_risk_count']
                    ),
                    high_risk_pct=self.formatter.format_percent(
                        summary_stats['high_risk_pct']
                    ),
                    with_change_points=self.formatter.format_number(
                        summary_stats['with_change_points']
                    ),
                    with_change_points_pct=self.formatter.format_percent(
                        summary_stats['with_change_points_pct']
                    ),
                    with_trends=self.formatter.format_number(
                        summary_stats['with_trends']
                    ),
                    with_trends_pct=self.formatter.format_percent(
                        summary_stats['with_trends_pct']
                    ),
                    with_fraud_patterns=self.formatter.format_number(
                        entities_with_fraud_patterns
                    ),
                    with_fraud_patterns_pct=self.formatter.format_percent(
                        fraud_patterns_percentage
                    ),
                    with_current_risks=self.formatter.format_number(
                        entities_with_current_risks
                    ),
                    with_current_risks_pct=self.formatter.format_percent(
                        current_risks_percentage
                    ),
                )
                content.append(formatted_statistic)

    def _write_temporal_interpretation_guide(self, content: list[str]) -> None:
        """
        Write the interpretation guide for investigators.

        This guide helps investigators prioritize their review by explaining
        which indicators are highest confidence, which are moderate, and
        which are lower priority.

        Args:
            content: list to append formatted lines to

        Responsibility:
            - Retrieve guide structure from ConfigLoader
            - Format guide sections
            - Append to content list
        """
        content.append('\n' + self.formatter.separator('='))

        guide_config: TemporalAnalysisInterpretationGuide = (
            self.new_config.temporal_analysis.interpretation_guide
        )
        guide_title: str = guide_config.title
        content.append(guide_title)
        content.append(self.formatter.separator('='))

        # ====================================================================
        # High Confidence Indicators
        # ====================================================================
        high_confidence: TemporalAnalysisInterpretationGuideGroup = (
            guide_config.high_confidence
        )
        high_confidence_title: str = high_confidence.title
        content.append(f'\n{high_confidence_title}')

        for item in high_confidence.items:
            content.append(item)

        # ====================================================================
        # Medium Confidence Indicators
        # ====================================================================
        medium_confidence: TemporalAnalysisInterpretationGuideGroup = (
            guide_config.medium_confidence
        )
        medium_confidence_title: str = medium_confidence.title
        content.append(f'\n{medium_confidence_title}')

        for item in medium_confidence.items:
            content.append(item)

        # ====================================================================
        # Lower Priority Indicators
        # ====================================================================
        lower_priority: TemporalAnalysisInterpretationGuideGroup = (
            guide_config.lower_priority
        )
        lower_priority_title: str = lower_priority.title
        content.append(f'\n{lower_priority_title}')

        for item in lower_priority.items:
            content.append(item)

    def _write_temporal_caveats(self, content: list[str]) -> None:
        """
        Write caveats and limitations section for temporal analysis.

        This important section discloses the limitations of the analysis
        and provides appropriate caveats for interpretation.

        Args:
            content: list to append formatted lines to

        Responsibility:
            - Retrieve caveats from ConfigLoader
            - Format caveat items
            - Append to content list
        """
        caveats_config: TemporalAnalysisCaveats = (
            self.new_config.temporal_analysis.caveats
        )

        if not caveats_config:
            return  # No caveats configured, skip section

        # Section header
        content.append('\n' + self.formatter.separator('='))
        caveats_title: str = caveats_config.title
        content.append(caveats_title)
        content.append(self.formatter.separator('='))

        # Caveat items
        for item in caveats_config.items:
            content.append(f'{item}')

        # Recommendations
        recommendation: str = caveats_config.recommendation
        continuation: str = caveats_config.continuation

        if recommendation:
            content.append(f'\n{recommendation}')
            if continuation:
                content.append(continuation)

    def _write_temporal_top_entities(
        self,
        content: list[str],
        temporal_profiles: list['TemporalRiskProfile'],
        top_n: int,
    ) -> None:
        """
        Write the top high-risk entities section with detailed analysis for each.

        This is an orchestrator method that loops through the top N entities
        and delegates individual entity analysis to a specialized method.

        Args:
            content: list to append formatted lines to
            temporal_profiles: All temporal risk profiles (sorted by risk)
            top_n: Number of top entities to display

        Responsibility:
            - Create section header
            - Loop through top N entities
            - Delegate individual entity writing to helper method
        """
        content.append('\n' + self.formatter.separator('='))

        top_entities_config: TemporalAnalysisTopEntities = (
            self.new_config.temporal_analysis.top_entities
        )
        title_template: str = top_entities_config.title
        title: str = self.formatter.format_template(title_template, top_n=top_n)
        content.append(title)
        content.append(self.formatter.separator('='))

        # Introduction
        introduction: str = top_entities_config.introduction
        content.append(f'\n{introduction}')

        priority_note: str = top_entities_config.priority_note
        if priority_note:
            content.append(priority_note)

        # Write detailed analysis for each top entity
        for profile in temporal_profiles[:top_n]:
            self._write_temporal_single_entity(content, profile, top_entities_config)

        content.append(f'\n{self.formatter.separator("-")}')

    def _write_temporal_single_entity(
        self,
        content: list[str],
        profile: 'TemporalRiskProfile',
        top_entities_config: TemporalAnalysisTopEntities,
    ) -> None:
        """
        Write detailed analysis for a single temporal entity.

        This is an orchestrator method that coordinates all subsections
        of an individual entity's temporal analysis.

        Args:
            content: list to append formatted lines to
            profile: TemporalRiskProfile for this entity
            top_entities_config: Configuration for top entities section

        Responsibility:
            - Write entity header and basic info
            - Delegate subsections to specialized helper methods
            - Maintain consistent structure for each entity
        """
        # ====================================================================
        # Entity Header
        # ====================================================================
        entity_header_separator: str = top_entities_config.entity_header
        content.append(f'\n{entity_header_separator}')
        entity_type: str = profile.entity_type

        # Entity identification (handle trucks specially)
        if profile.truck_description is not None and entity_type != 'Driver':
            title_template: str = top_entities_config.truck_entity_title
            entity_title: str = self.formatter.format_template(
                title_template,
                entity_type=entity_type,
                display_id=profile.display_id,
                truck_description=profile.truck_description,
            )
        else:
            title_template = top_entities_config.entity_title
            entity_title = self.formatter.format_template(
                title_template, entity_type=entity_type, display_id=profile.display_id
            )
        content.append(entity_title)

        # Risk score with category
        risk_line_template: str = top_entities_config.risk_line
        risk_line: str = self.formatter.format_template(
            risk_line_template,
            risk_score=self.formatter.format_number(profile.risk_score),
            risk_category=profile.get_risk_category(),
        )
        content.append(risk_line)

        # Activity summary
        activity_line_template: str = top_entities_config.activity_line
        activity_line: str = self.formatter.format_template(
            activity_line_template,
            months_active=profile.months_active,
            total_transactions=self.formatter.format_number(profile.total_transactions),
        )
        content.append(activity_line)

        # Analysis flags
        analysis_flags: list[str] = profile.get_analysis_flags()
        if analysis_flags:
            flags_line_template: str = top_entities_config.flags_line
            flags_display_list: list[str] = [
                self.formatter.format_display_name(flag) for flag in analysis_flags
            ]
            flags_line: str = self.formatter.format_template(
                flags_line_template, flags=', '.join(flags_display_list)
            )
            content.append(flags_line)

        # ====================================================================
        # Subsections (delegated to specialized methods)
        # ====================================================================
        self._write_temporal_entity_current_risks(content, profile, top_entities_config)
        self._write_temporal_entity_fraud_patterns(
            content, profile, top_entities_config
        )
        self._write_temporal_entity_mom_analysis(content, profile, top_entities_config)
        self._write_temporal_entity_change_points(content, profile, top_entities_config)
        self._write_temporal_entity_autocorrelation(
            content, profile, top_entities_config
        )
        self._write_temporal_entity_rolling_anomalies(
            content, profile, top_entities_config
        )
        self._write_temporal_entity_trends(content, profile, top_entities_config)
        self._write_temporal_entity_period_comparison(
            content, profile, top_entities_config
        )
        self._write_temporal_entity_summary(content, profile, top_entities_config)

    def _write_temporal_entity_current_risks(
        self,
        content: list[str],
        profile: 'TemporalRiskProfile',
        top_entities_config: TemporalAnalysisTopEntities,
    ) -> None:
        """
        Write current risk factors for an entity (what's happening NOW).

        This is the most critical subsection as it shows active, recent risks
        that require immediate attention.

        Args:
            content: list to append formatted lines to
            profile: TemporalRiskProfile for this entity
            top_entities_config: Configuration dict
        """
        current_risks_config: TemporalAnalysisTopEntitiesCurrentRisks = (
            top_entities_config.current_risks
        )

        if profile.has_current_risks():
            # Entity has current risk factors
            title: str = current_risks_config.title
            content.append(f'\n{title}')

            item_format_template: str = current_risks_config.item_format
            for risk_factor in profile.current_risk_factors:
                formatted_item: str = self.formatter.format_template(
                    item_format_template, factor=risk_factor
                )
                content.append(formatted_item)
        else:
            # No current risk factors
            none_message: str = current_risks_config.none
            content.append(f'\n{none_message}')

    def _write_temporal_entity_fraud_patterns(
        self,
        content: list[str],
        profile: 'TemporalRiskProfile',
        top_entities_config: TemporalAnalysisTopEntities,
    ) -> None:
        """
        Write detected fraud patterns for an entity.

        Fraud patterns are specific behavioral signatures that match
        known fraud schemes (e.g., spike-and-retreat, gradual escalation).

        Args:
            content: list to append formatted lines to
            profile: TemporalRiskProfile for this entity
            top_entities_config: Configuration dict
        """
        fraud_patterns_config: TemporalAnalysisTopEntitiesFraudPatterns = (
            top_entities_config.fraud_patterns
        )

        if profile.has_fraud_patterns():
            # Entity has detected fraud patterns
            title: str = fraud_patterns_config.title
            content.append(f'\n{title}')

            patterns_dict: dict[str, str] = fraud_patterns_config.patterns
            detected_patterns: list[str] = profile.get_detected_fraud_patterns()

            for pattern_name in detected_patterns:
                pattern_text: str = patterns_dict.get(
                    pattern_name, f'  • {pattern_name}'
                )
                content.append(pattern_text)
        else:
            # No fraud patterns detected
            none_message: str = fraud_patterns_config.none
            content.append(f'\n{none_message}')

    def _write_temporal_entity_mom_analysis(
        self,
        content: list[str],
        profile: 'TemporalRiskProfile',
        top_entities_config: TemporalAnalysisTopEntities,
    ) -> None:
        """
        Write month-over-month volatility analysis for an entity.

        This section identifies sudden spikes, gradual escalations, and
        overall volatility in behavioral metrics.

        Args:
            content: list to append formatted lines to
            profile: TemporalRiskProfile for this entity
            top_entities_config: Configuration dict
        """
        if not profile.month_over_month:
            return  # No MoM data available

        mom_config: TemporalAnalysisTopEntitiesMonthOverMonth = (
            top_entities_config.month_over_month
        )
        title: str = mom_config.title
        content.append(f'\n{title}')

        # ====================================================================
        # Sudden Spikes
        # ====================================================================
        spikes_config: TemporalAnalysisTopEntitiesMonthOverMonthGroup = (
            mom_config.sudden_spikes
        )
        sudden_spikes: list[dict[str, str | float | list[str]]] = (
            profile.month_over_month.get('sudden_spikes', [])
        )

        if sudden_spikes:
            spikes_label: str = spikes_config.label
            content.append(spikes_label)

            item_format_template: str = spikes_config.item_format

            for spike_data in sudden_spikes:
                spike_metric_name: str | float | list[str] = spike_data['metric']
                month_list: str | float | list[str] = spike_data.get('months', [])
                if isinstance(month_list, list) and isinstance(spike_metric_name, str):
                    months_string: str = ', '.join(str(m) for m in month_list)

                    formatted_item: str = self.formatter.format_template(
                        item_format_template,
                        metric=self.formatter.format_temporal_metric_name(
                            spike_metric_name
                        ),
                        percentile=spike_data['percentile'],
                        count=len(month_list),
                        months=months_string,
                    )
                    content.append(formatted_item)
        else:
            spikes_label = spikes_config.label
            none_message: str = spikes_config.none
            content.append(f'{spikes_label} {none_message}')

        # ====================================================================
        # Gradual Escalation
        # ====================================================================
        escalation_config: TemporalAnalysisTopEntitiesMonthOverMonthGroup = (
            mom_config.gradual_escalation
        )
        escalations: list[dict[str, str | int]] = profile.month_over_month.get(
            'gradual_escalation', []
        )

        if escalations:
            escalation_label: str = escalation_config.label
            content.append(f'\n{escalation_label}')

            item_format_template = escalation_config.item_format

            for escalation_data in escalations:
                escalation_metric_name: str | int = escalation_data['metric']
                if isinstance(escalation_metric_name, str):
                    formatted_item = self.formatter.format_template(
                        item_format_template,
                        metric=self.formatter.format_temporal_metric_name(
                            escalation_metric_name
                        ),
                        consecutive=escalation_data['consecutive_months'],
                    )
                    content.append(formatted_item)
        else:
            escalation_label = escalation_config.label
            none_message = escalation_config.none
            content.append(f'{escalation_label} {none_message}')

        # ====================================================================
        # Volatility Score
        # ====================================================================
        volatility_config: dict[str, str] = mom_config.volatility
        volatility_score: float = profile.get_volatility_score()

        volatility_label_template: str = volatility_config.get(
            'label', '  Volatility Score: {volatility_score}'
        )
        volatility_line: str = self.formatter.format_template(
            volatility_label_template,
            volatility_score=self.formatter.format_number(volatility_score, decimals=2),
        )
        content.append(f'\n{volatility_line}')

        # High volatility warning
        if volatility_score > 1.0:
            high_volatility_note: str = volatility_config.get(
                'high_note', '    ⚠ High volatility indicates erratic behavior'
            )
            content.append(high_volatility_note)

    def _write_temporal_entity_change_points(
        self,
        content: list[str],
        profile: 'TemporalRiskProfile',
        top_entities_config: TemporalAnalysisTopEntities,
    ) -> None:
        """
        Write detected change points for an entity.

        Change points indicate significant shifts in behavior patterns,
        which could signal the start of fraudulent activity. This method displays
        both single change points and multiple change points per metric.

        Args:
            content: list to append formatted lines to
            profile: TemporalRiskProfile for this entity
            top_entities_config: Configuration dict
        """
        if not profile.has_change_points():
            return  # No change points detected

        change_points_config: TemporalAnalysisTopEntitiesChangePoints = (
            top_entities_config.change_points
        )
        title: str = change_points_config.title
        content.append(f'\n{title}')

        item_format: str = change_points_config.item_format

        # Single change points
        if profile.change_points is not None:
            for metric, date in profile.change_points.items():
                formatted_item: str = self.formatter.format_template(
                    item_format,
                    metric=self.formatter.format_temporal_metric_name(metric),
                    date=self.formatter.format_month(date),
                )
                content.append(formatted_item)

        # Multiple change points (if any)
        if profile.multiple_change_points:
            multiple_format: str = change_points_config.multiple_format

            for metric, dates in profile.multiple_change_points.items():
                formatted_dates: str = ', '.join(
                    self.formatter.format_month(d) for d in dates
                )
                formatted_item = self.formatter.format_template(
                    multiple_format,
                    metric=self.formatter.format_temporal_metric_name(metric),
                    dates=formatted_dates,
                    count=len(dates),
                )
                content.append(formatted_item)

    def _write_temporal_entity_autocorrelation(
        self,
        content: list[str],
        profile: 'TemporalRiskProfile',
        top_entities_config: TemporalAnalysisTopEntities,
    ) -> None:
        """
        Write autocorrelation analysis for an entity.

        Autocorrelation measures how predictable an entity's behavior is
        based on past patterns. High autocorrelation with concerning behavior
        indicates persistent bad patterns (not just one-time events).

        Args:
            content: list to append formatted lines to
            profile: TemporalRiskProfile for this entity
            top_entities_config: Configuration dict
        """
        if not profile.autocorrelation:
            return  # No autocorrelation data available

        # Only show if there are high-risk persistent patterns
        high_risk_metrics: list[str] = [
            metric
            for metric, data in profile.autocorrelation.items()
            if data.get('risk_level') == 'HIGH'
        ]

        if not high_risk_metrics:
            return  # No concerning persistent patterns

        autocorr_config: TemporalAnalysisTopEntitiesAutocorrelation = (
            top_entities_config.autocorrelation
        )
        title: str = autocorr_config.title
        content.append(f'\n{title}')

        explanation: str = autocorr_config.explanation
        content.append(explanation)

        item_format: str = autocorr_config.item_format

        for metric in high_risk_metrics:
            data: dict[str, Any] = profile.autocorrelation[metric]
            correlation: float = data.get('lag1_correlation', 0.0)

            formatted_item: str = self.formatter.format_template(
                item_format,
                metric=self.formatter.format_temporal_metric_name(metric),
                correlation=self.formatter.format_number(correlation, decimals=2),
                level=data.get('risk_level', 'UNKNOWN'),
            )
            content.append(formatted_item)

    def _write_temporal_entity_rolling_anomalies(
        self,
        content: list[str],
        profile: 'TemporalRiskProfile',
        top_entities_config: TemporalAnalysisTopEntities,
    ) -> None:
        """
        Write rolling window anomaly detection results for an entity.

        Rolling anomalies identify periods where behavior deviates significantly
        from recent historical patterns (using a rolling window approach).

        Args:
            content: list to append formatted lines to
            profile: TemporalRiskProfile for this entity
            top_entities_config: Configuration dict
        """
        if not profile.rolling_anomalies:
            return  # No rolling anomaly data available

        # Filter to only metrics with detected outliers
        metrics_with_outliers: dict[str, dict[str, Any]] = {
            metric: data
            for metric, data in profile.rolling_anomalies.items()
            if data.get('outlier_months')
        }

        if not metrics_with_outliers:
            return  # No outliers detected

        anomalies_config: TemporalAnalysisTopEntitiesRollingAnomalies = (
            top_entities_config.rolling_anomalies
        )
        title: str = anomalies_config.title
        content.append(f'\n{title}')

        item_format: str = anomalies_config.item_format

        for metric, data in metrics_with_outliers.items():
            outlier_months: list[str] = data.get('outlier_months', [])
            max_z_score: float = data.get('max_z_score', 0.0)

            formatted_months: str = ', '.join(
                self.formatter.format_month(m) for m in outlier_months
            )

            formatted_item: str = self.formatter.format_template(
                item_format,
                metric=self.formatter.format_temporal_metric_name(metric),
                months=formatted_months,
                z_score=self.formatter.format_number(max_z_score, decimals=2),
            )
            content.append(formatted_item)

    def _write_temporal_entity_trends(
        self,
        content: list[str],
        profile: 'TemporalRiskProfile',
        top_entities_config: TemporalAnalysisTopEntities,
    ) -> None:
        """
        Write detected trends for an entity.

        Trends identify long-term directional changes in behavior
        (increasing, decreasing patterns). These are extracted from
        the risk_indicators list.

        Args:
            content: list to append formatted lines to
            profile: TemporalRiskProfile for this entity
            top_entities_config: Configuration dict
        """
        if not profile.risk_indicators:
            return  # No risk indicators available

        # Filter risk_indicators for trend-related items
        # These typically start with "INCREASING" or "DECREASING"
        trend_keywords: list[str] = ['INCREASING', 'DECREASING', 'RISING', 'DECLINING']
        trend_indicators: list[str] = [
            indicator
            for indicator in profile.risk_indicators
            if any(keyword in indicator.upper() for keyword in trend_keywords)
        ]

        if not trend_indicators:
            return  # No trend indicators found

        trends_config: TemporalAnalysisTopEntitiesTrends = top_entities_config.trends
        title: str = trends_config.title
        content.append(f'\n{title}')

        # Just display the trend indicators directly
        for indicator in trend_indicators:
            content.append(f'  • {indicator}')

    def _write_temporal_entity_period_comparison(
        self,
        content: list[str],
        profile: 'TemporalRiskProfile',
        top_entities_config: TemporalAnalysisTopEntities,
    ) -> None:
        """
        Write period-over-period comparison for an entity.

        Compares metrics between first half and second half of the analysis period
        to identify significant changes over time. Uses the segment_comparison field.

        Args:
            content: list to append formatted lines to
            profile: TemporalRiskProfile for this entity
            top_entities_config: Configuration dict
        """
        if not profile.segment_comparison:
            return  # No period comparison data available

        period_config: TemporalAnalysisTopEntitiesPeriodComparison = (
            top_entities_config.period_comparison
        )
        title: str = period_config.title
        content.append(f'\n{title}')

        explanation: str = period_config.explanation
        content.append(explanation)

        item_format: str = period_config.item_format

        # The segment_comparison is already formatted strings like:
        # 'INCREASED (p=0.023, r=0.45)' or 'NO SIGNIFICANT CHANGE'
        for metric, result in profile.segment_comparison.items():
            formatted_item: str = self.formatter.format_template(
                item_format,
                metric=self.formatter.format_temporal_metric_name(metric),
                result=result,
            )
            content.append(formatted_item)

    def _write_temporal_entity_summary(
        self,
        content: list[str],
        profile: 'TemporalRiskProfile',
        top_entities_config: TemporalAnalysisTopEntities,
    ) -> None:
        """
        Write overall summary and risk assessment for an entity.

        Provides a comprehensive overview of the entity's risk profile
        and recommended actions based on risk score and detected patterns.

        Args:
            content: list to append formatted lines to
            profile: TemporalRiskProfile for this entity
            top_entities_config: Configuration dict
        """
        summary_config: TemporalAnalysisTopEntitiesEntitySummary = (
            top_entities_config.entity_summary
        )
        title: str = summary_config.title
        content.append(f'\n{title}')

        # Get risk category and recommendation
        risk_category: str = profile.get_risk_category()
        risk_score: int = profile.risk_score

        # *** I'm not going to tell people what to do ***
        # Get recommendation based on risk level
        # recommendations = summary_config.get('recommendations', {})
        # if risk_score >= 75:
        #     recommendation = recommendations.get(
        #         'critical',
        #         'Immediate investigation recommended - Critical risk level'
        #     )
        # elif risk_score >= 50:
        #     recommendation = recommendations.get(
        #         'high',
        #         'Priority review recommended - High risk level'
        #     )
        # elif risk_score >= 25:
        #     recommendation = recommendations.get(
        #         'moderate',
        #         'Routine monitoring recommended - Moderate risk level'
        #     )
        # else:
        #     recommendation = recommendations.get(
        #         'low',
        #         'Standard monitoring sufficient - Low risk level'
        #     )

        # Display risk level
        risk_template: str = summary_config.risk_format
        risk_line: str = self.formatter.format_template(
            risk_template, risk_category=risk_category, risk_score=risk_score
        )
        content.append(risk_line)

        # Display key flags
        flags: list[str] = profile.get_analysis_flags()
        if flags:
            flags_formatted: list[str] = [
                self.formatter.format_display_name(f) for f in flags
            ]
            flags_template: str = summary_config.flags_format
            flags_line: str = self.formatter.format_template(
                flags_template, flags=', '.join(flags_formatted)
            )
            content.append(flags_line)

        # Display recommendation
        # content.append(f"  Recommendation: {recommendation}")

    def _write_temporal_fraud_pattern_summary(
        self, content: list[str], temporal_profiles: list['TemporalRiskProfile']
    ) -> None:
        """
        Write branch-wide fraud pattern detection summary.

        Aggregates all detected fraud patterns across entities and provides
        counts and percentages for each pattern type.

        Args:
            content: list to append formatted lines to
            temporal_profiles: All temporal risk profiles

        Responsibility:
            - Aggregate fraud pattern detection counts
            - Format pattern statistics
            - Display prevalence information
        """
        fraud_summary_config: TemporalAnalysisFraudPatternSummary = (
            self.new_config.temporal_analysis.fraud_pattern_summary
        )

        title: str = fraud_summary_config.title
        self._write_subsection_header(content, title)

        # ====================================================================
        # Aggregate Pattern Counts
        # ====================================================================
        pattern_counts: dict[str, int] = {}
        total_with_patterns = 0

        for profile in temporal_profiles:
            if profile.has_fraud_patterns():
                total_with_patterns += 1
                for pattern in profile.get_detected_fraud_patterns():
                    pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

        # ====================================================================
        # Display Pattern Statistics
        # ====================================================================
        if pattern_counts:
            intro: str = fraud_summary_config.intro
            content.append(f'\n{intro}')

            # Define the order of patterns to display (matches YAML order)
            pattern_order: list[str] = [
                'off_hours_concentration',
                'spike_retreat',
                'gradual_escalation',
                'operational_anomaly',
            ]

            # Display each detected pattern with full detail
            for pattern_key in pattern_order:
                if pattern_key in pattern_counts:
                    pattern_config: TemporalAnalysisFraudPatternSummaryPattern = (
                        getattr(fraud_summary_config, pattern_key)
                    )
                    count: int = pattern_counts[pattern_key]

                    # Pattern title
                    pattern_title: str = pattern_config.title
                    content.append(f'\n{pattern_title}')

                    # Pattern description
                    pattern_desc: str = pattern_config.description
                    if pattern_desc:
                        content.append(pattern_desc)

                    # Pattern count
                    count_template: str = pattern_config.count
                    count_line: str = self.formatter.format_template(
                        count_template, count=count
                    )
                    content.append(count_line)

                    # Pattern concern
                    pattern_concern: str = pattern_config.concern
                    if pattern_concern:
                        content.append(pattern_concern)
        else:
            # No patterns detected
            none_config: dict[str, str] = fraud_summary_config.none_detected
            none_message: str = none_config.get(
                'message',
                '  ✓ No specific fraud patterns detected in analyzed entities.',
            )
            content.append(f'\n{none_message}')

    def _write_temporal_risk_distribution(
        self,
        content: list[str],
        temporal_profiles: list['TemporalRiskProfile'],
        summary_stats: dict[str, Any],
    ) -> None:
        """
        Write risk score distribution by entity type (Driver vs Vehicle).

        Provides comparative statistics to identify if risk is concentrated
        in specific entity types.

        Args:
            content: list to append formatted lines to
            temporal_profiles: All temporal risk profiles (needed for medium/low counts)
            summary_stats: dictionary of summary statistics

        Responsibility:
            - Retrieve entity-type-specific statistics
            - Display risk distribution across all levels
            - Compare driver vs vehicle risk profiles
        """
        risk_dist_config: TemporalAnalysisRiskDistribution = (
            self.new_config.temporal_analysis.risk_distribution
        )

        title: str = risk_dist_config.title
        self._write_subsection_header(content, title)

        # ====================================================================
        # Overall Distribution (all entities)
        # ====================================================================
        overall_config: TemporalAnalysisRiskDistributionOverall = (
            risk_dist_config.overall
        )
        overall_title: str = overall_config.title
        content.append(f'\n{overall_title}')

        # Calculate counts for all risk levels
        critical_count: int = summary_stats['critical_count']  # ≥75
        high_count: int = summary_stats['high_risk_count'] - critical_count  # 50-74
        medium_count: int = sum(
            1
            for p in temporal_profiles
            if LOW_RISK_SCORE <= p.risk_score < MEDIUM_RISK_SCORE
        )
        low_count: int = sum(
            1 for p in temporal_profiles if p.risk_score < LOW_RISK_SCORE
        )

        # Display each risk level
        critical_template: str = overall_config.critical
        critical_line: str = self.formatter.format_template(
            critical_template, critical_count=critical_count
        )
        content.append(critical_line)

        high_template: str = overall_config.high
        high_line: str = self.formatter.format_template(
            high_template, high_count=high_count
        )
        content.append(high_line)

        medium_template: str = overall_config.medium
        medium_line: str = self.formatter.format_template(
            medium_template, medium_count=medium_count
        )
        content.append(medium_line)

        low_template: str = overall_config.low
        low_line: str = self.formatter.format_template(
            low_template, low_count=low_count
        )
        content.append(low_line)

        # ====================================================================
        # Driver Statistics
        # ====================================================================
        drivers_config: TemporalAnalysisRiskDistributionGroup = risk_dist_config.drivers
        driver_stats: dict[str, int | float] | None = summary_stats.get('driver_stats')

        if driver_stats:
            driver_title_template: str = drivers_config.title
            driver_title: str = self.formatter.format_template(
                driver_title_template, count=driver_stats['count']
            )
            content.append(f'\n{driver_title}')

            # Calculate high risk count (50-74 range)
            driver_high_50_74: int | float = (
                driver_stats['high_risk_count'] - driver_stats['critical_count']
            )

            # Format each driver stat item
            self._write_config_items(
                content,
                drivers_config.items,
                formatter_kwargs={
                    'mean_risk': driver_stats['mean_risk'],
                    'median_risk': driver_stats['median_risk'],
                    'critical_count': driver_stats['critical_count'],
                    'critical_pct': driver_stats['critical_pct']
                    * 100,  # Convert to percentage
                    'high_risk_count': driver_high_50_74,
                    'high_risk_pct': (driver_high_50_74 / driver_stats['count'] * 100)
                    if driver_stats['count'] > 0
                    else 0,
                },
            )
        else:
            # No driver data
            none_message: str | None = drivers_config.none
            content.append(f'\n{none_message}')

        # ====================================================================
        # Vehicle Statistics
        # ====================================================================
        vehicles_config: TemporalAnalysisRiskDistributionGroup = (
            risk_dist_config.vehicles
        )
        vehicle_stats: dict[str, int | float] | None = summary_stats.get(
            'vehicle_stats'
        )

        if vehicle_stats:
            vehicle_title_template: str = vehicles_config.title
            vehicle_title: str = self.formatter.format_template(
                vehicle_title_template, count=vehicle_stats['count']
            )
            content.append(f'\n{vehicle_title}')

            # Calculate high risk count (50-74 range)
            vehicle_high_50_74: int | float = (
                vehicle_stats['high_risk_count'] - vehicle_stats['critical_count']
            )

            # Format each vehicle stat item
            self._write_config_items(
                content,
                vehicles_config.items,
                formatter_kwargs={
                    'mean_risk': vehicle_stats['mean_risk'],
                    'median_risk': vehicle_stats['median_risk'],
                    'critical_count': vehicle_stats['critical_count'],
                    'critical_pct': vehicle_stats['critical_pct']
                    * 100,  # Convert to percentage
                    'high_risk_count': vehicle_high_50_74,
                    'high_risk_pct': (vehicle_high_50_74 / vehicle_stats['count'] * 100)
                    if vehicle_stats['count'] > 0
                    else 0,
                },
            )
        else:
            # No vehicle data
            none_message = vehicles_config.none
            content.append(f'\n{none_message}')

    def _write_temporal_fraud_timeline(
        self, content: list[str], timeline_data: pd.DataFrame | None
    ) -> None:
        """
        Write fraud emergence timeline showing when patterns first appeared.

        If timeline data is available, displays monthly emergence of
        change points and fraud patterns.

        Args:
            content: list to append formatted lines to
            timeline_data: Optional DataFrame with timeline information

        Responsibility:
            - Check if timeline data exists
            - Calculate change point frequency statistics
            - Display peak months and temporal patterns
            - Show detailed entity timeline
        """
        timeline_config: TemporalAnalysisFraudTimeline = (
            self.new_config.temporal_analysis.fraud_timeline
        )

        # Handle no changes case
        if timeline_data is None or timeline_data.empty:
            title: str = timeline_config.title
            self._write_subsection_header(content, title)

            subtitle: str = timeline_config.subtitle
            if subtitle:
                content.append(subtitle)
                content.append('')

            self._write_config_items(content, timeline_config.no_changes.paragraphs)
            return

        # ====================================================================
        # Section Header
        # ====================================================================
        title = timeline_config.title
        self._write_subsection_header(content, title)

        subtitle = timeline_config.subtitle
        if subtitle:
            content.append(subtitle)
            content.append('')

        # ====================================================================
        # Calculate Frequency Statistics
        # ====================================================================
        monthly_counts: pd.Series = timeline_data.groupby('month').size().sort_index()
        total_changes: int = len(timeline_data)

        # ====================================================================
        # Frequency Overview
        # ====================================================================
        freq_config: TemporalAnalysisFraudTimelineFrequencyIntro = (
            timeline_config.frequency_intro
        )
        freq_title: str = freq_config.title
        content.append(freq_title)

        freq_subtitle: str = freq_config.subtitle
        if freq_subtitle:
            content.append(freq_subtitle)

        # Write monthly counts
        month_format: str = timeline_config.month_format

        for month, count in monthly_counts.items():
            month_display: str = self.formatter.format_month(str(month))
            label: Literal['entities'] | Literal['entity'] = (
                'entities' if count != 1 else 'entity'
            )

            formatted_line: str = self.formatter.format_template(
                month_format, month=month_display, count=count, label=label
            )
            content.append(formatted_line)

        content.append('')

        # ====================================================================
        # Peak Month Insights
        # ====================================================================
        peak_config: TemporalAnalysisFraudTimelinePeakInsight = (
            timeline_config.peak_insight
        )
        marker: str = peak_config.marker
        content.append(marker)

        # Find peak month(s)
        max_count: int = monthly_counts.max()
        peak_months: list[str] = monthly_counts[
            monthly_counts == max_count
        ].index.tolist()

        if len(peak_months) == 1:
            # Single peak
            peak_month: str = self.formatter.format_month(peak_months[0])
            self._write_config_items(
                content,
                peak_config.peak_single.paragraphs,
                formatter_kwargs={'peak_month': peak_month, 'peak_count': max_count},
            )
        else:
            # Multiple peaks
            peak_month_names: list[str] = [
                self.formatter.format_month(m) for m in peak_months
            ]
            peak_months_str: str = ', '.join(peak_month_names)
            self._write_config_items(
                content,
                peak_config.peak_multiple.paragraphs,
                formatter_kwargs={
                    'peak_months': peak_months_str,
                    'peak_count': max_count,
                },
            )

        content.append('')

        # ====================================================================
        # Temporal Pattern Insights
        # ====================================================================
        patterns_config: TemporalAnalysisFraudTimelinePatterns = (
            timeline_config.patterns
        )
        patterns_title: str = patterns_config.title
        content.append(patterns_title)

        # Calculate temporal distribution
        months_sorted: list[str] = sorted(monthly_counts.index)
        if len(months_sorted) >= MINIMUM_MONTHS:
            third: int = len(months_sorted) // 3
            early_months: list[str] = months_sorted[:third]
            late_months: list[str] = months_sorted[-third:]

            early_count: int = sum(monthly_counts[m] for m in early_months)
            late_count: int = sum(monthly_counts[m] for m in late_months)

            early_pct: int = round(100 * early_count / total_changes)
            late_pct: int = round(100 * late_count / total_changes)

            # Write early changes insight
            if early_pct >= MIN_MONTHS_PCT_THRESHOLD:
                early_template: str = patterns_config.early_changes
                formatted_early: str = self.formatter.format_template(
                    early_template, early_pct=early_pct
                )
                content.append(formatted_early)

            # Write late changes insight
            if late_pct >= MIN_MONTHS_PCT_THRESHOLD:
                late_template: str = patterns_config.late_changes
                formatted_late: str = self.formatter.format_template(
                    late_template, late_pct=late_pct
                )
                content.append(formatted_late)

        # Clustering analysis
        # Check if changes are clustered (high variance) or distributed (low variance)
        if len(monthly_counts) > 1:
            count_variance: float = cast(float, monthly_counts.var())
            count_mean: float = monthly_counts.mean()

            # If variance is high relative to mean, it's clustered
            if count_variance > count_mean:
                clustered_template: str = patterns_config.clustered
                content.append(clustered_template)
            else:
                distributed_template: str = patterns_config.distributed
                content.append(distributed_template)

        content.append('')

        # ====================================================================
        # Detailed Entity Timeline
        # ====================================================================
        detail_config: TemporalAnalysisFraudTimelineEntityDetails = (
            timeline_config.entity_details
        )
        detail_title: str = detail_config.title
        content.append(detail_title)
        content.append('')

        # Group by month and show entity details
        item_format: str = detail_config.item_format

        for month, month_df in timeline_data.groupby('month'):
            month_display: str = self.formatter.format_month(str(month))
            content.append(f'{month_display}:')

            for _, row in month_df.iterrows():
                formatted_item: str = self.formatter.format_template(
                    item_format,
                    entity_type=row.get('entity_type', 'Entity'),
                    entity_id=row.get('entity', 'Unknown'),
                    metric=row.get('metric', 'Change detected'),
                )
                content.append(formatted_item)

            content.append('')

    def _write_temporal_comparative_statistics(
        self, content: list[str], comparative_stats: dict[str, Any]
    ) -> None:
        """
        Write comparative analysis between target location and other branches.

        Performs statistical comparison (Mann-Whitney U test) and effect size
        analysis to determine if target location is significantly different.

        Args:
            content: list to append formatted lines to
            comparative_stats: dictionary containing comparative analysis results

        Responsibility:
            - Display target vs baseline comparison
            - Report statistical test results
            - Interpret effect size and practical significance
            - Provide actionable recommendations based on comparison
        """
        comp_config: TemporalAnalysisComparativeAnalysis = (
            self.new_config.temporal_analysis.comparative_analysis
        )

        title: str = comp_config.title
        self._write_subsection_header(content, title)

        # ====================================================================
        # Introduction
        # ====================================================================
        intro_template: str = comp_config.introduction
        intro: str = self.formatter.format_template(
            intro_template, target_location=self.target_location
        )
        content.append(f'\n{intro}')

        # ====================================================================
        # Target Location Statistics
        # ====================================================================
        comp_title: str = comp_config.comparison_title
        self._write_subsection_header(content, comp_title)

        target_line_template: str = comp_config.target_line
        target_line: str = self.formatter.format_template(
            target_line_template, target_location=self.target_location
        )
        content.append(target_line)

        target_stats_template: str = comp_config.target_stats
        target_stats_line: str = self.formatter.format_template(
            target_stats_template,
            target_mean=self.formatter.format_number(
                comparative_stats['target_mean'], decimals=1
            ),
            target_median=self.formatter.format_number(
                comparative_stats['target_median'], decimals=1
            ),
        )
        content.append(target_stats_line)

        # Interquartile range for additional context
        iqr_template: str = comp_config.iqr_format
        iqr_line: str = self.formatter.format_template(
            iqr_template,
            p25=self.formatter.format_number(
                comparative_stats['target_p25'], decimals=1
            ),
            p75=self.formatter.format_number(
                comparative_stats['target_p75'], decimals=1
            ),
        )
        content.append(iqr_line)

        sample_size_template: str = comp_config.sample_size_format
        sample_size_line: str = self.formatter.format_template(
            sample_size_template, n=comparative_stats['target_n']
        )
        content.append(sample_size_line)

        # ====================================================================
        # Other Branches Statistics
        # ====================================================================
        others_line_template: str = comp_config.others_line
        others_line: str = self.formatter.format_template(others_line_template)
        content.append(f'\n{others_line}')

        others_stats_template: str = comp_config.others_stats
        others_stats_line: str = self.formatter.format_template(
            others_stats_template,
            others_mean=self.formatter.format_number(
                comparative_stats['others_mean'], decimals=1
            ),
            others_median=self.formatter.format_number(
                comparative_stats['others_median'], decimals=1
            ),
        )
        content.append(others_stats_line)

        # Other branches IQR
        others_iqr_line: str = self.formatter.format_template(
            iqr_template,
            p25=self.formatter.format_number(
                comparative_stats['others_p25'], decimals=1
            ),
            p75=self.formatter.format_number(
                comparative_stats['others_p75'], decimals=1
            ),
        )
        content.append(others_iqr_line)

        others_sample_size_line: str = self.formatter.format_template(
            sample_size_template, n=comparative_stats['others_n']
        )
        content.append(others_sample_size_line)

        # ====================================================================
        # Statistical Test Results
        # ====================================================================
        test_line_template: str = comp_config.test_line
        test_line: str = self.formatter.format_template(
            test_line_template,
            p_value=self.formatter.format_number(
                comparative_stats['p_value'], decimals=4
            ),
        )
        content.append(f'\n{test_line}')

        # Effect size (Cliff's Delta)
        effect_size_template: str = comp_config.effect_size_line
        effect_size_line: str = self.formatter.format_template(
            effect_size_template,
            delta=self.formatter.format_number(
                comparative_stats['effect_size'], decimals=3
            ),
            interpretation=comparative_stats['effect_interpretation'],
        )
        content.append(effect_size_line)

        # ====================================================================
        # Interpretation with Actionable Recommendations
        # ====================================================================
        interpretations: TemporalAnalysisComparativeInterpretations = (
            comp_config.interpretations
        )

        if comparative_stats['is_significant']:
            direction: str = comparative_stats['direction']

            if direction == 'higher':
                sig_higher: dict[str, list[str]] = interpretations.significant_higher
                for para_template in sig_higher.get('paragraphs', []):
                    formatted_para: str = self.formatter.format_template(
                        para_template, target_location=self.target_location
                    )
                    content.append(formatted_para)

            elif direction == 'lower':
                sig_lower: dict[str, list[str]] = interpretations.significant_lower
                for para_template in sig_lower.get('paragraphs', []):
                    formatted_para = self.formatter.format_template(
                        para_template, target_location=self.target_location
                    )
                    content.append(formatted_para)

        else:
            # Not statistically significant
            not_sig: dict[str, list[str]] = interpretations.not_significant
            for para_template in not_sig.get('paragraphs', []):
                formatted_para = self.formatter.format_template(
                    para_template, target_location=self.target_location
                )
                content.append(formatted_para)

        # ====================================================================
        # Effect Size Interpretation Guide
        # ====================================================================
        effect_guide_config: TemporalAnalysisComparativeEffectSizeGuide = (
            comp_config.effect_size_guide
        )
        if effect_guide_config:
            guide_title: str = effect_guide_config.title
            content.append(f'\n{guide_title}')

            # Determine magnitude category
            delta: float = comparative_stats['effect_size']
            abs_delta: float = abs(delta)

            if abs_delta < EFFECT_MAGNITUDE_THRESHOLD_NEGLIGIBLE:
                magnitude_text: str = effect_guide_config.negligible
            elif abs_delta < EFFECT_MAGNITUDE_THRESHOLD_SMALL:
                magnitude_text = effect_guide_config.small
            elif abs_delta < EFFECT_MAGNITUDE_THRESHOLD_MEDIUM:
                magnitude_text = effect_guide_config.medium
            else:
                magnitude_text = effect_guide_config.large

            content.append(f'    {magnitude_text}')

            # Explain practical interpretation
            probability_explanation_template: list[str] = (
                effect_guide_config.probability_explanation
            )

            if delta > 0:
                probability: float = (delta + 1) / 2
                probability_text: list[str] = self.formatter.format_list(
                    probability_explanation_template,
                    target_location=self.target_location,
                    probability=self.formatter.format_percent(probability),
                    comparison_entity=self.target_location,
                )
                [content.append(item) for item in probability_text]
            elif delta < 0:
                probability = (-delta + 1) / 2
                probability_text = self.formatter.format_list(
                    probability_explanation_template,
                    target_location=self.target_location,
                    probability=self.formatter.format_percent(probability),
                    comparison_entity='other branch',
                )
                [content.append(item) for item in probability_text]
            else:
                identical_text: str = effect_guide_config.identical
                content.append(identical_text)

    def write_multi_fillup_analysis(
        self,
        test_result: 'StatisticalTest',
        summary_stats: dict[str, Any],
        suspicious_events: pd.DataFrame,
        top_n: int = 15,
    ) -> None:
        """
        Write comprehensive multi-fillup analysis with fraud detection context.

        This orchestrator method coordinates all sections of the multi-fillup analysis,
        which detects cases where a single driver makes multiple fuel card purchases
        on the same day - a potential fraud indicator.

        Args:
            test_result: StatisticalTest object for multi-fillup test
            summary_stats: dictionary containing summary statistics
            suspicious_events: DataFrame with flagged suspicious events
            top_n: Number of top suspicious events to display (default 15)

        Responsibility:
            - Coordinate the flow of multi-fillup analysis sections
            - Delegate section writing to specialized helper methods
            - Assemble all sections into cohesive report
        """
        content: list[str] = []

        # ====================================================================
        # Section 1: Header
        # ====================================================================
        self._write_section_header(
            content, literal_text=self.new_config.multi_fillup_analysis.section_title
        )

        # ====================================================================
        # Section 2: Statistical Significance Context
        # ====================================================================
        self._write_multifillup_significance(content, test_result)

        # ====================================================================
        # Section 3: Summary Statistics
        # ====================================================================
        self._write_multifillup_summary(content, summary_stats)

        # ====================================================================
        # Section 4: Detailed Event Table
        # ====================================================================
        self._write_multifillup_events_table(content, suspicious_events, top_n)

        # ====================================================================
        # Section 5: Red Flag Legend
        # ====================================================================
        self._write_multifillup_red_flag_legend(content)

        # Add completed section to report
        self.add_to_section(ReportSection.DRIVER_ANALYSIS, '\n'.join(content))

    def _write_multifillup_significance(
        self, content: list[str], test_result: StatisticalTest
    ) -> None:
        """
        Write statistical significance context for multi-fillup test.

        Explains whether the observed multi-fillup pattern is statistically
        significant compared to expected baseline behavior.

        Args:
            content: list to append formatted lines to
            test_result: StatisticalTest object with p-value and significance

        Responsibility:
            - Retrieve significance templates from ConfigLoader
            - Format test results using ReportFormatter
            - Display appropriate interpretation based on significance
        """
        sig_context: MultiFillupAnalysisSignificanceContext = (
            self.new_config.multi_fillup_analysis.significance_context
        )

        if test_result.is_significant:
            # Statistically significant result
            sig_section: MultiFillupAnalysisSignificanceState = sig_context.significant
            marker: str = sig_section.marker
            title: str = sig_section.title

            details_template: str = sig_section.details
            details: str = self.formatter.format_template(
                details_template,
                p_value=self.formatter.format_p_value(test_result.p_value),
                q_value=self.formatter.format_number(test_result.q_value, decimals=3),
            )

            interp_template: str = sig_section.interpretation
            interp: str = self.formatter.format_template(
                interp_template, target_location=self.target_location
            )

            content.append(f'\n{marker} {title}')
            content.append(details)
            content.append(interp)

        else:
            # Not statistically significant
            not_sig_section: MultiFillupAnalysisSignificanceState = (
                sig_context.not_significant
            )
            marker = not_sig_section.marker
            title = not_sig_section.title

            details_template = not_sig_section.details
            details = self.formatter.format_template(
                details_template,
                p_value=self.formatter.format_p_value(test_result.p_value),
                q_value=self.formatter.format_number(test_result.q_value, decimals=3),
            )

            interp = not_sig_section.interpretation

            content.append(f'\n{marker} {title}')
            content.append(details)
            content.append(interp)

    def _write_multifillup_summary(
        self, content: list[str], summary_stats: dict[str, Any]
    ) -> None:
        """
        Write summary statistics for multi-fillup analysis.

        Displays aggregate metrics about multi-fillup events including
        total events, drivers involved, average fillups, and costs.

        Args:
            content: list to append formatted lines to
            summary_stats: dictionary containing summary statistics

        Responsibility:
            - Format summary statistics using ReportFormatter
            - Apply statistics to templates from ConfigLoader
            - Display aggregate metrics
        """
        content.append('\n' + self.formatter.separator('-'))
        content.append(self.new_config.multi_fillup_analysis.summary_title)
        content.append(self.formatter.separator('-'))

        summary_items: list[str] = self.new_config.multi_fillup_analysis.summary_items

        for item_template in summary_items:
            formatted_item: str = self.formatter.format_template(
                item_template,
                total_events=self.formatter.format_integer(
                    summary_stats['total_events']
                ),
                total_drivers=self.formatter.format_integer(
                    summary_stats['total_drivers']
                ),
                avg_fillups=self.formatter.format_number(
                    summary_stats['avg_fillups'], decimals=1
                ),
                total_cost=self.formatter.format_currency(summary_stats['total_cost']),
                high_suspicion_count=self.formatter.format_integer(
                    summary_stats['high_suspicion_count']
                ),
            )
            content.append(formatted_item)

    def _write_multifillup_events_table(
        self, content: list[str], suspicious_events: pd.DataFrame, top_n: int
    ) -> None:
        """
        Write detailed table of top suspicious multi-fillup events.

        Displays a formatted table showing driver, date, fill counts,
        and red flag indicators for the most suspicious events.

        Args:
            content: list to append formatted lines to
            suspicious_events: DataFrame with flagged suspicious events
            top_n: Number of events to display

        Responsibility:
            - Format table header
            - Format each row using ReportFormatter
            - Handle red flag display and truncation
        """
        content.append('\n' + self.formatter.separator('-'))

        table_title_template: str = (
            self.new_config.multi_fillup_analysis.events_table_title
        )
        table_title: str = self.formatter.format_template(
            table_title_template, top_n=top_n
        )
        content.append(table_title)
        content.append(self.formatter.separator('-'))

        # ====================================================================
        # Table Header
        # ====================================================================
        headers: CompositeTableHeadersType = self.template.get_table_headers(
            'multi_fillup_analysis'
        )
        if isinstance(headers, MultiFillupAnalysisTableHeaders):
            header_line: str = (
                f'{headers.driver:<20} '
                f'{headers.date:<12} '
                f'{headers.fills:<6} '
                f'{headers.sites:<5} '
                f'{headers.hours:<7} '
                f'{headers.avg_vol:<9} '
                f'{headers.avg_cost:<11} '
                f'{headers.red_flags:<45}'
            )
            content.append(header_line)
            content.append(self.formatter.separator('-'))

        # ====================================================================
        # Table Rows
        # ====================================================================
        for _, row in suspicious_events.head(top_n).iterrows():
            # Format red flags with truncation
            red_flags: str = row['red_flags'] if row['red_flags'] else 'None'
            red_flags_display: str = (
                (red_flags[:42] + '...') if len(red_flags) > 45 else red_flags
            )

            date_str: str = self.formatter.format_date(row['date_only'])
            # Format the row
            row_line: str = (
                f'{row["Driver"]!s:<20} '
                f'{date_str:<12} '
                f'{int(row["fillup_count"]):<6} '
                f'{int(row["unique_stations"]):<5} '
                f'{row["time_span_hours"]:>6.1f} '
                f'{self.formatter.format_number(row["avg_volume"], decimals=1):>8} '
                f'{self.formatter.format_currency(row["avg_cost"]):>10} '
                f'{red_flags_display:<45}'
            )
            content.append(row_line)

        content.append(self.formatter.separator('-'))

    def _write_multifillup_red_flag_legend(self, content: list[str]) -> None:
        """
        Write red flag legend explaining all acronyms and suspicion score.

        Provides detailed explanations of all red flag indicators used
        in the multi-fillup analysis, organized by category.

        Args:
            content: list to append formatted lines to

        Responsibility:
            - Retrieve red flag configuration from ConfigLoader
            - Display passenger vehicle indicators
            - Display card misuse indicators
            - Explain suspicion score calculation
        """
        content.append('\n' + self.formatter.separator('-'))
        content.append(self.new_config.multi_fillup_analysis.legend_title)
        content.append(self.formatter.separator('-'))

        # Get red flag configuration
        red_flags_config: RedFlags = self.new_config.red_flags

        # ====================================================================
        # Passenger Vehicle Indicators
        # ====================================================================
        pv_indicators: RedFlagsGroup = red_flags_config.passenger_vehicle_indicators
        pv_title: str = f'  {pv_indicators.emoji} {pv_indicators.title}:'
        content.append(pv_title)
        pv_indicator_flags: dict[str, RedFlagItem] = pv_indicators.flags

        for acronym, flag_info in pv_indicator_flags.items():
            flag_name: str = flag_info.full_name
            flag_description: str = flag_info.description
            flag_line: str = f'     {acronym} = {flag_name}: {flag_description}'
            content.append(flag_line)

        # ====================================================================
        # Card Misuse Indicators
        # ====================================================================
        cm_indicators: RedFlagsGroup = red_flags_config.card_misuse_indicators
        cm_title: str = f'\n  {cm_indicators.emoji}  {cm_indicators.title}:'
        content.append(cm_title)
        cm_indicator_flags: dict[str, RedFlagItem] = cm_indicators.flags

        for acronym, flag_info in cm_indicator_flags.items():
            flag_line = (
                f'     {acronym} = {flag_info.full_name}: {flag_info.description}'
            )
            content.append(flag_line)

        # ====================================================================
        # Suspicion Score Formula
        # ====================================================================
        formula: str = red_flags_config.suspicion_score_formula
        content.append(f'\n  {formula}')
        content.append(self.formatter.separator('-'))

    # ============================================================================
    # GEOGRAPHIC ANALYSIS
    # ============================================================================

    def write_geographic_analysis(
        self,
        station_stats: pd.DataFrame,
        suspicious_stations: pd.DataFrame,
        top_n: int = 10,
    ) -> None:
        """
        Write geographic/station usage analysis.

        This orchestrator method coordinates all sections of the geographic analysis,
        which examines fuel station usage patterns to identify locations with
        suspicious transaction characteristics.

        Args:
            station_stats: DataFrame with station-level statistics
            suspicious_stations: DataFrame with flagged suspicious stations
            top_n: Number of top stations to display (default 10)

        Responsibility:
            - Coordinate the flow of geographic analysis sections
            - Delegate section writing to specialized helper methods
            - Assemble all sections into cohesive report
        """
        content: list[str] = []

        # ====================================================================
        # Section 1: Header and Introduction
        # ====================================================================
        self._write_section_header(content, 'geographic_analysis')

        self._write_geographic_introduction(content)

        # ====================================================================
        # Section 2: Top Stations Table
        # ====================================================================
        self._write_geographic_stations_table(content, station_stats, top_n)

        # ====================================================================
        # Section 3: Suspicious Stations (if any)
        # ====================================================================
        if not suspicious_stations.empty:
            self._write_geographic_suspicious_stations(content, suspicious_stations)

        # Final separator
        content.append(self.formatter.separator('-'))

        # Add completed section to report
        self.add_to_section(ReportSection.VEHICLE_ANALYSIS, '\n'.join(content))

    def _write_geographic_introduction(self, content: list[str]) -> None:
        """
        Write introduction paragraph for geographic analysis.

        Args:
            content: list to append formatted lines to

        Responsibility:
            - Retrieve introduction template from ConfigLoader
            - Format with target location name
            - Append to content list
        """
        intro_template: str = self.new_config.geographic_analysis.introduction
        intro: str = self.formatter.format_template(
            intro_template, target_location=self.target_location
        )
        content.append(f'\n{intro}')

    def _write_geographic_stations_table(
        self, content: list[str], station_stats: pd.DataFrame, top_n: int
    ) -> None:
        """
        Write table of top fuel stations by transaction volume.

        Displays formatted table showing station name, transaction counts,
        percentage of total transactions, driver counts, and risk indicators.

        Args:
            content: list to append formatted lines to
            station_stats: DataFrame with station-level statistics
            top_n: Number of stations to display

        Responsibility:
            - Format table header
            - Format each row using ReportFormatter
            - Handle station name truncation
        """
        content.append('\n' + self.formatter.separator('-'))

        table_title_template: str = self.new_config.geographic_analysis.table_title
        table_title: str = self.formatter.format_template(
            table_title_template, top_n=top_n, target_location=self.target_location
        )
        content.append(table_title)
        content.append(self.formatter.separator('-'))

        # ====================================================================
        # Table Header
        # ====================================================================
        geo_config_headers: GeographicAnalysisTableHeaders = (
            self.new_config.geographic_analysis.table_headers
        )

        station_name: str = geo_config_headers.station_name
        transactions: str = geo_config_headers.transactions
        pct_total: str = geo_config_headers.pct_total
        drivers: str = geo_config_headers.drivers
        non_diesel_pct: str = geo_config_headers.non_diesel_pct
        no_eld_pct: str = geo_config_headers.no_eld_pct
        avg_cost: str = geo_config_headers.avg_cost
        headers: dict[str, str] = {
            'station_name': station_name,
            'transactions': transactions,
            'pct_total': pct_total,
            'drivers': drivers,
            'non_diesel_pct': non_diesel_pct,
            'no_eld_pct': no_eld_pct,
            'avg_cost': avg_cost,
        }

        # 2. Define Column Specifications
        # Derived from the widths and formatting in the original code.
        column_specs: dict[str, dict[str, int | str]] = {
            'station_name': {
                'width': 35,
                'format': 'string',
                'truncate': 35,
                'truncate_suffix': '...',
            },
            'transactions': {'width': 8, 'format': 'integer'},
            'pct_total': {'width': 9, 'format': 'percent'},
            'drivers': {'width': 8, 'format': 'integer'},
            'non_diesel_pct': {'width': 13, 'format': 'percent'},
            'no_eld_pct': {'width': 10, 'format': 'percent'},
            'avg_cost': {'width': 11, 'format': 'currency'},
        }

        # 3. Prepare Row Data
        # Pass the raw data; _create_table handles the formatting.
        rows_data: list[dict[str, str | int | float]] = []
        for _, row in station_stats.head(top_n).iterrows():
            rows_data.append(
                {
                    'station_name': row['Station Name'],
                    'transactions': row['transaction_count'],
                    'pct_total': row['pct_of_total'],
                    'drivers': row['unique_drivers'],
                    'non_diesel_pct': row['non_diesel_rate'],
                    'no_eld_pct': row['no_eld_rate'],
                    'avg_cost': row['avg_cost'],
                }
            )

        # 4. Generate and append all table lines at once
        table_lines: list[str] = self._create_table(
            headers, rows_data, column_specs, separator_char='-'
        )
        content.extend(table_lines)

    def _write_geographic_suspicious_stations(
        self, content: list[str], suspicious_stations: pd.DataFrame
    ) -> None:
        """
        Write flagged suspicious stations section.

        Highlights stations that exceed thresholds for concerning behavior
        such as high non-diesel rates, missing ELD data, or unusually low costs.

        Args:
            content: list to append formatted lines to
            suspicious_stations: DataFrame with flagged suspicious stations

        Responsibility:
            - Retrieve suspicious station configuration
            - Format each suspicious station with its flags
            - Display concatenated red flags for each station
        """
        susp_config: GeographicAnalysisSuspiciousStations = (
            self.new_config.geographic_analysis.suspicious_stations
        )

        title: str = susp_config.title
        content.append(f'\n{title}')

        item_format: str = susp_config.item_format
        flag_sep: str = susp_config.flag_separator
        flag_formats: GeographicAnalysisSuspiciousFlagFormats = susp_config.flag_formats

        # ====================================================================
        # Process Each Suspicious Station
        # ====================================================================
        for _, row in suspicious_stations.iterrows():
            flags: list[str] = []

            # Check for high non-diesel rate
            if row.get('high_non_diesel', False):
                flag_template: str = flag_formats.high_non_diesel
                flag_text: str = self.formatter.format_template(
                    flag_template,
                    rate=self.formatter.format_percent(row['non_diesel_rate']),
                )
                flags.append(flag_text)

            # Check for high no-ELD rate
            if row.get('high_no_eld', False):
                flag_template = flag_formats.high_no_eld
                flag_text = self.formatter.format_template(
                    flag_template,
                    rate=self.formatter.format_percent(row['no_eld_rate']),
                )
                flags.append(flag_text)

            # Check for low average cost
            if row.get('low_avg_cost', False):
                flag_template = flag_formats.low_avg_cost
                flag_text = self.formatter.format_template(
                    flag_template, cost=self.formatter.format_currency(row['avg_cost'])
                )
                flags.append(flag_text)

            # Concatenate all flags
            flag_str: str = flag_sep.join(flags)

            # Format the complete line
            formatted_line: str = self.formatter.format_template(
                item_format,
                station_name=row['Station Name'],
                transaction_count=int(row['transaction_count']),
                flags=flag_str,
            )
            content.append(formatted_line)

    def write_executive_summary(self, all_tests: dict[str, 'StatisticalTest']) -> None:
        """
        Generate executive summary based on significant statistical findings.

        This orchestrator method coordinates the executive summary generation,
        which provides a high-level overview of significant findings for
        decision-makers and investigators.

        Args:
            all_tests: dictionary of all completed StatisticalTest objects

        Responsibility:
            - Identify significant findings
            - Coordinate section flow
            - Delegate to helper methods based on findings
        """
        significant_tests: list[StatisticalTest] = [
            test for test in all_tests.values() if test.is_significant
        ]

        content: list[str] = []

        # ====================================================================
        # Section 1: Header and Introduction
        # ====================================================================
        self._write_section_header(content, 'executive_summary')

        intro: str = self.new_config.executive_summary.introduction
        content.append(f'\n{intro}')

        # ====================================================================
        # Section 2: Findings or No Findings
        # ====================================================================
        if not significant_tests:
            self._write_executive_summary_no_findings(content)
        else:
            self._write_executive_summary_findings(content, significant_tests)

        # ====================================================================
        # Section 3: Recommendation
        # ====================================================================
        if significant_tests:
            self._write_executive_summary_recommendation(content)

        # Add completed section to report
        self.add_to_section(ReportSection.EXECUTIVE_SUMMARY, '\n'.join(content))

    def _write_executive_summary_no_findings(self, content: list[str]) -> None:
        """
        Write executive summary when no significant findings are detected.

        Provides context and reassurance when statistical analysis reveals
        no significant differences from baseline behavior.

        Args:
            content: list to append formatted lines to

        Responsibility:
            - Display "no findings" message
            - Provide context about what this means
            - Reassure about analysis quality
        """
        no_findings: ExecutiveSummaryNoFindings = (
            self.new_config.executive_summary.no_findings
        )

        content.append('\n' + self.formatter.separator('-'))
        content.append(no_findings.title)
        content.append(self.formatter.separator('-'))

        for para_template in no_findings.paragraphs:
            formatted_para: str = self.formatter.format_template(
                para_template, target_location=self.target_location
            )
            content.append(f'\n{formatted_para}')

    def _write_executive_summary_findings(
        self, content: list[str], significant_tests: list['StatisticalTest']
    ) -> None:
        """
        Write executive summary when significant findings are detected.

        lists all significant findings in order of statistical strength
        and provides detailed interpretation for each.

        Args:
            content: list to append formatted lines to
            significant_tests: list of statistically significant test results

        Responsibility:
            - Sort findings by p-value (strongest first)
            - Format findings header
            - Delegate individual finding details to helper method
        """
        # Sort findings by p-value (most significant first)
        significant_tests.sort(key=lambda x: x.p_value)

        findings: ExecutiveSummaryFindingsPresent = (
            self.new_config.executive_summary.findings_present
        )

        header_template: str = findings.header
        header: str = self.formatter.format_template(
            header_template, count=len(significant_tests)
        )
        content.append(f'\n{header}')

        # Write each finding in detail
        for idx, test in enumerate(significant_tests, 1):
            self._write_executive_summary_finding_detail(content, test, idx, findings)

    def _write_executive_summary_finding_detail(
        self,
        content: list[str],
        test: 'StatisticalTest',
        index: int,
        findings_config: ExecutiveSummaryFindingsPresent,
    ) -> None:
        """
        Write detailed information for a single finding.

        Provides comprehensive interpretation including test type,
        effect sizes, rates/costs, and statistical strength.

        Args:
            content: list to append formatted lines to
            test: StatisticalTest object for this finding
            index: Finding number (1, 2, 3, etc.)
            findings_config: Configuration dict for findings section

        Responsibility:
            - Format finding header
            - Determine finding type (rate vs cost comparison)
            - Display appropriate metrics and interpretations
            - Show statistical strength
        """
        content.append('\n' + self.formatter.separator('-'))

        title_template: str = findings_config.finding_title
        title: str = self.formatter.format_template(
            title_template, index=index, test_name=test.name.upper()
        )
        content.append(title)
        content.append(self.formatter.separator('-'))

        # ====================================================================
        # Rate Comparison Finding
        # ====================================================================
        if (
            not math.isnan(test.risk_ratio)
            and not math.isnan(test.target_rate)
            and not math.isnan(test.baseline_rate)
        ):
            rate_comp: ExecutiveSummaryFindingsPresentRateComparison = (
                findings_config.rate_comparison
            )
            rate_direction: Literal['higher'] | Literal['lower'] = (
                'higher' if test.target_rate > test.baseline_rate else 'lower'
            )

            # Main interpretation
            main_template: str = rate_comp.main
            content.append(
                self.formatter.format_template(
                    main_template, target_location=self.target_location
                )
            )

            # Detailed risk ratio
            detail_template: str = rate_comp.detail
            content.append(
                self.formatter.format_template(
                    detail_template,
                    risk_ratio=self.formatter.format_number(
                        test.risk_ratio, decimals=2
                    ),
                    direction=rate_direction,
                    test_name=test.name.lower(),
                )
            )

            # Actual rates
            rates_template: str = rate_comp.rates
            content.append(
                self.formatter.format_template(
                    rates_template,
                    target_rate=self.formatter.format_percent(test.target_rate),
                    baseline_rate=self.formatter.format_percent(test.baseline_rate),
                )
            )

            # Odds ratio if substantially different from risk ratio
            if (
                not math.isnan(test.odds_ratio)
                and abs(test.odds_ratio - test.risk_ratio)
                > ODDS_RISK_RATIO_DIFFERENCE_THRESHOLD
            ):
                odds_template: str = rate_comp.odds_ratio
                content.append(
                    self.formatter.format_template(
                        odds_template,
                        odds_ratio=self.formatter.format_number(
                            test.odds_ratio, decimals=2
                        ),
                    )
                )

        # ====================================================================
        # Cost Comparison Finding (Cliff's Delta)
        # ====================================================================
        elif test.effect_size_name == "Cliff's Delta":
            cost_comp: ExecutiveSummaryFindingsPresentCostComparison = (
                findings_config.cost_comparison
            )
            effect_direction: Literal['higher'] | Literal['lower'] = (
                'higher' if test.effect_size and test.effect_size > 0 else 'lower'
            )

            # Main interpretation
            main_template = cost_comp.main
            content.append(
                self.formatter.format_template(main_template, test_name=test.name)
            )

            # Average costs if available
            if not math.isnan(test.target_avg) and not math.isnan(test.baseline_avg):
                averages_template: str = cost_comp.averages
                content.append(
                    self.formatter.format_template(
                        averages_template,
                        target_avg=self.formatter.format_currency(test.target_avg),
                        baseline_avg=self.formatter.format_currency(test.baseline_avg),
                    )
                )

            # Effect size
            effect_template: str = cost_comp.effect
            content.append(
                self.formatter.format_template(
                    effect_template,
                    effect_size=self.formatter.format_number(
                        test.effect_size, decimals=3
                    ),
                    direction=effect_direction,
                )
            )

        # ====================================================================
        # Statistical Strength
        # ====================================================================
        stat_strength: ExecutiveSummaryFindingsPresentStatisticalStrength = (
            findings_config.statistical_strength
        )

        main_template = stat_strength.main
        content.append(
            self.formatter.format_template(
                main_template,
                p_value=self.formatter.format_p_value(test.p_value),
                q_value=self.formatter.format_number(test.q_value, decimals=4),
            )
        )

        interpretation: str = stat_strength.interpretation
        content.append(interpretation)

        # ====================================================================
        # Risk Difference (if applicable and substantial)
        # ====================================================================
        if not math.isnan(test.target_rate) and not math.isnan(test.baseline_rate):
            risk_diff: float = abs(test.target_rate - test.baseline_rate)
            threshold: str | None | float = findings_config.risk_difference.get(
                'threshold', 0.05
            )

            if isinstance(threshold, float) and risk_diff >= threshold:
                rd_template: str | None | float = findings_config.risk_difference.get(
                    'format', ''
                )
                direction: Literal['increase'] | Literal['decrease'] = (
                    'increase' if test.target_rate > test.baseline_rate else 'decrease'
                )
                if isinstance(rd_template, str):
                    content.append(
                        self.formatter.format_template(
                            rd_template,
                            risk_diff=self.formatter.format_percent(risk_diff),
                            direction=direction,
                        )
                    )

    def _write_executive_summary_recommendation(self, content: list[str]) -> None:
        """
        Write final recommendation section for executive summary.

        Provides actionable guidance based on the findings.

        Args:
            content: list to append formatted lines to

        Responsibility:
            - Display recommendation marker and text
            - Format closing separator
        """
        content.append('\n' + self.formatter.separator('='))

        recommendation: ExecutiveSummaryRecommendation = (
            self.new_config.executive_summary.recommendation
        )
        marker: str = recommendation.marker
        text: str = recommendation.text

        content.append(f'{marker} {text}')
        content.append(self.formatter.separator('='))

    # ============================================================================
    # REPORT FOOTER
    # ============================================================================

    def write_report_footer(
        self, all_tests: dict[str, 'StatisticalTest'], data_coverage: dict[str, Any]
    ) -> None:
        """
        Generate final report section with metadata and statistical summary.

        This orchestrator method coordinates the footer generation, which provides
        transparency about data coverage, statistical rigor, and report metadata.

        Args:
            all_tests: dictionary of all completed StatisticalTest objects
            data_coverage: dictionary containing data coverage statistics

        Responsibility:
            - Coordinate footer section flow
            - Delegate to specialized helper methods
            - Assemble complete footer
        """
        content: list[str] = []

        # ====================================================================
        # Section 1: Header
        # ====================================================================
        self._write_section_header(content, 'report_footer')

        # ====================================================================
        # Section 2: Data Coverage
        # ====================================================================
        self._write_footer_data_coverage(content, data_coverage)

        # ====================================================================
        # Section 3: Statistical Rigor
        # ====================================================================
        self._write_footer_statistical_rigor(content, all_tests)

        # ====================================================================
        # Section 4: Test Summary Table
        # ====================================================================
        if all_tests:
            self._write_footer_test_summary(content, all_tests)

        # ====================================================================
        # Section 5: Report Metadata
        # ====================================================================
        self._write_footer_metadata(content)

        # ====================================================================
        # Section 6: Disclaimer
        # ====================================================================
        self._write_footer_disclaimer(content)

        # ====================================================================
        # Section 7: Closing
        # ====================================================================
        self._write_footer_closing(content)

        # Add completed section to report
        self.add_to_section(ReportSection.FOOTER, '\n'.join(content))

    def _write_footer_data_coverage(
        self, content: list[str], data_coverage: dict[str, Any]
    ) -> None:
        """
        Write data coverage section showing what data was analyzed.

        Provides transparency about the scope and completeness of the
        data included in the analysis.

        Args:
            content: list to append formatted lines to
            data_coverage: dictionary containing data coverage statistics

        Responsibility:
            - Display total records analyzed
            - Show target vs other location breakdowns
            - Report ELD match rates
        """
        footer: ReportFooter = self.new_config.report_footer
        coverage: ReportFooterDataCoverage = footer.data_coverage

        title: str = coverage.title
        content.append(f'\n{title}')
        content.append(self.formatter.separator('-'))

        coverage_items: list[str] = coverage.items

        for item_template in coverage_items:
            formatted_item: str = self.formatter.format_template(
                item_template,
                target_location=self.target_location,
                total_records=self.formatter.format_integer(
                    data_coverage['total_records']
                ),
                analysis_records=self.formatter.format_integer(
                    data_coverage['analysis_records']
                ),
                target_records=self.formatter.format_integer(
                    data_coverage['target_records']
                ),
                target_pct=self.formatter.format_percent(
                    data_coverage['target_records'] / data_coverage['analysis_records']
                ),
                other_records=self.formatter.format_integer(
                    data_coverage['other_records']
                ),
                other_pct=self.formatter.format_percent(
                    data_coverage['other_records'] / data_coverage['analysis_records']
                ),
                eld_match_rate=self.formatter.format_percent(
                    data_coverage['eld_match_rate']
                ),
            )
            content.append(formatted_item)

    def _write_footer_statistical_rigor(
        self, content: list[str], all_tests: dict[str, 'StatisticalTest']
    ) -> None:
        """
        Write statistical rigor section showing test methodology.

        Provides transparency about the statistical methods used
        and the overall rigor of the analysis.

        Args:
            content: list to append formatted lines to
            all_tests: dictionary of all completed StatisticalTest objects

        Responsibility:
            - Count and display number of tests performed
            - Show significance rate
            - Display confidence level and alpha threshold
        """
        num_significant: int = sum(
            1 for test in all_tests.values() if test.is_significant
        )

        footer: ReportFooter = self.new_config.report_footer
        rigor: ReportFooterStatisticalRigor = footer.statistical_rigor

        title: str = rigor.title
        self._write_subsection_header(content, title)

        rigor_items: list[str] = rigor.items

        for item_template in rigor_items:
            formatted_item: str = self.formatter.format_template(
                item_template,
                total_tests=len(all_tests),
                significant_count=num_significant,
                significant_pct=self.formatter.format_percent(
                    num_significant / len(all_tests) if all_tests else 0
                ),
                confidence_level=self.formatter.format_percent(
                    self.confidence_level, decimals=0
                ),
                alpha=self.formatter.format_number(
                    1 - self.confidence_level, decimals=2
                ),
            )
            content.append(formatted_item)

    def _write_footer_test_summary(
        self, content: list[str], all_tests: dict[str, 'StatisticalTest']
    ) -> None:
        """
        Write test summary table showing all tests performed.

        Provides a comprehensive table of all statistical tests,
        their p-values, q-values, and significance status.

        Args:
            content: list to append formatted lines to
            all_tests: dictionary of all completed StatisticalTest objects

        Responsibility:
            - Format test summary table header
            - Sort tests by significance and p-value
            - Display each test with its metrics
        """
        footer: ReportFooter = self.new_config.report_footer
        test_summary: ReportFooterTestSummary = footer.test_summary

        title: str = test_summary.title
        self._write_subsection_header(content, title)

        # ====================================================================
        # Table Header
        # ====================================================================
        headers: ReportFooterTestSummaryTableHeaders = test_summary.table_headers
        header_dict: dict[str, str] = {
            'test_name': headers.test_name,
            'raw_p_value': headers.raw_p_value,
            'q_value': headers.q_value,
            'significant': headers.significant,
        }

        # Define column specs
        column_specs: dict[str, dict[str, int | str]] = {
            'test_name': {'width': 35, 'format': 'string', 'truncate': 35},
            'raw_p_value': {'width': 15, 'format': 'number', 'decimals': 4},
            'q_value': {'width': 15, 'format': 'number', 'decimals': 4},
            'significant': {'width': 12, 'format': 'string'},
        }

        # ====================================================================
        # Table Rows (sorted by significance, then p-value)
        # ====================================================================
        sorted_tests: list[StatisticalTest] = sorted(
            all_tests.values(),
            key=lambda x: (not x.is_significant, math.isnan(x.p_value), x.p_value),
        )

        rows: list[dict[str, str | float]] = []
        for test in sorted_tests:
            rows.append(
                {
                    'test_name': test.name,
                    'raw_p_value': test.p_value,
                    'q_value': test.q_value if not math.isnan(test.q_value) else 'N/A',
                    'significant': self._format_significance_marker(
                        test.is_significant
                    ),
                }
            )

        # Generate table
        table_lines: list[str] = self._create_table(header_dict, rows, column_specs)
        content.extend(table_lines)

    def _write_footer_metadata(self, content: list[str]) -> None:
        """
        Write report metadata section.

        Displays key information about when and how the report was generated.

        Args:
            content: list to append formatted lines to

        Responsibility:
            - Display report date and analysis period
            - Show target location information
            - Display system name and version
        """
        footer: ReportFooter = self.new_config.report_footer
        metadata: ReportFooterReportMetadata = footer.report_metadata

        title: str = metadata.title
        self._write_subsection_header(content, title)

        system_name: str = self.new_config.metadata.system.name
        version: str = self.new_config.metadata.system.version

        metadata_items: list[str] = metadata.items

        for item_template in metadata_items:
            formatted_item: str = self.formatter.format_template(
                item_template,
                report_date=self.report_date,
                analysis_period=self.analysis_period,
                target_location=self.target_location,
                target_location_number=self.target_location_number,
                system_name=system_name,
                version=version,
            )
            content.append(formatted_item)

    def _write_footer_disclaimer(self, content: list[str]) -> None:
        """
        Write important disclaimer section.

        Provides legal and interpretive context about the limitations
        and proper use of the analysis.

        Args:
            content: list to append formatted lines to

        Responsibility:
            - Display disclaimer title
            - Show all disclaimer paragraphs
        """
        footer: ReportFooter = self.new_config.report_footer
        disclaimer: ReportFooterDisclaimer = footer.disclaimer

        content.append(f'\n{self.formatter.separator("-")}')
        content.append(disclaimer.title)
        content.append(self.formatter.separator('-'))

        for para in disclaimer.paragraphs:
            content.append(para)

    def _write_footer_closing(self, content: list[str]) -> None:
        """
        Write closing section with centered text.

        Displays final closing message with system branding.

        Args:
            content: list to append formatted lines to

        Responsibility:
            - Display centered closing message
            - Show system attribution
            - Format final separator
        """
        footer: ReportFooter = self.new_config.report_footer
        closing: ReportFooterClosing = footer.closing

        system_name: str = self.new_config.metadata.system.name
        system_full_name: str = self.new_config.metadata.system.full_name

        content.append('\n' + self.formatter.separator('='))

        # Main closing message (centered)
        main_message: str = closing.main
        content.append(self.formatter.center_text(main_message))

        # Subtitle with system attribution (centered)
        subtitle_template: str = closing.subtitle
        subtitle: str = self.formatter.format_template(
            subtitle_template,
            system_name=system_name,
            system_full_name=system_full_name,
        )
        content.append(self.formatter.center_text(subtitle))

        content.append(self.formatter.separator('='))

    # ============================================================================
    # REPORT RENDERING AND SAVING
    # ============================================================================

    def render_report(self) -> None:
        """
        Render the complete report in the correct order.

        Outputs all report sections in their defined order using
        the configured output method (print or logging).

        Responsibility:
            - Iterate through sections in correct order
            - Output each section's content
        """
        for section in ReportSection:
            if self.sections[section]:
                for content in self.sections[section]:
                    logger.info(content)

    def save_report(self, filepath: str) -> None:
        """
        Save the complete report to a file.

        Writes all report sections in their defined order to
        the specified file path.

        Args:
            filepath: Path where the report should be saved

        Responsibility:
            - Create/open output file
            - Write all sections in correct order
            - Ensure proper file closure
        """
        path_obj = Path(filepath)
        with Path.open(path_obj, mode='w') as f:
            for section in ReportSection:
                if self.sections[section]:
                    for content in self.sections[section]:
                        f.write(content + '\n')
