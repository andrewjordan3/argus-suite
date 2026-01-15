# argus/models/config/column_mapping.py
"""
=============================================================================
COLUMN MAPPING CONFIGURATION
=============================================================================
User configuration model for mapping DataFrame column names to canonical package names.
"""

from collections.abc import Iterable

from pydantic import Field

from argus.models.common import FrozenModel

__all__: list[str] = [
    'ColumnMappingConfig',
]

class ColumnMappingConfig(FrozenModel):
    """
    User configuration mapping their DataFrame column names to canonical package names.

    Users provide their actual column names in YAML config. This model validates
    the configuration and provides methods to rename DataFrames to canonical names.

    Example YAML:
        column_mapping:
          vehicle_id: "vin"
          transaction_timestamp: "datetime"
          transaction_amount: "cost"
          # ... etc

    Attributes:
        All attributes represent the user's column name for the corresponding
        canonical field. Required fields must be present; optional fields can
        be omitted if not available in the user's data.
    """

    # =========================================================================
    # CORE TRANSACTION FIELDS (Required)
    # =========================================================================

    vehicle_id: str = Field(
        ...,
        description="User's column name for vehicle identifier (e.g., VIN)",
        min_length=1,
    )

    transaction_timestamp: str = Field(
        ...,
        description="User's column name for transaction datetime (should be timezone-aware)",
        min_length=1,
    )

    driver_name: str = Field(
        ...,
        description="User's column name for driver full name",
        min_length=1,
    )

    merchant_name: str = Field(
        ...,
        description="User's column name for fuel station/merchant name",
        min_length=1,
    )

    merchant_address: str = Field(
        ...,
        description="User's column name for merchant address (street, city, state, zip)",
        min_length=1,
    )

    assigned_location: str = Field(
        ...,
        description="User's column name for vehicle's assigned location/branch",
        min_length=1,
    )

    transaction_amount: str = Field(
        ...,
        description="User's column name for total transaction cost",
        min_length=1,
    )

    fuel_volume_gallons: str = Field(
        ...,
        description="User's column name for fuel volume in gallons",
        min_length=1,
    )

    product_category: str = Field(
        ...,
        description=(
            "User's column name for product category. "
            'Should contain specific product types: diesel, premium_gasoline, '
            'DEF, car_wash, food, etc.'
        ),
        min_length=1,
    )

    odometer_miles: str = Field(
        ...,
        description="User's column name for odometer reading (ELD or pump-entered)",
        min_length=1,
    )

    # =========================================================================
    # ENTITY IDENTIFIERS (Required)
    # =========================================================================

    vehicle_index: str = Field(
        ...,
        description="User's column name for integer vehicle identifier",
        min_length=1,
    )

    driver_index: str = Field(
        ...,
        description="User's column name for integer driver identifier",
        min_length=1,
    )

    location_index: str = Field(
        ...,
        description="User's column name for integer location identifier",
        min_length=1,
    )

    vehicle_description: str = Field(
        ...,
        description="User's column name for vehicle description (year/make/model)",
        min_length=1,
    )

    # =========================================================================
    # SUPPLEMENTARY FIELDS (Optional)
    # =========================================================================

    driver_pin: str | None = Field(
        None,
        description="User's column name for driver PIN (if used for fraud detection)",
        min_length=1,
    )

    geographic_region: str | None = Field(
        None,
        description="User's column name for geographic region (for regional analysis)",
        min_length=1,
    )

    # =========================================================================
    # TELEMETRY FIELDS (Required)
    # =========================================================================

    distance_miles: str = Field(
        ...,
        description="User's column name for distance traveled between transactions",
        min_length=1,
    )

    idle_duration_minutes: str = Field(
        ...,
        description="User's column name for idle time in minutes",
        min_length=1,
    )

    driving_duration_minutes: str = Field(
        ...,
        description="User's column name for driving time in minutes",
        min_length=1,
    )

    engine_runtime_minutes: str = Field(
        ...,
        description="User's column name for total engine runtime in minutes",
        min_length=1,
    )

    # =========================================================================
    # PUBLIC METHODS
    # =========================================================================

    def get_rename_mapping(self) -> dict[str, str]:
        """
        Generate dictionary to rename user columns to canonical package names.

        This method creates a mapping from the user's column names (values in
        the config) to the canonical names used internally by the package (keys
        in the config).

        Only includes fields that are present (non-None) in the configuration.

        Returns:
            Dictionary mapping user column names to canonical names.
            Format: {user_column_name: canonical_name}

        Example:
            >>> config = ColumnMappingConfig(
            ...     vehicle_id="vin",
            ...     transaction_timestamp="datetime",
            ...     transaction_amount="cost",
            ...     # ... other required fields
            ... )
            >>> mapping = config.get_rename_mapping()
            >>> # Returns: {"vin": "vehicle_id", "datetime": "transaction_timestamp", ...}
            >>> df_canonical = df_user.rename(columns=mapping)
        """
        return {
            user_col: canonical
            for canonical, user_col in self.model_dump(exclude_none=True).items()
        }

    def get_required_columns(self) -> list[str]:
        """
        Get list of required user column names.

        Returns list of column names that MUST be present in the user's
        DataFrame for the package to function correctly.

        Returns:
            List of required user column names.

        Example:
            >>> config.get_required_columns()
            ['vin', 'datetime', 'driver', 'station_name', ...]
        """
        required_columns: list[str] = []

        # Iterate over the schema definitions (Metadata).
        for canonical_name, field_info in self.get_field_definitions().items():
            if field_info.is_required():
                user_column_name: str = getattr(self, canonical_name)
                required_columns.append(user_column_name)

        return required_columns

    def validate_dataframe_columns(
        self,
        dataframe_columns: Iterable[str],
    ) -> tuple[bool, list[str]]:
        """
        Validate that a DataFrame contains all required columns.

        Args:
            dataframe_columns: List (iterable) of column names present in user's DataFrame.

        Returns:
            Tuple of (is_valid, missing_columns).
            - is_valid: True if all required columns present, False otherwise.
            - missing_columns: List of required columns that are missing.

        Example:
            >>> is_valid, missing = config.validate_dataframe_columns(df.columns.tolist())
            >>> if not is_valid:
            ...     raise ValueError(f"Missing required columns: {missing}")
        """
        required_columns: set[str] = set(self.get_required_columns())
        present_columns: set[str] = set(dataframe_columns)
        missing_columns: list[str] = list(required_columns - present_columns)

        is_valid: bool = len(missing_columns) == 0

        return is_valid, sorted(missing_columns)
