"""Unit tests for configuration loading system.

Tests the YAML-based configuration loading, validation, and error handling.
"""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from argus.config import load_config
from argus.models.config.root import FuelCardForensicsConfig


class TestLoadConfig:
    """Tests for load_config() function."""

    def test_load_valid_config(self, temp_config_dir: Path) -> None:
        """Test loading a valid configuration file."""
        config_path = temp_config_dir / 'config.yaml'
        config = load_config(config_path)

        assert isinstance(config, FuelCardForensicsConfig)
        assert config.analysis_target.location_number == 42
        assert config.analysis_target.location_name == 'Test Location'

    def test_load_config_missing_file(self, tmp_path: Path) -> None:
        """Test loading a non-existent config file raises FileNotFoundError."""
        non_existent = tmp_path / 'does_not_exist.yaml'

        with pytest.raises(FileNotFoundError):
            load_config(non_existent)

    def test_load_config_malformed_yaml(self, tmp_path: Path) -> None:
        """Test loading malformed YAML raises appropriate error."""
        bad_yaml = tmp_path / 'bad.yaml'
        bad_yaml.write_text('{ invalid yaml content: [')

        with pytest.raises(yaml.YAMLError):
            load_config(bad_yaml)

    def test_load_config_invalid_type(self, tmp_path: Path) -> None:
        """Test loading non-dict YAML raises ValueError."""
        list_yaml = tmp_path / 'list.yaml'
        list_yaml.write_text('- item1\n- item2\n')

        with pytest.raises(ValueError, match='must be a dictionary'):
            load_config(list_yaml)

    def test_load_config_missing_required_field(self, tmp_path: Path) -> None:
        """Test loading config missing required field raises ValidationError."""
        incomplete_config = tmp_path / 'incomplete.yaml'
        incomplete_config.write_text("""
output:
  directory: "./reports"
""")

        with pytest.raises(ValidationError):
            load_config(incomplete_config)

    def test_load_config_invalid_location_number(self, tmp_path: Path) -> None:
        """Test loading config with invalid location number type."""
        bad_config = tmp_path / 'bad.yaml'
        bad_config.write_text("""
analysis_target:
  location_number: "not_a_number"  # Should be int
  location_name: "Test"

column_mapping:
  vehicle_id: "vin"
  transaction_timestamp: "datetime"
  driver_name: "driver"
  merchant_name: "station"
  transaction_amount: "cost"
  fuel_volume_gallons: "volume"
  product_category: "fuel_type"
  vehicle_index: "vinindex"
  driver_index: "driverindex"
  location_index: "locationindex"

output:
  directory: "./reports"
""")

        with pytest.raises(ValidationError):
            load_config(bad_config)

    def test_load_config_with_path_object(self, temp_config_dir: Path) -> None:
        """Test loading config using Path object."""
        config_path = temp_config_dir / 'config.yaml'
        config = load_config(config_path)

        assert isinstance(config, FuelCardForensicsConfig)

    def test_load_config_with_string_path(self, temp_config_dir: Path) -> None:
        """Test loading config using string path."""
        config_path = str(temp_config_dir / 'config.yaml')
        config = load_config(config_path)

        assert isinstance(config, FuelCardForensicsConfig)

    def test_config_column_mapping_validation(self, tmp_path: Path) -> None:
        """Test that column mapping requires all mandatory fields."""
        incomplete_mapping = tmp_path / 'incomplete_mapping.yaml'
        incomplete_mapping.write_text("""
analysis_target:
  location_number: 42
  location_name: "Test"

column_mapping:
  vehicle_id: "vin"
  # Missing many required fields

output:
  directory: "./reports"
""")

        with pytest.raises(ValidationError):
            load_config(incomplete_mapping)

    def test_config_defaults_applied(self, temp_config_dir: Path) -> None:
        """Test that default values are applied for optional fields."""
        config_path = temp_config_dir / 'config.yaml'
        config = load_config(config_path)

        # Check that defaults are present
        assert config.output is not None
        assert config.output.directory is not None

    def test_config_preserves_custom_values(self, tmp_path: Path) -> None:
        """Test that custom values override defaults."""
        custom_config = tmp_path / 'custom.yaml'
        custom_config.write_text("""
analysis_target:
  location_number: 99
  location_name: "Custom Location"

column_mapping:
  vehicle_id: "my_vin"
  transaction_timestamp: "my_datetime"
  driver_name: "my_driver"
  merchant_name: "my_station"
  transaction_amount: "my_cost"
  fuel_volume_gallons: "my_volume"
  product_category: "my_fuel_type"
  vehicle_index: "my_vinindex"
  driver_index: "my_driverindex"
  location_index: "my_locationindex"

output:
  directory: "./custom_reports"
  report_width: 120
""")

        config = load_config(custom_config)

        assert config.analysis_target.location_number == 99
        assert config.analysis_target.location_name == 'Custom Location'
        assert config.output.directory == './custom_reports'
        assert config.output.report_width == 120


class TestConfigModel:
    """Tests for FuelCardForensicsConfig Pydantic model."""

    def test_create_minimal_config(self) -> None:
        """Test creating config with minimal required fields."""
        config = FuelCardForensicsConfig(
            analysis_target={
                'location_number': 42,
                'location_name': 'Test Location',
            },
            column_mapping={
                'vehicle_id': 'vin',
                'transaction_timestamp': 'datetime',
                'driver_name': 'driver',
                'merchant_name': 'station',
                'transaction_amount': 'cost',
                'fuel_volume_gallons': 'volume',
                'product_category': 'fuel_type',
                'vehicle_index': 'vinindex',
                'driver_index': 'driverindex',
                'location_index': 'locationindex',
            },
        )

        assert config.analysis_target.location_number == 42

    def test_config_serialization_roundtrip(self, temp_config_dir: Path) -> None:
        """Test config can be loaded, serialized, and reloaded."""
        config_path = temp_config_dir / 'config.yaml'

        # Load original
        config1 = load_config(config_path)

        # Serialize to dict and recreate
        config_dict = config1.model_dump()
        config2 = FuelCardForensicsConfig(**config_dict)

        # Should be equivalent
        assert config1.analysis_target.location_number == config2.analysis_target.location_number
        assert config1.analysis_target.location_name == config2.analysis_target.location_name

    def test_config_validation_negative_location_number_fails(self) -> None:
        """Test that negative location numbers are rejected."""
        with pytest.raises(ValidationError):
            FuelCardForensicsConfig(
                analysis_target={
                    'location_number': -1,  # Invalid
                    'location_name': 'Test',
                },
                column_mapping={
                    'vehicle_id': 'vin',
                    'transaction_timestamp': 'datetime',
                    'driver_name': 'driver',
                    'merchant_name': 'station',
                    'transaction_amount': 'cost',
                    'fuel_volume_gallons': 'volume',
                    'product_category': 'fuel_type',
                    'vehicle_index': 'vinindex',
                    'driver_index': 'driverindex',
                    'location_index': 'locationindex',
                },
            )
