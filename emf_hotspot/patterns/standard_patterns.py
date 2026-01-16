"""
Standard-Antennendiagramme nach ITU-R/3GPP für Mobilfunk-Basisstationen.

Verwendet für Berechnungen wenn keine herstellerspezifischen MSI-Files verfügbar sind.

Wissenschaftliche Referenzen (FINAL KORRIGIERT):

**PRIMÄR (autoritativ):**
- 3GPP TR 36.814 V9.2.0 (2017): "Further advancements for E-UTRA physical layer aspects"
  → Section A.2.1.1: "3-sector cell antenna model"
  → Definiert exakte Formeln: A(φ) = -min[12(φ/φ₃dB)², Am]
  → Für LTE/4G Basisstationen
  → Link: https://portal.3gpp.org/desktopmodules/Specifications/SpecificationDetails.aspx?specificationId=2493

- 3GPP TR 38.901 V17.0.0 (2022): "Study on channel model for frequencies from 0.5 to 100 GHz"
  → Table 7.3-1: "Antenna patterns"
  → Für 5G NR Basisstationen
  → Link: https://portal.3gpp.org/desktopmodules/Specifications/SpecificationDetails.aspx?specificationId=3173

**SEKUNDÄR (zur Unterstützung):**
- ITU-R M.2412-0 (2017): "Guidelines for evaluation of [...] IMT-2020"
  → Verweist selbst auf 3GPP als primäre Quelle
  → Link: https://www.itu.int/rec/R-REC-M.2412/en

HINWEIS: 3GPP (3rd Generation Partnership Project) ist DAS globale Standardisierungsgremium
für Mobilfunk (UMTS, LTE, 5G). ITU übernimmt von 3GPP, nicht umgekehrt.

WICHTIG - Rechtliche Verwendung:
Diese Standardmodelle sind:
1. Von internationalen Gremien (ITU, 3GPP) verabschiedet
2. Von ETSI (Europa) übernommen → EU-konform
3. Wissenschaftlich peer-reviewed
4. Von Telekom-Regulierern weltweit für EMF-Berechnungen akzeptiert

Konservativität:
Die hier implementierten Modelle sind tendenziell KONSERVATIV (weniger Dämpfung
als reale Antennen), d.h.:
- Wenn mit diesen Patterns AGW-Überschreitungen berechnet werden
- Sind diese auch mit herstellerspezifischen Patterns wahrscheinlich

Beweislast:
Falls Behörde/Betreiber bestreitet: Obliegenheit zur Vorlage der echten MSI-Files
zum Nachweis geringerer Immissionen.
"""

import numpy as np
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class StandardPatternParams:
    """Parameter für Standard-Antennendiagramme."""
    # Azimut (Horizontal)
    azimuth_3dB_beamwidth_deg: float  # Halbwertsbreite in Grad
    azimuth_max_attenuation_dB: float  # Maximale Dämpfung

    # Elevation (Vertikal)
    elevation_3dB_beamwidth_deg: float
    elevation_max_attenuation_dB: float

    # Metadaten
    antenna_type: str
    reference: str


class StandardPattern:
    """Standard-Antennendiagramme nach ITU-R."""

    # Vordefinierte Antennentypen
    SECTOR_65_7 = StandardPatternParams(
        azimuth_3dB_beamwidth_deg=65,
        azimuth_max_attenuation_dB=25,
        elevation_3dB_beamwidth_deg=7,
        elevation_max_attenuation_dB=30,
        antenna_type="Sektor 65°/7° (LTE/4G Standard)",
        reference="3GPP TR 36.814 V9.2.0 Section A.2.1.1"
    )

    # 5G NR Narrow Beam (Worst-Case für Beamforming)
    SECTOR_33_5_5G = StandardPatternParams(
        azimuth_3dB_beamwidth_deg=33,
        azimuth_max_attenuation_dB=25,
        elevation_3dB_beamwidth_deg=5,
        elevation_max_attenuation_dB=30,
        antenna_type="Sektor 33°/5° (5G NR Narrow Beam)",
        reference="3GPP TR 38.901 V17.0.0 Table 7.3-1"
    )

    SECTOR_90_7 = StandardPatternParams(
        azimuth_3dB_beamwidth_deg=90,
        azimuth_max_attenuation_dB=25,
        elevation_3dB_beamwidth_deg=7,
        elevation_max_attenuation_dB=30,
        antenna_type="Sektor 90°/7°",
        reference="ITU-R F.1336-5"
    )

    SECTOR_33_7 = StandardPatternParams(
        azimuth_3dB_beamwidth_deg=33,
        azimuth_max_attenuation_dB=25,
        elevation_3dB_beamwidth_deg=7,
        elevation_max_attenuation_dB=30,
        antenna_type="Sektor 33°/7° (narrow beam)",
        reference="ITU-R F.1336-5"
    )

    OMNI = StandardPatternParams(
        azimuth_3dB_beamwidth_deg=360,
        azimuth_max_attenuation_dB=0,
        elevation_3dB_beamwidth_deg=7,
        elevation_max_attenuation_dB=30,
        antenna_type="Omnidirektional",
        reference="Simplified model"
    )

    def __init__(self, params: StandardPatternParams):
        """
        Args:
            params: Antennenparameter
        """
        self.params = params

    @classmethod
    def sector_antenna(
        cls,
        azimuth_beamwidth_deg: float = 65,
        elevation_beamwidth_deg: float = 7
    ) -> 'StandardPattern':
        """
        Erstellt Standard-Sektorantenne mit konfigurierbaren Beamwidths.

        Args:
            azimuth_beamwidth_deg: 3dB Beamwidth horizontal (typisch: 33, 65, 90)
            elevation_beamwidth_deg: 3dB Beamwidth vertikal (typisch: 7)

        Returns:
            StandardPattern-Instanz
        """
        params = StandardPatternParams(
            azimuth_3dB_beamwidth_deg=azimuth_beamwidth_deg,
            azimuth_max_attenuation_dB=25,
            elevation_3dB_beamwidth_deg=elevation_beamwidth_deg,
            elevation_max_attenuation_dB=30,
            antenna_type=f"Sektor {azimuth_beamwidth_deg}°/{elevation_beamwidth_deg}°",
            reference="ITU-R F.1336-5"
        )
        return cls(params)

    def azimuth_attenuation(self, phi_deg: np.ndarray) -> np.ndarray:
        """
        Berechnet Azimut-Dämpfung (Horizontal) nach ITU-R F.1336-5.

        Formel:
            A(phi) = -min(12 * (phi / phi_3dB)^2, Am)

        wobei:
            phi = Winkel relativ zur Hauptstrahlrichtung [Grad]
            phi_3dB = 3dB Beamwidth [Grad]
            Am = Maximale Dämpfung [dB]

        Args:
            phi_deg: Winkel in Grad [-180, 180]
                     0° = Hauptstrahlrichtung
                     Positiv = im Uhrzeigersinn

        Returns:
            Dämpfung in dB (negativ!)
        """
        phi_3dB = self.params.azimuth_3dB_beamwidth_deg
        Am = self.params.azimuth_max_attenuation_dB

        # Normalisiere Winkel auf [-180, 180]
        phi = np.asarray(phi_deg)
        phi = ((phi + 180) % 360) - 180

        # ITU-R Formel
        attenuation = -np.minimum(12 * (phi / phi_3dB)**2, Am)

        return attenuation

    def elevation_attenuation(
        self,
        theta_deg: np.ndarray,
        electrical_downtilt_deg: float = 0
    ) -> np.ndarray:
        """
        Berechnet Elevation-Dämpfung (Vertikal) nach ITU-R F.1336-5.

        Formel:
            A(theta) = -min(12 * ((theta - theta_tilt) / theta_3dB)^2, Am)

        wobei:
            theta = Elevationswinkel [Grad] (positiv = oberhalb Horizont)
            theta_tilt = Elektrischer Downtilt [Grad]
            theta_3dB = 3dB Beamwidth [Grad]
            Am = Maximale Dämpfung [dB]

        Args:
            theta_deg: Elevationswinkel in Grad [-90, 90]
                       0° = Horizont
                       Positiv = oberhalb, Negativ = unterhalb
            electrical_downtilt_deg: Elektrischer Downtilt (default: 0)

        Returns:
            Dämpfung in dB (negativ!)
        """
        theta_3dB = self.params.elevation_3dB_beamwidth_deg
        Am = self.params.elevation_max_attenuation_dB

        # Anwende Downtilt
        theta = np.asarray(theta_deg) - electrical_downtilt_deg

        # ITU-R Formel
        attenuation = -np.minimum(12 * (theta / theta_3dB)**2, Am)

        return attenuation

    def total_attenuation(
        self,
        azimuth_deg: np.ndarray,
        elevation_deg: np.ndarray,
        electrical_downtilt_deg: float = 0
    ) -> np.ndarray:
        """
        Kombinierte Dämpfung (Azimut + Elevation).

        Nach ITU-R wird die Gesamtdämpfung als Leistungssumme berechnet:
            A_total = -10 * log10(10^(-A_h/10) * 10^(-A_v/10))

        Approximation (für kleine Dämpfungen):
            A_total ≈ A_h + A_v

        Wir verwenden die exakte Formel.

        Args:
            azimuth_deg: Azimutwinkel relativ zur Hauptstrahlrichtung
            elevation_deg: Elevationswinkel
            electrical_downtilt_deg: Elektrischer Downtilt

        Returns:
            Gesamtdämpfung in dB (negativ!)
        """
        A_h = self.azimuth_attenuation(azimuth_deg)
        A_v = self.elevation_attenuation(elevation_deg, electrical_downtilt_deg)

        # Exakte Leistungsaddition
        gain_h = 10**(A_h / 10)  # Linear (< 1 weil A_h negativ)
        gain_v = 10**(A_v / 10)  # Linear

        total_gain = gain_h * gain_v
        A_total = 10 * np.log10(total_gain)  # Zurück zu dB

        return A_total

    def get_pattern_array(
        self,
        angles_deg: np.ndarray,
        pattern_type: str = 'azimuth'
    ) -> np.ndarray:
        """
        Gibt Pattern als Array für Plotting/Export.

        Args:
            angles_deg: Winkel-Array [0-360]
            pattern_type: 'azimuth' oder 'elevation'

        Returns:
            Dämpfungs-Array in dB (positiv für Plots: 0-30 dB)
        """
        if pattern_type == 'azimuth':
            # Konvertiere 0-360 zu -180 bis 180 (relativ zu 0°)
            phi_rel = ((angles_deg + 180) % 360) - 180
            attenuation = self.azimuth_attenuation(phi_rel)
        elif pattern_type == 'elevation':
            # Konvertiere 0-360 zu -90 bis 90 (Elevation)
            # Annahme: 0°=Horizont, 90°=Zenith, 270°=Nadir
            theta = ((angles_deg + 90) % 360) - 90
            # Clip auf sinnvollen Bereich
            theta = np.clip(theta, -90, 90)
            attenuation = self.elevation_attenuation(theta)
        else:
            raise ValueError(f"Unknown pattern_type: {pattern_type}")

        # Konvertiere zu positivem dB-Wert (wie in Antennendiagrammen üblich)
        return -attenuation  # 0 dB = keine Dämpfung, 30 dB = max Dämpfung

    def __repr__(self) -> str:
        return (f"StandardPattern({self.params.antenna_type})\n"
                f"  Azimuth: {self.params.azimuth_3dB_beamwidth_deg}° 3dB, "
                f"max {self.params.azimuth_max_attenuation_dB} dB\n"
                f"  Elevation: {self.params.elevation_3dB_beamwidth_deg}° 3dB, "
                f"max {self.params.elevation_max_attenuation_dB} dB\n"
                f"  Reference: {self.params.reference}")


class AdaptiveAntennaModel:
    """
    Modell für adaptive Antennen (z.B. Ericsson AIR 3268).

    Hinweis:
    Adaptive Antennen haben KEIN festes Pattern. Das hier ist ein
    konservativer Worst-Case-Ansatz für NISV-Berechnungen.

    Annahmen:
    - Ohne Beamforming: Standard-Sektorantenne
    - Mit Beamforming: Engerer Beam, aber höhere Leistungsdichte
    - Worst-Case: Nutze Standard-Pattern ohne Beamforming-Gewinn
    """

    def __init__(
        self,
        base_pattern: StandardPattern,
        num_beams: int = 1,
        beamforming_gain_dB: float = 0
    ):
        """
        Args:
            base_pattern: Basis-Pattern (ohne Beamforming)
            num_beams: Anzahl simultaner Beams (typisch: 1-8)
            beamforming_gain_dB: Beamforming-Gewinn [dB]
                                 Positiv = engerer Beam, höhere Leistung
        """
        self.base_pattern = base_pattern
        self.num_beams = num_beams
        self.beamforming_gain_dB = beamforming_gain_dB

    def worst_case_attenuation(
        self,
        azimuth_deg: np.ndarray,
        elevation_deg: np.ndarray
    ) -> np.ndarray:
        """
        Worst-Case Dämpfung (konservativ für EMF-Schutz).

        Annahme: Beam zeigt genau in Richtung des Messpunkts.
        """
        base_att = self.base_pattern.total_attenuation(azimuth_deg, elevation_deg)

        # Beamforming reduziert Dämpfung (höhere Leistungsdichte)
        return base_att + self.beamforming_gain_dB


# Vordefinierte Typen für häufige CH-Antennen
def ericsson_air3268_standard(mode: str = '4g') -> StandardPattern:
    """
    Standard-Approximation für Ericsson AIR 3268.

    WARNUNG: Dies ist NICHT das echte Pattern!
    Adaptive Antennen haben variable Patterns.
    Nutze dies nur als konservativen Platzhalter.

    Args:
        mode: '4g' oder '5g'
              '4g': Nutze 65°/7° Pattern (3GPP TR 36.814)
              '5g': Nutze 33°/5° Narrow Beam (3GPP TR 38.901) - WORST-CASE

    Typische Spezifikation AIR 3268:
    - 4G-Modus: 3 Sektoren à 120° (effektiv ~65° 3dB beamwidth)
    - 5G-Modus: Massive MIMO, Beamforming → variable Patterns

    Reference: Ericsson Datasheet (historisch, pre-adaptive)

    RECHTLICHE EMPFEHLUNG:
    Für Gutachten: Nutze '4g' auch für 5G-Antennen als Worst-Case
    (konservativ, einfach zu argumentieren)
    """
    if mode == '5g':
        return StandardPattern(StandardPattern.SECTOR_33_5_5G)
    else:
        return StandardPattern(StandardPattern.SECTOR_65_7)


def huawei_aau_standard() -> StandardPattern:
    """
    Standard-Approximation für Huawei AAU (Active Antenna Unit).

    Ähnliche Charakteristik wie Ericsson AIR.
    """
    return StandardPattern(StandardPattern.SECTOR_65_7)


def generic_sector_antenna() -> StandardPattern:
    """Generische 3-Sektor-Antenne (120° Coverage, 65° Beamwidth)."""
    return StandardPattern(StandardPattern.SECTOR_65_7)
