"""
EMF-Hotspot-Finder: Datenmodelle
"""

from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np


@dataclass
class LV95Coordinate:
    """Schweizer Landesvermessung 1995 (EPSG:2056)"""
    e: float  # Easting (2'xxx'xxx)
    n: float  # Northing (1'xxx'xxx)
    h: float  # Höhe über Meer [m]

    def to_array(self) -> np.ndarray:
        return np.array([self.e, self.n, self.h])

    @classmethod
    def from_string(cls, coord_str: str) -> "LV95Coordinate":
        """
        Parst '2681044 / 1252266 / 462.20' zu LV95Coordinate.
        """
        parts = coord_str.replace(" ", "").split("/")
        return cls(
            e=float(parts[0]),
            n=float(parts[1]),
            h=float(parts[2])
        )

    def offset(self, dx: float, dy: float, dz: float) -> "LV95Coordinate":
        """Wendet lokale Offsets (in Metern) an."""
        return LV95Coordinate(
            e=self.e + dx,
            n=self.n + dy,
            h=self.h + dz
        )


@dataclass
class Antenna:
    """Einzelne Antenne/Sektor"""
    id: int
    mast_nr: int
    position: LV95Coordinate
    azimuth_deg: float  # Hauptstrahlrichtung (0° = Nord)
    tilt_deg: float  # Neigung (negativ = nach unten) - nur für Referenz
    tilt_from_deg: float  # Minimaler Tilt-Winkel (für Worst-Case-Suche)
    tilt_to_deg: float  # Maximaler Tilt-Winkel (für Worst-Case-Suche)
    erp_watts: float  # Equivalent Radiated Power
    frequency_band: str  # z.B. "700-900", "3600"
    antenna_type: str  # z.B. "HybridAIR3268"
    is_adaptive: bool = False  # Adaptiver Betrieb (5G)
    sub_arrays: int = 1  # Anzahl Sub-Arrays


@dataclass
class OMENLocation:
    """OMEN (Ort mit empfindlicher Nutzung) Position"""
    nr: int
    position: LV95Coordinate
    building_attenuation_db: float = 0.0  # Gebäudedämpfung
    e_field_expected: Optional[float] = None  # Erwarteter E-Feld-Wert aus XLS


@dataclass
class AntennaSystem:
    """Gesamtes Antennensystem eines Standorts"""
    name: str
    base_position: LV95Coordinate
    antennas: List[Antenna] = field(default_factory=list)
    stdb_date: str = ""
    address: str = ""
    omen_locations: List[OMENLocation] = field(default_factory=list)


@dataclass
class AntennaPattern:
    """Antennendiagramm (H und V)"""
    antenna_type: str
    frequency_band: str
    h_angles: np.ndarray  # Winkel in Grad
    h_gains: np.ndarray  # Gain/Dämpfung in dB
    v_angles: np.ndarray
    v_gains: np.ndarray

    def get_h_attenuation(self, azimuth_rel: float) -> float:
        """
        Horizontale Dämpfung aus Azimut-Diagramm.

        Args:
            azimuth_rel: Relativer Azimut [-180, 180]°

        Returns:
            H-Dämpfung in dB (positiv = Abschwächung)
        """
        # Normalisiere Azimut auf 0-360
        h_angle = azimuth_rel % 360

        # Interpoliere H-Gain
        h_gain = np.interp(h_angle, self.h_angles, self.h_gains)

        # Maximaler Gain
        max_h = np.max(self.h_gains)

        # Dämpfung = Differenz zum Maximum
        return max_h - h_gain

    def get_v_attenuation(self, elevation_rel: float) -> float:
        """
        Vertikale Dämpfung aus Elevations-Diagramm.

        Args:
            elevation_rel: Relative Elevation [-90, 90]°

        Returns:
            V-Dämpfung in dB (positiv = Abschwächung)
        """
        # Normalisiere Elevation auf 0-360
        # V-Pattern ist im 0-360° Format (voller Kreis):
        # 0° = Hauptstrahl, 90° = nach oben, 270° = nach unten
        # Negative Winkel: -70° → 290° (70° nach unten)
        v_angle = elevation_rel % 360

        # Interpoliere V-Gain
        v_gain = np.interp(v_angle, self.v_angles, self.v_gains)

        # Maximaler Gain
        max_v = np.max(self.v_gains)

        # Dämpfung = Differenz zum Maximum
        return max_v - v_gain

    def get_attenuation(self, azimuth_rel: float, elevation_rel: float) -> float:
        """
        Berechnet Gesamtdämpfung (H + V) relativ zum Maximum.

        Args:
            azimuth_rel: Relativer Azimut [-180, 180]°
            elevation_rel: Relative Elevation [-90, 90]°

        Returns:
            Gesamtdämpfung in dB (positiv = Abschwächung)
        """
        return self.get_h_attenuation(azimuth_rel) + self.get_v_attenuation(elevation_rel)


@dataclass
class WallSurface:
    """Fassaden-Polygon"""
    id: str
    vertices: np.ndarray  # Shape (N, 3) - LV95 E, N, H
    normal: Optional[np.ndarray] = None  # Flächennormale
    faces: Optional[np.ndarray] = None  # PyVista Face-Array für TIN-Meshes


@dataclass
class Building:
    """Gebäude aus swissBUILDINGS3D"""
    id: str
    egid: str = ""  # Eidgenössischer Gebäudeidentifikator
    wall_surfaces: List[WallSurface] = field(default_factory=list)
    roof_surfaces: List[WallSurface] = field(default_factory=list)  # Wiederverwendung von WallSurface für Dächer


@dataclass
class FacadePoint:
    """Einzelner Sampling-Punkt auf einer Fassade"""
    building_id: str
    x: float  # LV95 E
    y: float  # LV95 N
    z: float  # Höhe über Meer
    normal: np.ndarray  # Flächennormale

    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z])


@dataclass
class AntennaContribution:
    """Einzelbeitrag einer Antenne zu einem Punkt"""
    antenna_id: int
    e_field_vm: float
    critical_tilt_deg: float
    distance_m: float
    h_attenuation_db: float
    v_attenuation_db: float


@dataclass
class HotspotResult:
    """Berechnungsergebnis für einen Punkt"""
    building_id: str
    x: float
    y: float
    z: float
    e_field_vm: float
    exceeds_limit: bool
    contributions: List[AntennaContribution] = field(default_factory=list)
