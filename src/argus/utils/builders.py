# argus/utils/builders.py
"""
Factory functions to build ARGUS configuration and service objects.
Side effects:
    Reads configuration files from disk.
Raises:
    OSError: If config files cannot be read.
    ValueError: If config contents fail validation.
"""

from pathlib import Path

from argus.formatting.report_formatter import ReportFormatter
from argus.models.context.argus_config import ArgusConfig
from argus.models.context.argus_services import ArgusServices
from argus.output_formatter import ForensicReportWriter
from argus.utils import (
    load_locale_yaml,
    load_policy_yaml,
    load_user_config_yaml,
)
from argus.utils.clock import SystemClock
from argus.utils.logger import setup_logger

__all__: list[str] = ['build_argus_config', 'build_argus_services', 'build_dependencies_from_paths']

def build_argus_config(
    *,
    user_config_path: str | Path,
    policy_path: str | Path | None = None,
    locale_path: str | Path | None = None,
) -> ArgusConfig:
    """
    Load YAML configuration files and return a validated ArgusConfig.

    Side effects:
        Reads files from disk.

    Raises:
        OSError: If config files cannot be read.
        ValueError: If config contents fail validation.
    """
    return ArgusConfig(
        user=load_user_config_yaml(user_config_path),
        policy=load_policy_yaml(policy_path),
        locale=load_locale_yaml(locale_path),
    )


def build_argus_services(*, config: ArgusConfig) -> ArgusServices:
    """
    Instantiate and bundle ARGUS service objects.

    Side effects:
        None expected (services may allocate in-memory structures).

    Raises:
        ValueError: If service construction fails due to invalid config.
    """
    clock = SystemClock()
    report_formatter = ReportFormatter(config)
    report_writer = ForensicReportWriter(
        config=config,
        formatter=report_formatter,
        clock=clock,
    )

    return ArgusServices(
        report_writer=report_writer,
        report_formatter=report_formatter,
        clock=clock,
    )

def build_dependencies_from_paths(
    *,
    user_config_path: str | Path,
    policy_path: str | Path | None = None,
    locale_path: str | Path | None = None,
) -> tuple[ArgusConfig, ArgusServices]:
    """
    Build ARGUS config + services from configuration file paths.

    Side effects:
        - Reads config files.
        - Configures logging.
        - Ensures output directory exists.

    Returns:
        (config, services)

    Raises:
        OSError: If config files cannot be read.
        ValueError: If config contents fail validation.
    """
    config: ArgusConfig = build_argus_config(
        user_config_path=user_config_path,
        policy_path=policy_path,
        locale_path=locale_path,
    )

    setup_logger(config=config.user.logging)
    config.user.output.ensure_output_directory_exists()

    services: ArgusServices = build_argus_services(config=config)

    return config, services
