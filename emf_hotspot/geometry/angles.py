"""
Winkelberechnungen für Azimut und Elevation
"""

import numpy as np

from ..models import LV95Coordinate


def calculate_azimuth(dx: float, dy: float) -> float:
    """
    Berechnet Azimut in Grad.

    Konvention:
    - 0° = Nord
    - 90° = Ost
    - 180° = Süd
    - 270° = West
    - Im Uhrzeigersinn

    Args:
        dx: Ost-Differenz (positiv = Osten)
        dy: Nord-Differenz (positiv = Norden)

    Returns:
        Azimut in Grad [0, 360)
    """
    # atan2(x, y) gibt Winkel von y-Achse (Nord), positiv im Uhrzeigersinn
    azimuth_rad = np.arctan2(dx, dy)
    azimuth_deg = np.degrees(azimuth_rad)

    # Normalisieren auf [0, 360)
    return azimuth_deg % 360.0


def calculate_elevation(horizontal_distance: float, dz: float) -> float:
    """
    Berechnet Elevationswinkel in Grad.

    Konvention:
    - 0° = Horizont
    - Positiv = über dem Horizont
    - Negativ = unter dem Horizont

    Args:
        horizontal_distance: Horizontaler Abstand [m]
        dz: Höhendifferenz (Ziel - Quelle) [m]

    Returns:
        Elevation in Grad [-90, 90]
    """
    if horizontal_distance < 0.001:  # Zu nah
        return 90.0 if dz > 0 else (-90.0 if dz < 0 else 0.0)

    elevation_rad = np.arctan2(dz, horizontal_distance)
    return np.degrees(elevation_rad)


def calculate_relative_angles(
    antenna_pos: LV95Coordinate,
    point_pos: np.ndarray,  # [E, N, H]
    antenna_azimuth: float,
    antenna_tilt: float,
) -> tuple[float, float, float]:
    """
    Berechnet relative Winkel eines Punktes bezüglich der Antennenausrichtung.

    Args:
        antenna_pos: Position der Antenne (LV95)
        point_pos: Position des Zielpunktes [E, N, H]
        antenna_azimuth: Hauptstrahlrichtung der Antenne [°]
        antenna_tilt: Neigung der Antenne (negativ = nach unten) [°]

    Returns:
        Tuple:
        - distance_3d: 3D-Abstand [m]
        - rel_azimuth: Relativer Azimut zur Hauptstrahlrichtung [-180, 180]°
        - rel_elevation: Relative Elevation zum Tilt [°]
    """
    # Differenzvektor: Punkt - Antenne
    dx = point_pos[0] - antenna_pos.e
    dy = point_pos[1] - antenna_pos.n
    dz = point_pos[2] - antenna_pos.h

    # Abstände
    horizontal_distance = np.sqrt(dx**2 + dy**2)
    distance_3d = np.sqrt(dx**2 + dy**2 + dz**2)

    # Absoluter Azimut des Punktes
    point_azimuth = calculate_azimuth(dx, dy)

    # Relativer Azimut (Differenz zur Hauptstrahlrichtung)
    rel_azimuth = point_azimuth - antenna_azimuth

    # Normalisieren auf [-180, 180]
    rel_azimuth = ((rel_azimuth + 180) % 360) - 180

    # Elevation des Punktes (von Antenne aus gesehen)
    point_elevation = calculate_elevation(horizontal_distance, dz)

    # Relative Elevation (Differenz zum Tilt)
    # Positiver Tilt = Antenne zeigt nach oben
    # Bei Mobilfunk ist Tilt meist negativ (Downtilt)
    rel_elevation = point_elevation - antenna_tilt

    return distance_3d, rel_azimuth, rel_elevation


def normalize_azimuth(angle: float) -> float:
    """Normalisiert Azimut auf [0, 360)."""
    return angle % 360.0


def normalize_azimuth_centered(angle: float) -> float:
    """Normalisiert Azimut auf [-180, 180)."""
    return ((angle + 180) % 360) - 180
