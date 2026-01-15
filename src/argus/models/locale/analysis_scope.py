# argus/models/locale/analysis_scope.py
"""
============================================================================
ANALYSIS SCOPE
============================================================================
Content defining and explaining the temporal scope of analysis, including
logic for splitting data across multiple years when appropriate. The logic
for determining the appropriate scope is based on the availability and quality
of data across different years. The final scope is summarized in a box at the
end of the report, summarizing the key statistics and data included in the analysis.
============================================================================
"""

from pydantic import Field

from argus.models.common import FrozenModel
from argus.models.locale.placeholder_registry import P
from argus.models.locale.placeholder_validators import FormatStr

__all__: list[str] = [
    'AnalysisScope',
    'AnalysisScopeLabels',
    'AnalysisScopeScenarios',
    'InsufficientScenarioItem',
    'SingleScenarioItem',
    'SplitScenarioItem',
]


class AnalysisScopeLabels(FrozenModel):
    """
    Labels for analysis scope summary statistics.

    These appear in the scope summary box that defines what data is included.

    Attributes:
        branches: Label for number of branches analyzed
        date_range: Label for analysis date range
        total_transactions: Label for transaction count
    """

    branches: str = Field(description='Label for branch count statistic')
    date_range: str = Field(description='Label for date range of analysis')
    total_transactions: str = Field(description='Label for total transaction count')


class SplitScenarioItem(FrozenModel):
    """
    Explanation for split analysis scenario.

    This scenario applies when data spans multiple years with sufficient
    current-year coverage to warrant focused analysis.

    Required placeholders:
        - min_year: First year in the dataset
        - current_year: Most recent year being analyzed
        - num_months_current_year: Number of months available in current year

    Attributes:
        description: Multi-line explanation including year range and rationale
    """

    description: FormatStr[P.ScopeSplitScenario] = Field(
        description='Explanation of split scope strategy with year placeholders'
    )


class InsufficientScenarioItem(FrozenModel):
    """
    Explanation for insufficient current-year data scenario.

    This scenario applies when data spans multiple years but the current
    year has too few months to support separate analysis.

    Required placeholders:
        - num_months_current_year: Number of months available (insufficient)

    Attributes:
        description: Multi-line explanation of why unified analysis is used
    """

    description: FormatStr[P.ScopeInsufficientScenario] = Field(
        description='Explanation of unified scope due to insufficient current data'
    )


class SingleScenarioItem(FrozenModel):
    """
    Explanation for single-year analysis scenario.

    This scenario applies when data does not span multiple years or lacks
    sufficient history for meaningful temporal splitting.

    Required placeholders: None - this is static explanatory text.

    Attributes:
        description: Multi-line explanation of single-period analysis
    """

    # No placeholders required - just a plain string
    description: str = Field(
        description='Explanation of single-period unified analysis'
    )


class AnalysisScopeScenarios(FrozenModel):
    """
    Collection of all analysis scope scenario explanations.

    Three scenarios are possible based on data span and current-year coverage:
    1. Split: Multi-year data with sufficient current year for focused analysis
    2. Insufficient: Multi-year data but inadequate current year data
    3. Single: Single-year or limited historical data

    Attributes:
        split: Explanation for split analysis approach
        insufficient: Explanation for unified analysis with insufficient current data
        single: Explanation for single-period analysis
    """

    split: SplitScenarioItem = Field(
        description='Scenario where current year is analyzed separately from historical baseline'
    )
    insufficient: InsufficientScenarioItem = Field(
        description='Scenario where insufficient current year data requires unified analysis'
    )
    single: SingleScenarioItem = Field(
        description="Scenario where data doesn't span multiple years"
    )


class AnalysisScope(FrozenModel):
    """
    Complete analysis scope section configuration.

    This section explains what data is included in the analysis and provides
    rationale for temporal scope decisions (e.g., focusing on current year
    vs. using full historical data).

    Attributes:
        section_title: Title for the analysis scope section
        final_scope_title: Title for the final scope summary box
        labels: Labels for scope statistics
        format: Format string for scope line items
        scenarios: Explanations for different scope strategies
    """

    section_title: str = Field(description='Main title for the analysis scope section')
    final_scope_title: str = Field(description='Title for the final scope summary box')
    labels: AnalysisScopeLabels
    format: str = Field(
        description="Format string for displaying scope items (e.g., '  • {label}: {value}')"
    )
    scenarios: AnalysisScopeScenarios
