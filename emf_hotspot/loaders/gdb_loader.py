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

        # Finde Wall, Roof und Floor Layer (GDB hat separate Layer)
        wall_layer = None
        roof_layer = None
        floor_layer = None

        for i in range(datasource.GetLayerCount()):
            layer = datasource.GetLayerByIndex(i)
            layer_name = layer.GetName()

            if layer_name == 'Wall':
                wall_layer = layer
            elif layer_name == 'Roof':
                roof_layer = layer
            elif layer_name == 'Floor':
                floor_layer = layer

        # Fallback: Suche nach Building (falls keine separaten Layer)
        if wall_layer is None:
            for i in range(datasource.GetLayerCount()):
                layer = datasource.GetLayerByIndex(i)
                layer_name = layer.GetName()
                if 'building' in layer_name.lower():
                    wall_layer = layer
                    break

        if wall_layer is None:
            raise ValueError("Kein Wall oder Building Layer gefunden")

        print(f"  Gefundene Layer:")
        print(f"    Wall: {wall_layer.GetFeatureCount()} Features")
        if roof_layer:
            print(f"    Roof: {roof_layer.GetFeatureCount()} Features")
        if floor_layer:
            print(f"    Floor: {floor_layer.GetFeatureCount()} Features")

        # Spatial Filter setzen (falls center gegeben)
        if center:
            x_min = center[0] - radius
            x_max = center[0] + radius
            y_min = center[1] - radius
            y_max = center[1] + radius

            wall_layer.SetSpatialFilterRect(x_min, y_min, x_max, y_max)
            if roof_layer:
                roof_layer.SetSpatialFilterRect(x_min, y_min, x_max, y_max)
            if floor_layer:
                floor_layer.SetSpatialFilterRect(x_min, y_min, x_max, y_max)

            print(f"  Filter: {wall_layer.GetFeatureCount()} Wände im Radius {radius}m")

        # Iteriere über Features und gruppiere nach EGID
        from collections import defaultdict
        walls_by_egid = defaultdict(list)
        roofs_by_egid = defaultdict(list)
        parsed_walls = 0
        failed_walls = 0
        walls_without_egid = 0
        total_walls_checked = 0

        # Lade Wände
        for idx, feature in enumerate(wall_layer):
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

        print(f"  DEBUG: {total_walls_checked} Wände geprüft, {walls_without_egid} ohne EGID, {parsed_walls} erfolgreich")

        # Lade Dächer (falls Roof-Layer vorhanden)
        if roof_layer:
            parsed_roofs = 0
            failed_roofs = 0
            roofs_without_egid = 0
            total_roofs_checked = 0

            for idx, feature in enumerate(roof_layer):
                total_roofs_checked += 1
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
                        roofs_without_egid += 1
                        continue

                    # Geometrie extrahieren
                    geom = feature.GetGeometryRef()
                    if geom is None:
                        continue

                    # Extrahiere Flächen
                    surfaces = _extract_all_surfaces(geom)
                    if surfaces:
                        roofs_by_egid[egid].extend(surfaces)
                        parsed_roofs += 1
                    else:
                        failed_roofs += 1

                except Exception as e:
                    failed_roofs += 1
                    continue

            print(f"  DEBUG: {total_roofs_checked} Dächer geprüft, {roofs_without_egid} ohne EGID, {parsed_roofs} erfolgreich")

        # Erstelle Building-Objekte aus gruppierten Wänden und Dächern
        all_egids = set(walls_by_egid.keys()) | set(roofs_by_egid.keys())

        for egid in all_egids:
            wall_surfaces = walls_by_egid.get(egid, [])
            roof_surfaces = roofs_by_egid.get(egid, [])

            if wall_surfaces or roof_surfaces:
                building = Building(
                    id=f"GDB_EGID_{egid}",
                    egid=egid,
                    wall_surfaces=wall_surfaces,
                    roof_surfaces=roof_surfaces,
                )
                buildings.append(building)

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

    # TIN: Spezialbehandlung - clustere Triangles nach Wänden
    if geom_name == 'TIN':
        tin_surfaces = _extract_surface_from_tin(geom)
        surfaces.extend(tin_surfaces)

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


def _cluster_triangles_by_normal(triangles, normals, angle_threshold_deg=45.0):
    """
    Clustert Triangles nach Normalenvektor.

    Triangles mit ähnlichen Normalen (innerhalb angle_threshold) werden gruppiert.
    Dies trennt z.B. Nord-, Süd-, Ost-, West-Wände eines Gebäudes.

    Args:
        triangles: Liste von Triangle-Arrays (je 3 Punkte)
        normals: Array von Normalenvektoren (N, 3)
        angle_threshold_deg: Maximaler Winkel für gleiche Wand in Grad

    Returns:
        Liste von (cluster_triangles, cluster_normal) Tupeln
    """
    if len(triangles) == 0:
        return []

    cos_threshold = np.cos(np.radians(angle_threshold_deg))
    clusters = []  # Liste von (triangles, normal) Tupeln

    for tri_idx, (tri, normal) in enumerate(zip(triangles, normals)):
        # Finde Cluster mit ähnlicher Normale
        found_cluster = False
        for cluster_triangles, cluster_normal in clusters:
            # Dot-Product: 1 = gleiche Richtung, 0 = senkrecht, -1 = entgegengesetzt
            similarity = np.dot(normal, cluster_normal)

            if similarity > cos_threshold:
                # Füge Triangle zu diesem Cluster hinzu
                cluster_triangles.append(tri)
                found_cluster = True
                break

        if not found_cluster:
            # Neuer Cluster
            clusters.append(([tri], normal.copy()))

    # Berechne gemittelte Normale für jeden Cluster
    result = []
    for cluster_triangles, _ in clusters:
        # Durchschnittliche Normale aller Triangles im Cluster
        cluster_normals = []
        for tri in cluster_triangles:
            v1 = tri[1] - tri[0]
            v2 = tri[2] - tri[0]
            n = np.cross(v1, v2)
            n_norm = np.linalg.norm(n)
            if n_norm > 1e-6:
                cluster_normals.append(n / n_norm)

        if cluster_normals:
            avg_normal = np.mean(cluster_normals, axis=0)
            avg_normal = avg_normal / np.linalg.norm(avg_normal)
        else:
            avg_normal = np.array([0.0, 0.0, 1.0])

        result.append((cluster_triangles, avg_normal))

    return result


def _extract_surface_from_tin(tin) -> List[WallSurface]:
    """
    Extrahiert ALLE Triangles aus einem TIN und clustert sie nach Wänden.

    WICHTIG: TIN enthält oft ALLE Wände eines Gebäudes in EINEM Mesh.
    Wir müssen die Triangles nach Normalenvektor clustern um separate Wände zu erhalten.
    """
    all_triangles = []  # Liste aller Triangle-Vertices (je 3 Punkte)
    all_normals = []  # Normale jedes Triangles

    # Iteriere über alle Triangles im TIN
    for i in range(tin.GetGeometryCount()):
        triangle = tin.GetGeometryRef(i)
        if triangle is None:
            continue

        triangle_points = []

        # Methode 1: Versuche Punkte direkt vom Triangle zu holen
        if triangle.GetPointCount() > 0:
            for j in range(triangle.GetPointCount()):
                x, y, z = triangle.GetPoint(j)
                triangle_points.append(np.array([x, y, z]))

        # Methode 2: Versuche über Ring (LINEARRING im Triangle)
        elif triangle.GetGeometryCount() > 0:
            ring = triangle.GetGeometryRef(0)
            if ring and ring.GetPointCount() > 0:
                for j in range(ring.GetPointCount()):
                    x, y, z = ring.GetPoint(j)
                    triangle_points.append(np.array([x, y, z]))

        # Validiere Triangle (genau 3 oder 4 Punkte, wobei letzter = erster bei 4)
        if len(triangle_points) >= 3:
            # Bei 4 Punkten: Letzter Punkt ist meist Duplikat des ersten (Ring-Closing)
            if len(triangle_points) == 4 and np.allclose(triangle_points[0], triangle_points[3]):
                triangle_points = triangle_points[:3]

            tri = triangle_points[:3]
            all_triangles.append(tri)

            # Berechne Normale für dieses Triangle
            try:
                v1 = tri[1] - tri[0]
                v2 = tri[2] - tri[0]
                normal = np.cross(v1, v2)
                normal_norm = np.linalg.norm(normal)
                if normal_norm > 1e-6:
                    normal = normal / normal_norm
                else:
                    normal = np.array([0.0, 0.0, 1.0])
                all_normals.append(normal)
            except:
                all_normals.append(np.array([0.0, 0.0, 1.0]))

    if not all_triangles:
        return []

    # Clustere Triangles nach Normalenvektor (= nach Wand)
    # Triangles mit ähnlichen Normalen gehören zur gleichen Wand
    all_normals_arr = np.array(all_normals)
    clusters = _cluster_triangles_by_normal(all_triangles, all_normals_arr)

    # Erstelle für jeden Cluster (= jede Wand) eine separate WallSurface
    surfaces = []
    for cluster_idx, (cluster_triangles, cluster_normal) in enumerate(clusters):
        vertices = []
        faces = []

        for tri in cluster_triangles:
            # Füge 3 Vertices hinzu
            start_idx = len(vertices)
            vertices.extend(tri)

            # Erstelle Face: [3, idx0, idx1, idx2]
            faces.extend([3, start_idx, start_idx + 1, start_idx + 2])

        vertices = np.array(vertices)
        faces = np.array(faces)

        # Erstelle WallSurface für diesen Cluster
        surface = WallSurface(
            id=f"tin_surface_{id(tin)}_wall_{cluster_idx}",
            vertices=vertices,
            normal=cluster_normal,
            faces=faces,
        )
        surfaces.append(surface)

    return surfaces


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

            # Generiere Faces für Polygon (Triangle Fan)
            n_points = len(vertices)
            faces = []
            for i in range(1, n_points - 1):
                faces.extend([3, 0, i, i + 1])

            surface = WallSurface(
                id=f"surface_{id(vertices)}",
                vertices=vertices,
                normal=normal,
                faces=np.array(faces) if faces else None,
            )
            surfaces.append(surface)

    return surfaces
