# argus/models/user_config/data_sources.py
"""
=============================================================================
ARGUS FUEL CARD FORENSICS - DATA SOURCE CONFIGURATION MODEL
=============================================================================
Pydantic model for data source configuration.

Defines paths to input data files (fuel transactions, ELD telemetry, or
pre-merged datasets). Supports CSV or Parquet.
"""

from pathlib import Path
from typing import Annotated, Self

from pydantic import Field, model_validator

from argus.models.common import FrozenModel

__all__: list[str] = [
    'DataSourcesConfig',
]

class DataSourcesConfig(FrozenModel):
    """
    Configuration for input data file paths.

    Specifies the locations of fuel transaction data, ELD/telemetry data,
    and optionally a pre-merged dataset. ARGUS requires ELD data for
    transaction verification, so valid configurations are:

      1. `merged_dataset` alone - Pre-merged fuel + ELD data
      2. Both `fuel_transactions` AND `eld_telemetry` - ARGUS merges them

    Attributes:
        fuel_transactions: Path to fuel transaction data file. Required when
            using separate files (must be paired with `eld_telemetry`).
        eld_telemetry: Path to ELD/telematics data file. Required when using
            separate files (must be paired with `fuel_transactions`).
        merged_dataset: Path to pre-merged dataset combining fuel and ELD data.
            When provided, ARGUS skips the internal merge step and
            `fuel_transactions`/`eld_telemetry` are ignored.

    Example:
        >>> # Option 1: Separate files (ARGUS merges)
        >>> config = DataSourcesConfig(
        ...     fuel_transactions="./data/fuel_transactions.parquet",
        ...     eld_telemetry="./data/eld_telemetry.parquet",
        ... )

        >>> # Option 2: Pre-merged file
        >>> config = DataSourcesConfig(
        ...     merged_dataset="./data/merged.parquet",
        ... )

    Raises:
        ValueError: If configuration doesn't provide valid data sources
    """

    fuel_transactions: Annotated[
        Path | None,
        Field(
            default=None,
            description=(
                'Path to fuel transaction data file. Required unless '
                '`merged_dataset` is provided.'
            ),
        ),
    ]

    eld_telemetry: Annotated[
        Path | None,
        Field(
            default=None,
            description=(
                'Path to ELD/telematics data file for transaction verification. '
            ),
        ),
    ]

    merged_dataset: Annotated[
        Path | None,
        Field(
            default=None,
            description=(
                'Path to pre-merged dataset. When provided, ARGUS skips the '
                'internal merge of fuel and ELD data.'
            ),
        ),
    ]

    @model_validator(mode='after')
    def validate_data_source_availability(self) -> Self:
        """
        Ensure at least one primary data source is configured.

        Either `fuel_transactions` or `merged_dataset` must be provided.
        This allows flexibility for users who have pre-merged data vs. those
        who need ARGUS to perform the merge.

        Returns:
            Self, if validation passes.

        Raises:
            ValueError: If neither `fuel_transactions` nor `merged_dataset`
                is provided.
        """
        has_fuel_transactions: bool = self.fuel_transactions is not None
        has_eld_telemetry: bool = self.eld_telemetry is not None
        has_merged_dataset: bool = self.merged_dataset is not None

        # Valid: pre-merged dataset provided
        if has_merged_dataset:
            return self

        # Valid: both fuel and ELD provided for merge
        if has_fuel_transactions and has_eld_telemetry:
            return self

        # Invalid configurations with helpful error messages
        if not has_fuel_transactions and not has_eld_telemetry:
            raise ValueError(
                "No data sources configured. Provide either 'merged_dataset' "
                "or both 'fuel_transactions' and 'eld_telemetry'."
            )

        if has_fuel_transactions and not has_eld_telemetry:
            raise ValueError(
                "ELD data required: 'fuel_transactions' provided without "
                "'eld_telemetry'. Provide 'eld_telemetry' or use 'merged_dataset' "
                'with pre-merged ELD data.'
            )

        # has_eld_telemetry and not has_fuel_transactions
        raise ValueError(
            "Fuel data required: 'eld_telemetry' provided without "
            "'fuel_transactions'. Provide 'fuel_transactions' or use "
            "'merged_dataset' with pre-merged data."
        )

    def validate_paths_exist(self) -> list[str]:
        """
        Check that all configured file paths exist on disk.

        This is a separate method (not a validator) because path existence
        should be checked at runtime, not at config load time. This allows
        configs to be validated before data files are available.

        Returns:
            List of error messages for missing files. Empty list if all
            configured paths exist.

        Side Effects:
            None. This method only reads filesystem metadata.
        """
        missing_files: list[str] = []

        # Check each configured path
        path_fields: list[tuple[str, Path | None]] = [
            ('fuel_transactions', self.fuel_transactions),
            ('eld_telemetry', self.eld_telemetry),
            ('merged_dataset', self.merged_dataset),
        ]

        for field_name, path_value in path_fields:
            if path_value is not None and not path_value.exists():
                missing_files.append(f"{field_name}: file not found at '{path_value}'")

        return missing_files

    def resolve_paths(self, base_directory: Path | None = None) -> Self:
        """
        Resolve relative paths against a base directory.

        Converts relative paths to absolute paths anchored at the specified
        base directory. Useful when config files reference paths relative
        to the config file location rather than the current working directory.

        Args:
            base_directory: Directory to resolve relative paths against.
                If None, uses the current working directory.

        Returns:
            New DataSourcesConfig with resolved absolute paths.

        Side Effects:
            None. Returns a new instance; does not modify self.
        """
        base: Path = base_directory or Path.cwd()

        def resolve_if_relative(path: Path | None) -> Path | None:
            """Resolve path if relative, leave absolute paths unchanged."""
            if path is None:
                return None

            expanded_path: Path = path.expanduser()

            if expanded_path.is_absolute():
                return expanded_path.resolve()

            return (base / expanded_path).resolve()

        return self.__class__(
            fuel_transactions=resolve_if_relative(self.fuel_transactions),
            eld_telemetry=resolve_if_relative(self.eld_telemetry),
            merged_dataset=resolve_if_relative(self.merged_dataset),
        )

    @property
    def requires_merge(self) -> bool:
        """
        Determine if ARGUS needs to merge fuel and ELD data.

        Returns:
            True if no pre-merged dataset is provided and ARGUS must
            perform the merge internally. False if `merged_dataset`
            is configured.
        """
        return self.merged_dataset is None

