"""
Leistungsaddition für E-Felder mehrerer Quellen
"""

from typing import List, Tuple
import numpy as np

from ..config import AGW_LIMIT_VM
from ..models import (
    Antenna,
    AntennaContribution,
    AntennaPattern,
    AntennaSystem,
    FacadePoint,
    HotspotResult,
)
from ..geometry.angles import calculate_relative_angles
from ..loaders.pattern_loader_ods import get_pattern_for_antenna
from .propagation import calculate_e_field_with_pattern


def sum_e_fields(e_fields: List[float]) -> float:
    """
    Summiert E-Felder mehrerer Quellen (Leistungsaddition).

    E_total = sqrt(Σ E_i²)

    Diese Formel gilt für inkohärente Quellen (verschiedene Frequenzen
    oder keine feste Phasenbeziehung).

    Args:
        e_fields: Liste von E-Feldstärken [V/m]

    Returns:
        Summierte E-Feldstärke [V/m]
    """
    e_squared_sum = sum(e**2 for e in e_fields)
    return np.sqrt(e_squared_sum)


def calculate_total_e_field_at_point(
    point: FacadePoint,
    antenna_system: AntennaSystem,
    patterns: dict[Tuple[str, str], AntennaPattern],
    building_attenuation_db: float = 0.0,
) -> HotspotResult:
    """
    Berechnet die Gesamt-E-Feldstärke an einem Punkt von allen Antennen.

    Args:
        point: Zielpunkt auf der Fassade
        antenna_system: System mit allen Antennen
        patterns: Dictionary der Antennendiagramme
        building_attenuation_db: Optionale Gebäudedämpfung [dB]

    Returns:
        HotspotResult mit Gesamtfeldstärke und Einzelbeiträgen
    """
    point_pos = point.to_array()
    contributions = []

    for antenna in antenna_system.antennas:
        # Antennendiagramm für diese Antenne holen
        pattern = get_pattern_for_antenna(
            patterns,
            antenna.antenna_type,
            antenna.frequency_band,
        )

        # Worst-Case-Tilt-Suche: Loop über Tilt-Bereich
        # Finde den Tilt, der die niedrigste V-Dämpfung ergibt (= höchste Feldstärke)
        min_v_attenuation = float('inf')
        critical_tilt = antenna.tilt_deg
        critical_distance = 0.0
        critical_azimuth = 0.0
        critical_elevation = 0.0

        # Tilt-Bereich bestimmen
        tilt_from = int(antenna.tilt_from_deg)
        tilt_to = int(antenna.tilt_to_deg)

        # Wenn kein Bereich definiert (from == to), nur einen Wert prüfen
        if tilt_from == tilt_to:
            tilt_range = [antenna.tilt_deg]
        else:
            tilt_range = range(tilt_from, tilt_to + 1)

        for tilt in tilt_range:
            # Relative Winkel für diesen Tilt berechnen
            distance, rel_azimuth, rel_elevation = calculate_relative_angles(
                antenna_pos=antenna.position,
                point_pos=point_pos,
                antenna_azimuth=antenna.azimuth_deg,
                antenna_tilt=tilt,
            )

            # V-Dämpfung aus Diagramm holen
            if pattern:
                v_atten = pattern.get_v_attenuation(rel_elevation)
            else:
                v_atten = 0.0

            # Prüfe ob dieser Tilt zu niedrigerer Dämpfung führt (Worst-Case)
            if v_atten < min_v_attenuation:
                min_v_attenuation = v_atten
                critical_tilt = tilt
                critical_distance = distance
                critical_azimuth = rel_azimuth
                critical_elevation = rel_elevation

        # Verwende kritischen Tilt für H-Dämpfung und E-Feld-Berechnung
        if pattern:
            h_atten = pattern.get_h_attenuation(critical_azimuth)
            v_atten = min_v_attenuation
        else:
            h_atten = 0.0
            v_atten = 0.0

        # E-Feldstärke berechnen mit kritischen Werten
        e_field = calculate_e_field_with_pattern(
            erp_watts=antenna.erp_watts,
            distance_m=critical_distance,
            h_attenuation_db=h_atten,
            v_attenuation_db=v_atten,
            building_attenuation_db=building_attenuation_db,
        )

        # Speichere detaillierte Contribution-Info
        contribution = AntennaContribution(
            antenna_id=antenna.id,
            e_field_vm=e_field,
            critical_tilt_deg=critical_tilt,
            distance_m=critical_distance,
            h_attenuation_db=h_atten,
            v_attenuation_db=v_atten,
        )
        contributions.append(contribution)

    # Leistungsaddition
    e_values = [c.e_field_vm for c in contributions]
    e_total = sum_e_fields(e_values)

    return HotspotResult(
        building_id=point.building_id,
        x=point.x,
        y=point.y,
        z=point.z,
        e_field_vm=e_total,
        exceeds_limit=(e_total >= AGW_LIMIT_VM),
        contributions=contributions,
    )


def calculate_hotspots(
    points: List[FacadePoint],
    antenna_system: AntennaSystem,
    patterns: dict[Tuple[str, str], AntennaPattern],
    threshold_vm: float = AGW_LIMIT_VM,
    building_attenuation_db: float = 0.0,
) -> List[HotspotResult]:
    """
    Berechnet E-Feldstärke für alle Punkte und gibt Hotspots zurück.

    Args:
        points: Liste aller Fassadenpunkte
        antenna_system: System mit allen Antennen
        patterns: Dictionary der Antennendiagramme
        threshold_vm: Schwellwert für Hotspot [V/m]
        building_attenuation_db: Optionale Gebäudedämpfung [dB]

    Returns:
        Liste von HotspotResults mit E >= threshold
    """
    hotspots = []

    for point in points:
        result = calculate_total_e_field_at_point(
            point=point,
            antenna_system=antenna_system,
            patterns=patterns,
            building_attenuation_db=building_attenuation_db,
        )

        if result.e_field_vm >= threshold_vm:
            hotspots.append(result)

    return hotspots


def calculate_all_points(
    points: List[FacadePoint],
    antenna_system: AntennaSystem,
    patterns: dict[Tuple[str, str], AntennaPattern],
    building_attenuation_db: float = 0.0,
) -> List[HotspotResult]:
    """
    Berechnet E-Feldstärke für alle Punkte (ohne Filterung).

    Nützlich für Visualisierung aller E-Werte.
    """
    results = []

    for point in points:
        result = calculate_total_e_field_at_point(
            point=point,
            antenna_system=antenna_system,
            patterns=patterns,
            building_attenuation_db=building_attenuation_db,
        )
        results.append(result)

    return results
