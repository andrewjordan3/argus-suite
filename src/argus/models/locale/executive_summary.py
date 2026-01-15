# argus/schemas/executive_summary.py
"""
============================================================================
EXECUTIVE SUMMARY
============================================================================
Templates for executive summary based on statistical findings.
Different content is shown depending on whether significant findings exist.
The executive summary adapts based on the presence of significant findings,
providing either a "no concerns" message or detailed reporting of significant findings.
============================================================================
"""

from pydantic import Field

from argus.models.common import FrozenModel
from argus.models.locale.placeholder_registry import P
from argus.models.locale.placeholder_validators import FormatStr, FormatStrList

__all__: list[str] = [
    'ExecutiveSummary',
    'ExecutiveSummaryFindingsPresent',
    'ExecutiveSummaryFindingsPresentCostComparison',
    'ExecutiveSummaryFindingsPresentRateComparison',
    'ExecutiveSummaryFindingsPresentStatisticalStrength',
    'ExecutiveSummaryNoFindings',
    'ExecutiveSummaryRecommendation',
]


class ExecutiveSummaryNoFindings(FrozenModel):
    """
    Executive summary content when no significant findings exist.

    Used when all tests fail to reject null hypothesis after FDR correction.

    Attributes:
        title: Section title for no findings scenario
        paragraphs: list of paragraphs explaining the results
    """

    title: str = Field(
        description='Title when no statistically significant differences are detected'
    )
    paragraphs: FormatStrList[P.ExecSummaryNoFindings] = Field(
        description='Paragraphs explaining absence of significant findings'
    )


class ExecutiveSummaryFindingsPresentRateComparison(FrozenModel):
    """
    Template for reporting significant rate comparison findings.

    Used when categorical tests find significant differences in event rates.

    Attributes:
        main: Opening statement template
        detail: Risk ratio interpretation template
        rates: Template showing actual rates for both groups
        odds_ratio: Template showing odds ratio and its meaning
    """

    main: FormatStr[P.ExecSummaryRateComparisonMain] = Field(
        description='Opening statement of rate comparison finding'
    )
    detail: FormatStr[P.ExecSummaryRateComparisonDetail] = Field(
        description='Risk ratio interpretation (includes placeholders)'
    )
    rates: FormatStr[P.ExecSummaryRateComparisonRates] = Field(
        description='Display of actual rates for both groups'
    )
    odds_ratio: FormatStr[P.ExecSummaryRateComparisonOddsRatio] = Field(
        description='Odds ratio display and interpretation'
    )


class ExecutiveSummaryFindingsPresentCostComparison(FrozenModel):
    """
    Template for reporting significant cost comparison findings.

    Used when continuous cost comparisons find significant differences.

    Attributes:
        main: Opening statement template
        averages: Template showing average costs for both groups
        effect: Template showing effect size and direction
    """

    main: FormatStr[P.ExecSummaryCostComparisonMain] = Field(
        description='Opening statement of cost comparison finding'
    )
    averages: FormatStr[P.ExecSummaryCostComparisonAverages] = Field(
        description='Display of average costs for both groups'
    )
    effect: FormatStr[P.ExecSummaryCostComparisonEffect] = Field(
        description="Effect size (Cliff's Delta) display and interpretation"
    )


class ExecutiveSummaryFindingsPresentStatisticalStrength(FrozenModel):
    """
    Template for reporting statistical strength of findings.

    Shows p-values, q-values, and interpretation of reliability.

    Attributes:
        main: Template showing p-value and q-value
        interpretation: Statement about likelihood due to chance
    """

    main: FormatStr[P.ExecSummaryStatisticalStrength] = Field(
        description='Display of p-value and FDR-adjusted q-value'
    )
    interpretation: str = Field(description='Statement about statistical reliability')


class ExecutiveSummaryFindingsPresent(FrozenModel):
    """
    Executive summary content when significant findings exist.

    Provides structured templates for reporting each significant finding
    in a consistent, executive-friendly format.

    Attributes:
        header: Header template showing count of findings
        finding_title: Template for individual finding titles
        rate_comparison: Templates for rate comparison findings
        cost_comparison: Templates for cost comparison findings
        statistical_strength: Templates for statistical reliability statements
        risk_difference: Settings for risk difference reporting
    """

    header: FormatStr[P.ExecSummaryFindingsHeader] = Field(
        description='Header showing number of significant findings (includes placeholder)'
    )
    finding_title: FormatStr[P.ExecSummaryFindingTitle] = Field(
        description='Title template for individual findings (includes index and test name)'
    )
    rate_comparison: ExecutiveSummaryFindingsPresentRateComparison
    cost_comparison: ExecutiveSummaryFindingsPresentCostComparison
    statistical_strength: ExecutiveSummaryFindingsPresentStatisticalStrength
    risk_difference: FormatStr[P.ExecSummaryRiskDifference] = Field(
        description='Risk difference format string'
    )


class ExecutiveSummaryRecommendation(FrozenModel):
    """
    Recommendation section shown when significant findings exist.

    Provides guidance on next steps for investigation.

    Attributes:
        marker: Visual marker for recommendation (e.g., "⚠ RECOMMENDATION:")
        text: Recommendation text
    """

    marker: str = Field(description='Visual marker/label for recommendation section')
    text: str = Field(
        description='Recommendation text for addressing significant findings'
    )


class ExecutiveSummary(FrozenModel):
    """
    Complete executive summary section configuration.

    The executive summary adapts based on whether statistically significant
    findings exist, providing either a "no concerns" message or detailed
    reporting of significant findings.

    Attributes:
        section_title: Title for executive summary section
        introduction: Introductory statement about FDR correction
        no_findings: Content when no significant findings exist
        findings_present: Content and templates when findings exist
        recommendation: Recommendation section for significant findings
    """

    section_title: str = Field(description='Title for the executive summary section')
    introduction: str = Field(
        description='Introduction about FDR correction and reliability'
    )
    no_findings: ExecutiveSummaryNoFindings
    findings_present: ExecutiveSummaryFindingsPresent
    recommendation: ExecutiveSummaryRecommendation
