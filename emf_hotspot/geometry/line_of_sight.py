"""
Line-of-Sight (LOS) Analyse für EMF-Berechnungen

Prüft ob Gebäude zwischen Antenne und Messpunkt stehen und
berechnet die resultierende Gebäudedämpfung.
"""

from typing import List, Tuple, Optional
import numpy as np

from ..models import Building, LV95Coordinate


def check_line_of_sight_3d(
    start: LV95Coordinate,
    end: LV95Coordinate,
    buildings: List[Building],
    margin: float = 0.5,
    debug: bool = False,
) -> Tuple[bool, List[Building], float]:
    """
    Prüft ob freie Sichtlinie zwischen zwei Punkten besteht (3D).

    Verwendet 2D-Footprint-Check mit 3D-Höhenvalidierung.

    Args:
        start: Startpunkt (z.B. Antennenposition)
        end: Endpunkt (z.B. Messpunkt/Hotspot)
        buildings: Liste aller Gebäude
        margin: Sicherheitsabstand in Metern (Default: 0.5m)

    Returns:
        Tuple von:
        - has_los: True wenn freie Sichtlinie, False wenn blockiert
        - blocking_buildings: Liste der blockierenden Gebäude
        - total_attenuation_db: Gesamtdämpfung in dB
    """

    if not buildings:
        return True, [], 0.0

    # 2D-Linie zwischen Start und Ende (XY-Projektion)
    line_start = np.array([start.e, start.n])
    line_end = np.array([end.e, end.n])
    line_vec = line_end - line_start
    total_dist = np.linalg.norm(line_vec)

    if total_dist < 0.01:  # Start == End
        return True, [], 0.0

    blocking_buildings = []

    # Prüfe jedes Gebäude ob die Sichtlinie eine der Wandflächen schneidet (3D-Ansatz)
    for building in buildings:
        if not building.wall_surfaces:
            continue

        # Prüfe jede Wandfläche des Gebäudes
        for wall in building.wall_surfaces:
            if wall.vertices is None or len(wall.vertices) < 3:
                continue

            # Prüfe ob die 3D-Sichtlinie dieses Wand-Polygon schneidet
            if _ray_intersects_polygon_3d(start, end, wall.vertices, margin, debug=debug):
                # Gebäude blockiert die Sichtlinie!
                if debug:
                    print(f"      [BLOCKING] Gebäude: {building.id[:40]}...")
                blocking_buildings.append(building)
                break  # Ein Treffer reicht, nächstes Gebäude


    # Berechne Gesamtdämpfung
    total_attenuation_db = calculate_building_attenuation(blocking_buildings)

    has_los = len(blocking_buildings) == 0

    return has_los, blocking_buildings, total_attenuation_db


def calculate_building_attenuation(buildings: List[Building]) -> float:
    """
    Berechnet die Gebäudedämpfung basierend auf blockierenden Gebäuden.

    Typische Werte (ITU-R P.2040):
    - Holzgebäude: 5-10 dB
    - Betongebäude (dünn): 10-15 dB
    - Betongebäude (dick): 15-25 dB
    - Mehrere Gebäude: additive Dämpfung

    Args:
        buildings: Liste blockierender Gebäude

    Returns:
        Gesamtdämpfung in dB
    """

    if not buildings:
        return 0.0

    # DÄMPFUNGSWERT ANPASSEN:
    # - 0 dB: Worst-Case für Bauanträge (konservativ, Fenster möglich)
    # - 6 dB: Leichte Dämpfung (Holz, Fenster)
    # - 12 dB: Typischer Betonbau ohne Fenster (ITU-R P.2040) ← STANDARD
    # - 20 dB: Dicke Betonwände

    attenuation_per_building = 12.0  # dB - Typischer Betonbau (ITU-R P.2040)

    total_attenuation = 0.0

    for building in buildings:
        # TODO: Könnte später nach Gebäudetyp differenziert werden
        # (z.B. aus swissBUILDINGS3D Attributen)
        total_attenuation += attenuation_per_building

    return total_attenuation


def add_los_info_to_results(
    results: List,
    antenna_position: LV95Coordinate,
    buildings: List[Building],
    mast_height_offset: float = 0.0,
) -> None:
    """
    Fügt LOS-Information zu allen HotspotResults hinzu (in-place).

    OPTIMIERUNG: Nur Punkte die das Limit überschreiten werden analysiert,
    da nur diese potenzielle Hotspots sind.

    Args:
        results: Liste von HotspotResult-Objekten
        antenna_position: Position der Antenne
        buildings: Liste aller Gebäude
    """

    # Filtere nur Punkte die Schwellwert überschreiten (potenzielle Hotspots)
    results_to_check = [r for r in results if r.exceeds_limit]

    print(f"    Prüfe LOS für {len(results_to_check)} potenzielle Hotspots (von {len(results)} Punkten)")

    # Wende Mast-Offset an für LOS-Prüfung
    actual_antenna_height = antenna_position.h + mast_height_offset
    antenna_los_pos = LV95Coordinate(
        e=antenna_position.e,
        n=antenna_position.n,
        h=actual_antenna_height
    )

    if mast_height_offset > 0:
        print(f"    Antenne: Basis H={antenna_position.h:.2f}m, mit Mast H={actual_antenna_height:.2f}m (+{mast_height_offset:.2f}m)")

    # WICHTIG: Antennengebäude wird NICHT mehr excludiert!
    # Begründung: Obere Stockwerke können durch Oberlichter belastet sein.
    # Die Betondecke dämpft nur wenn geschlossen (keine Fenster/Oberlichter).
    # → Konservative Annahme: Prüfe alle Gebäude

    for result in results_to_check:
        # Erstelle LV95Coordinate für Result-Position
        result_pos = LV95Coordinate(e=result.x, n=result.y, h=result.z)

        # Prüfe LOS - WICHTIG: Exclude nur das eigene Gebäude (wo der Messpunkt liegt)
        buildings_to_check = [
            b for b in buildings
            if b.id != result.building_id  # Nur eigenes Gebäude excludieren
        ]

        has_los, blocking, attenuation_db = check_line_of_sight_3d(
            antenna_los_pos,  # Mit Mast-Offset!
            result_pos,
            buildings_to_check,
        )

        # Füge als Attribute hinzu
        result.has_los = has_los
        result.num_buildings_blocking = len(blocking)
        result.building_attenuation_db = attenuation_db

        # Optional: Liste der blockierenden Gebäude-IDs
        result.blocking_building_ids = [b.id for b in blocking] if blocking else []


def _extract_building_footprint(building) -> List:
    """
    Extrahiert die 2D-Footprint-Koordinaten eines Gebäudes aus seinen Wandflächen.

    WICHTIG: Nimmt nur BODEN-Vertices (unterste 20% der Höhe), um korrekte
    Footprints zu erhalten und nicht versehentlich Dach-Overhangs einzubeziehen.

    Args:
        building: Building-Objekt mit wall_surfaces und roof_surfaces

    Returns:
        Liste von (x, y) Koordinaten des Gebäude-Grundrisses
    """
    all_vertices = []

    # Sammle alle Vertices von Wänden (NICHT Dächer - die können überstehen!)
    for wall in building.wall_surfaces:
        if wall.vertices is not None and len(wall.vertices) > 0:
            all_vertices.extend(wall.vertices)

    if not all_vertices:
        return []

    # Konvertiere zu numpy array
    all_vertices = np.array(all_vertices)

    # Finde minimale und maximale Z-Koordinate
    z_min = all_vertices[:, 2].min()
    z_max = all_vertices[:, 2].max()
    z_threshold = z_min + (z_max - z_min) * 0.2  # Unterste 20% der Höhe

    # Filtere nur Boden-Vertices (unterste 20%)
    ground_vertices = all_vertices[all_vertices[:, 2] <= z_threshold]

    if len(ground_vertices) == 0:
        # Fallback: Verwende alle Vertices
        ground_vertices = all_vertices

    # Projiziere auf 2D (nur X, Y) und finde einzigartige Punkte
    unique_xy = {}
    for vertex in ground_vertices:
        xy_key = (round(vertex[0], 1), round(vertex[1], 1))  # Runde auf dm
        if xy_key not in unique_xy:
            unique_xy[xy_key] = vertex[2]
        else:
            unique_xy[xy_key] = min(unique_xy[xy_key], vertex[2])

    # Erstelle Koordinatenliste (nur XY für Footprint)
    footprint_coords = [(x, y) for (x, y) in unique_xy.keys()]

    if len(footprint_coords) < 3:
        return []

    # Sortiere Punkte im Uhrzeigersinn (für Polygon)
    footprint_coords = _sort_polygon_vertices(footprint_coords)

    return footprint_coords


def _sort_polygon_vertices(coords: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """
    Sortiert 2D-Koordinaten im Uhrzeigersinn um ihren Schwerpunkt.

    Args:
        coords: Liste von (x, y) Tupeln

    Returns:
        Sortierte Liste von (x, y) Tupeln
    """
    if len(coords) < 3:
        return coords

    # Berechne Schwerpunkt
    coords_array = np.array(coords)
    centroid = coords_array.mean(axis=0)

    # Sortiere nach Winkel vom Schwerpunkt
    def angle_from_centroid(point):
        return np.arctan2(point[1] - centroid[1], point[0] - centroid[0])

    sorted_coords = sorted(coords, key=angle_from_centroid)

    return sorted_coords


def _get_building_height_range(building) -> Tuple[float, float]:
    """
    Ermittelt die minimale und maximale Höhe eines Gebäudes.

    Args:
        building: Building-Objekt

    Returns:
        Tuple (z_min, z_max) in Metern über Meer
    """
    all_z = []

    # Sammle alle Z-Koordinaten
    for wall in building.wall_surfaces:
        if wall.vertices is not None and len(wall.vertices) > 0:
            all_z.extend(wall.vertices[:, 2])

    for roof in building.roof_surfaces:
        if roof.vertices is not None and len(roof.vertices) > 0:
            all_z.extend(roof.vertices[:, 2])

    if not all_z:
        return 0.0, 1000.0  # Default-Werte

    return float(np.min(all_z)), float(np.max(all_z))


def _ray_intersects_polygon_3d(
    start: LV95Coordinate,
    end: LV95Coordinate,
    polygon_vertices: np.ndarray,
    margin: float = 0.0,
    debug: bool = False,
) -> bool:
    """
    Prüft ob ein 3D-Ray (Sichtlinie) ein 3D-Polygon schneidet.

    Verwendet Möller-Trumbore Ray-Triangle-Intersection-Algorithmus.
    Das Polygon wird in Dreiecke zerlegt (Fan-Triangulation).

    Args:
        start: Startpunkt der Sichtlinie (Antenne)
        end: Endpunkt der Sichtlinie (Messpunkt)
        polygon_vertices: numpy array (N, 3) der Polygon-Vertices
        margin: Sicherheitsabstand (nicht verwendet bei 3D)
        debug: Debug-Ausgaben aktivieren

    Returns:
        True wenn die Sichtlinie das Polygon schneidet
    """
    if len(polygon_vertices) < 3:
        return False

    # Strahlrichtung und -länge
    ray_origin = start.to_array()
    ray_end = end.to_array()
    ray_direction = ray_end - ray_origin
    ray_length = np.linalg.norm(ray_direction)

    if ray_length < 0.01:
        return False  # Start == End

    ray_direction = ray_direction / ray_length  # Normalisieren

    # Trianguliere das Polygon (Fan-Triangulation um ersten Vertex)
    v0 = polygon_vertices[0]

    for i in range(1, len(polygon_vertices) - 1):
        v1 = polygon_vertices[i]
        v2 = polygon_vertices[i + 1]

        # Möller-Trumbore Ray-Triangle-Intersection
        t = _ray_triangle_intersection(ray_origin, ray_direction, v0, v1, v2)

        if t is not None and 0 <= t <= ray_length:
            # DEBUG: Zeige Schnittpunkt-Details
            if debug:
                intersection_point = ray_origin + t * ray_direction
                print(f"        [HIT] t={t:.2f}m (ray_length={ray_length:.2f}m)")
                print(f"              Intersection: E={intersection_point[0]:.2f}, N={intersection_point[1]:.2f}, H={intersection_point[2]:.2f}")
                print(f"              Start: E={start.e:.2f}, N={start.n:.2f}, H={start.h:.2f}")
                print(f"              End:   E={end.e:.2f}, N={end.n:.2f}, H={end.h:.2f}")
                print(f"              Wall Z-range: {polygon_vertices[:, 2].min():.2f} - {polygon_vertices[:, 2].max():.2f}")
            # Schnittpunkt liegt auf dem Strahl zwischen Start und End
            return True

    return False


def _ray_triangle_intersection(
    ray_origin: np.ndarray,
    ray_direction: np.ndarray,
    v0: np.ndarray,
    v1: np.ndarray,
    v2: np.ndarray,
) -> Optional[float]:
    """
    Möller-Trumbore Ray-Triangle-Intersection-Algorithmus.

    Args:
        ray_origin: Startpunkt des Strahls (3D)
        ray_direction: Richtung des Strahls (normalisiert)
        v0, v1, v2: Dreieck-Vertices (3D)

    Returns:
        Distanz t entlang des Strahls zum Schnittpunkt, oder None
    """
    epsilon = 1e-6

    # Kanten des Dreiecks
    edge1 = v1 - v0
    edge2 = v2 - v0

    # Berechne Determinante
    h = np.cross(ray_direction, edge2)
    a = np.dot(edge1, h)

    if abs(a) < epsilon:
        # Strahl ist parallel zum Dreieck
        return None

    f = 1.0 / a
    s = ray_origin - v0
    u = f * np.dot(s, h)

    if u < 0.0 or u > 1.0:
        return None

    q = np.cross(s, edge1)
    v = f * np.dot(ray_direction, q)

    if v < 0.0 or u + v > 1.0:
        return None

    # Berechne t um den Schnittpunkt zu finden
    t = f * np.dot(edge2, q)

    if t > epsilon:
        return t

    return None


def _line_intersects_polygon_2d(
    line_start: np.ndarray,
    line_end: np.ndarray,
    polygon_coords: List,
    margin: float = 0.0,
) -> bool:
    """
    Prüft ob eine 2D-Linie ein Polygon schneidet oder durchläuft.

    Args:
        line_start: Start-Punkt der Linie [x, y]
        line_end: End-Punkt der Linie [x, y]
        polygon_coords: Liste von (x, y) Koordinaten des Polygons
        margin: Sicherheitsabstand in Metern

    Returns:
        True wenn Linie das Polygon schneidet
    """
    if len(polygon_coords) < 3:
        return False

    # Prüfe ob Startpunkt oder Endpunkt im Polygon liegt
    if _point_in_polygon_2d(line_start, polygon_coords):
        return True
    if _point_in_polygon_2d(line_end, polygon_coords):
        return True

    # Prüfe Schnitt mit jeder Polygon-Kante
    n = len(polygon_coords)
    for i in range(n):
        p1 = np.array(polygon_coords[i][:2])  # Nur X, Y
        p2 = np.array(polygon_coords[(i + 1) % n][:2])

        if _line_segments_intersect(line_start, line_end, p1, p2):
            return True

    return False


def _point_in_polygon_2d(point: np.ndarray, polygon_coords: List) -> bool:
    """
    Ray-Casting-Algorithmus für Point-in-Polygon-Test (2D).

    Args:
        point: 2D-Punkt [x, y]
        polygon_coords: Liste von (x, y) oder (x, y, z) Koordinaten

    Returns:
        True wenn Punkt innerhalb des Polygons liegt
    """
    n = len(polygon_coords)
    inside = False

    j = n - 1
    for i in range(n):
        xi, yi = polygon_coords[i][0], polygon_coords[i][1]
        xj, yj = polygon_coords[j][0], polygon_coords[j][1]

        if ((yi > point[1]) != (yj > point[1])) and (
            point[0] < (xj - xi) * (point[1] - yi) / (yj - yi + 1e-10) + xi
        ):
            inside = not inside
        j = i

    return inside


def _line_segments_intersect(
    p1: np.ndarray,
    p2: np.ndarray,
    p3: np.ndarray,
    p4: np.ndarray,
) -> bool:
    """
    Prüft ob zwei 2D-Liniensegmente sich schneiden.

    Args:
        p1, p2: Start- und Endpunkt des ersten Segments
        p3, p4: Start- und Endpunkt des zweiten Segments

    Returns:
        True wenn Segmente sich schneiden
    """
    def ccw(A, B, C):
        """Prüft ob drei Punkte gegen den Uhrzeigersinn angeordnet sind."""
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

    return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)


def _line_polygon_intersection_points(
    line_start: np.ndarray,
    line_end: np.ndarray,
    polygon_coords: List,
) -> List[Tuple[float, float]]:
    """
    Findet alle Schnittpunkte einer Linie mit einem Polygon.

    Args:
        line_start: Start-Punkt der Linie [x, y]
        line_end: End-Punkt der Linie [x, y]
        polygon_coords: Liste von (x, y) Koordinaten des Polygons

    Returns:
        Liste von (x, y) Schnittpunkten
    """
    intersections = []

    n = len(polygon_coords)
    for i in range(n):
        p1 = np.array(polygon_coords[i][:2])
        p2 = np.array(polygon_coords[(i + 1) % n][:2])

        intersection = _line_segment_intersection(line_start, line_end, p1, p2)
        if intersection is not None:
            # Vermeide Duplikate (Eckpunkte)
            is_duplicate = False
            for existing in intersections:
                if np.allclose([intersection[0], intersection[1]], existing, atol=0.01):
                    is_duplicate = True
                    break
            if not is_duplicate:
                intersections.append((intersection[0], intersection[1]))

    return intersections


def _line_segment_intersection(
    p1: np.ndarray,
    p2: np.ndarray,
    p3: np.ndarray,
    p4: np.ndarray,
) -> Optional[np.ndarray]:
    """
    Berechnet den Schnittpunkt zweier 2D-Liniensegmente.

    Args:
        p1, p2: Start- und Endpunkt des ersten Segments
        p3, p4: Start- und Endpunkt des zweiten Segments

    Returns:
        Schnittpunkt [x, y] oder None wenn keine Schnittmenge
    """
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4

    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)

    if abs(denom) < 1e-10:
        # Linien sind parallel
        return None

    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

    # Prüfe ob Schnittpunkt innerhalb beider Segmente liegt
    if 0 <= t <= 1 and 0 <= u <= 1:
        x = x1 + t * (x2 - x1)
        y = y1 + t * (y2 - y1)
        return np.array([x, y])

    return None
