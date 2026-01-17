"""
3D-Visualisierung von Antennendiagrammen als Keulen/Lobes

Erstellt 3D-Meshes aus H/V-Diagrammen für ParaView-Darstellung.
Zeigt die -3dB Beamwidth visuell - ähnlich wie Ranplan/ATDI.
"""

import numpy as np
from typing import Tuple, Optional
try:
    import pyvista as pv
except ImportError:
    pv = None


def create_antenna_lobe_3d(
    antenna_position: Tuple[float, float, float],  # (E, N, H) in LV95
    azimuth_deg: float,  # Hauptstrahlrichtung
    tilt_deg: float,  # Tilt (negativ = nach unten)
    h_pattern: np.ndarray,  # Horizontal-Diagramm (360 Werte, 0-360°)
    v_pattern: np.ndarray,  # Vertikal-Diagramm (180 Werte, -90 bis +90°)
    max_gain_dbi: float = 0.0,  # Max Gain der Antenne
    scale_distance_m: float = 100.0,  # Normierung: 0dB = 100m Radius
    min_attenuation_db: float = -20.0,  # Nur bis -20dB darstellen
) -> Optional['pv.PolyData']:
    """
    Erstellt 3D-Mesh der Antennenkeule aus H/V-Diagrammen.

    Konzept:
    - Kombiniert Horizontal- und Vertikal-Diagramm zu 3D-Oberfläche
    - Dämpfung → Radius: 0dB = scale_distance_m, -20dB = scale_distance_m/10
    - Rotiert auf Azimut/Tilt der Antenne
    - Farbcodiert nach Dämpfung (Rot = Hauptkeule, Blau = Nebenkeulen)

    Args:
        antenna_position: (E, N, H) Koordinaten im LV95-System
        azimuth_deg: Hauptstrahlrichtung (0° = Nord, 90° = Ost)
        tilt_deg: Tilt (negativ = nach unten, z.B. -4°)
        h_pattern: Horizontal-Dämpfung in dB, 360 Werte für 0-360° (relativ zu Azimut!)
        v_pattern: Vertikal-Dämpfung in dB, 180 Werte für -90 bis +90° (relativ zu Tilt!)
        max_gain_dbi: Maximaler Gewinn der Antenne in dBi (für Absolutwerte)
        scale_distance_m: Radius bei 0dB (0dB = scale_distance_m)
        min_attenuation_db: Minimale Dämpfung die gezeichnet wird (z.B. -20dB)

    Returns:
        PyVista PolyData Mesh oder None falls PyVista nicht verfügbar
    """
    if pv is None:
        return None

    # Interpoliere Diagramme auf gemeinsames Grid
    # Azimut: 0-360° in 5° Schritten (72 Punkte)
    # Elevation: -90 bis +90° in 5° Schritten (36 Punkte)
    azimuth_angles = np.arange(0, 360, 5)  # 72 Werte
    elevation_angles = np.arange(-90, 95, 5)  # 37 Werte (inkl. +90)

    # Interpoliere H-Pattern (zyklisch!)
    h_interp = np.interp(
        azimuth_angles,
        np.linspace(0, 360, len(h_pattern), endpoint=False),
        h_pattern,
        period=360  # Zyklisch: 360° = 0°
    )

    # Interpoliere V-Pattern
    v_interp = np.interp(
        elevation_angles,
        np.linspace(-90, 90, len(v_pattern)),
        v_pattern
    )

    # Erstelle 3D-Grid: Für jeden (Azimut, Elevation) Punkt
    points = []
    attenuation_values = []

    for i, az in enumerate(azimuth_angles):
        for j, el in enumerate(elevation_angles):
            # Kombinierte Dämpfung: H + V (in dB, addieren)
            atten_db = h_interp[i] + v_interp[j]

            # Clipping: Nur bis min_attenuation_db darstellen
            if atten_db < min_attenuation_db:
                atten_db = min_attenuation_db

            # Dämpfung → Radius (logarithmisch)
            # 0dB → scale_distance_m
            # -20dB → scale_distance_m * 10^(-20/20) = scale_distance_m / 10
            radius = scale_distance_m * 10 ** (atten_db / 20.0)

            # Polar → Kartesisch (relativ zur Antenne)
            # WICHTIG: Diagramme sind relativ! Azimut 0° = Hauptstrahlrichtung
            # Elevation 0° = Horizontale

            # 1. Lokale Koordinaten (Antenne zeigt in +X Richtung, +Z nach oben)
            # Azimut: Rotation um Z-Achse
            # Elevation: Rotation in XZ-Ebene

            az_rad = np.radians(az)
            el_rad = np.radians(el)

            # Kartesisch in lokalem System (Antenne = Ursprung)
            x_local = radius * np.cos(el_rad) * np.cos(az_rad)
            y_local = radius * np.cos(el_rad) * np.sin(az_rad)
            z_local = radius * np.sin(el_rad)

            points.append([x_local, y_local, z_local])
            attenuation_values.append(atten_db)

    points = np.array(points)
    attenuation_values = np.array(attenuation_values)

    # Rotiere auf echte Azimut/Tilt-Richtung
    # 1. Rotation um Z-Achse (Azimut): 0° = Nord = +Y, 90° = Ost = +X
    azimuth_rad = np.radians(azimuth_deg)
    cos_az = np.cos(azimuth_rad)
    sin_az = np.sin(azimuth_rad)

    # Rotationsmatrix um Z (Azimut)
    # Achtung: 0° = Nord = +Y, also 90° Offset zu üblichem Koordinatensystem
    # LV95: +E = Ost = +X, +N = Nord = +Y
    # Azimut 0° = Nord → in +Y Richtung
    # Azimut 90° = Ost → in +X Richtung

    # Anpassen: Azimut 0° in lokalen Koordinaten ist +X, aber soll +Y sein (Nord)
    # → Rotation um -90° im lokalen System, dann Rotation um Azimut

    # Einfacher: Direkte Transformation
    # Lokales +X (Azimut 0°) → Globales Azimut_deg
    rotation_z = np.array([
        [np.cos(azimuth_rad), -np.sin(azimuth_rad), 0],
        [np.sin(azimuth_rad),  np.cos(azimuth_rad), 0],
        [0, 0, 1]
    ])

    # 2. Rotation um Ost-Achse (Tilt)
    # Tilt negativ = nach unten → Rotation um lokale Y-Achse
    tilt_rad = np.radians(tilt_deg)
    rotation_tilt = np.array([
        [np.cos(-tilt_rad), 0, np.sin(-tilt_rad)],
        [0, 1, 0],
        [-np.sin(-tilt_rad), 0, np.cos(-tilt_rad)]
    ])

    # Kombinierte Rotation: Erst Azimut, dann Tilt
    # Achtung: Tilt muss um die schon rotierte Achse erfolgen!
    # → Komplexere Rotation nötig

    # Vereinfachung: Rotiere erst um Tilt (lokal), dann um Azimut (global)
    points_rotated = points @ rotation_tilt.T @ rotation_z.T

    # Translation zur Antennenposition
    points_world = points_rotated + np.array(antenna_position)

    # Erstelle Mesh aus Punkten (strukturiertes Grid)
    # Grid: azimuth_angles × elevation_angles
    n_az = len(azimuth_angles)
    n_el = len(elevation_angles)

    # Erstelle Faces (Dreiecke) aus strukturiertem Grid
    faces = []
    for i in range(n_az - 1):
        for j in range(n_el - 1):
            # Vier Eckpunkte des Quads
            idx0 = i * n_el + j
            idx1 = (i + 1) * n_el + j
            idx2 = (i + 1) * n_el + (j + 1)
            idx3 = i * n_el + (j + 1)

            # Zwei Dreiecke pro Quad
            faces.extend([3, idx0, idx1, idx2])
            faces.extend([3, idx0, idx2, idx3])

    # Füge Verbindung am Azimut-Wraparound hinzu (360° → 0°)
    i = n_az - 1
    for j in range(n_el - 1):
        idx0 = i * n_el + j
        idx1 = 0 * n_el + j  # Wrap to first column
        idx2 = 0 * n_el + (j + 1)
        idx3 = i * n_el + (j + 1)

        faces.extend([3, idx0, idx1, idx2])
        faces.extend([3, idx0, idx2, idx3])

    # Erstelle PolyData
    mesh = pv.PolyData(points_world, faces=faces)

    # Füge Dämpfungs-Daten hinzu (für Farbcodierung)
    mesh["Attenuation_dB"] = attenuation_values
    mesh["Gain_dBi"] = max_gain_dbi + attenuation_values  # Absoluter Gewinn

    return mesh


def create_all_antenna_lobes(
    antenna_system,
    pattern_data: dict,  # {antenna_id: {"h_pattern": array, "v_pattern": array}}
    scale_distance_m: float = 80.0,
    min_attenuation_db: float = -15.0,
) -> Optional['pv.PolyData']:
    """
    Erstellt 3D-Keulen für alle Antennen eines Systems.

    Args:
        antenna_system: AntennaSystem Objekt
        pattern_data: Dict mit H/V-Patterns pro Antenne
        scale_distance_m: Normierung (0dB = X Meter)
        min_attenuation_db: Cutoff-Dämpfung

    Returns:
        Kombiniertes PyVista Mesh aller Keulen oder None
    """
    if pv is None:
        return None

    lobes = []

    for antenna in antenna_system.antennas:
        if antenna.id not in pattern_data:
            print(f"  WARNUNG: Kein Pattern für Antenne {antenna.id} (Freq: {antenna.frequency_band})")
            continue

        patterns = pattern_data[antenna.id]

        # Mittlerer Tilt
        tilt = (antenna.tilt_from_deg + antenna.tilt_to_deg) / 2

        lobe = create_antenna_lobe_3d(
            antenna_position=(antenna.position.e, antenna.position.n, antenna.position.h),
            azimuth_deg=antenna.azimuth_deg,
            tilt_deg=tilt,
            h_pattern=patterns["h_pattern"],
            v_pattern=patterns["v_pattern"],
            max_gain_dbi=patterns.get("max_gain_dbi", 0.0),
            scale_distance_m=scale_distance_m,
            min_attenuation_db=min_attenuation_db,
        )

        if lobe is not None:
            # Füge Metadaten hinzu
            lobe["Antenna_ID"] = np.full(lobe.n_cells, antenna.id)
            lobe["Frequency_MHz"] = np.full(lobe.n_cells, _parse_frequency(antenna.frequency_band))
            lobe["Azimuth_deg"] = np.full(lobe.n_cells, antenna.azimuth_deg)
            lobe["Tilt_deg"] = np.full(lobe.n_cells, tilt)
            lobes.append(lobe)

    if not lobes:
        return None

    # Kombiniere alle Lobes
    combined = lobes[0]
    for lobe in lobes[1:]:
        combined = combined.merge(lobe)

    return combined


def _parse_frequency(freq_band: str) -> float:
    """
    Extrahiert mittlere Frequenz aus Band-String.

    Beispiele:
        "700-900 MHz" → 800.0
        "1800-2600" → 2200.0
        "3600 MHz" → 3600.0
    """
    freq_band = freq_band.replace(" MHz", "").replace("MHz", "")

    if "-" in freq_band:
        # Bereich: nimm Mittelwert
        parts = freq_band.split("-")
        return sum(float(p) for p in parts) / len(parts)
    else:
        # Einzelwert
        return float(freq_band)
