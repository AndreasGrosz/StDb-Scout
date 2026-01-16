"""
Pattern-Loader für ODS-Datei (Antennendämpfungen Hybrid AIR3268 R5.ods)
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple

from ..models import AntennaPattern, AntennaSystem


# Mapping von OMEN-Frequenzbändern zu ODS-Frequenzbändern
FREQUENCY_MAPPING = {
    "700-900": "738-921",
    "1800-2600": "1427-2570",  # Höheres Band
    "1400-2600": "1427-2570",  # Gleich wie 1800-2600
    "3600": "3600",
}

# Mapping von OMEN-Antennentypen zu ODS-Antennentypen
ANTENNA_TYPE_MAPPING = {
    "HybridAIR3268": "AIR3268",
}


def load_patterns_from_ods(
    ods_file: Path,
    antenna_system: AntennaSystem,
) -> dict[Tuple[str, str], AntennaPattern]:
    """
    Lädt Antennendiagramme aus ODS-Datei.

    Args:
        ods_file: Pfad zur ODS-Datei
        antenna_system: AntennaSystem mit Antenneninformationen

    Returns:
        Dictionary: (antenna_type, frequency_band) -> AntennaPattern
    """
    print(f"  Lade Antennendiagramme aus: {ods_file.name}")

    # Lade alle Daten aus dem dB-Sheet
    df = pd.read_excel(ods_file, sheet_name='dB', engine='odf')

    # Normalisiere Spalten (entferne Leerzeichen)
    df['Antennen-Typ'] = df['Antennen-Typ'].str.strip()
    df['Frequenz-band'] = df['Frequenz-band'].astype(str).str.strip()
    df['vertical or horizontal'] = df['vertical or horizontal'].str.strip().str.lower()

    # Sammle benötigte Frequenzbänder
    needed_freqs = set()
    needed_types = set()
    for antenna in antenna_system.antennas:
        needed_freqs.add(antenna.frequency_band)
        needed_types.add(antenna.antenna_type)

    patterns = {}

    for omen_type in needed_types:
        ods_type = ANTENNA_TYPE_MAPPING.get(omen_type, omen_type)

        for omen_freq in needed_freqs:
            ods_freq = FREQUENCY_MAPPING.get(omen_freq, omen_freq)

            # Filtere Daten für diesen Typ und Frequenz
            mask = (df['Antennen-Typ'] == ods_type) & (df['Frequenz-band'] == ods_freq)
            subset = df[mask]

            if subset.empty:
                print(f"    WARNUNG: Keine Daten für {ods_type} @ {ods_freq} MHz")
                continue

            # Extrahiere H und V Diagramme
            h_data = subset[subset['vertical or horizontal'] == 'h']
            v_data = subset[subset['vertical or horizontal'] == 'v']

            if h_data.empty or v_data.empty:
                print(f"    WARNUNG: H oder V Daten fehlen für {ods_type} @ {ods_freq} MHz")
                continue

            # Sortiere nach Winkel
            h_data = h_data.sort_values('Phi')
            v_data = v_data.sort_values('Phi')

            # Extrahiere Winkel und Dämpfungs-Werte
            # "dB"-Spalte enthält die Dämpfung relativ zum Maximum
            # Radius + dB = konstant 30 dBi (Maximum), daher:
            # - Bei dB=0: Maximum (keine Dämpfung)
            # - Bei dB=20: 20 dB Dämpfung
            #
            # AntennaPattern erwartet Gain-Werte (höher = besser)
            # Dämpfung ist das Gegenteil (höher = schlechter)
            # → Konvertiere zu Gain: gain = -dämpfung
            # Dann kann get_h_attenuation() rechnen: max_gain - gain = 0 - (-20) = 20 dB
            h_angles = h_data['Phi'].values
            h_gains = -h_data['dB'].values  # Negativ: Dämpfung → Gain

            v_angles = v_data['Phi'].values
            v_gains = -v_data['dB'].values  # Negativ: Dämpfung → Gain

            # Erstelle Pattern
            pattern = AntennaPattern(
                antenna_type=omen_type,  # Verwende OMEN-Typ als Key
                frequency_band=omen_freq,  # Verwende OMEN-Frequenz als Key
                h_angles=h_angles,
                h_gains=h_gains,
                v_angles=v_angles,
                v_gains=v_gains,
            )

            patterns[(omen_type, omen_freq)] = pattern
            print(f"    - {omen_type} @ {omen_freq} MHz: H={len(h_angles)} Punkte, V={len(v_angles)} Punkte")

    return patterns


def get_pattern_for_antenna(
    patterns: dict[Tuple[str, str], AntennaPattern],
    antenna_type: str,
    frequency_band: str,
) -> AntennaPattern:
    """
    Holt das passende Antennendiagramm für einen Typ und Frequenzband.

    Args:
        patterns: Dictionary der geladenen Patterns
        antenna_type: Typ der Antenne (z.B. "HybridAIR3268")
        frequency_band: Frequenzband (z.B. "700-900")

    Returns:
        AntennaPattern oder None wenn nicht gefunden
    """
    return patterns.get((antenna_type, frequency_band), None)
