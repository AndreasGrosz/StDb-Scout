"""
GDB Loader für swissBUILDINGS3D ESRI Geodatabase Format

Nutzt GDAL/OGR um .gdb.zip Dateien zu lesen.
"""

from pathlib import Path
from typing import List, Optional
import tempfile
import zipfile
import numpy as np

try:
    from osgeo import ogr, osr
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False
    raise ImportError("GDAL/OGR nicht verfügbar. Installation: conda install -c conda-forge gdal")

from ..models import Building, WallSurface, LV95Coordinate


def load_buildings_from_gdb(
    gdb_zip_path: Path,
    center: Optional[tuple] = None,  # (E, N) LV95
    radius: float = 100.0,
) -> List[Building]:
    """
    Lädt Gebäude aus einer ESRI Geodatabase (.gdb.zip).

    Args:
        gdb_zip_path: Pfad zur .gdb.zip Datei
        center: Optional - Zentrum für Umkreisfilter (E, N) in LV95
        radius: Suchradius in Metern

    Returns:
        Liste von Building-Objekten
    """
    if not GDAL_AVAILABLE:
        raise ImportError("GDAL/OGR nicht verfügbar")

    buildings = []

    # Entpacke GDB in temporäres Verzeichnis
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        print(f"  Entpacke GDB: {gdb_zip_path.name}")
        with zipfile.ZipFile(gdb_zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmppath)

        # Finde .gdb Ordner
        gdb_dirs = list(tmppath.glob("*.gdb"))
        if not gdb_dirs:
            raise ValueError(f"Keine .gdb Datei in {gdb_zip_path} gefunden")

        gdb_path = gdb_dirs[0]
        print(f"  Öffne GDB: {gdb_path.name}")

        # Öffne GDB mit GDAL
        datasource = ogr.Open(str(gdb_path))
        if datasource is None:
            raise ValueError(f"Konnte GDB nicht öffnen: {gdb_path}")

        # Finde Wall Layer (GDB hat separate Wand/Dach/Boden Layer)
        wall_layer = None
        for i in range(datasource.GetLayerCount()):
            layer = datasource.GetLayerByIndex(i)
            layer_name = layer.GetName()
            if layer_name == 'Wall':
                wall_layer = layer
                break

        if wall_layer is None:
            # Fallback: Suche nach Building
            for i in range(datasource.GetLayerCount()):
                layer = datasource.GetLayerByIndex(i)
                layer_name = layer.GetName()
                if 'building' in layer_name.lower():
                    wall_layer = layer
                    break

        if wall_layer is None:
            raise ValueError("Kein Wall oder Building Layer gefunden")

        building_layer = wall_layer
        print(f"  Layer: {building_layer.GetName()} ({building_layer.GetFeatureCount()} Features)")

        # Spatial Filter setzen (falls center gegeben)
        if center:
            x_min = center[0] - radius
            x_max = center[0] + radius
            y_min = center[1] - radius
            y_max = center[1] + radius
            building_layer.SetSpatialFilterRect(x_min, y_min, x_max, y_max)
            print(f"  Filter: {building_layer.GetFeatureCount()} Gebäude im Radius {radius}m")

        # Iteriere über Features und gruppiere nach EGID
        from collections import defaultdict
        walls_by_egid = defaultdict(list)
        parsed_walls = 0
        failed_walls = 0
        walls_without_egid = 0
        total_walls_checked = 0

        for idx, feature in enumerate(building_layer):
            total_walls_checked += 1
            try:
                # EGID extrahieren
                egid = None
                try:
                    egid_val = feature.GetField("EGID")
                    if egid_val:
                        egid = str(egid_val)
                except:
                    pass

                if not egid:
                    walls_without_egid += 1
                    if walls_without_egid == 1:
                        print(f"  DEBUG: Erste Wand ohne EGID gefunden (Feature {idx})")
                    continue  # Überspringe Wände ohne EGID

                # Geometrie extrahieren
                geom = feature.GetGeometryRef()
                if geom is None:
                    continue

                # Extrahiere Flächen
                surfaces = _extract_all_surfaces(geom)
                if surfaces:
                    walls_by_egid[egid].extend(surfaces)
                    parsed_walls += 1
                else:
                    failed_walls += 1
                    if failed_walls <= 3:  # Zeige erste 3 Fehler
                        print(f"  DEBUG: Wand ohne Surfaces - Geom: {geom.GetGeometryName()}, Count: {geom.GetGeometryCount()}, EGID: {egid}")

            except Exception as e:
                failed_walls += 1
                if failed_walls == 1:
                    print(f"  WARNUNG: Wall-Parsing-Fehler: {e}")
                continue

        # Erstelle Building-Objekte aus gruppierten Wänden
        for egid, wall_surfaces in walls_by_egid.items():
            if wall_surfaces:
                building = Building(
                    id=f"GDB_EGID_{egid}",
                    egid=egid,
                    wall_surfaces=wall_surfaces,
                    roof_surfaces=[],
                )
                buildings.append(building)

        print(f"  DEBUG: {total_walls_checked} Wände geprüft, {walls_without_egid} ohne EGID, {parsed_walls} erfolgreich")

        datasource = None  # Close datasource

    print(f"  → {len(buildings)} Gebäude geladen")
    return buildings


def _parse_gdb_feature(feature) -> Optional[Building]:
    """
    Parst ein einzelnes GDB Feature zu einem Building.
    """
    # ID extrahieren
    fid = feature.GetFID()
    building_id = f"GDB_FID_{fid}"

    # EGID extrahieren
    egid = ""
    try:
        egid_val = feature.GetField("EGID")
        if egid_val:
            egid = str(egid_val)
    except:
        pass

    # Geometrie extrahieren
    geom = feature.GetGeometryRef()
    if geom is None:
        return None

    # Extrahiere alle Flächen rekursiv
    wall_surfaces = _extract_all_surfaces(geom)

    if not wall_surfaces:
        return None

    return Building(
        id=building_id,
        egid=egid,
        wall_surfaces=wall_surfaces,
        roof_surfaces=[],  # Trennung Wand/Dach später
    )


def _extract_all_surfaces(geom) -> List[WallSurface]:
    """
    Extrahiert rekursiv alle Flächen aus beliebiger Geometrie.
    GDB Wall-Layer nutzt TIN (Triangulated Irregular Network) oder MULTIPOLYGON.
    """
    surfaces = []
    geom_type = geom.GetGeometryType()
    geom_name = geom.GetGeometryName()

    # TIN: Spezialbehandlung - kombiniere alle Triangles zu einer Wand
    if geom_name == 'TIN':
        surface = _extract_surface_from_tin(geom)
        if surface:
            surfaces.append(surface)

    # Container-Typen: Rekursiv durchsuchen (MULTI*, COLLECTION, etc.)
    # WICHTIG: Vor POLYGON-Check, weil MULTIPOLYGON auch "POLYGON" enthält!
    elif 'MULTI' in geom_name or 'COLLECTION' in geom_name or 'SOLID' in geom_name or 'SURFACE' in geom_name:
        for i in range(geom.GetGeometryCount()):
            child_geom = geom.GetGeometryRef(i)
            if child_geom:
                surfaces.extend(_extract_all_surfaces(child_geom))

    # Basis-Typen: Einzelnes Polygon (nach Container-Check!)
    elif 'POLYGON' in geom_name:
        surfaces.extend(_extract_surfaces_from_polygon(geom))

    return surfaces


def _extract_surface_from_tin(tin) -> Optional[WallSurface]:
    """
    Extrahiert eine Wand-Surface aus einem TIN (Triangulated Irregular Network).

    Ein TIN besteht aus mehreren TRIANGLE-Geometrien. Wir extrahieren alle
    eindeutigen Vertices und kombinieren sie zu einer WallSurface.
    """
    all_points = set()  # Set für eindeutige Punkte

    # Iteriere über alle Triangles im TIN
    for i in range(tin.GetGeometryCount()):
        triangle = tin.GetGeometryRef(i)
        if triangle is None:
            continue

        # Methode 1: Versuche Punkte direkt vom Triangle zu holen
        if triangle.GetPointCount() > 0:
            for j in range(triangle.GetPointCount()):
                x, y, z = triangle.GetPoint(j)
                # Runde auf mm, um fast-identische Punkte zu vereinen
                all_points.add((round(x, 3), round(y, 3), round(z, 3)))

        # Methode 2: Versuche über Ring (LINEARRING im Triangle)
        elif triangle.GetGeometryCount() > 0:
            ring = triangle.GetGeometryRef(0)
            if ring and ring.GetPointCount() > 0:
                for j in range(ring.GetPointCount()):
                    x, y, z = ring.GetPoint(j)
                    all_points.add((round(x, 3), round(y, 3), round(z, 3)))

    if len(all_points) < 3:
        return None

    # Konvertiere zu numpy array
    vertices = np.array(list(all_points))

    # Berechne durchschnittliche Normale über alle Triangles
    # (einfache Methode: Nutze erste 3 nicht-kollineare Punkte)
    normal = np.array([0.0, 0.0, 1.0])  # Default
    if len(vertices) >= 3:
        try:
            v1 = vertices[1] - vertices[0]
            v2 = vertices[2] - vertices[0]
            normal = np.cross(v1, v2)
            normal_norm = np.linalg.norm(normal)

            if normal_norm > 1e-6:
                normal = normal / normal_norm
        except:
            pass  # Nutze Default

    # Erstelle WallSurface
    surface = WallSurface(
        id=f"tin_surface_{id(tin)}",
        vertices=vertices,
        normal=normal,
    )

    return surface


def _extract_surfaces_from_polygon(polygon) -> List[WallSurface]:
    """
    Extrahiert Flächen aus einem 3D Polygon.
    """
    surfaces = []

    # Äußerer Ring
    ring = polygon.GetGeometryRef(0)
    if ring:
        points = []
        for i in range(ring.GetPointCount()):
            x, y, z = ring.GetPoint(i)
            points.append(np.array([x, y, z]))

        if len(points) >= 3:
            vertices = np.array(points)

            # Berechne Normale (wenn möglich)
            normal = np.array([0.0, 0.0, 1.0])  # Default: horizontal
            if len(vertices) >= 3:
                try:
                    v1 = vertices[1] - vertices[0]
                    v2 = vertices[2] - vertices[0]
                    normal = np.cross(v1, v2)
                    normal_norm = np.linalg.norm(normal)

                    if normal_norm > 1e-6:
                        normal = normal / normal_norm
                except:
                    pass  # Nutze Default

            # KEIN Filter mehr - akzeptiere ALLE Flächen
            # (Wand/Dach-Trennung später, falls nötig)
            surface = WallSurface(
                id=f"surface_{id(vertices)}",
                vertices=vertices,
                normal=normal,
            )
            surfaces.append(surface)

    return surfaces
