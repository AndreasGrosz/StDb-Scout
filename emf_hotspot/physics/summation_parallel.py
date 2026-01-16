"""
Parallele Version der E-Feld-Berechnung mit multiprocessing.

Performance-Optimierung: Verwendet alle verfügbaren CPU-Kerne für die
Berechnung der E-Feldstärken an allen Messpunkten.
"""

from typing import List, Tuple
import multiprocessing as mp
from functools import partial

from ..models import (
    AntennaPattern,
    AntennaSystem,
    FacadePoint,
    HotspotResult,
)
from .summation import calculate_total_e_field_at_point


def _calculate_point_worker(
    point: FacadePoint,
    antenna_system: AntennaSystem,
    patterns: dict[Tuple[str, str], AntennaPattern],
    building_attenuation_db: float,
) -> HotspotResult:
    """
    Worker-Funktion für multiprocessing.

    Args:
        point: Einzelner Fassadenpunkt
        antenna_system: System mit allen Antennen
        patterns: Dictionary der Antennendiagramme
        building_attenuation_db: Gebäudedämpfung [dB]

    Returns:
        HotspotResult für diesen Punkt
    """
    return calculate_total_e_field_at_point(
        point=point,
        antenna_system=antenna_system,
        patterns=patterns,
        building_attenuation_db=building_attenuation_db,
    )


def calculate_all_points_parallel(
    points: List[FacadePoint],
    antenna_system: AntennaSystem,
    patterns: dict[Tuple[str, str], AntennaPattern],
    building_attenuation_db: float = 0.0,
    n_workers: int = None,
) -> List[HotspotResult]:
    """
    Berechnet E-Feldstärke für alle Punkte parallel.

    Verwendet multiprocessing.Pool um die Berechnung auf mehrere CPU-Kerne zu verteilen.
    Jeder Punkt wird unabhängig berechnet, daher ideal für Parallelisierung.

    Args:
        points: Liste aller Fassadenpunkte
        antenna_system: System mit allen Antennen
        patterns: Dictionary der Antennendiagramme
        building_attenuation_db: Gebäudedämpfung [dB]
        n_workers: Anzahl paralleler Worker (None = CPU-Kerne)

    Returns:
        Liste von HotspotResults (in gleicher Reihenfolge wie points)
    """
    if not points:
        return []

    # Bestimme Anzahl Worker (Standard: Anzahl CPU-Kerne)
    if n_workers is None:
        n_workers = mp.cpu_count()

    # Für sehr wenige Punkte ist seriell schneller (Overhead vermeiden)
    if len(points) < n_workers * 10:
        # Fallback auf serielle Berechnung
        from .summation import calculate_all_points
        return calculate_all_points(
            points, antenna_system, patterns, building_attenuation_db
        )

    # Worker-Funktion mit festen Parametern vorbereiten
    worker = partial(
        _calculate_point_worker,
        antenna_system=antenna_system,
        patterns=patterns,
        building_attenuation_db=building_attenuation_db,
    )

    # Parallele Berechnung mit Pool
    with mp.Pool(processes=n_workers) as pool:
        results = pool.map(worker, points)

    return results


def calculate_all_points_parallel_chunksize(
    points: List[FacadePoint],
    antenna_system: AntennaSystem,
    patterns: dict[Tuple[str, str], AntennaPattern],
    building_attenuation_db: float = 0.0,
    n_workers: int = None,
    chunksize: int = None,
) -> List[HotspotResult]:
    """
    Parallele Berechnung mit optimiertem Chunksize.

    Für viele Punkte ist es effizienter, sie in Chunks zu verarbeiten,
    um Overhead zu reduzieren.

    Args:
        points: Liste aller Fassadenpunkte
        antenna_system: System mit allen Antennen
        patterns: Dictionary der Antennendiagramme
        building_attenuation_db: Gebäudedämpfung [dB]
        n_workers: Anzahl paralleler Worker (None = CPU-Kerne)
        chunksize: Punkte pro Chunk (None = automatisch)

    Returns:
        Liste von HotspotResults
    """
    if not points:
        return []

    if n_workers is None:
        n_workers = mp.cpu_count()

    # Automatischer Chunksize: Punkte gleichmäßig auf Worker verteilen
    if chunksize is None:
        chunksize = max(1, len(points) // (n_workers * 4))

    # Worker-Funktion mit festen Parametern
    worker = partial(
        _calculate_point_worker,
        antenna_system=antenna_system,
        patterns=patterns,
        building_attenuation_db=building_attenuation_db,
    )

    # Parallele Berechnung mit optimiertem Chunksize
    with mp.Pool(processes=n_workers) as pool:
        results = pool.map(worker, points, chunksize=chunksize)

    return results
