# argus/models/locale/methodology.py
"""
============================================================================
STATISTICAL METHODOLOGY
============================================================================
Comprehensive explanation of all statistical methods used in analysis.
Provides legal defensibility and helps stakeholders understand rigor. These
schemas define the structure for documenting statistical methods, ensuring
consistency and clarity in documentation.
============================================================================
"""

from pydantic import Field

from argus.models.common import FormatStr, FormatStrList, FrozenModel, P

__all__: list[str] = [
    'StatisticalMethodology',
    'StatisticalMethodologyEffectOddsRatio',
    'StatisticalMethodologyEffectRiskDifference',
    'StatisticalMethodologyEffectRiskRatio',
    'StatisticalMethodologyEffectSizes',
    'StatisticalMethodologyIndependenceTests',
    'StatisticalMethodologyMultipleTesting',
    'StatisticalMethodologyNonParametricCliffsDelta',
    'StatisticalMethodologyNonParametricCohensD',
    'StatisticalMethodologyNonParametricItem',
    'StatisticalMethodologyNonParametricTests',
    'StatisticalMethodologySignificance',
    'StatisticalMethodologySignificanceConfidenceIntervals',
    'StatisticalMethodologySignificancePValue',
]


class StatisticalMethodologyEffectRiskRatio(FrozenModel):
    """
    Risk Ratio effect size documentation with locale-specific formatting.

    Risk Ratio (RR) provides a multiplicative comparison of event probabilities
    between groups. Uses parameterized format strings to support locale-specific
    terminology and thresholds.

    Attributes:
        label: Display name for Risk Ratio measure
        description: Technical definition with locale-specific target location parameter
        interpretation: Interpretation guidelines with locale-specific threshold parameters
    """

    label: str = Field(description='Display name for this effect size measure')
    description: FormatStr[P.MethodologyTargetLocation] = Field(
        description='Technical definition and explanation of the measure'
    )
    interpretation: FormatStrList[P.MethodologyRiskRatioThresholds] = Field(
        description="List of interpretation guidelines (e.g., 'RR > 2.0: Substantial difference')",
    )


class StatisticalMethodologyEffectOddsRatio(FrozenModel):
    """
    Odds Ratio effect size documentation with locale-specific interpretation.

    Odds Ratio (OR) measures the strength of association between variables,
    commonly used in case-control studies and logistic regression contexts.

    Attributes:
        label: Display name for Odds Ratio measure
        description: Technical definition (non-parameterized string)
        interpretation: Interpretation guidelines with locale-specific threshold parameters
    """

    label: str = Field(description='Display name for this effect size measure')
    description: str = Field(
        description='Technical definition and explanation of the measure'
    )
    interpretation: FormatStrList[P.MethodologyOddsRatioThresholds] = Field(
        description="List of interpretation guidelines (e.g., 'OR > 3.0: Strong association')",
    )


class StatisticalMethodologyEffectRiskDifference(FrozenModel):
    """
    Risk Difference effect size documentation with locale-specific interpretation.

    Risk Difference (RD) provides the absolute difference in event rates between
    groups, expressed as a percentage or proportion. Useful for assessing practical
    significance alongside relative measures.

    Attributes:
        label: Display name for Risk Difference measure
        description: Technical definition (non-parameterized string)
        interpretation: Interpretation guidelines with locale-specific threshold parameters
    """

    label: str = Field(description='Display name for this effect size measure')
    description: str = Field(
        description='Technical definition and explanation of the measure'
    )
    interpretation: FormatStrList[P.MethodologyRiskDiffThresholds] = Field(
        description="List of interpretation guidelines (e.g., 'RD > 10%: Substantial difference')",
    )


class StatisticalMethodologyEffectSizes(FrozenModel):
    """
    Documentation of effect size measures used in analysis.

    Three primary effect sizes are used:
    - Risk Ratio: Multiplicative comparison of event probabilities
    - Odds Ratio: Strength of association measure
    - Risk Difference: Absolute difference in event rates

    Attributes:
        section_header: Header for the effect sizes section
        risk_ratio: Risk Ratio definition and interpretation
        odds_ratio: Odds Ratio definition and interpretation
        risk_difference: Risk Difference definition and interpretation
    """

    section_header: str = Field(description='Section header for effect size measures')
    risk_ratio: StatisticalMethodologyEffectRiskRatio
    odds_ratio: StatisticalMethodologyEffectOddsRatio
    risk_difference: StatisticalMethodologyEffectRiskDifference


class StatisticalMethodologySignificancePValue(FrozenModel):
    """
    Documentation of p-value interpretation.

    P-values indicate the probability of observing results as extreme as
    those obtained, assuming the null hypothesis is true.

    Attributes:
        label: Display label for p-value
        description: Technical definition of p-value
        interpretation: Guidelines for interpreting different p-value ranges
        note: Additional context about significance threshold
    """

    label: str = Field(description='Display label for p-value concept')
    description: str = Field(
        description='Technical definition of what p-value represents'
    )
    interpretation: FormatStrList[P.MethodologyPValueThresholds] = Field(
        description='Guidelines for interpreting p-value magnitudes'
    )
    note: FormatStr[P.MethodologySignificanceNote] = Field(
        description='Context about significance threshold (alpha) being used'
    )


class StatisticalMethodologySignificanceConfidenceIntervals(FrozenModel):
    """
    Documentation of confidence interval interpretation.

    Confidence intervals provide a range of plausible values for true parameters.

    Attributes:
        label: Display label for confidence intervals
        description: Technical definition of confidence intervals
        interpretation: How to interpret CI in context of hypothesis testing
    """

    label: str = Field(description='Display label for confidence interval concept')
    description: str = Field(
        description='Technical definition of what confidence intervals represent'
    )
    interpretation: str = Field(
        description='How to interpret confidence intervals for hypothesis testing'
    )


class StatisticalMethodologySignificance(FrozenModel):
    """
    Documentation of statistical significance concepts.

    Explains p-values and confidence intervals used to assess whether
    findings are statistically reliable.

    Attributes:
        section_header: Header for the significance section
        p_value: P-value documentation
        confidence_intervals: Confidence interval documentation
    """

    section_header: str = Field(
        description='Section header for statistical significance'
    )
    p_value: StatisticalMethodologySignificancePValue
    confidence_intervals: StatisticalMethodologySignificanceConfidenceIntervals


class StatisticalMethodologyNonParametricItem(FrozenModel):
    """
    Documentation of a general non-parametric test without interpretation guidelines.

    Used for tests where interpretation is straightforward from p-values alone,
    such as Mann-Whitney U test. Does not include effect size interpretation.

    Attributes:
        label: Display name for this test
        description: What this test measures and when it's used
    """

    label: str = Field(
        description='Display name for this non-parametric test or measure'
    )
    description: str = Field(
        description='Explanation of what this test measures and its purpose'
    )


class StatisticalMethodologyNonParametricCliffsDelta(FrozenModel):
    """
    Cliff's Delta effect size documentation with locale-specific interpretation.

    Cliff's Delta is a non-parametric effect size measure that quantifies the
    degree to which values in one group tend to be larger than values in another.
    Ranges from -1 to +1, with 0 indicating no difference.

    Attributes:
        label: Display name for Cliff's Delta
        description: Technical definition and explanation
        interpretation: Guidelines with locale-specific threshold parameters
    """

    label: str = Field(
        description='Display name for this non-parametric test or measure'
    )
    description: str = Field(
        description='Explanation of what this test measures and its purpose'
    )
    interpretation: FormatStrList[P.MethodologyCliffsDeltaThresholds] = Field(
        description='Guidelines for interpreting effect size magnitudes'
    )


class StatisticalMethodologyNonParametricCohensD(FrozenModel):
    """
    Cohen's d effect size documentation with locale-specific interpretation.

    Cohen's d measures standardized difference between two means. While
    traditionally parametric, it can be calculated with robust estimators
    for use with non-parametric tests.

    Attributes:
        label: Display name for Cohen's d
        description: Technical definition and explanation
        interpretation: Guidelines with locale-specific threshold parameters
    """

    label: str = Field(
        description='Display name for this non-parametric test or measure'
    )
    description: str = Field(
        description='Explanation of what this test measures and its purpose'
    )
    interpretation: FormatStrList[P.MethodologyCohensDThresholds] = Field(
        description='Guidelines for interpreting effect size magnitudes'
    )


class StatisticalMethodologyNonParametricTests(FrozenModel):
    """
    Documentation of non-parametric tests used in analysis.

    Includes Mann-Whitney U test and associated effect sizes (Cliff's Delta
    and Cohen's d).

    Attributes:
        section_header: Header for non-parametric tests section
        mann_whitney: Mann-Whitney U test documentation
        cliffs_delta: Cliff's Delta effect size documentation
        cohens_d: Cohen's d effect size documentation
    """

    section_header: str = Field(description='Section header for non-parametric tests')
    mann_whitney: StatisticalMethodologyNonParametricItem
    cliffs_delta: StatisticalMethodologyNonParametricCliffsDelta
    cohens_d: StatisticalMethodologyNonParametricCohensD


class StatisticalMethodologyIndependenceTests(FrozenModel):
    """
    Documentation of independence/association tests.

    These tests assess relationships between categorical variables.

    Attributes:
        section_header: Header for independence tests section
        chi_square: Chi-square test documentation
        fishers_exact: Fisher's exact test documentation
        cramers_v: Cramér's V effect size documentation
    """

    section_header: str = Field(description='Section header for independence tests')
    chi_square: StatisticalMethodologyNonParametricItem
    fishers_exact: StatisticalMethodologyNonParametricItem
    cramers_v: StatisticalMethodologyNonParametricItem


class StatisticalMethodologyMultipleTesting(FrozenModel):
    """
    Documentation of multiple testing correction procedure.

    The Benjamini-Hochberg procedure controls the False Discovery Rate (FDR)
    when performing multiple hypothesis tests simultaneously.

    Attributes:
        section_header: Header for multiple testing section
        label: Name of the correction method
        description: What FDR control means and why it's necessary
        procedure: How the correction is applied
    """

    section_header: str = Field(
        description='Section header for multiple testing correction'
    )
    label: str = Field(description='Name of the multiple testing correction method')
    description: str = Field(description='Explanation of False Discovery Rate control')
    procedure: FormatStr[P.MethodologyAlpha] = Field(
        description='How the Benjamini-Hochberg procedure is applied'
    )


class StatisticalMethodology(FrozenModel):
    """
    Complete statistical methodology documentation.

    This section provides comprehensive explanation of all statistical
    techniques used in the analysis, supporting legal defensibility and
    stakeholder understanding.

    Attributes:
        section_title: Main title for methodology section
        introduction: Introductory paragraph about statistical rigor
        effect_sizes: Effect size measure documentation
        significance: Statistical significance documentation
        non_parametric: Non-parametric test documentation
        independence: Independence test documentation
        multiple_testing: Multiple testing correction documentation
        assumptions: Statement about statistical assumptions and limitations
    """

    section_title: str = Field(
        description='Main title for the statistical methodology section'
    )
    introduction: str = Field(
        description='Introductory text about statistical rigor and techniques'
    )
    effect_sizes: StatisticalMethodologyEffectSizes
    significance: StatisticalMethodologySignificance
    non_parametric: StatisticalMethodologyNonParametricTests
    independence: StatisticalMethodologyIndependenceTests
    multiple_testing: StatisticalMethodologyMultipleTesting
    assumptions: str = Field(
        description='Statement about statistical assumptions and their limitations'
    )
