"""Pytest configuration and shared fixtures for argus-suite tests."""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_fuel_data() -> pd.DataFrame:
    """Create a sample fuel transaction dataset for testing.

    Returns:
        DataFrame with realistic fuel transaction data including all required fields.
    """
    np.random.seed(42)
    n_records = 100

    return pd.DataFrame({
        'transaction_timestamp': pd.date_range(
            '2024-01-01', periods=n_records, freq='D'
        ),
        'vehicle_id': np.random.choice(
            ['VIN001', 'VIN002', 'VIN003'], size=n_records
        ),
        'driver_name': np.random.choice(
            ['John Doe', 'Jane Smith', 'Bob Johnson'], size=n_records
        ),
        'merchant_name': np.random.choice(
            ['Shell Station A', 'Chevron B', 'BP C'], size=n_records
        ),
        'transaction_amount': np.random.uniform(50, 200, n_records),
        'fuel_volume_gallons': np.random.uniform(15, 50, n_records),
        'product_category': np.random.choice(['Diesel', 'Gasoline'], size=n_records),
        'vehicle_index': np.random.choice([1, 2, 3], size=n_records),
        'driver_index': np.random.choice([101, 102, 103], size=n_records),
        'location_index': np.random.choice([42, 43, 44], size=n_records),
        'odometer_miles': np.cumsum(np.random.uniform(100, 300, n_records)),
    })


@pytest.fixture
def sample_eld_data() -> pd.DataFrame:
    """Create a sample ELD telemetry dataset for testing.

    Returns:
        DataFrame with ELD data matching the fuel transaction data.
    """
    np.random.seed(42)
    n_records = 100

    return pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=n_records, freq='D'),
        'vehicle_id': np.random.choice(
            ['VIN001', 'VIN002', 'VIN003'], size=n_records
        ),
        'distance_miles': np.random.uniform(200, 400, n_records),
        'idle_duration_minutes': np.random.uniform(30, 120, n_records),
        'driving_duration_minutes': np.random.uniform(300, 600, n_records),
        'engine_runtime_minutes': np.random.uniform(350, 700, n_records),
    })


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with sample config files.

    Args:
        tmp_path: Pytest temporary directory fixture

    Returns:
        Path to temporary config directory with YAML files
    """
    config_dir = tmp_path / 'config'
    config_dir.mkdir()

    # Create minimal valid config.yaml
    config_yaml = config_dir / 'config.yaml'
    config_yaml.write_text("""
analysis_target:
  location_number: 42
  location_name: "Test Location"

column_mapping:
  vehicle_id: "vehicle_id"
  transaction_timestamp: "transaction_timestamp"
  driver_name: "driver_name"
  merchant_name: "merchant_name"
  transaction_amount: "transaction_amount"
  fuel_volume_gallons: "fuel_volume_gallons"
  product_category: "product_category"
  vehicle_index: "vehicle_index"
  driver_index: "driver_index"
  location_index: "location_index"

output:
  directory: "./test_reports"
  generate_visualizations: false
  save_report: false
""")

    return config_dir


@pytest.fixture
def sample_2x2_table() -> dict[str, int]:
    """Create a sample 2x2 contingency table for statistical tests.

    Returns:
        Dictionary with target/baseline counts and sample sizes
    """
    return {
        'target_count': 15,
        'target_n': 100,
        'baseline_count': 8,
        'baseline_n': 100,
    }


@pytest.fixture
def sample_distributions() -> dict[str, np.ndarray]:
    """Create sample distributions for effect size testing.

    Returns:
        Dictionary containing various distribution types
    """
    np.random.seed(42)
    return {
        'normal_small': np.random.normal(0, 1, 100),
        'normal_large': np.random.normal(0.5, 1, 100),
        'uniform': np.random.uniform(0, 1, 100),
        'exponential': np.random.exponential(2, 100),
        'constant': np.ones(100),
        'with_outliers': np.concatenate([
            np.random.normal(0, 1, 95),
            np.array([10, -10, 15, -15, 20])
        ]),
    }


def assert_valid_confidence_interval(
    lower: float, upper: float, min_val: float = 0.0, max_val: float = 1.0
) -> None:
    """Assert that a confidence interval is valid.

    Args:
        lower: Lower bound of CI
        upper: Upper bound of CI
        min_val: Minimum allowed value (default 0.0)
        max_val: Maximum allowed value (default 1.0)

    Raises:
        AssertionError: If CI is invalid
    """
    assert min_val <= lower <= max_val, f'Lower bound {lower} outside [{min_val}, {max_val}]'
    assert min_val <= upper <= max_val, f'Upper bound {upper} outside [{min_val}, {max_val}]'
    assert lower <= upper, f'Lower bound {lower} > upper bound {upper}'


def assert_valid_pvalue(pvalue: float) -> None:
    """Assert that a p-value is valid.

    Args:
        pvalue: P-value to validate

    Raises:
        AssertionError: If p-value is invalid
    """
    assert 0.0 <= pvalue <= 1.0, f'P-value {pvalue} outside [0, 1]'
