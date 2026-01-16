"""
Adapter: Konvertiert neue PatternData zu altem AntennaPattern-Format.

Ermöglicht Nutzung von Standard-Patterns mit bestehendem Hotspot-Finder.
"""

import numpy as np
from pathlib import Path
from typing import Tuple, Optional

from ..models import AntennaPattern, AntennaSystem
from ..patterns import load_antenna_patterns, PatternData


def convert_pattern_data_to_antenna_pattern(
    pattern_h: PatternData,
    pattern_v: PatternData,
    antenna_type: str,
    frequency_band: str
) -> AntennaPattern:
    """
    Konvertiert neues PatternData-Format zu altem AntennaPattern-Format.

    Args:
        pattern_h: Horizontales Pattern (Azimut)
        pattern_v: Vertikales Pattern (Elevation)
        antenna_type: Antennentyp
        frequency_band: Frequenzband

    Returns:
        AntennaPattern im alten Format
    """
    # PatternData hat Dämpfung als positive Werte (0-30 dB)
    # AntennaPattern erwartet Gains als negative Werte (0 bis -30 dB)
    h_gains = -pattern_h.attenuation_dB
    v_gains = -pattern_v.attenuation_dB

    return AntennaPattern(
        antenna_type=antenna_type,
        frequency_band=frequency_band,
        h_angles=pattern_h.angles_deg,
        h_gains=h_gains,
        v_angles=pattern_v.angles_deg,
        v_gains=v_gains,
    )


def load_patterns_with_standard_fallback(
    ods_file: Optional[Path],
    antenna_system: AntennaSystem,
) -> dict[Tuple[str, str], AntennaPattern]:
    """
    Lädt Patterns mit automatischem Fallback zu Standard-Patterns.

    Ersetzt load_patterns_from_ods() mit intelligentem Fallback.

    Args:
        ods_file: Pfad zur ODS-Datei (optional, kann None sein)
        antenna_system: AntennaSystem mit Antenneninformationen

    Returns:
        Dictionary: (antenna_type, frequency_band) -> AntennaPattern
    """
    patterns = {}

    # Antenna type mapping (OMEN → ODS)
    antenna_type_map = {
        "HybridAIR3268": "AIR3268",
    }

    # Sammle benötigte Frequenzbänder
    needed_combinations = set()
    for antenna in antenna_system.antennas:
        needed_combinations.add((antenna.antenna_type, antenna.frequency_band))

    print(f"\n[Pattern-Loading] Benötigte Patterns:")
    for antenna_type, freq_band in needed_combinations:
        print(f"  - {antenna_type} @ {freq_band}")

    # Versuche für jede Kombination Pattern zu laden
    for antenna_type, freq_band in needed_combinations:
        # Mappe Antennentyp
        ods_antenna_type = antenna_type_map.get(antenna_type, antenna_type)

        print(f"\n  Lade {antenna_type} @ {freq_band}...")

        # Übergebe freq_band direkt als String
        # PatternLoader.from_ods() hat intelligentes Matching:
        # - Exakter Match (numerisch oder String)
        # - Bereichs-Match (z.B. 800 passt zu "738-921")
        pattern_h, pattern_v = load_antenna_patterns(
            antenna_type=ods_antenna_type,
            freq_mhz=freq_band,  # Übergebe als String-Bereich
            ods_file=ods_file
        )

        # Konvertiere zu altem Format
        pattern = convert_pattern_data_to_antenna_pattern(
            pattern_h=pattern_h,
            pattern_v=pattern_v,
            antenna_type=antenna_type,
            frequency_band=freq_band
        )

        patterns[(antenna_type, freq_band)] = pattern

        # Zeige Quelle
        if "standard:" in pattern_h.source:
            print(f"    → Standard-Pattern: {pattern_h.source.split('standard:')[1][:60]}")
        elif "ods:" in pattern_h.source:
            print(f"    → ODS-Pattern: {pattern_h.source.split('ods:')[1]}")

    return patterns
