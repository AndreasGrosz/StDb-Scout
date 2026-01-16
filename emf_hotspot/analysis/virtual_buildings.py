"""
Virtuelle Gebäude für unbebaute Parzellen
"""

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

from ..models import Building, WallSurface
from ..loaders.parcel_loader import Parcel, get_parcel_center


@dataclass
class VirtualBuilding:
    """Virtuelles Gebäude für unbebaute Parzelle"""
    parcel_egrid: str
    parcel_number: str
    base_polygon: np.ndarray  # Shape (N, 2) - Grundfläche mit Grenzabstand
    base_height: float  # Untere Höhe (Terrain)
    roof_height: float  # Obere Höhe (von höchstem Nachbar)
    num_floors: int  # Geschosszahl
    is_virtual: bool = True


def point_in_polygon(x: float, y: float, polygon: np.ndarray) -> bool:
    """
    Prüft ob Punkt in Polygon liegt (Ray-Casting-Algorithmus).

    Args:
        x, y: Punkt-Koordinaten
        polygon: np.ndarray mit shape (N, 2)

    Returns:
        True wenn Punkt im Polygon liegt
    """
    n = len(polygon)
    inside = False

    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y

    return inside


def buildings_on_parcel(parcel: Parcel, buildings: List[Building]) -> List[Building]:
    """
    Findet alle Gebäude die auf einer Parzelle stehen.

    Prüft ob der Mittelpunkt des Gebäudes innerhalb der Parzelle liegt.
    """
    buildings_on = []

    for building in buildings:
        if not building.wall_surfaces:
            continue

        # Berechne Gebäude-Mittelpunkt aus allen Wand-Vertices
        e_coords = []
        n_coords = []
        for wall in building.wall_surfaces:
            if len(wall.vertices) > 0:
                e_coords.extend(wall.vertices[:, 0])
                n_coords.extend(wall.vertices[:, 1])

        if not e_coords:
            continue

        center_e = sum(e_coords) / len(e_coords)
        center_n = sum(n_coords) / len(n_coords)

        # Prüfe ob Mittelpunkt in Parzelle
        if point_in_polygon(center_e, center_n, parcel.polygon):
            buildings_on.append(building)

    return buildings_on


def shrink_polygon(polygon: np.ndarray, distance: float) -> Optional[np.ndarray]:
    """
    Schrumpft ein Polygon um einen bestimmten Abstand (negative buffer).

    Args:
        polygon: np.ndarray mit shape (N, 2)
        distance: Abstand in Metern (z.B. 3.0 für 3m Grenzabstand)

    Returns:
        Geschrumpftes Polygon oder None falls zu klein
    """
    try:
        # Verwende Shapely für Buffer-Operation
        poly = Polygon(polygon)
        shrunk = poly.buffer(-distance)

        if shrunk.is_empty or shrunk.area < 10:  # Mindestens 10m²
            return None

        # Konvertiere zurück zu numpy array
        if hasattr(shrunk, 'exterior'):
            coords = list(shrunk.exterior.coords)
            return np.array(coords)
        else:
            return None

    except Exception as e:
        print(f"  WARNUNG: Polygon-Schrumpfung fehlgeschlagen: {e}")
        return None


def find_tallest_neighbor(
    parcel_center: Tuple[float, float],
    buildings: List[Building],
    max_distance_m: float = 100.0
) -> Tuple[float, int]:
    """
    Findet das höchste Gebäude in der Nachbarschaft.

    Args:
        parcel_center: (E, N) Koordinaten des Parzellen-Mittelpunkts
        buildings: Liste aller Gebäude
        max_distance_m: Maximale Suchradius

    Returns:
        (max_height, num_floors) - Höhe und Geschosszahl
    """
    max_height = 0.0
    max_floors = 1

    center_e, center_n = parcel_center

    for building in buildings:
        if not building.wall_surfaces:
            continue

        # Berechne Gebäude-Mittelpunkt
        e_coords = []
        n_coords = []
        h_coords = []
        for wall in building.wall_surfaces:
            if len(wall.vertices) > 0:
                e_coords.extend(wall.vertices[:, 0])
                n_coords.extend(wall.vertices[:, 1])
                h_coords.extend(wall.vertices[:, 2])

        if not e_coords:
            continue

        building_e = sum(e_coords) / len(e_coords)
        building_n = sum(n_coords) / len(n_coords)

        # Distanz prüfen
        distance = np.sqrt((building_e - center_e)**2 + (building_n - center_n)**2)
        if distance > max_distance_m:
            continue

        # Gebäudehöhe berechnen
        min_h = min(h_coords)
        max_h = max(h_coords)
        height = max_h - min_h

        if height > max_height:
            max_height = height
            # Geschosszahl schätzen (typisch 3m pro Stockwerk)
            max_floors = max(1, int(round(height / 3.0)))

    # Fallback: Mindestens 2 Stockwerke / 6m Höhe
    if max_height < 6.0:
        max_height = 6.0
        max_floors = 2

    return max_height, max_floors


def create_virtual_building(
    parcel: Parcel,
    buildings: List[Building],
    setback_m: float = 3.0
) -> Optional[VirtualBuilding]:
    """
    Erstellt ein virtuelles Gebäude für eine unbebaute Parzelle.

    Args:
        parcel: Die Parzelle
        buildings: Alle verfügbaren Gebäude (für Höhen-Lookup)
        setback_m: Grenzabstand in Metern

    Returns:
        VirtualBuilding oder None falls nicht möglich
    """
    # 1. Prüfe ob Parzelle bebaut ist
    buildings_on = buildings_on_parcel(parcel, buildings)
    if buildings_on:
        return None  # Parzelle ist bereits bebaut

    # 2. Schrumpfe Polygon um Grenzabstand
    shrunk_polygon = shrink_polygon(parcel.polygon, setback_m)
    if shrunk_polygon is None:
        return None  # Parzelle zu klein

    # 3. Finde höchstes Nachbargebäude
    parcel_center = get_parcel_center(parcel)
    max_height, num_floors = find_tallest_neighbor(parcel_center, buildings)

    # 4. Schätze Terrain-Höhe (Mittelwert aller Gebäude-Basishöhen in der Nähe)
    terrain_heights = []
    for building in buildings:
        if not building.wall_surfaces:
            continue

        # Berechne minimale Z-Koordinate (Basis)
        for wall in building.wall_surfaces:
            if len(wall.vertices) > 0:
                terrain_heights.append(float(wall.vertices[:, 2].min()))

    if terrain_heights:
        base_height = np.median(terrain_heights)
    else:
        base_height = 400.0  # Fallback

    roof_height = base_height + max_height

    # 5. Erstelle virtuelles Gebäude
    return VirtualBuilding(
        parcel_egrid=parcel.egrid,
        parcel_number=parcel.number,
        base_polygon=shrunk_polygon,
        base_height=base_height,
        roof_height=roof_height,
        num_floors=num_floors,
        is_virtual=True
    )


def find_empty_parcels_with_virtual_buildings(
    parcels: List[Parcel],
    buildings: List[Building],
    setback_m: float = 3.0
) -> List[VirtualBuilding]:
    """
    Findet alle leeren Parzellen und erstellt virtuelle Gebäude.

    Args:
        parcels: Alle Parzellen
        buildings: Alle realen Gebäude
        setback_m: Grenzabstand

    Returns:
        Liste von virtuellen Gebäuden
    """
    virtual_buildings = []

    for parcel in parcels:
        virtual = create_virtual_building(parcel, buildings, setback_m)
        if virtual:
            virtual_buildings.append(virtual)

    return virtual_buildings


def sample_virtual_building_facades(
    virtual_building: VirtualBuilding,
    resolution_m: float = 1.0
) -> List[Tuple[float, float, float]]:
    """
    Erstellt Messpunkte an den Fassaden eines virtuellen Gebäudes.

    Args:
        virtual_building: Das virtuelle Gebäude
        resolution_m: Auflösung des Samplings in Metern

    Returns:
        Liste von (E, N, H) Koordinaten für Messpunkte
    """
    facade_points = []
    polygon = virtual_building.base_polygon
    base_h = virtual_building.base_height
    roof_h = virtual_building.roof_height

    # Höhen-Sampling: Pro Stockwerk ein Messpunkt bei 1.5m Fensterhöhe
    floor_height = 3.0  # Typische Geschosshöhe
    num_floors = virtual_building.num_floors

    heights = []
    for floor in range(num_floors):
        # Messpunkt bei 1.5m über Boden des Stockwerks
        h = base_h + floor * floor_height + 1.5
        if h < roof_h:
            heights.append(h)

    # Fassaden-Sampling: Für jede Kante des Polygons
    for i in range(len(polygon) - 1):
        p1 = polygon[i]
        p2 = polygon[i + 1]

        # Kantenlänge
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = np.sqrt(dx**2 + dy**2)

        if length < 0.1:
            continue

        # Anzahl Messpunkte entlang der Kante
        num_points = max(1, int(length / resolution_m))

        for j in range(num_points):
            t = j / max(1, num_points - 1) if num_points > 1 else 0.5
            e = p1[0] + t * dx
            n = p1[1] + t * dy

            # Für jede Höhe einen Messpunkt
            for h in heights:
                facade_points.append((e, n, h))

    return facade_points


def convert_virtual_to_building(virtual: VirtualBuilding) -> Building:
    """
    Konvertiert ein virtuelles Gebäude in ein Building-Objekt für die Berechnung.

    Args:
        virtual: VirtualBuilding

    Returns:
        Building-Objekt mit Wall-Surfaces
    """
    walls = []
    polygon = virtual.base_polygon
    base_h = virtual.base_height
    roof_h = virtual.roof_height

    # Erstelle Wand-Surfaces für jede Kante
    for i in range(len(polygon) - 1):
        p1 = polygon[i]
        p2 = polygon[i + 1]

        # 4 Eckpunkte der Wand (unten-links, unten-rechts, oben-rechts, oben-links)
        vertices = np.array([
            [p1[0], p1[1], base_h],
            [p2[0], p2[1], base_h],
            [p2[0], p2[1], roof_h],
            [p1[0], p1[1], roof_h],
            [p1[0], p1[1], base_h],  # Schließe Polygon
        ])

        # Berechne Normale (nach außen zeigend)
        edge_vec = np.array([p2[0] - p1[0], p2[1] - p1[1], 0])
        up_vec = np.array([0, 0, 1])
        normal = np.cross(edge_vec, up_vec)
        normal = normal / (np.linalg.norm(normal) + 1e-10)

        wall = WallSurface(
            id=f"VIRTUAL_{virtual.parcel_egrid}_wall_{i}",
            vertices=vertices,
            normal=normal
        )
        walls.append(wall)

    # Erstelle Building-Objekt
    building = Building(
        id=f"VIRTUAL_{virtual.parcel_egrid}",
        egid=f"VIRTUAL_{virtual.parcel_number}",
        wall_surfaces=walls,
        roof_surfaces=[]  # Keine Dach-Sampling für virtuelle Gebäude
    )

    return building
