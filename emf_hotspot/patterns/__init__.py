"""
Antennendiagramm-Module für EMF-Hotspot-Finder.

Unterstützt:
- Digitalisierte Patterns (ODS-Format)
- Standard-Patterns (ITU-R Modelle)
"""

from .standard_patterns import (
    StandardPattern,
    StandardPatternParams,
    AdaptiveAntennaModel,
    ericsson_air3268_standard,
    huawei_aau_standard,
    generic_sector_antenna,
)

from .pattern_loader import (
    PatternData,
    PatternLoader,
    load_antenna_patterns,
)

__all__ = [
    # Standard Patterns
    'StandardPattern',
    'StandardPatternParams',
    'AdaptiveAntennaModel',
    'ericsson_air3268_standard',
    'huawei_aau_standard',
    'generic_sector_antenna',

    # Pattern Loading
    'PatternData',
    'PatternLoader',
    'load_antenna_patterns',
]
