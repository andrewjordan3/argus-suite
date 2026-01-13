"""Unit tests for statistical utility functions in stat_tools.py.

This module tests the most critical statistical functions that form the foundation
of the ARGUS Suite's fraud detection capabilities.
"""

import numpy as np
import pytest
from scipy import stats

from argus.utils.stat_tools import (
    benjamini_hochberg_correction,
    chi_square_test,
    cliffs_delta,
    cohens_d,
    fishers_exact_test,
    odds_ratio_ci,
    risk_ratio_ci,
    two_prop_z_test,
    wilson_ci,
)
from tests.conftest import assert_valid_confidence_interval, assert_valid_pvalue


class TestWilsonCI:
    """Tests for Wilson confidence interval calculation."""

    @pytest.mark.parametrize(
        'successes,n,alpha,expected_lower,expected_upper',
        [
            # Known values from statistical tables
            (0, 10, 0.05, 0.0, 0.308),  # Lower extreme
            (10, 10, 0.05, 0.692, 1.0),  # Upper extreme
            (5, 10, 0.05, 0.187, 0.813),  # Middle value
            (50, 100, 0.05, 0.398, 0.602),  # Larger sample
            (1, 20, 0.05, 0.001, 0.248),  # Small proportion
            (19, 20, 0.05, 0.752, 0.999),  # Large proportion
        ],
    )
    def test_known_values(
        self,
        successes: int,
        n: int,
        alpha: float,
        expected_lower: float,
        expected_upper: float,
    ) -> None:
        """Test Wilson CI against known statistical values."""
        lower, upper = wilson_ci(successes, n, alpha=alpha)
        assert np.isclose(lower, expected_lower, atol=0.003)
        assert np.isclose(upper, expected_upper, atol=0.003)

    def test_zero_sample_size_returns_nan(self) -> None:
        """Zero observations should return NaN bounds."""
        lower, upper = wilson_ci(0, 0)
        assert np.isnan(lower)
        assert np.isnan(upper)

    @pytest.mark.parametrize('k,n', [(k, n) for k in range(0, 21) for n in range(max(1, k), 21)])
    def test_bounds_always_valid(self, k: int, n: int) -> None:
        """CI bounds must always be in [0, 1] and lower <= upper."""
        lower, upper = wilson_ci(k, n)
        assert_valid_confidence_interval(lower, upper, min_val=0.0, max_val=1.0)

    @pytest.mark.parametrize('alpha', [0.01, 0.05, 0.10, 0.20])
    def test_different_alpha_levels(self, alpha: float) -> None:
        """Test various significance levels."""
        lower, upper = wilson_ci(50, 100, alpha=alpha)
        # Width should increase as alpha decreases (more confidence)
        width = upper - lower
        assert width > 0
        assert_valid_confidence_interval(lower, upper)

    def test_width_increases_with_confidence(self) -> None:
        """Higher confidence (lower alpha) should produce wider intervals."""
        lower_95, upper_95 = wilson_ci(50, 100, alpha=0.05)  # 95% CI
        lower_90, upper_90 = wilson_ci(50, 100, alpha=0.10)  # 90% CI

        width_95 = upper_95 - lower_95
        width_90 = upper_90 - lower_90

        assert width_95 > width_90

    def test_width_decreases_with_sample_size(self) -> None:
        """Larger samples should produce narrower intervals."""
        lower_small, upper_small = wilson_ci(5, 10)
        lower_large, upper_large = wilson_ci(50, 100)

        width_small = upper_small - lower_small
        width_large = upper_large - lower_large

        assert width_small > width_large


class TestBenjaminiHochbergCorrection:
    """Tests for Benjamini-Hochberg FDR correction."""

    def test_empty_input_returns_empty(self) -> None:
        """Empty p-value array should return empty q-values."""
        pvalues = np.array([])
        qvalues = benjamini_hochberg_correction(pvalues)
        assert len(qvalues) == 0

    def test_all_nan_input_returns_nan(self) -> None:
        """All NaN p-values should return all NaN q-values."""
        pvalues = np.array([np.nan, np.nan, np.nan])
        qvalues = benjamini_hochberg_correction(pvalues)
        assert np.all(np.isnan(qvalues))

    def test_single_pvalue(self) -> None:
        """Single p-value should equal its q-value."""
        pvalues = np.array([0.05])
        qvalues = benjamini_hochberg_correction(pvalues)
        assert qvalues[0] == 0.05

    @pytest.mark.parametrize(
        'pvalues,expected_rejections',
        [
            # Classic example: 5 tests, 2 significant at FDR 0.05
            (np.array([0.001, 0.008, 0.040, 0.050, 0.300]), 3),
            # All highly significant
            (np.array([0.001, 0.002, 0.003, 0.004, 0.005]), 5),
            # All non-significant
            (np.array([0.20, 0.30, 0.40, 0.50, 0.60]), 0),
        ],
    )
    def test_known_fdr_scenarios(
        self, pvalues: np.ndarray, expected_rejections: int
    ) -> None:
        """Test against known FDR scenarios."""
        qvalues = benjamini_hochberg_correction(pvalues, alpha=0.05)
        rejections = np.sum(qvalues < 0.05)
        assert rejections == expected_rejections

    def test_qvalues_monotonic(self) -> None:
        """Q-values should be monotonically increasing when sorted by rank."""
        pvalues = np.array([0.001, 0.01, 0.05, 0.10, 0.50])
        qvalues = benjamini_hochberg_correction(pvalues)

        # Q-values for sorted p-values should be non-decreasing
        assert np.all(qvalues[:-1] <= qvalues[1:])

    def test_qvalues_greater_equal_pvalues(self) -> None:
        """Q-values should always be >= corresponding p-values."""
        pvalues = np.random.uniform(0, 1, 100)
        qvalues = benjamini_hochberg_correction(pvalues)

        assert np.all(qvalues >= pvalues)

    def test_qvalues_bounded_by_one(self) -> None:
        """Q-values should never exceed 1.0."""
        pvalues = np.random.uniform(0, 1, 100)
        qvalues = benjamini_hochberg_correction(pvalues)

        assert np.all(qvalues <= 1.0)

    def test_handles_ties(self) -> None:
        """Should handle tied p-values correctly."""
        pvalues = np.array([0.01, 0.01, 0.05, 0.05, 0.10])
        qvalues = benjamini_hochberg_correction(pvalues)

        # Tied p-values should have same q-values
        assert qvalues[0] == qvalues[1]
        assert qvalues[2] == qvalues[3]

    def test_preserves_nan_positions(self) -> None:
        """NaN positions should be preserved in output."""
        pvalues = np.array([0.01, np.nan, 0.05, np.nan, 0.10])
        qvalues = benjamini_hochberg_correction(pvalues)

        assert np.isnan(qvalues[1])
        assert np.isnan(qvalues[3])
        assert not np.isnan(qvalues[0])

    @pytest.mark.parametrize('alpha', [0.01, 0.05, 0.10, 0.20])
    def test_different_alpha_levels(self, alpha: float) -> None:
        """Test with different FDR control levels."""
        pvalues = np.array([0.001, 0.01, 0.05, 0.10, 0.50])
        qvalues = benjamini_hochberg_correction(pvalues, alpha=alpha)

        # Should return valid q-values
        assert np.all((qvalues >= 0) & (qvalues <= 1))


class TestRiskRatioCI:
    """Tests for risk ratio confidence intervals."""

    def test_equal_proportions_rr_equals_one(self) -> None:
        """Equal proportions should give RR = 1.0."""
        rr, lower, upper = risk_ratio_ci(10, 100, 10, 100)
        assert np.isclose(rr, 1.0)

    def test_doubled_risk(self) -> None:
        """Target with 2x baseline risk should give RR ≈ 2.0."""
        rr, lower, upper = risk_ratio_ci(20, 100, 10, 100)
        assert np.isclose(rr, 2.0)

    def test_zero_baseline_returns_inf_rr(self) -> None:
        """Zero baseline events should return inf RR."""
        rr, lower, upper = risk_ratio_ci(10, 100, 0, 100)
        assert np.isinf(rr)

    def test_both_zero_returns_nan(self) -> None:
        """Both zero should return NaN."""
        rr, lower, upper = risk_ratio_ci(0, 100, 0, 100)
        assert np.isnan(rr)

    def test_ci_contains_point_estimate(self) -> None:
        """Confidence interval should contain the point estimate."""
        rr, lower, upper = risk_ratio_ci(15, 100, 10, 100)
        assert lower <= rr <= upper

    @pytest.mark.parametrize(
        'target_count,target_n,baseline_count,baseline_n',
        [
            (15, 100, 10, 100),
            (5, 50, 10, 100),
            (20, 200, 10, 100),
            (1, 20, 5, 100),
        ],
    )
    def test_confidence_intervals_valid(
        self, target_count: int, target_n: int, baseline_count: int, baseline_n: int
    ) -> None:
        """CI bounds should be positive and properly ordered."""
        rr, lower, upper = risk_ratio_ci(
            target_count, target_n, baseline_count, baseline_n
        )

        if not np.isnan(rr) and not np.isinf(rr):
            assert lower > 0
            assert upper > 0
            assert lower <= upper

    def test_continuity_correction(self) -> None:
        """Test with continuity correction for small counts."""
        # With continuity correction (default)
        rr1, lower1, upper1 = risk_ratio_ci(1, 20, 1, 20, continuity_correction=True)

        # Without continuity correction
        rr2, lower2, upper2 = risk_ratio_ci(1, 20, 1, 20, continuity_correction=False)

        # Continuity correction should widen the interval
        width1 = upper1 - lower1
        width2 = upper2 - lower2
        assert width1 > width2


class TestOddsRatioCI:
    """Tests for odds ratio confidence intervals."""

    def test_equal_proportions_or_equals_one(self) -> None:
        """Equal proportions should give OR = 1.0."""
        odds_ratio, lower, upper = odds_ratio_ci(10, 90, 10, 90)
        assert np.isclose(odds_ratio, 1.0)

    def test_extreme_association(self) -> None:
        """Strong association should give large OR."""
        odds_ratio, lower, upper = odds_ratio_ci(40, 60, 10, 90)
        assert odds_ratio > 1.0

    def test_zero_cell_handling(self) -> None:
        """Should handle zero cells with continuity correction."""
        # With zero in target unexposed
        odds_ratio, lower, upper = odds_ratio_ci(10, 0, 5, 10)
        assert not np.isnan(odds_ratio)
        assert odds_ratio > 0

    def test_ci_contains_point_estimate(self) -> None:
        """Confidence interval should contain the point estimate."""
        odds_ratio, lower, upper = odds_ratio_ci(15, 85, 10, 90)
        assert lower <= odds_ratio <= upper

    @pytest.mark.parametrize('alpha', [0.01, 0.05, 0.10])
    def test_different_alpha_levels(self, alpha: float) -> None:
        """Test with different significance levels."""
        odds_ratio, lower, upper = odds_ratio_ci(15, 85, 10, 90, alpha=alpha)

        assert lower > 0
        assert upper > 0
        assert lower <= odds_ratio <= upper


class TestTwoPropZTest:
    """Tests for two-proportion z-test."""

    def test_equal_proportions_not_significant(self) -> None:
        """Equal proportions should not be significant."""
        result = two_prop_z_test(50, 100, 50, 100)

        assert_valid_pvalue(result['p_value'])
        assert result['p_value'] > 0.05  # Should not be significant

    def test_very_different_proportions_significant(self) -> None:
        """Very different proportions should be significant."""
        result = two_prop_z_test(80, 100, 20, 100)

        assert_valid_pvalue(result['p_value'])
        assert result['p_value'] < 0.001  # Should be highly significant

    def test_degenerate_case_all_zeros(self) -> None:
        """All zeros should return NaN."""
        result = two_prop_z_test(0, 100, 0, 100)

        assert np.isnan(result['p_value'])
        assert np.isnan(result['z_stat'])

    def test_degenerate_case_all_ones(self) -> None:
        """All ones should return NaN."""
        result = two_prop_z_test(100, 100, 100, 100)

        assert np.isnan(result['p_value'])

    @pytest.mark.parametrize('yates', [True, False])
    def test_yates_correction_parameter(self, yates: bool) -> None:
        """Test with and without Yates correction."""
        result = two_prop_z_test(15, 100, 10, 100, yates_correction=yates)

        assert 'p_value' in result
        assert 'z_stat' in result
        assert_valid_pvalue(result['p_value'])


class TestCliffsDelth:
    """Tests for Cliff's Delta effect size."""

    def test_identical_distributions_zero_delta(self) -> None:
        """Identical distributions should give delta ≈ 0."""
        x = np.array([1, 2, 3, 4, 5])
        y = np.array([1, 2, 3, 4, 5])

        delta = cliffs_delta(x, y)
        assert np.isclose(delta, 0.0, atol=0.01)

    def test_completely_separated_distributions(self) -> None:
        """Completely separated distributions should give |delta| ≈ 1."""
        x = np.array([1, 2, 3, 4, 5])
        y = np.array([10, 11, 12, 13, 14])

        delta = cliffs_delta(x, y)
        assert np.isclose(abs(delta), 1.0, atol=0.01)

    def test_small_difference(self) -> None:
        """Small difference should give small effect size."""
        np.random.seed(42)
        x = np.random.normal(0, 1, 100)
        y = np.random.normal(0.2, 1, 100)

        delta = cliffs_delta(x, y)
        assert abs(delta) < 0.3  # Should be small effect

    def test_large_difference(self) -> None:
        """Large difference should give large effect size."""
        np.random.seed(42)
        x = np.random.normal(0, 1, 100)
        y = np.random.normal(2, 1, 100)

        delta = cliffs_delta(x, y)
        assert abs(delta) > 0.5  # Should be large effect

    def test_bounded_by_minus_one_and_one(self) -> None:
        """Cliff's Delta should always be in [-1, 1]."""
        np.random.seed(42)
        for _ in range(10):
            x = np.random.normal(0, 1, 50)
            y = np.random.normal(np.random.uniform(-2, 2), 1, 50)

            delta = cliffs_delta(x, y)
            assert -1 <= delta <= 1


class TestCohensD:
    """Tests for Cohen's d effect size."""

    def test_identical_distributions_zero_d(self) -> None:
        """Identical distributions should give d ≈ 0."""
        x = np.array([1, 2, 3, 4, 5])
        y = np.array([1, 2, 3, 4, 5])

        d = cohens_d(x, y)
        assert np.isclose(d, 0.0, atol=0.01)

    def test_one_sd_difference(self) -> None:
        """One SD difference should give |d| ≈ 1."""
        np.random.seed(42)
        x = np.random.normal(0, 1, 1000)
        y = np.random.normal(1, 1, 1000)

        d = cohens_d(x, y)
        assert np.isclose(abs(d), 1.0, atol=0.1)

    def test_small_effect_size(self) -> None:
        """Small mean difference should give small effect size."""
        np.random.seed(42)
        x = np.random.normal(0, 1, 100)
        y = np.random.normal(0.2, 1, 100)

        d = cohens_d(x, y)
        assert abs(d) < 0.5  # Cohen's convention: small < 0.5

    def test_large_effect_size(self) -> None:
        """Large mean difference should give large effect size."""
        np.random.seed(42)
        x = np.random.normal(0, 1, 100)
        y = np.random.normal(1, 1, 100)

        d = cohens_d(x, y)
        assert abs(d) > 0.8  # Cohen's convention: large > 0.8

    def test_zero_variance_returns_nan(self) -> None:
        """Zero variance should return NaN."""
        x = np.ones(10)
        y = np.ones(10)

        d = cohens_d(x, y)
        assert np.isnan(d)


class TestChiSquareTest:
    """Tests for chi-square test of independence."""

    def test_perfect_independence(self) -> None:
        """Perfectly independent should not be significant."""
        # Proportions identical in both groups
        result = chi_square_test(50, 50, 50, 50)

        assert_valid_pvalue(result['p_value'])
        assert result['p_value'] > 0.05

    def test_strong_association(self) -> None:
        """Strong association should be significant."""
        # Very different proportions
        result = chi_square_test(90, 10, 10, 90)

        assert_valid_pvalue(result['p_value'])
        assert result['p_value'] < 0.001

    @pytest.mark.parametrize('yates', [True, False])
    def test_yates_correction(self, yates: bool) -> None:
        """Test with and without Yates correction."""
        result = chi_square_test(15, 85, 10, 90, yates_correction=yates)

        assert 'p_value' in result
        assert 'chi2_stat' in result
        assert_valid_pvalue(result['p_value'])


class TestFishersExactTest:
    """Tests for Fisher's exact test."""

    def test_small_sample_fisher(self) -> None:
        """Fisher's exact is preferred for small samples."""
        result = fishers_exact_test(3, 7, 1, 9)

        assert 'p_value' in result
        assert 'odds_ratio' in result
        assert_valid_pvalue(result['p_value'])

    def test_perfect_independence_not_significant(self) -> None:
        """Perfect independence should not be significant."""
        result = fishers_exact_test(5, 5, 5, 5)

        assert_valid_pvalue(result['p_value'])
        assert result['p_value'] > 0.05

    def test_strong_association_significant(self) -> None:
        """Strong association should be significant."""
        result = fishers_exact_test(9, 1, 1, 9)

        assert_valid_pvalue(result['p_value'])
        assert result['p_value'] < 0.05
