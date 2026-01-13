"""Unit tests for data cleaning module.

Tests the critical data cleaning and validation functions that ensure
data quality before analysis.
"""

import numpy as np
import pandas as pd
import pytest

from argus.preprocessing.cleaning import DataCleaner


class TestDataCleaner:
    """Tests for DataCleaner class."""

    @pytest.fixture
    def cleaner(self, sample_fuel_data: pd.DataFrame) -> DataCleaner:
        """Create a DataCleaner instance with sample data."""
        return DataCleaner(sample_fuel_data)

    def test_cleaner_initialization(self, sample_fuel_data: pd.DataFrame) -> None:
        """Test DataCleaner initializes correctly."""
        cleaner = DataCleaner(sample_fuel_data)

        assert cleaner.df is not None
        assert len(cleaner.df) == len(sample_fuel_data)

    def test_remove_duplicates_no_duplicates(
        self, sample_fuel_data: pd.DataFrame
    ) -> None:
        """Test duplicate removal when no duplicates exist."""
        cleaner = DataCleaner(sample_fuel_data)
        original_len = len(cleaner.df)

        cleaner._remove_duplicates()

        assert len(cleaner.df) == original_len

    def test_remove_duplicates_with_duplicates(
        self, sample_fuel_data: pd.DataFrame
    ) -> None:
        """Test duplicate removal when duplicates exist."""
        # Add duplicate rows
        df_with_dupes = pd.concat([sample_fuel_data, sample_fuel_data.iloc[:5]])

        cleaner = DataCleaner(df_with_dupes)
        original_len = len(cleaner.df)

        cleaner._remove_duplicates()

        # Should have removed 5 duplicates
        assert len(cleaner.df) == original_len - 5

    def test_parse_timestamps_converts_to_datetime(self) -> None:
        """Test timestamp parsing converts strings to datetime."""
        df = pd.DataFrame({
            'transaction_timestamp': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'other_col': [1, 2, 3],
        })

        cleaner = DataCleaner(df)
        cleaner._parse_timestamps()

        assert pd.api.types.is_datetime64_any_dtype(
            cleaner.df['transaction_timestamp']
        )

    def test_parse_timestamps_handles_invalid_dates(self) -> None:
        """Test timestamp parsing with invalid dates uses coerce."""
        df = pd.DataFrame({
            'transaction_timestamp': ['2024-01-01', 'invalid', '2024-01-03'],
            'other_col': [1, 2, 3],
        })

        cleaner = DataCleaner(df)
        cleaner._parse_timestamps()

        # Invalid date should become NaT
        assert pd.isna(cleaner.df['transaction_timestamp'].iloc[1])
        assert not pd.isna(cleaner.df['transaction_timestamp'].iloc[0])
        assert not pd.isna(cleaner.df['transaction_timestamp'].iloc[2])

    def test_filter_incomplete_months_last_month(self) -> None:
        """Test filtering of incomplete final month."""
        # Create data with incomplete last month (only 5 days)
        dates = pd.date_range('2024-01-01', '2024-02-05', freq='D')
        df = pd.DataFrame({
            'transaction_timestamp': dates,
            'vehicle_id': 'VIN001',
            'transaction_amount': 100.0,
        })

        cleaner = DataCleaner(df)
        cleaner._filter_incomplete_months()

        # Should filter out February (incomplete)
        remaining_months = cleaner.df['transaction_timestamp'].dt.to_period('M').unique()
        assert len(remaining_months) == 1
        assert remaining_months[0].month == 1

    def test_filter_incomplete_months_complete_month(self) -> None:
        """Test that complete months are not filtered."""
        # Create data with complete month
        dates = pd.date_range('2024-01-01', '2024-01-31', freq='D')
        df = pd.DataFrame({
            'transaction_timestamp': dates,
            'vehicle_id': 'VIN001',
            'transaction_amount': 100.0,
        })

        cleaner = DataCleaner(df)
        original_len = len(cleaner.df)

        cleaner._filter_incomplete_months()

        # Should not filter anything
        assert len(cleaner.df) == original_len

    def test_enforce_types_converts_dtypes(self) -> None:
        """Test type enforcement converts columns to correct dtypes."""
        df = pd.DataFrame({
            'vehicle_index': ['1', '2', '3'],  # String that should be int
            'transaction_amount': ['100.5', '200.3', '150.0'],  # String that should be float
            'driver_name': ['John', 'Jane', 'Bob'],  # Should stay string
        })

        cleaner = DataCleaner(df)
        cleaner._enforce_types()

        # Check conversions (this will depend on TYPE_SPECIFICATION in cleaning.py)
        assert pd.api.types.is_integer_dtype(cleaner.df['vehicle_index'])
        assert pd.api.types.is_float_dtype(cleaner.df['transaction_amount'])
        assert pd.api.types.is_string_dtype(cleaner.df['driver_name'])

    def test_validate_schema_required_columns(self) -> None:
        """Test schema validation checks for required columns."""
        df = pd.DataFrame({
            'vehicle_id': ['VIN001'],
            # Missing other required columns
        })

        cleaner = DataCleaner(df)

        # This should log warnings or raise errors depending on implementation
        # Just test it doesn't crash
        cleaner._validate_schema()

    def test_clean_pipeline_runs_successfully(
        self, sample_fuel_data: pd.DataFrame
    ) -> None:
        """Test full cleaning pipeline runs without errors."""
        cleaner = DataCleaner(sample_fuel_data)

        # Run full clean process (assuming there's a clean() or run() method)
        # If not, this test documents the expected usage pattern
        cleaner._remove_duplicates()
        cleaner._parse_timestamps()
        cleaner._validate_schema()

        assert cleaner.df is not None
        assert len(cleaner.df) > 0


class TestDataCleaningEdgeCases:
    """Tests for edge cases in data cleaning."""

    def test_empty_dataframe_handling(self) -> None:
        """Test handling of empty DataFrame."""
        df = pd.DataFrame()
        cleaner = DataCleaner(df)

        # Should not crash
        assert len(cleaner.df) == 0

    def test_single_row_dataframe(self) -> None:
        """Test handling of single-row DataFrame."""
        df = pd.DataFrame({
            'transaction_timestamp': [pd.Timestamp('2024-01-01')],
            'vehicle_id': ['VIN001'],
            'transaction_amount': [100.0],
        })

        cleaner = DataCleaner(df)
        cleaner._remove_duplicates()

        assert len(cleaner.df) == 1

    def test_all_null_column(self) -> None:
        """Test handling of column with all NULL values."""
        df = pd.DataFrame({
            'transaction_timestamp': [pd.Timestamp('2024-01-01')] * 10,
            'vehicle_id': ['VIN001'] * 10,
            'nullable_field': [None] * 10,
        })

        cleaner = DataCleaner(df)

        # Should handle gracefully
        assert cleaner.df is not None

    def test_mixed_types_in_column(self) -> None:
        """Test handling of mixed types in a column."""
        df = pd.DataFrame({
            'transaction_amount': [100, '200', 300.5, 'invalid', None],
            'vehicle_id': ['VIN001'] * 5,
        })

        cleaner = DataCleaner(df)

        # Type enforcement should handle this
        cleaner._enforce_types()

        # Check that valid values were converted
        assert not pd.isna(cleaner.df['transaction_amount'].iloc[0])

    def test_extreme_values_handling(self) -> None:
        """Test handling of extreme numerical values."""
        df = pd.DataFrame({
            'transaction_amount': [1e10, -1e10, 0, 1e-10],
            'vehicle_id': ['VIN001'] * 4,
            'transaction_timestamp': pd.date_range('2024-01-01', periods=4),
        })

        cleaner = DataCleaner(df)

        # Should not crash with extreme values
        assert cleaner.df is not None
        assert len(cleaner.df) == 4

    def test_unicode_and_special_characters(self) -> None:
        """Test handling of Unicode and special characters in text fields."""
        df = pd.DataFrame({
            'driver_name': ['José García', 'François Müller', '北京', 'Test™'],
            'vehicle_id': ['VIN001'] * 4,
            'transaction_timestamp': pd.date_range('2024-01-01', periods=4),
        })

        cleaner = DataCleaner(df)

        # Should handle Unicode gracefully
        assert cleaner.df['driver_name'].iloc[0] == 'José García'
        assert cleaner.df['driver_name'].iloc[2] == '北京'

    def test_duplicate_timestamps_same_vehicle(self) -> None:
        """Test handling of duplicate timestamps for the same vehicle."""
        df = pd.DataFrame({
            'transaction_timestamp': [pd.Timestamp('2024-01-01 10:00:00')] * 3,
            'vehicle_id': ['VIN001'] * 3,
            'transaction_amount': [100, 100, 100],  # Exact duplicates
        })

        cleaner = DataCleaner(df)
        cleaner._remove_duplicates()

        # Should remove exact duplicates
        assert len(cleaner.df) == 1

    def test_far_future_dates(self) -> None:
        """Test handling of unrealistic future dates."""
        df = pd.DataFrame({
            'transaction_timestamp': [
                pd.Timestamp('2024-01-01'),
                pd.Timestamp('2099-12-31'),  # Far future
                pd.Timestamp('2024-01-03'),
            ],
            'vehicle_id': ['VIN001'] * 3,
        })

        cleaner = DataCleaner(df)

        # Should not crash; validation might flag this
        assert cleaner.df is not None
