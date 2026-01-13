"""Integration tests for basic pipeline functionality.

These tests verify that major components work together correctly.
"""

import pandas as pd
import pytest

from argus.preprocessing.cleaning import DataCleaner
from argus.utils.stat_tools import wilson_ci, two_prop_z_test


class TestBasicIntegration:
    """Basic integration tests to verify component interaction."""

    def test_data_cleaning_to_statistical_analysis(
        self, sample_fuel_data: pd.DataFrame
    ) -> None:
        """Test that cleaned data can be used for statistical analysis."""
        # Clean the data
        cleaner = DataCleaner(sample_fuel_data)
        cleaner._remove_duplicates()
        cleaner._parse_timestamps()

        cleaned_df = cleaner.df

        # Perform basic statistical analysis on cleaned data
        target_data = cleaned_df[cleaned_df['location_index'] == 42]
        baseline_data = cleaned_df[cleaned_df['location_index'] != 42]

        if len(target_data) > 0 and len(baseline_data) > 0:
            # Calculate rates for some metric (e.g., diesel usage)
            target_diesel = (target_data['product_category'] == 'Diesel').sum()
            target_n = len(target_data)

            baseline_diesel = (baseline_data['product_category'] == 'Diesel').sum()
            baseline_n = len(baseline_data)

            # Calculate confidence intervals
            target_lower, target_upper = wilson_ci(target_diesel, target_n)

            # Perform statistical test
            test_result = two_prop_z_test(
                target_diesel, target_n, baseline_diesel, baseline_n
            )

            # Verify results are valid
            assert 0 <= target_lower <= 1
            assert 0 <= target_upper <= 1
            assert 0 <= test_result['p_value'] <= 1

    def test_config_to_data_processing(self, temp_config_dir, sample_fuel_data):
        """Test loading config and using it with data processing."""
        from argus.config import load_config

        config = load_config(temp_config_dir / 'config.yaml')

        # Verify config loaded
        assert config.analysis_target.location_number == 42

        # Verify we can use config settings with data
        target_location = config.analysis_target.location_number
        target_data = sample_fuel_data[
            sample_fuel_data['location_index'] == target_location
        ]

        assert len(target_data) > 0

    def test_end_to_end_statistical_test_workflow(
        self, sample_fuel_data: pd.DataFrame
    ) -> None:
        """Test complete workflow from raw data to statistical test results."""
        # Step 1: Clean data
        cleaner = DataCleaner(sample_fuel_data)
        cleaner._remove_duplicates()
        cleaned_df = cleaner.df

        # Step 2: Split into target and baseline
        target = cleaned_df[cleaned_df['location_index'] == 42]
        baseline = cleaned_df[cleaned_df['location_index'] != 42]

        # Step 3: Calculate a metric (e.g., average transaction amount)
        if len(target) > 0 and len(baseline) > 0:
            target_mean = target['transaction_amount'].mean()
            baseline_mean = baseline['transaction_amount'].mean()

            # Step 4: Verify calculations are valid
            assert not pd.isna(target_mean)
            assert not pd.isna(baseline_mean)
            assert target_mean > 0
            assert baseline_mean > 0


class TestModelIntegration:
    """Integration tests for Pydantic models."""

    def test_statistical_test_creation_from_analysis(self):
        """Test creating StatisticalTest model from analysis results."""
        from argus.models.analysis.statistical_test import StatisticalTest
        from argus.utils.stat_tools import two_prop_z_test, risk_ratio_ci

        # Perform analysis
        target_count = 15
        target_n = 100
        baseline_count = 8
        baseline_n = 100

        test_result = two_prop_z_test(
            target_count, target_n, baseline_count, baseline_n
        )
        rr, rr_lower, rr_upper = risk_ratio_ci(
            target_count, target_n, baseline_count, baseline_n
        )

        # Create model from results
        stat_test = StatisticalTest(
            test_name='Multi-Fillup Rate',
            target_count=target_count,
            target_n=target_n,
            target_rate=target_count / target_n,
            baseline_count=baseline_count,
            baseline_n=baseline_n,
            baseline_rate=baseline_count / baseline_n,
            p_value=test_result['p_value'],
            is_significant=test_result['p_value'] < 0.05,
            risk_ratio=rr,
            rr_ci_lower=rr_lower,
            rr_ci_upper=rr_upper,
        )

        # Verify model is valid
        assert stat_test.target_rate == 0.15
        assert stat_test.baseline_rate == 0.08
        assert 0 <= stat_test.p_value <= 1


@pytest.mark.slow
class TestPerformanceIntegration:
    """Integration tests for performance with larger datasets."""

    def test_large_dataset_cleaning(self):
        """Test cleaning performance with larger dataset."""
        # Create larger dataset
        n_records = 10000
        df = pd.DataFrame({
            'transaction_timestamp': pd.date_range(
                '2024-01-01', periods=n_records, freq='H'
            ),
            'vehicle_id': [f'VIN{i%100:03d}' for i in range(n_records)],
            'driver_name': [f'Driver {i%50}' for i in range(n_records)],
            'transaction_amount': [100.0] * n_records,
            'location_index': [42] * n_records,
        })

        cleaner = DataCleaner(df)
        cleaner._remove_duplicates()

        assert len(cleaner.df) <= n_records

    def test_statistical_test_on_large_samples(self):
        """Test statistical tests with large sample sizes."""
        from argus.utils.stat_tools import two_prop_z_test

        # Large samples should give precise p-values
        result = two_prop_z_test(500, 10000, 450, 10000)

        assert 0 <= result['p_value'] <= 1
        assert 'z_stat' in result
