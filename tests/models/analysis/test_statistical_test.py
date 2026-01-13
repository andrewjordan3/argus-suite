"""Unit tests for StatisticalTest Pydantic model and validators.

Tests the critical validation logic that ensures statistical test results
maintain logical consistency and data integrity.
"""

import pytest
from pydantic import ValidationError

from argus.models.analysis.statistical_test import StatisticalTest


class TestStatisticalTestValidation:
    """Tests for StatisticalTest model validators."""

    def test_valid_statistical_test_creation(self) -> None:
        """Test creating a valid StatisticalTest instance."""
        test = StatisticalTest(
            test_name='Multi-Fillup Rate',
            target_count=15,
            target_n=100,
            target_rate=0.15,
            baseline_count=8,
            baseline_n=100,
            baseline_rate=0.08,
            p_value=0.045,
            is_significant=True,
        )

        assert test.target_rate == 0.15
        assert test.baseline_rate == 0.08
        assert test.is_significant is True

    def test_target_rate_below_zero_fails(self) -> None:
        """Target rate < 0 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            StatisticalTest(
                test_name='Test',
                target_rate=-0.1,  # Invalid
                baseline_rate=0.05,
                p_value=0.05,
            )

        assert 'target_rate' in str(exc_info.value)

    def test_target_rate_above_one_fails(self) -> None:
        """Target rate > 1 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            StatisticalTest(
                test_name='Test',
                target_rate=1.5,  # Invalid
                baseline_rate=0.05,
                p_value=0.05,
            )

        assert 'target_rate' in str(exc_info.value)

    def test_baseline_rate_below_zero_fails(self) -> None:
        """Baseline rate < 0 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            StatisticalTest(
                test_name='Test',
                target_rate=0.15,
                baseline_rate=-0.05,  # Invalid
                p_value=0.05,
            )

        assert 'baseline_rate' in str(exc_info.value)

    def test_baseline_rate_above_one_fails(self) -> None:
        """Baseline rate > 1 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            StatisticalTest(
                test_name='Test',
                target_rate=0.15,
                baseline_rate=1.2,  # Invalid
                p_value=0.05,
            )

        assert 'baseline_rate' in str(exc_info.value)

    def test_pvalue_below_zero_fails(self) -> None:
        """P-value < 0 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            StatisticalTest(
                test_name='Test',
                target_rate=0.15,
                baseline_rate=0.05,
                p_value=-0.01,  # Invalid
            )

        assert 'p_value' in str(exc_info.value)

    def test_pvalue_above_one_fails(self) -> None:
        """P-value > 1 should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            StatisticalTest(
                test_name='Test',
                target_rate=0.15,
                baseline_rate=0.05,
                p_value=1.5,  # Invalid
            )

        assert 'p_value' in str(exc_info.value)

    def test_nan_rates_allowed(self) -> None:
        """NaN values should be allowed for rates (missing data)."""
        test = StatisticalTest(
            test_name='Test',
            target_rate=float('nan'),
            baseline_rate=float('nan'),
            p_value=0.05,
        )

        assert test.target_rate != test.target_rate  # NaN check
        assert test.baseline_rate != test.baseline_rate

    def test_target_count_exceeds_n_fails(self) -> None:
        """Target count > target_n should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            StatisticalTest(
                test_name='Test',
                target_count=150,  # Invalid: > target_n
                target_n=100,
                target_rate=0.15,
                baseline_rate=0.05,
                p_value=0.05,
            )

        assert 'target_count' in str(exc_info.value)

    def test_baseline_count_exceeds_n_fails(self) -> None:
        """Baseline count > baseline_n should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            StatisticalTest(
                test_name='Test',
                target_count=15,
                target_n=100,
                baseline_count=150,  # Invalid: > baseline_n
                baseline_n=100,
                target_rate=0.15,
                baseline_rate=0.05,
                p_value=0.05,
            )

        assert 'baseline_count' in str(exc_info.value)

    def test_count_equals_n_allowed(self) -> None:
        """Count = n should be valid (all successes)."""
        test = StatisticalTest(
            test_name='Test',
            target_count=100,
            target_n=100,
            target_rate=1.0,
            baseline_count=50,
            baseline_n=50,
            baseline_rate=1.0,
            p_value=0.99,
        )

        assert test.target_count == test.target_n
        assert test.baseline_count == test.baseline_n

    def test_none_counts_allowed(self) -> None:
        """None values should be allowed for optional fields."""
        test = StatisticalTest(
            test_name='Test',
            target_count=None,
            target_n=None,
            baseline_count=None,
            baseline_n=None,
            target_rate=0.15,
            baseline_rate=0.05,
            p_value=0.05,
        )

        assert test.target_count is None
        assert test.baseline_count is None

    @pytest.mark.parametrize(
        'target_rate,baseline_rate',
        [
            (0.0, 0.0),  # Both zero
            (1.0, 1.0),  # Both one
            (0.5, 0.5),  # Equal mid-range
            (0.0, 1.0),  # Extremes
            (1.0, 0.0),  # Reversed extremes
        ],
    )
    def test_boundary_rates(self, target_rate: float, baseline_rate: float) -> None:
        """Test boundary values for rates."""
        test = StatisticalTest(
            test_name='Test',
            target_rate=target_rate,
            baseline_rate=baseline_rate,
            p_value=0.5,
        )

        assert test.target_rate == target_rate
        assert test.baseline_rate == baseline_rate

    def test_effect_size_fields_optional(self) -> None:
        """Effect size fields should be optional."""
        test = StatisticalTest(
            test_name='Test',
            target_rate=0.15,
            baseline_rate=0.05,
            p_value=0.05,
            effect_size=None,
            effect_size_interpretation=None,
            risk_ratio=None,
            odds_ratio=None,
        )

        assert test.effect_size is None
        assert test.risk_ratio is None

    def test_confidence_interval_fields_optional(self) -> None:
        """Confidence interval fields should be optional."""
        test = StatisticalTest(
            test_name='Test',
            target_rate=0.15,
            baseline_rate=0.05,
            p_value=0.05,
            ci_lower=None,
            ci_upper=None,
            rr_ci_lower=None,
            rr_ci_upper=None,
        )

        assert test.ci_lower is None
        assert test.rr_ci_lower is None

    def test_full_statistical_test_with_all_fields(self) -> None:
        """Test creating a complete StatisticalTest with all fields."""
        test = StatisticalTest(
            test_name='Multi-Fillup Rate Comparison',
            target_count=15,
            target_n=100,
            target_rate=0.15,
            baseline_count=8,
            baseline_n=120,
            baseline_rate=0.067,
            p_value=0.045,
            q_value=0.090,
            is_significant=True,
            test_statistic=2.15,
            effect_size=0.083,
            effect_size_interpretation='Small',
            risk_ratio=2.24,
            rr_ci_lower=1.05,
            rr_ci_upper=4.78,
            odds_ratio=2.42,
            or_ci_lower=1.08,
            or_ci_upper=5.42,
            ci_lower=0.08,
            ci_upper=0.23,
        )

        assert test.test_name == 'Multi-Fillup Rate Comparison'
        assert test.is_significant is True
        assert test.effect_size == 0.083
        assert test.risk_ratio == 2.24
