# argus/models/locale/red_flags.py
"""
============================================================================
RED FLAG DEFINITIONS
============================================================================
Definitions of red flags used in multi-fillup fraud detection analysis.
Flags are organized by category with associated weighting for scoring. The
suspicion score formula explains how these flags are combined to produce a
single suspicion score for each fillup. The suspicion score is used to
prioritize and investigate potential fraud cases.
============================================================================
"""

from pydantic import Field

from argus.models.common import FrozenModel
from argus.models.locale.placeholder_registry import P
from argus.models.locale.placeholder_validators import FormatStr

__all__: list[str] = [
    'RedFlagItem',
    'RedFlags',
    'RedFlagsGroup',
]


class RedFlagItem(FrozenModel):
    """
    Definition of a single red flag indicator.

    Red flags are individual suspicious characteristics that, when combined,
    help identify potential fraud patterns.

    Attributes:
        acronym: Short code for the flag (e.g., "LC" for Low Cost)
        full_name: Complete descriptive name
        description: Explanation of what this flag indicates and why it matters
    """

    acronym: str = Field(
        max_length=5,
        description='Short acronym code for the red flag (2-3 characters typical)',
    )
    full_name: str = Field(description='Full descriptive name of the red flag')
    description: str = Field(
        description='Detailed explanation of what this flag indicates and its significance'
    )


class RedFlagsGroup(FrozenModel):
    """
    A category of related red flags with common characteristics.

    Red flags are grouped by type (e.g., passenger vehicle indicators vs
    card misuse indicators). Weight multipliers for scoring are defined
    in the policy configuration, not in locale settings.

    Attributes:
        title: Display title for this group of flags
        emoji: Visual indicator emoji for quick category recognition
        flags: dictionary mapping flag acronyms to their definitions
    """

    title: str = Field(description='Display title for this red flag category')
    emoji: str = Field(
        max_length=2, description='Emoji character for visual category identification'
    )
    flags: dict[str, RedFlagItem] = Field(
        description="dictionary of red flag definitions, keyed by acronym (e.g., 'LC', 'LV')"
    )


class RedFlags(FrozenModel):
    """
    Complete red flag system definition.

    Red flags are suspicious characteristics that may indicate fuel card fraud.
    Different flag types are weighted differently based on their correlation
    with known fraud patterns.

    Attributes:
        passenger_vehicle_indicators: Flags suggesting passenger vehicle use (high weight)
        card_misuse_indicators: Flags suggesting operational anomalies (standard weight)
        suspicion_score_formula: Formula for calculating overall suspicion score
    """

    passenger_vehicle_indicators: RedFlagsGroup = Field(
        description='Primary fraud indicators suggesting passenger vehicle misuse'
    )
    card_misuse_indicators: RedFlagsGroup = Field(
        description='Secondary indicators suggesting card misuse or operational anomalies'
    )
    suspicion_score_formula: FormatStr[P.RedFlagSuspicionFormula] = Field(
        description='Formula explaining how suspicion score is calculated from flags'
    )
