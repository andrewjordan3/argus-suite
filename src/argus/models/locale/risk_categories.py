# argus/models/locale/risk_categories.py
"""
============================================================================
RISK CATEGORIES
============================================================================
Localized text labels for risk level classifications. This module contains
only display text and recommended actions. Numeric thresholds are defined in
the policy configuration, not in locale settings.
============================================================================
"""

from pydantic import Field

from argus.models.common import BaseConfigModel

__all__: list[str] = ['RiskCategories', 'RiskCategoryItem']


class RiskCategoryItem(BaseConfigModel):
    """
    Display text for one risk category level.

    Contains only the localized text labels for risk categories.
    Numeric thresholds are configured separately in policy settings.

    Attributes:
        label: Display label for this risk level (e.g., "Critical", "High")
        action: Recommended action for this risk level
    """

    label: str = Field(description='Display label for this risk category')
    action: str = Field(description='Recommended action/response for this risk level')


class RiskCategories(BaseConfigModel):
    """
    Complete set of risk category display labels.

    Contains localized text for all four standard risk categories.
    Thresholds that determine which category applies are stored in
    the policy configuration.

    Attributes:
        critical: Critical risk category labels
        high: High risk category labels
        medium: Medium risk category labels
        low: Low risk category labels
    """

    critical: RiskCategoryItem = Field(
        description='Critical risk category (highest priority, immediate action)'
    )
    high: RiskCategoryItem = Field(
        description='High risk category (priority review recommended)'
    )
    medium: RiskCategoryItem = Field(
        description='Medium risk category (monitoring required)'
    )
    low: RiskCategoryItem = Field(
        description='Low risk category (within normal parameters)'
    )
