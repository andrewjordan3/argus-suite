# argus/models/locale/corrections.py
"""
============================================================================
MULTIPLE TESTING CORRECTION
============================================================================
Content for the multiple testing correction results table, showing both
raw and FDR-adjusted p-values for all tests performed. The FDR correction
is performed using the Benjamini-Hochberg procedure, and significance is
determined based on a specified FDR threshold.
============================================================================
"""

from pydantic import Field

from argus.models.common import FrozenModel
from argus.models.locale.placeholder_registry import P
from argus.models.locale.placeholder_validators import FormatStr

__all__: list[str] = [
    'MultipleTestingCorrection',
    'MultipleTestingCorrectionSignificanceMarkers',
    'MultipleTestingCorrectionTableHeaders',
]


class MultipleTestingCorrectionTableHeaders(FrozenModel):
    """
    Column headers for the multiple testing correction table.

    This table shows all statistical tests performed, their raw p-values,
    FDR-adjusted q-values, and significance determination.

    Attributes:
        test_name: Header for test name column
        raw_p_value: Header for uncorrected p-value column
        q_value: Header for FDR-adjusted q-value column
        significant: Header for significance determination column
    """

    test_name: str = Field(description='Column header for statistical test names')
    raw_p_value: str = Field(description='Column header for raw (uncorrected) p-values')
    q_value: str = Field(description='Column header for FDR-adjusted q-values')
    significant: str = Field(description='Column header for significance determination')


class MultipleTestingCorrectionSignificanceMarkers(FrozenModel):
    """
    Text markers for significance determination.

    Visual indicators showing whether each test remains significant after
    FDR correction.

    Attributes:
        significant: Marker when test is significant (typically "✓ YES")
        not_significant: Marker when test is not significant (typically "✗ NO")
    """

    significant: str = Field(
        description='Marker indicating test IS significant after FDR correction'
    )
    not_significant: str = Field(
        description='Marker indicating test is NOT significant after FDR correction'
    )


class MultipleTestingCorrection(FrozenModel):
    """
    Complete multiple testing correction section configuration.

    This section presents a table of all hypothesis tests performed,
    showing how the Benjamini-Hochberg FDR correction affects significance
    determinations.

    Attributes:
        section_title: Title for this section
        introduction: Explanation of FDR correction and its importance
        table_headers: Column headers for the results table
        significance_markers: Visual markers for significance determination
    """

    section_title: str = Field(
        description='Title for the multiple testing correction section'
    )
    introduction: FormatStr[P.MethodologyAlpha] = Field(
        description='Introduction explaining FDR correction procedure and interpretation'
    )
    table_headers: MultipleTestingCorrectionTableHeaders
    markers: MultipleTestingCorrectionSignificanceMarkers
