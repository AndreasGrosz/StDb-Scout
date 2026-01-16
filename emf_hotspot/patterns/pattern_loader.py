"""
Unified Pattern Loader für Antennendiagramme.

Unterstützt:
- MSI-Files (ODS-Format, digitalisiert)
- Standard-Patterns (ITU-R Modelle)
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional, Union
from scipy.interpolate import interp1d

from .standard_patterns import StandardPattern, ericsson_air3268_standard


class PatternData:
    """Wrapper für Antennendiagramm-Daten (unabhängig von Quelle)."""

    def __init__(
        self,
        angles_deg: np.ndarray,
        attenuation_dB: np.ndarray,
        pattern_type: str,  # 'azimuth' oder 'elevation'
        antenna_type: str,
        frequency_mhz: Optional[float] = None,
        source: str = "unknown"
    ):
        """
        Args:
            angles_deg: Winkel-Array [0-360]
            attenuation_dB: Dämpfung in dB [0-30] (positiv!)
            pattern_type: 'azimuth' (H) oder 'elevation' (V)
            antenna_type: Antennenbezeichnung
            frequency_mhz: Frequenz in MHz
            source: Quelle ('ods', 'standard', 'msi')
        """
        self.angles_deg = np.asarray(angles_deg)
        self.attenuation_dB = np.asarray(attenuation_dB)
        self.pattern_type = pattern_type
        self.antenna_type = antenna_type
        self.frequency_mhz = frequency_mhz
        self.source = source

        # Erstelle Interpolator für beliebige Winkel
        self._interpolator = interp1d(
            self.angles_deg,
            self.attenuation_dB,
            kind='linear',
            bounds_error=False,
            fill_value=(self.attenuation_dB[0], self.attenuation_dB[-1])
        )

    def get_attenuation(self, angle_deg: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """
        Gibt Dämpfung bei beliebigem Winkel zurück (interpoliert).

        Args:
            angle_deg: Winkel in Grad [0-360] oder Array

        Returns:
            Dämpfung in dB (positiv!)
        """
        # Normalisiere auf [0, 360]
        angle = np.asarray(angle_deg) % 360
        return self._interpolator(angle)

    def __repr__(self) -> str:
        return (f"PatternData({self.antenna_type}, {self.pattern_type})\n"
                f"  Source: {self.source}\n"
                f"  Frequency: {self.frequency_mhz} MHz\n"
                f"  Angles: {len(self.angles_deg)} samples, "
                f"{self.angles_deg.min():.1f}° - {self.angles_deg.max():.1f}°\n"
                f"  Attenuation: {self.attenuation_dB.min():.1f} - "
                f"{self.attenuation_dB.max():.1f} dB")


class PatternLoader:
    """Lädt Antennendiagramme aus verschiedenen Quellen."""

    @staticmethod
    def from_ods(
        ods_file: Path,
        antenna_type: str,
        freq_band: Union[str, float],
        h_or_v: str
    ) -> Optional[PatternData]:
        """
        Lädt Pattern aus digitalisierter ODS-Datei.

        Args:
            ods_file: Pfad zur ODS-Datei
            antenna_type: Antennentyp (z.B. "AIR3268")
            freq_band: Frequenzband (z.B. "1805" oder 1805.0)
            h_or_v: "h" (azimuth) oder "v" (elevation)

        Returns:
            PatternData oder None falls nicht gefunden
        """
        if not ods_file.exists():
            print(f"⚠️  ODS nicht gefunden: {ods_file}")
            return None

        try:
            df = pd.read_excel(ods_file, sheet_name='dB', engine='odf')
        except Exception as e:
            print(f"❌ Fehler beim Laden von {ods_file}: {e}")
            return None

        # Filter - versuche verschiedene Matching-Strategien
        df_filtered = pd.DataFrame()

        # Strategie 1: Exakter Match (numerisch)
        try:
            freq_float = float(freq_band)
            df_filtered = df[
                (df['Antennen-Typ'] == antenna_type) &
                (df['Frequenz-band'] == freq_float) &
                (df['vertical or horizontal'] == h_or_v.lower())
            ]
        except (ValueError, TypeError):
            pass

        # Strategie 2: Exakter Match (String)
        if len(df_filtered) == 0:
            df_filtered = df[
                (df['Antennen-Typ'] == antenna_type) &
                (df['Frequenz-band'].astype(str) == str(freq_band)) &
                (df['vertical or horizontal'] == h_or_v.lower())
            ]

        # Strategie 3: Bereichs-Overlap-Match (bidirektional)
        # Input "700-900" matched ODS "738-921" wenn Bereiche überlappen
        if len(df_filtered) == 0:
            try:
                # Parse input freq_band
                freq_band_str = str(freq_band)
                if '-' in freq_band_str:
                    # Input ist Bereich (z.B. "700-900")
                    input_low, input_high = map(float, freq_band_str.split('-'))
                else:
                    # Input ist einzelner Wert (z.B. 3600)
                    input_low = input_high = float(freq_band)

                # Suche in ODS nach überlappendem Bereich
                for idx, row in df[(df['Antennen-Typ'] == antenna_type) &
                                   (df['vertical or horizontal'] == h_or_v.lower())].iterrows():
                    ods_freq_str = str(row['Frequenz-band'])

                    if '-' in ods_freq_str:
                        # ODS hat Bereich (z.B. "738-921")
                        ods_low, ods_high = map(float, ods_freq_str.split('-'))
                    else:
                        # ODS hat einzelnen Wert (z.B. "3600")
                        ods_low = ods_high = float(ods_freq_str)

                    # Prüfe ob Bereiche überlappen
                    # Overlap wenn: input_low <= ods_high AND ods_low <= input_high
                    if input_low <= ods_high and ods_low <= input_high:
                        df_filtered = df[
                            (df['Antennen-Typ'] == antenna_type) &
                            (df['Frequenz-band'] == row['Frequenz-band']) &
                            (df['vertical or horizontal'] == h_or_v.lower())
                        ]
                        print(f"    → Bereichs-Match: {freq_band} ↔ {row['Frequenz-band']}")
                        break
            except (ValueError, TypeError):
                pass

        if len(df_filtered) == 0:
            print(f"⚠️  Keine Daten für {antenna_type} {freq_band} {h_or_v.upper()}")
            return None

        # Sortiere nach Winkel
        df_sorted = df_filtered.sort_values('Phi')

        pattern_type = 'azimuth' if h_or_v.lower() == 'h' else 'elevation'

        # ODS-Daten können negativ sein (Gain-Format: -20 dB = 20 dB Dämpfung)
        # PatternData erwartet positive Dämpfung (0-30 dB)
        dB_values = df_sorted['dB'].values

        # Falls Werte negativ sind, konvertiere zu positiver Dämpfung
        if dB_values.min() < 0:
            # Gain-Format: Invertiere Vorzeichen
            attenuation_dB = -dB_values
        else:
            # Bereits Dämpfung
            attenuation_dB = dB_values

        return PatternData(
            angles_deg=df_sorted['Phi'].values,
            attenuation_dB=attenuation_dB,
            pattern_type=pattern_type,
            antenna_type=antenna_type,
            frequency_mhz=float(freq_band) if isinstance(freq_band, (int, float)) else None,
            source=f"ods:{ods_file.name}"
        )

    @staticmethod
    def from_standard(
        pattern: StandardPattern,
        pattern_type: str = 'azimuth',
        resolution_deg: float = 0.5
    ) -> PatternData:
        """
        Erstellt PatternData aus Standard-Pattern.

        Args:
            pattern: StandardPattern-Instanz
            pattern_type: 'azimuth' oder 'elevation'
            resolution_deg: Winkel-Auflösung in Grad

        Returns:
            PatternData
        """
        angles_deg = np.arange(0, 360, resolution_deg)
        attenuation_dB = pattern.get_pattern_array(angles_deg, pattern_type)

        return PatternData(
            angles_deg=angles_deg,
            attenuation_dB=attenuation_dB,
            pattern_type=pattern_type,
            antenna_type=pattern.params.antenna_type,
            frequency_mhz=None,  # Frequenz-unabhängig
            source=f"standard:{pattern.params.reference}"
        )

    @staticmethod
    def load_or_fallback(
        ods_file: Optional[Path],
        antenna_type: str,
        freq_band: Union[str, float],
        h_or_v: str,
        fallback_pattern: Optional[StandardPattern] = None
    ) -> PatternData:
        """
        Versucht ODS zu laden, nutzt sonst Fallback.

        Args:
            ods_file: Pfad zur ODS (oder None)
            antenna_type: Antennentyp
            freq_band: Frequenzband
            h_or_v: "h" oder "v"
            fallback_pattern: Standard-Pattern (default: Sector 65/7)

        Returns:
            PatternData (entweder aus ODS oder Standard)
        """
        # Versuche ODS
        if ods_file is not None:
            pattern_data = PatternLoader.from_ods(ods_file, antenna_type, freq_band, h_or_v)
            if pattern_data is not None:
                print(f"✓ Geladen: {antenna_type} {freq_band} {h_or_v.upper()} aus ODS")
                return pattern_data

        # Fallback: Standard-Pattern
        if fallback_pattern is None:
            fallback_pattern = ericsson_air3268_standard()

        print(f"⚠️  Nutze Standard-Pattern für {antenna_type} {freq_band} {h_or_v.upper()}")
        print(f"    Basis: {fallback_pattern.params.antenna_type}")

        pattern_type = 'azimuth' if h_or_v.lower() == 'h' else 'elevation'
        return PatternLoader.from_standard(fallback_pattern, pattern_type)


# Convenience-Funktionen
def load_antenna_patterns(
    antenna_type: str,
    freq_mhz: float,
    ods_file: Optional[Path] = None
) -> tuple[PatternData, PatternData]:
    """
    Lädt H- und V-Patterns für eine Antenne.

    Args:
        antenna_type: Antennentyp (z.B. "AIR3268")
        freq_mhz: Frequenz in MHz
        ods_file: ODS-Datei mit digitalisierten Patterns (optional)

    Returns:
        (pattern_h, pattern_v)
    """
    # Erstelle Standard-Fallback
    standard = ericsson_air3268_standard()

    pattern_h = PatternLoader.load_or_fallback(
        ods_file, antenna_type, freq_mhz, 'h', standard
    )

    pattern_v = PatternLoader.load_or_fallback(
        ods_file, antenna_type, freq_mhz, 'v', standard
    )

    return pattern_h, pattern_v
