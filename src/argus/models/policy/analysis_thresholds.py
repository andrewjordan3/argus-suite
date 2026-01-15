# argus/models/policy/analysis_thresholds.py
"""
Defines configuration models for risk score and anomaly detection thresholds
used in policy evaluations within the Argus system.
"""

import logging
from enum import IntEnum, unique
from typing import Self

from pydantic import Field, model_validator

from argus.models.common import FrozenModel
from argus.utils.common_utils import is_missing_like

__all__: list[str] = [
    'AnomalyThresholds',
    'RiskCategory',
    'RiskScoreThresholds',
]

logger: logging.Logger = logging.getLogger(__name__)


@unique
class RiskCategory(IntEnum):
    """
    Risk severity categories with ordinal ranking.

    Integer values represent severity (higher = more severe), enabling
    direct comparisons: RiskCategory.CRITICAL > RiskCategory.HIGH evaluates True.

    Values are arbitrary but ordered; they are NOT score thresholds.
    """

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


# =============================================================================
# RISK THRESHOLDS CONFIGURATION
# =============================================================================
class RiskScoreThresholds(FrozenModel):
    """
    Thresholds for categorizing risk scores into severity levels.

    Risk scores range from 0-100. These thresholds define the cutoff
    points for Critical/High/Medium categories. Low risk is implicitly
    any score below the medium threshold.

    Attributes:
        critical: Minimum score for Critical risk (immediate investigation).
        high: Minimum score for High risk (priority review).
        medium: Minimum score for Medium risk (monitoring recommended).
    """

    critical: int = Field(
        default=75,
        description='Minimum score for Critical risk category',
        ge=0,
        le=100,
    )

    high: int = Field(
        default=50,
        description='Minimum score for High risk category',
        ge=0,
        le=100,
    )

    medium: int = Field(
        default=25,
        description='Minimum score for Medium risk category',
        ge=0,
        le=100,
    )

    @model_validator(mode='after')
    def validate_threshold_ordering(self) -> Self:
        """
        Ensure thresholds are in descending order: critical > high > medium.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If thresholds are not in proper descending order.
        """
        if not (self.critical > self.high > self.medium):
            raise ValueError(
                f'Risk thresholds must be in descending order: '
                f'critical ({self.critical}) > high ({self.high}) > '
                f'medium ({self.medium})'
            )
        return self

    @property
    def low(self) -> int:
        """
        Low risk threshold is implicitly 0.

        Returns:
            0 (scores below medium threshold are low risk).
        """
        return 0

    def get_risk_category(self, score: float) -> RiskCategory | None:
        """
                Determine risk category for a given score.

                Args:
                    score: Risk score (0-100).

                Returns:
                    RiskCategory enum value describing severity, or None if score is invalid.

                Note:
                    Invalid scores are defined as:
                        - NoneType
                        - Strings: Empty, whitespace, or common placeholders ('N/A', 'NULL')
                        - Floats: NaN and Infinity
                        - Pandas/NumPy: NaT or other library-specific nulls
                        - Outside 0-100 range
        """
        if is_missing_like(score) or not (0.0 <= score <= 100.0):  # noqa: PLR2004
            logger.warning(
                'Invalid risk score provided: %s. Must be float between 0 and 100. Returning None.',
                score,
            )
            return None  # Invalid score
        if score >= self.critical:
            return RiskCategory.CRITICAL
        if score >= self.high:
            return RiskCategory.HIGH
        if score >= self.medium:
            return RiskCategory.MEDIUM
        return RiskCategory.LOW


# =============================================================================
# ANOMALY THRESHOLDS CONFIGURATION
# =============================================================================
class AnomalyThresholds(FrozenModel):
    """
    Thresholds for flagging high rates of suspicious activity.

    These thresholds determine when a rate (proportion) is considered
    suspiciously high and should be flagged for investigation.

    All rates are on a 0-1 scale (0% to 100%).

    Attributes:
        high_no_eld_rate: Threshold for high rate of transactions without ELD match.
        high_non_diesel_rate: Threshold for high rate of non-diesel purchases.
        high_after_hours_rate: Threshold for high rate of after-hours transactions.
    """

    high_no_eld_rate: float = Field(
        default=0.20,
        description='Threshold for high rate of transactions without ELD match (0-1 scale)',
        ge=0.0,
        le=1.0,
    )

    high_non_diesel_rate: float = Field(
        default=0.15,
        description='Threshold for high rate of non-diesel purchases (0-1 scale)',
        ge=0.0,
        le=1.0,
    )

    high_after_hours_rate: float = Field(
        default=0.25,
        description='Threshold for high rate of after-hours transactions (0-1 scale)',
        ge=0.0,
        le=1.0,
    )
