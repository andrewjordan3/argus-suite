# argus/models/locale/root_config.py
"""
ARGUS Locale Configuration Models

This module defines Pydantic models for validating and accessing the locale YAML
configuration files used by the ARGUS (Analytics & Risk Governance Utility Suite)
fuel card forensic analysis system.

The locale configuration contains all language-specific content including:
- Display text and templates
- Formatting preferences (numbers, dates, currency)
- Report section content
- Localized labels and messages

By using Pydantic models instead of dictionary access, we gain:
- Strong type checking at runtime
- IDE autocomplete support
- Clear validation errors
- Self-documenting code structure
- Prevention of typos in configuration key access

Note: Business rules, thresholds, and numeric policy settings are stored in
separate policy and user configuration files, not in locale files.
"""

from pydantic import Field

from argus.models.common import BaseConfigModel
from argus.models.locale.analysis_scope import AnalysisScope
from argus.models.locale.corrections import MultipleTestingCorrection
from argus.models.locale.data_quality import DataPreparation, DataQuality
from argus.models.locale.driver_analysis import DriverAnalysis
from argus.models.locale.effect_size_labels import EffectSizeLabels
from argus.models.locale.executive_summary import ExecutiveSummary
from argus.models.locale.financial_impact import FinancialImpact
from argus.models.locale.geographic import GeographicAnalysis
from argus.models.locale.header_content import ReportHeader
from argus.models.locale.interpretations import TestInterpretations
from argus.models.locale.locale_settings import LocaleSettings
from argus.models.locale.methodology import StatisticalMethodology
from argus.models.locale.multi_fillup import MultiFillupAnalysis
from argus.models.locale.red_flags import RedFlags
from argus.models.locale.report_footer import ReportFooter
from argus.models.locale.report_metadata import Metadata
from argus.models.locale.risk_categories import RiskCategories
from argus.models.locale.temporal import TemporalAnalysis
from argus.models.locale.vehicle_analysis import VehicleAnalysis

__all__: list[str] = ['ReportConfig']

# ============================================================================
# ROOT MODEL (COMPLETE LOCALE CONFIGURATION)
# ============================================================================
# Top-level model that contains all locale configuration sections. This is the
# single entry point for loading and validating the entire locale YAML file.
# ============================================================================


class ReportConfig(BaseConfigModel):
    """
    Complete ARGUS locale configuration model.

    This is the root model that encompasses all locale-specific configuration
    for the ARGUS fuel card forensics report system. Load your locale YAML file
    (e.g., english.yaml, spanish.yaml) into this model to get validated,
    type-safe access to all localized content.

    Usage Example:
    ```python
        import yaml
        from ARGUS.models.locale.root_config import ReportConfig

        # Load locale YAML configuration
        with open('argus/locales/english.yaml', 'r') as f:
            config_dict = yaml.safe_load(f)

        # Parse and validate with Pydantic
        config = ReportConfig(**config_dict)

        # Access with type safety and IDE support
        currency_symbol = config.locale.currency_symbol
        system_name = config.metadata.system_name
        critical_label = config.risk_categories.critical.label
    ```

    Attributes:
        locale: Locale-specific formatting settings (numbers, dates, currency)
        metadata: System identification and report classification
        risk_categories: Risk category display labels
        effect_size_labels: Effect size interpretation labels
        red_flags: Red flag definitions for fraud detection
        report_header: Report header content and labels
        data_preparation: Data preparation section content
        data_quality: Data quality assessment content
        analysis_scope: Analysis scope section content
        statistical_methodology: Statistical methodology documentation
        multiple_testing_correction: Multiple testing correction content
        test_interpretations: Test result interpretation templates
        financial_impact: Financial impact analysis content
        executive_summary: Executive summary templates
        driver_analysis: Driver analysis section content
        vehicle_analysis: Vehicle analysis section content
        multi_fillup_analysis: Multi-fillup analysis content
        geographic_analysis: Geographic analysis content
        temporal_analysis: Temporal analysis content
        report_footer: Report footer content
    """

    # Section 1: Locale settings (formatting preferences)
    locale: LocaleSettings = Field(
        description='Locale-specific formatting for numbers, dates, and currency'
    )

    # Section 2: System and report metadata
    metadata: Metadata = Field(
        description='System identification and report classification'
    )

    # Section 3: Risk categories (display labels only, thresholds in policy)
    risk_categories: RiskCategories = Field(
        description='Risk category display labels and recommended actions'
    )

    # Section 4: Effect size labels
    effect_size_labels: EffectSizeLabels = Field(
        description='Localized labels for effect size magnitudes and directions'
    )

    # Section 5: Red flag definitions
    red_flags: RedFlags = Field(
        description='Red flag definitions for multi-fillup fraud detection'
    )

    # Section 6: Report header
    report_header: ReportHeader = Field(
        description='Report header titles and metadata labels'
    )

    # Section 7: Data preparation
    data_preparation: DataPreparation = Field(
        description='Data preparation summary section content'
    )

    # Section 8: Data quality
    data_quality: DataQuality = Field(
        description='Data quality assessment section content'
    )

    # Section 9: Analysis scope
    analysis_scope: AnalysisScope = Field(
        description='Analysis scope definition and explanation content'
    )

    # Section 10: Statistical methodology
    statistical_methodology: StatisticalMethodology = Field(
        description='Comprehensive statistical methodology documentation'
    )

    # Section 11: Multiple testing correction
    multiple_testing_correction: MultipleTestingCorrection = Field(
        description='Multiple testing correction table and explanation'
    )

    # Section 12: Test interpretations
    test_interpretations: TestInterpretations = Field(
        description='Standard interpretation templates for statistical tests'
    )

    # Section 13: Financial impact
    financial_impact: FinancialImpact = Field(
        description='Financial impact analysis section content'
    )

    # Section 14: Executive summary
    executive_summary: ExecutiveSummary = Field(
        description='Executive summary templates and content'
    )

    # Section 15: Driver analysis
    driver_analysis: DriverAnalysis = Field(
        description='Driver-level analysis section content'
    )

    # Section 16: Vehicle analysis
    vehicle_analysis: VehicleAnalysis = Field(
        description='Vehicle-level analysis section content'
    )

    # Section 17: Multi-fillup analysis
    multi_fillup_analysis: MultiFillupAnalysis = Field(
        description='Multiple same-day fillup analysis content'
    )

    # Section 18: Geographic analysis
    geographic_analysis: GeographicAnalysis = Field(
        description='Geographic/station usage analysis content'
    )

    # Section 19: Temporal analysis
    temporal_analysis: TemporalAnalysis = Field(
        description='Advanced temporal/time-based pattern analysis content'
    )

    # Section 20: Report footer
    report_footer: ReportFooter = Field(
        description='Report footer with summaries and disclaimers'
    )
