"""
Fassaden-Sampling: Erzeugt Rasterpunkte auf Gebäudefassaden
"""

from typing import List
import numpy as np

from ..models import FacadePoint, WallSurface


def sample_facade_polygon(
    wall_surface: WallSurface,
    resolution: float = 0.5,
    building_id: str = "",
) -> List[FacadePoint]:
    """
    Erzeugt Raster-Punkte auf einer Fassaden-Polygon.

    Args:
        wall_surface: WallSurface mit Polygon-Vertices
        resolution: Rasterweite in Metern
        building_id: Gebäude-ID für die erzeugten Punkte

    Returns:
        Liste von FacadePoint
    """
    vertices = wall_surface.vertices

    if len(vertices) < 3:
        return []

    # Flächennormale berechnen
    normal = _calculate_normal(vertices)
    if normal is None:
        return []

    # Prüfen ob Fassade vertikal genug ist (nicht Dach)
    # |normal.z| > 0.7 bedeutet zu horizontal (Dach oder Boden)
    if abs(normal[2]) > 0.7:
        return []

    # Lokales Koordinatensystem der Fassade
    u, v = _create_local_coordinate_system(normal)

    # Projektion auf lokale Ebene
    origin = vertices[0]
    local_coords = np.array([
        [np.dot(vtx - origin, u), np.dot(vtx - origin, v)]
        for vtx in vertices
    ])

    # Bounding-Box in lokalen Koordinaten
    min_u, max_u = local_coords[:, 0].min(), local_coords[:, 0].max()
    min_v, max_v = local_coords[:, 1].min(), local_coords[:, 1].max()

    # Raster erstellen
    points = []
    u_coords = np.arange(min_u + resolution / 2, max_u, resolution)
    v_coords = np.arange(min_v + resolution / 2, max_v, resolution)

    for u_val in u_coords:
        for v_val in v_coords:
            local_pt = np.array([u_val, v_val])

            # Point-in-Polygon Test
            if _point_in_polygon(local_pt, local_coords):
                # Zurück in 3D transformieren
                world_pt = origin + u_val * u + v_val * v

                points.append(FacadePoint(
                    building_id=building_id,
                    x=world_pt[0],
                    y=world_pt[1],
                    z=world_pt[2],
                    normal=normal.copy(),
                ))

    return points


def sample_roof_polygon(
    roof_surface: WallSurface,
    resolution: float = 0.5,
    building_id: str = "",
) -> List[FacadePoint]:
    """
    Erzeugt Raster-Punkte auf einer Dachfläche.

    Args:
        roof_surface: RoofSurface (wiederverwendet WallSurface) mit Polygon-Vertices
        resolution: Rasterweite in Metern
        building_id: Gebäude-ID für die erzeugten Punkte

    Returns:
        Liste von FacadePoint
    """
    vertices = roof_surface.vertices

    if len(vertices) < 3:
        return []

    # Flächennormale berechnen
    normal = _calculate_normal(vertices)
    if normal is None:
        return []

    # WICHTIG: Keine Vertikalitätsprüfung mehr!
    # Giebelwände können fälschlicherweise als RoofSurface klassifiziert sein,
    # sind aber vertikal → müssen trotzdem gesamplet werden (Dachgeschosswohnungen!)
    # Wir samplen ALLE als "Roof" markierten Flächen, egal ob vertikal oder horizontal.

    # Verwende gleichen Algorithmus wie für Fassaden
    u, v = _create_local_coordinate_system(normal)

    # Projektion auf lokale Ebene
    origin = vertices[0]
    local_coords = np.array([
        [np.dot(vtx - origin, u), np.dot(vtx - origin, v)]
        for vtx in vertices
    ])

    # Bounding-Box in lokalen Koordinaten
    min_u, max_u = local_coords[:, 0].min(), local_coords[:, 0].max()
    min_v, max_v = local_coords[:, 1].min(), local_coords[:, 1].max()

    # Raster erstellen
    points = []
    u_coords = np.arange(min_u + resolution / 2, max_u, resolution)
    v_coords = np.arange(min_v + resolution / 2, max_v, resolution)

    for u_val in u_coords:
        for v_val in v_coords:
            local_pt = np.array([u_val, v_val])

            # Point-in-Polygon Test
            if _point_in_polygon(local_pt, local_coords):
                # Zurück in 3D transformieren
                world_pt = origin + u_val * u + v_val * v

                points.append(FacadePoint(
                    building_id=building_id,
                    x=world_pt[0],
                    y=world_pt[1],
                    z=world_pt[2],
                    normal=normal.copy(),
                ))

    return points


def sample_all_facades(
    wall_surfaces: List[WallSurface],
    resolution: float = 0.5,
    building_id: str = "",
) -> List[FacadePoint]:
    """
    Erzeugt Rasterpunkte auf allen Fassaden eines Gebäudes.
    """
    all_points = []
    for wall in wall_surfaces:
        points = sample_facade_polygon(wall, resolution, building_id)
        all_points.extend(points)
    return all_points


def sample_all_roofs(
    roof_surfaces: List[WallSurface],
    resolution: float = 0.5,
    building_id: str = "",
) -> List[FacadePoint]:
    """
    Erzeugt Rasterpunkte auf allen Dachflächen eines Gebäudes.
    """
    all_points = []
    for roof in roof_surfaces:
        points = sample_roof_polygon(roof, resolution, building_id)
        all_points.extend(points)
    return all_points


def _calculate_normal(vertices: np.ndarray) -> np.ndarray:
    """Berechnet die Flächennormale eines Polygons."""
    if len(vertices) < 3:
        return None

    # Verwende erste drei nicht-kollineare Punkte
    v1 = vertices[1] - vertices[0]
    v2 = vertices[2] - vertices[0]

    normal = np.cross(v1, v2)
    norm = np.linalg.norm(normal)

    if norm < 1e-10:
        return None

    return normal / norm


def _create_local_coordinate_system(normal: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Erstellt ein lokales 2D-Koordinatensystem auf der Fassadenebene.

    Returns:
        (u, v) - zwei orthogonale Einheitsvektoren in der Fassadenebene
        u: horizontal entlang der Fassade
        v: vertikal entlang der Fassade
    """
    # u = horizontal entlang der Fassade (senkrecht zu normal und z-Achse)
    z_axis = np.array([0, 0, 1])

    u = np.cross(z_axis, normal)
    u_norm = np.linalg.norm(u)

    if u_norm < 0.01:
        # Fassade ist fast horizontal - verwende x-Achse
        u = np.array([1, 0, 0])
    else:
        u = u / u_norm

    # v = senkrecht zu u und normal (vertikal in der Fassadenebene)
    v = np.cross(normal, u)
    v = v / np.linalg.norm(v)

    return u, v


def _point_in_polygon(point: np.ndarray, polygon: np.ndarray) -> bool:
    """
    Ray-Casting-Algorithmus für Point-in-Polygon-Test.

    Args:
        point: 2D-Punkt [x, y]
        polygon: Array von 2D-Polygon-Vertices (N, 2)

    Returns:
        True wenn Punkt innerhalb des Polygons liegt
    """
    n = len(polygon)
    inside = False

    j = n - 1
    for i in range(n):
        yi, yj = polygon[i, 1], polygon[j, 1]
        xi, xj = polygon[i, 0], polygon[j, 0]

        if ((yi > point[1]) != (yj > point[1])) and (
            point[0] < (xj - xi) * (point[1] - yi) / (yj - yi + 1e-10) + xi
        ):
            inside = not inside
        j = i

    return inside


def filter_points_by_distance(
    points: List[FacadePoint],
    center_e: float,
    center_n: float,
    max_distance: float,
) -> List[FacadePoint]:
    """
    Filtert Punkte nach horizontalem Abstand zum Zentrum.
    """
    filtered = []
    for p in points:
        dist = np.sqrt((p.x - center_e) ** 2 + (p.y - center_n) ** 2)
        if dist <= max_distance:
            filtered.append(p)
    return filtered


def create_virtual_omen_points(
    omen_locations: list,
    buildings: list,
    resolution_m: float = 1.0,
) -> List[FacadePoint]:
    """
    Erstellt virtuelle Messpunkte für Bauplatz-OMENs (OMENs ohne Gebäudezuordnung).

    Für jedes OMEN das keinem existierenden Gebäude zugeordnet werden kann,
    werden virtuelle Fassadenpunkte erstellt. Dies ist wichtig für:
    - Bauplätze (Gebäude noch nicht gebaut)
    - Fehlende Gebäudedaten in swissBUILDINGS3D
    - Geplante Gebäude

    Args:
        omen_locations: Liste von OMENLocation-Objekten
        buildings: Liste von Building-Objekten für Zuordnungsprüfung
        resolution_m: Abstand zwischen Messpunkten (für mehrere Höhen)

    Returns:
        Liste von FacadePoint für nicht zugeordnete OMENs
    """
    if not omen_locations:
        return []

    # Building-Map für schnellen Zugriff
    building_map = {}
    for building in buildings:
        building_map[building.id] = building

    # Point-in-Polygon Helper
    def point_in_polygon_2d(x, y, polygon_points):
        """Ray-casting algorithm für Point-in-Polygon Test"""
        n = len(polygon_points)
        inside = False
        p1x, p1y = polygon_points[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon_points[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside

    # Prüfe jedes OMEN ob es einem Gebäude zugeordnet werden kann
    unassigned_omens = []

    for omen in omen_locations:
        assigned = False

        for building in buildings:
            # 1. Höhencheck
            if building.wall_surfaces or building.roof_surfaces:
                all_surfaces = building.wall_surfaces + building.roof_surfaces
                all_z = [v[2] for surface in all_surfaces for v in surface.vertices]
                building_min_z = min(all_z)
                building_max_z = max(all_z)
            else:
                continue

            height_tolerance = 0.5
            if not ((building_min_z - height_tolerance) <= omen.position.h <= (building_max_z + height_tolerance)):
                continue

            # 2. Point-in-Polygon Check
            all_surfaces = building.wall_surfaces + building.roof_surfaces
            if not all_surfaces:
                continue

            all_points_2d = set()
            for surface in all_surfaces:
                for vertex in surface.vertices:
                    all_points_2d.add((round(vertex[0], 2), round(vertex[1], 2)))

            if len(all_points_2d) < 3:
                continue

            polygon_points_2d = list(all_points_2d)
            if point_in_polygon_2d(omen.position.e, omen.position.n, polygon_points_2d):
                assigned = True
                break

        if not assigned:
            unassigned_omens.append(omen)

    # Erstelle virtuelle Messpunkte für nicht zugeordnete OMENs
    virtual_points = []

    for omen in unassigned_omens:
        # Erstelle Messpunkte in verschiedenen Richtungen (N, E, S, W)
        # für konservative Worst-Case-Abschätzung
        normals = [
            np.array([0.0, 1.0, 0.0]),  # Nord
            np.array([1.0, 0.0, 0.0]),  # Ost
            np.array([0.0, -1.0, 0.0]),  # Süd
            np.array([-1.0, 0.0, 0.0]),  # West
        ]

        # Erstelle Punkte an der OMEN-Höhe (direkt aus StDB)
        # Diese Höhe ist bereits die geplante Messpunkthöhe
        for normal in normals:
            virtual_points.append(FacadePoint(
                building_id=f"BAUPLATZ_OMEN_O{omen.nr}",
                x=omen.position.e,
                y=omen.position.n,
                z=omen.position.h,  # Direkt aus StDB
                normal=normal,
            ))

    return virtual_points
