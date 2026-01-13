# argus/formatting/__init__.py

from argus.formatting.effect_size_mapping import (
    EffectSize,
    EffectSizeLabelRegistry,
)
from argus.formatting.format_tools import (
    format_duration_between_times,
    format_entities_by_metric_for_month,
    slugify,
)
from argus.formatting.report_formatter import ReportFormatter
from argus.formatting.safe_template import safe_format_template

__all__: list[str] = [
    'EffectSize',
    'EffectSizeLabelRegistry',
    'ReportFormatter',
    'format_duration_between_times',
    'format_entities_by_metric_for_month',
    'safe_format_template',
    'slugify',
]
