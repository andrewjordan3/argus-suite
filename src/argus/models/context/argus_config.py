# argus/models/context/argus_config.py
"""
Unified configuration container for the ARGUS pipeline.

This module defines ArgusConfig, which bundles all configuration models
(user preferences, policy thresholds, locale text) into a single object
for dependency injection throughout the pipeline.

Architecture:
    YAML Files (user, policy, locale)
           │
           ▼
    Individual Config Models (UserConfig, PolicyConfig, LocaleConfig)
           │
           ▼
    ArgusConfig (unified container)
           │
           ▼
    Injected into services and analysis functions

Example:
    >>> from argus.models.context import ArgusConfig
    >>> config = ArgusConfig(
    ...     user=load_user_config('user.yaml'),
    ...     policy=load_policy_config('policy.yaml'),
    ...     locale=load_locale_config('en_US.yaml'),
    ... )
    >>> config.policy.statistics.p_value.significant
    0.05
"""

from pydantic import Field

from argus.models.common import FrozenModel
from argus.models.locale import LocaleConfig
from argus.models.locale.report_metadata import Metadata
from argus.models.policy import PolicyConfig
from argus.models.user_config import UserConfig

__all__: list[str] = ['ArgusConfig']


class ArgusConfig(FrozenModel):
    """
    Unified configuration for ARGUS operations.

    Bundles user preferences, policy thresholds, and locale text into a
    single immutable object. Created once at startup and shared across
    the entire pipeline run.

    Attributes:
        user: User-specific settings (paths, target location, logging).
        policy: Business logic thresholds (significance levels, risk cutoffs).
        locale: Localized strings and formatting rules.

    Example:
        >>> config = ArgusConfig(user=user_cfg, policy=policy_cfg, locale=locale_cfg)
        >>> alpha = config.policy.statistics.get_alpha()
        >>> missing_label = config.locale.locale.missing_value
    """

    user: UserConfig = Field(
        ..., description='User-specific preferences (paths, target, logging levels).'
    )
    policy: PolicyConfig = Field(
        ...,
        description='Business logic thresholds (significance levels, risk cutoffs).',
    )
    locale: LocaleConfig = Field(
        ..., description='Localized strings and formatting rules.'
    )

    def __str__(self) -> str:
        """Human-readable summary for logging."""
        metadata: Metadata = self.locale.metadata
        target_num: int = self.user.analysis.target_location_number
        target_name: str = self.user.analysis.target_location_name

        return (
            f'{metadata.system_name} v{metadata.version} | '
            f'Target: Loc #{target_num} ({target_name})'
        )

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        metadata: Metadata = self.locale.metadata
        target_num: int = self.user.analysis.target_location_number
        language: str = self.locale.locale.language_code

        return (
            f'ArgusConfig('
            f'version={metadata.version!r}, '
            f'target={target_num}, '
            f'locale={language!r})'
        )
