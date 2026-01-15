# argus/models/locale/interpretations.py
"""
============================================================================
TEST RESULT INTERPRETATIONS
============================================================================
Standard interpretation templates for different test types and outcomes.
Used to generate consistent, readable explanations of statistical results.
These templates ensure that the interpretation of statistical tests is clear and
consistent across different reports and analyses.
============================================================================
"""

from pydantic import Field

from argus.models.common import FormatStr, FrozenModel, P

__all__: list[str] = [
    'TestInterpretations',
    'TestInterpretationsCliffsDelta',
    'TestInterpretationsCohensD',
    'TestInterpretationsCostDistribution',
    'TestInterpretationsCostDistributionNotSignificant',
    'TestInterpretationsCostDistributionSignificant',
    'TestInterpretationsPValues',
    'TestInterpretationsRateComparison',
    'TestInterpretationsRateComparisonNotSignificant',
    'TestInterpretationsRateComparisonSignificant',
]


class TestInterpretationsCostDistributionSignificant(FrozenModel):
    """
    Interpretation template for significant cost distribution differences.

    Used when Mann-Whitney U or similar test finds significant difference
    in transaction cost distributions between groups.

    Attributes:
        title: Executive finding header for significant results
        direction: Template stating direction of difference
        difference: Template showing mean difference magnitude
    """

    title: str = Field(description='Header indicating significant finding')
    direction: FormatStr[P.TestInterpCostDirection] = Field(
        description='Template stating whether target is higher/lower (includes placeholders)'
    )
    difference: FormatStr[P.TestInterpCostDifference] = Field(
        description='Template showing mean difference amount'
    )


class TestInterpretationsCostDistributionNotSignificant(FrozenModel):
    """
    Interpretation template for non-significant cost differences.

    Used when statistical test doesn't find reliable difference after FDR correction.

    Attributes:
        title: Executive finding header for non-significant results
        message: Explanation that difference isn't statistically reliable
    """

    title: str = Field(description='Header indicating non-significant result')
    message: str = Field(
        description="Explanation that difference doesn't meet reliability threshold"
    )


class TestInterpretationsCostDistribution(FrozenModel):
    """
    Interpretation templates for cost distribution comparisons.

    Provides different messages depending on whether results are statistically
    significant after FDR correction.

    Attributes:
        significant: Template for significant results
        not_significant: Template for non-significant results
    """

    significant: TestInterpretationsCostDistributionSignificant
    not_significant: TestInterpretationsCostDistributionNotSignificant


class TestInterpretationsRateComparisonSignificant(FrozenModel):
    """
    Interpretation template for significant rate/proportion differences.

    Used for categorical tests (chi-square, Fisher's exact) when target
    location has significantly different event rate.

    Attributes:
        title: Executive finding header for significant results
        interpretation: Template explaining risk ratio magnitude
        context: Additional context about null hypothesis
    """

    title: str = Field(description='Header indicating significant finding')
    interpretation: FormatStr[P.TestInterpRateSignificant] = Field(
        description='Template explaining risk ratio interpretation'
    )
    context: FormatStr[P.TestInterpRateContext] = Field(
        description='Context statement about null hypothesis rejection'
    )


class TestInterpretationsRateComparisonNotSignificant(FrozenModel):
    """
    Interpretation template for non-significant rate differences.

    Attributes:
        title: Executive finding header for non-significant results
        message: Explanation that difference isn't statistically reliable
    """

    title: str = Field(description='Header indicating non-significant result')
    message: str = Field(
        description="Explanation that difference doesn't meet reliability threshold"
    )


class TestInterpretationsRateComparison(FrozenModel):
    """
    Interpretation templates for rate/proportion comparisons.

    Used for categorical tests comparing event frequencies between groups.

    Attributes:
        significant: Template for significant results
        not_significant: Template for non-significant results
    """

    significant: TestInterpretationsRateComparisonSignificant
    not_significant: TestInterpretationsRateComparisonNotSignificant


class TestInterpretationsCliffsDelta(FrozenModel):
    """
    Format string for Cliff's Delta effect size reporting.

    Cliff's Delta quantifies the degree of stochastic dominance between
    two groups. The format string template includes placeholders for
    magnitude and direction.

    Attributes:
        format: Format string for full interpretation
    """

    format: FormatStr[P.TestInterpEffectSize] = Field(
        description="Format string for Cliff's Delta interpretation (e.g., '({magnitude} effect, {target_location} costs are {direction})')"
    )


class TestInterpretationsCohensD(FrozenModel):
    """
    Format string for Cohen's D effect size reporting.

    Cohen's D quantifies the standardized mean difference between two groups.
    The format string template includes placeholders for magnitude and direction.

    Attributes:
        format: Format string for full interpretation
    """

    format: FormatStr[P.TestInterpEffectSize] = Field(
        description="Format string for Cohen's D interpretation (e.g., '({magnitude} effect, {target_location} costs are {direction})')"
    )


class TestInterpretationsPValues(FrozenModel):
    """
    Format strings for p-value significance levels.

    Attributes:
        highly_significant: Format string for highly significant results (p < 0.001)
        very_significant: Format string for very significant results (p < 0.01)
        significant: Format string for significant results (p < 0.05)
        not_significant: Format string for non-significant results (p >= 0.05)
    """

    highly_significant: FormatStr[P.TestInterpPValueHighlySignificant] = Field(
        description='Format string for highly significant results (p < 0.001)'
    )
    very_significant: FormatStr[P.TestInterpPValueFormatted] = Field(
        description='Format string for very significant results (p < 0.01)'
    )
    significant: FormatStr[P.TestInterpPValueFormatted] = Field(
        description='Format string for significant results (p < 0.05)'
    )
    not_significant: FormatStr[P.TestInterpPValueFormatted] = Field(
        description='Format string for non-significant results (p >= 0.05)'
    )


class TestInterpretations(FrozenModel):
    """
    Complete collection of test interpretation templates.

    Provides consistent language for explaining different types of
    statistical test results to non-technical stakeholders.

    Attributes:
        cost_distribution: Templates for cost comparison tests
        rate_comparison: Templates for rate/proportion comparison tests
        cliffs_delta: Format for Cliff's Delta interpretation
        cohens_d: Format for Cohen's D interpretation
        p_value: Format strings for p-value significance levels
    """

    cost_distribution: TestInterpretationsCostDistribution
    rate_comparison: TestInterpretationsRateComparison
    cliffs_delta: TestInterpretationsCliffsDelta
    cohens_d: TestInterpretationsCohensD
    p_value: TestInterpretationsPValues
