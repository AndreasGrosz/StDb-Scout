"""
Antennendiagramm CSV-Loader

Lädt die digitalisierten Antennendiagramme aus CSV-Dateien.
Format: Zeile→Dämpfung_dB;Winkel_Grad (Komma als Dezimaltrenner)
"""

from pathlib import Path
from typing import Optional
import numpy as np

from ..models import AntennaPattern, AntennaSystem
from ..config import FREQUENCY_BAND_MAPPING


def load_antenna_pattern(
    h_file: Path,
    v_file: Path,
    antenna_type: str = "",
    frequency_band: str = "",
) -> AntennaPattern:
    """
    Lädt ein Antennendiagramm aus H- und V-CSV-Dateien.

    Args:
        h_file: Pfad zur Horizontal-Diagramm-Datei
        v_file: Pfad zur Vertikal-Diagramm-Datei
        antenna_type: Antennentyp-Name
        frequency_band: Frequenzband-Name

    Returns:
        AntennaPattern mit interpolierbaren Daten
    """
    h_angles, h_gains = _parse_pattern_csv(h_file)
    v_angles, v_gains = _parse_pattern_csv(v_file)

    return AntennaPattern(
        antenna_type=antenna_type,
        frequency_band=frequency_band,
        h_angles=h_angles,
        h_gains=h_gains,
        v_angles=v_angles,
        v_gains=v_gains,
    )


def _parse_pattern_csv(filepath: Path) -> tuple[np.ndarray, np.ndarray]:
    """
    Parst CSV mit Antennendiagramm-Daten.

    Unterstützte Formate:
    - Format 1: "Dämpfung;Winkel" (z.B. "30,30731778;0,307412535")
    - Format 2: "Zeile→Dämpfung;Winkel" (falls Zeilennummern vorhanden)

    Die Werte verwenden Komma als Dezimaltrenner.

    Returns:
        (angles_array, gains_array) - sortiert nach Winkel
    """
    angles = []
    gains = []

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                # Format 2: Falls "→" vorhanden, Zeilennummer entfernen
                if "→" in line:
                    _, line = line.split("→", 1)

                # Prüfe auf Semikolon-Trenner
                if ";" not in line:
                    continue

                gain_str, angle_str = line.split(";")

                # Komma durch Punkt ersetzen (deutsches Dezimalformat)
                gain = float(gain_str.replace(",", "."))
                angle = float(angle_str.replace(",", "."))

                gains.append(gain)
                angles.append(angle)
            except (ValueError, IndexError):
                continue

    # In numpy arrays konvertieren
    angles_arr = np.array(angles)
    gains_arr = np.array(gains)

    if len(angles_arr) == 0:
        return angles_arr, gains_arr

    # Nach Winkel sortieren für Interpolation
    sort_idx = np.argsort(angles_arr)
    angles_arr = angles_arr[sort_idx]
    gains_arr = gains_arr[sort_idx]

    return angles_arr, gains_arr


def load_all_patterns(
    pattern_dir: Path,
    antenna_system: AntennaSystem,
) -> dict[str, AntennaPattern]:
    """
    Lädt alle benötigten Antennendiagramme für ein Antennensystem.

    Args:
        pattern_dir: Verzeichnis mit den CSV-Dateien
        antenna_system: AntennaSystem mit Antenneninformationen

    Returns:
        Dictionary: (antenna_type, frequency_band) -> AntennaPattern
    """
    patterns = {}

    # Sammle alle einzigartigen (Typ, Frequenz)-Kombinationen
    needed = set()
    for antenna in antenna_system.antennas:
        key = (antenna.antenna_type, antenna.frequency_band)
        needed.add(key)

    for antenna_type, freq_band in needed:
        pattern = _find_and_load_pattern(pattern_dir, antenna_type, freq_band)
        if pattern:
            patterns[(antenna_type, freq_band)] = pattern

    return patterns


def _find_and_load_pattern(
    pattern_dir: Path,
    antenna_type: str,
    frequency_band: str,
) -> Optional[AntennaPattern]:
    """
    Sucht und lädt ein Antennendiagramm basierend auf Typ und Frequenz.

    Dateinamen-Format: "{antenna_type} {frequency} H.csv" / "... V.csv"
    """
    # Frequenzband normalisieren
    normalized_freq = FREQUENCY_BAND_MAPPING.get(frequency_band, frequency_band)

    # Verschiedene Dateinamen-Muster probieren
    # z.B. "HybridAIR3268" -> "Hybrid AIR3268"
    type_with_space = antenna_type.replace("Hybrid", "Hybrid ")
    patterns_to_try = [
        f"{antenna_type} {normalized_freq}",
        f"{type_with_space} {normalized_freq}",
        f"Hybrid {antenna_type} {normalized_freq}",
        f"Hybrid {antenna_type.replace('Hybrid', '')} {normalized_freq}",
    ]

    for base_name in patterns_to_try:
        h_file = pattern_dir / f"{base_name} H.csv"
        v_file = pattern_dir / f"{base_name} V.csv"

        if h_file.exists() and v_file.exists():
            return load_antenna_pattern(
                h_file=h_file,
                v_file=v_file,
                antenna_type=antenna_type,
                frequency_band=frequency_band,
            )

    # Fuzzy-Suche als Fallback
    h_files = list(pattern_dir.glob(f"*{antenna_type}*{normalized_freq}*H*.csv"))
    v_files = list(pattern_dir.glob(f"*{antenna_type}*{normalized_freq}*V*.csv"))

    if h_files and v_files:
        return load_antenna_pattern(
            h_file=h_files[0],
            v_file=v_files[0],
            antenna_type=antenna_type,
            frequency_band=frequency_band,
        )

    return None


def get_pattern_for_antenna(
    patterns: dict[str, AntennaPattern],
    antenna_type: str,
    frequency_band: str,
) -> Optional[AntennaPattern]:
    """Holt das passende Pattern für eine Antenne."""
    # Exakter Match
    key = (antenna_type, frequency_band)
    if key in patterns:
        return patterns[key]

    # Mit normalisierter Frequenz
    normalized_freq = FREQUENCY_BAND_MAPPING.get(frequency_band, frequency_band)
    key = (antenna_type, normalized_freq)
    if key in patterns:
        return patterns[key]

    # Suche nach teilweisem Match
    for (ptype, pfreq), pattern in patterns.items():
        if antenna_type in ptype or ptype in antenna_type:
            if normalized_freq in pfreq or pfreq in normalized_freq:
                return pattern

    return None
