"""
Koordinatenfunktionen für LV95 (Schweizer Landesvermessung)
"""

from ..models import LV95Coordinate


def parse_lv95_string(coord_str: str) -> LV95Coordinate:
    """
    Parst einen LV95-Koordinaten-String.

    Formate:
    - "2681044 / 1252266 / 462.20"
    - "2681044/1252266/462.20"

    Returns:
        LV95Coordinate
    """
    return LV95Coordinate.from_string(coord_str)


def apply_offset(
    base: LV95Coordinate,
    dx: float,
    dy: float,
    dz: float,
) -> LV95Coordinate:
    """
    Wendet lokale Offsets auf eine Basiskoordinate an.

    Args:
        base: Ausgangskoordinate
        dx: Ost-Offset in Metern (positiv = Osten)
        dy: Nord-Offset in Metern (positiv = Norden)
        dz: Höhen-Offset in Metern (positiv = oben)

    Returns:
        Neue LV95Coordinate mit angewandten Offsets
    """
    return base.offset(dx, dy, dz)


def distance_2d(coord1: LV95Coordinate, coord2: LV95Coordinate) -> float:
    """Berechnet horizontale Distanz zwischen zwei Koordinaten."""
    import numpy as np

    dx = coord2.e - coord1.e
    dy = coord2.n - coord1.n
    return np.sqrt(dx**2 + dy**2)


def distance_3d(coord1: LV95Coordinate, coord2: LV95Coordinate) -> float:
    """Berechnet 3D-Distanz zwischen zwei Koordinaten."""
    import numpy as np

    dx = coord2.e - coord1.e
    dy = coord2.n - coord1.n
    dz = coord2.h - coord1.h
    return np.sqrt(dx**2 + dy**2 + dz**2)
