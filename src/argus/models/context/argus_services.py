# argus/models/context/argus_services.py
"""
Shared service container for the ARGUS pipeline.

This module defines ArgusServices, which holds service objects (formatters,
writers, clock) that are instantiated once and reused across all target
analyses in a run.

Lifecycle:
    1. ArgusConfig created from YAML files
    2. Services instantiated using config
    3. ArgusServices created to bundle services
    4. Passed to analysis functions alongside TargetAnalysisData
    5. Persists for entire run (services are stateless or append-only)

Design Rationale:
    Separating services from config allows:
    - Config to remain pure data (no behavior)
    - Services to be mocked independently in tests
    - Clear dependency boundaries in function signatures
"""

from pydantic import BaseModel, ConfigDict, Field

from argus.formatting.report_formatter import ReportFormatter
from argus.output_formatter import ForensicReportWriter
from argus.utils.clock import Clock

__all__: list[str] = ['ArgusServices']


class ArgusServices(BaseModel):
    """
    Container for shared services used throughout the ARGUS pipeline.

    Bundles service objects that are instantiated once at startup and
    reused across all target analyses. Services hold references to
    ArgusConfig internally for access to configuration values.

    This model uses arbitrary_types_allowed to support custom service
    classes and the Clock protocol. It is frozen to prevent reassignment.

    Attributes:
        report_writer: Service for writing forensic reports to Excel.
        report_formatter: Service for formatting values (currency, dates, etc).
        clock: Time provider for timestamps and duration measurement.

    Example:
        >>> services = ArgusServices(
        ...     report_writer=ForensicReportWriter(config),
        ...     report_formatter=ReportFormatter(config),
        ...     clock=SystemClock(),
        ... )
        >>> with Timer(clock=services.clock, label='analysis'):
        ...     run_analysis(data, services)
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True, extra='forbid')

    report_writer: ForensicReportWriter = Field(
        ...,
        description='Service for writing forensic reports to Excel.',
    )

    report_formatter: ReportFormatter = Field(
        ...,
        description='Service for formatting values (currency, percentages, dates).',
    )

    clock: Clock = Field(
        ...,
        description='Time provider for timestamps and duration measurement.',
    )

    def __repr__(self) -> str:
        """Developer-friendly representation showing service types."""
        return (
            f'ArgusServices('
            f'writer={self.report_writer.__class__.__name__}, '
            f'formatter={self.report_formatter.__class__.__name__}, '
            f'clock={self.clock.__class__.__name__})'
        )
