# argus/schemas/financial_impact.py
"""
============================================================================
FINANCIAL IMPACT ANALYSIS
============================================================================
Content for financial impact section showing costs, means, and potential
exposure from unverified transactions. This section quantifies the monetary
implications of findings, including potential exposure from unverified
transactions.
============================================================================
"""

from pydantic import Field

from argus.models.common import BaseConfigModel, FormatStr, FormatStrList, P

__all__: list[str] = [
    'FinancialImpact',
    'FinancialImpactLabels',
    'FinancialImpactSubsections',
]

class FinancialImpactSubsections(BaseConfigModel):
    """
    Headers for financial impact subsections.

    The financial impact section is divided into three analytical areas.

    Attributes:
        total_spend: Header for total spending comparison
        per_transaction: Header for per-transaction metrics
        exposure: Header for potential financial exposure calculation
    """

    total_spend: str = Field(
        description='Subsection header for total spending comparison'
    )
    per_transaction: str = Field(
        description='Subsection header for per-transaction average comparison'
    )
    exposure: str = Field(
        description='Subsection header for financial exposure from unverified transactions'
    )


class FinancialImpactLabels(BaseConfigModel):
    """
    Labels for financial metric line items.

    These labels appear in financial comparison sections.

    Attributes:
        target_total: Label for target location total (includes placeholder)
        baseline_total: Label for other branches total
        target_mean: Label for target location average (includes placeholder)
        baseline_mean: Label for other branches average
        mean_difference: Label for difference between averages
    """

    target_total: FormatStr[P.FinancialTargetLocation] = Field(
        description='Label for target location total spending (includes location name placeholder)'
    )
    baseline_total: str = Field(
        description='Label for other branches combined total spending'
    )
    target_mean: FormatStr[P.FinancialTargetLocation] = Field(
        description='Label for target location average cost (includes location name placeholder)'
    )
    baseline_mean: str = Field(description='Label for other branches average cost')
    mean_difference: str = Field(
        description='Label for difference between target and baseline means'
    )


class FinancialImpact(BaseConfigModel):
    """
    Complete financial impact analysis section configuration.

    This section quantifies the monetary implications of findings, including
    potential exposure from unverified transactions.

    Attributes:
        section_title: Title for financial impact section
        subsections: Headers for impact subsections
        labels: Labels for all financial metrics
        exposure_items: list of exposure calculation line items
        exposure_note: Explanatory note about exposure calculation
    """

    section_title: str = Field(
        description='Title for the financial impact analysis section'
    )
    subsections: FinancialImpactSubsections
    labels: FinancialImpactLabels
    exposure_items: FormatStrList[P.FinancialExposureItems] = Field(
        description='list of line items for exposure calculation (include placeholders)'
    )
    exposure_note: str = Field(description='Note explaining what exposure represents')
