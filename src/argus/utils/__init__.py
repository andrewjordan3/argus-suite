# argus/utils/__init__.py
"""
This package contains utility functions and classes for ARGUS. These utilities
support various operations such as statistical calculations, risk scoring,
and data manipulation.
"""

from argus.utils.common_utils import is_missing_like
from argus.utils.interpretation_tools import (
    categorize_risk_score,
    get_cliffs_delta_magnitude,
    get_cohens_d_magnitude,
    get_effect_magnitude,
)
from argus.utils.logger import setup_logger
from argus.utils.resources import (
    load_locale_yaml,
    load_policy_yaml,
    load_user_config_yaml,
)
from argus.utils.risk_scoring import RiskProfileCalculator
from argus.utils.stat_tools import (
    benjamini_hochberg_correction,
    bootstrap_ci,
    calculate_vif,
    chi_square_test,
    cliffs_delta,
    cohens_d,
    fishers_exact_test,
    hodges_lehmann_diff,
    newcombe_diff_ci,
    odds_ratio_ci,
    risk_ratio_ci,
    two_prop_z_test,
    wilson_ci,
)
from argus.utils.tail_test import decide_log1p

__all__: list[str] = [
    'RiskProfileCalculator',
    'benjamini_hochberg_correction',
    'bootstrap_ci',
    'calculate_vif',
    'categorize_risk_score',
    'chi_square_test',
    'cliffs_delta',
    'cohens_d',
    'decide_log1p',
    'fishers_exact_test',
    'get_cliffs_delta_magnitude',
    'get_cohens_d_magnitude',
    'get_effect_magnitude',
    'hodges_lehmann_diff',
    'is_missing_like',
    'load_locale_yaml',
    'load_policy_yaml',
    'load_user_config_yaml',
    'newcombe_diff_ci',
    'odds_ratio_ci',
    'risk_ratio_ci',
    'setup_logger',
    'two_prop_z_test',
    'wilson_ci',
]
