"""
Laden von Terrain-Daten (SwissALTI3D) via swisstopo API
"""

import numpy as np
from typing import Tuple, Optional
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
import json
from pathlib import Path
import zipfile
import io


def get_swissalti3d_tile(center_e: float, center_n: float) -> Tuple[int, int]:
    """
    Berechnet die SwissALTI3D Kachel-Koordinaten für einen Punkt.

    SwissALTI3D verwendet 1km × 1km Kacheln im LV95-System.
    Kachelnamen: swissalti3d_2024_EEEE-NNNN (E und N in km)

    Args:
        center_e: LV95 E-Koordinate
        center_n: LV95 N-Koordinate

    Returns:
        (tile_e, tile_n) - Kachel-Koordinaten in km
    """
    # Runde auf volle Kilometer (unterste linke Ecke der Kachel)
    tile_e = int(center_e / 1000)
    tile_n = int(center_n / 1000)
    return tile_e, tile_n


def download_swissalti3d_tile(tile_e: int, tile_n: int, cache_dir: Path = None) -> Optional[Path]:
    """
    Lädt eine SwissALTI3D-Kachel von swisstopo.

    Args:
        tile_e: Kachel E-Koordinate in km (z.B. 2681)
        tile_n: Kachel N-Koordinate in km (z.B. 1252)
        cache_dir: Verzeichnis zum Cachen der Downloads

    Returns:
        Pfad zur heruntergeladenen XYZ-Datei oder None bei Fehler
    """
    if cache_dir is None:
        cache_dir = Path.home() / ".cache" / "stdb-scout" / "swissalti3d"

    cache_dir.mkdir(parents=True, exist_ok=True)

    # Dateiname
    xyz_filename = f"swissalti3d_2_2024_{tile_e}-{tile_n}_2056_5728.xyz"
    cached_file = cache_dir / xyz_filename

    # Prüfe Cache
    if cached_file.exists():
        return cached_file

    # Download von swisstopo STAC API
    # Format: https://data.geo.admin.ch/ch.swisstopo.swissalti3d/swissalti3d_2024_EEEE-NNNN/swissalti3d_2_2024_EEEE-NNNN_2056_5728.xyz.zip
    base_url = "https://data.geo.admin.ch/ch.swisstopo.swissalti3d"
    tile_name = f"swissalti3d_2024_{tile_e}-{tile_n}"
    zip_filename = f"swissalti3d_2_2024_{tile_e}-{tile_n}_2056_5728.xyz.zip"

    url = f"{base_url}/{tile_name}/{zip_filename}"

    try:
        print(f"  Download Terrain-Kachel {tile_e}-{tile_n}...")
        req = Request(url, headers={'User-Agent': 'StDb-Scout/1.0'})

        with urlopen(req, timeout=60) as response:
            zip_data = response.read()

        # Entpacke ZIP
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            # Extrahiere XYZ-Datei
            zf.extract(xyz_filename, cache_dir)

        return cached_file

    except (HTTPError, URLError) as e:
        print(f"  WARNUNG: SwissALTI3D Download fehlgeschlagen: {e}")
        return None


def load_terrain_mesh(
    center_e: float,
    center_n: float,
    radius_m: float = 200.0,
    resolution_m: float = 2.0
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Lädt Terrain-Mesh für einen Bereich.

    Args:
        center_e: LV95 E-Koordinate des Zentrums
        center_n: LV95 N-Koordinate des Zentrums
        radius_m: Radius in Metern
        resolution_m: Auflösung in Metern (2m = SwissALTI3D Resolution)

    Returns:
        (vertices, faces, heights) oder (None, None, None) bei Fehler
        - vertices: np.ndarray (N, 3) - E, N, H Koordinaten
        - faces: np.ndarray (M, 3) - Triangle indices
        - heights: np.ndarray (N,) - Höhenwerte für Colormap
    """
    # Berechne benötigte Kacheln
    min_e = center_e - radius_m
    max_e = center_e + radius_m
    min_n = center_n - radius_m
    max_n = center_n + radius_m

    tile_min_e, tile_min_n = get_swissalti3d_tile(min_e, min_n)
    tile_max_e, tile_max_n = get_swissalti3d_tile(max_e, max_n)

    # Lade alle benötigten Kacheln
    all_points = []

    for tile_e in range(tile_min_e, tile_max_e + 1):
        for tile_n in range(tile_min_n, tile_max_n + 1):
            xyz_file = download_swissalti3d_tile(tile_e, tile_n)

            if xyz_file is None or not xyz_file.exists():
                continue

            # Lade XYZ-Daten
            try:
                # Format: E N H (space-separated, LV95 coordinates)
                data = np.loadtxt(xyz_file)

                # Filtere Punkte im Radius
                distances = np.sqrt((data[:, 0] - center_e)**2 + (data[:, 1] - center_n)**2)
                mask = distances <= radius_m
                points_in_radius = data[mask]

                all_points.append(points_in_radius)

            except Exception as e:
                print(f"  WARNUNG: Fehler beim Laden von {xyz_file.name}: {e}")
                continue

    if not all_points:
        print("  WARNUNG: Keine Terrain-Daten gefunden")
        return None, None, None

    # Kombiniere alle Punkte
    terrain_points = np.vstack(all_points)

    if len(terrain_points) < 3:
        return None, None, None

    # Erstelle regelmäßiges Grid via Interpolation
    from scipy.interpolate import LinearNDInterpolator

    # Definiere Grid
    grid_e = np.arange(min_e, max_e, resolution_m)
    grid_n = np.arange(min_n, max_n, resolution_m)
    grid_ee, grid_nn = np.meshgrid(grid_e, grid_n)

    # Interpoliere Höhen
    interp = LinearNDInterpolator(
        terrain_points[:, :2],  # E, N
        terrain_points[:, 2]     # H
    )

    grid_h = interp(grid_ee, grid_nn)

    # Entferne NaN-Werte (außerhalb der Konvexen Hülle)
    valid_mask = ~np.isnan(grid_h)

    # Erstelle Vertices
    vertices = np.column_stack([
        grid_ee[valid_mask],
        grid_nn[valid_mask],
        grid_h[valid_mask]
    ])

    # Erstelle Faces (Triangles)
    # Grid-basierte Triangulation
    rows, cols = grid_ee.shape
    faces = []

    # Erstelle Mapping von Grid-Koordinaten zu Vertex-Index
    vertex_map = np.full((rows, cols), -1, dtype=int)
    vertex_idx = 0
    for i in range(rows):
        for j in range(cols):
            if valid_mask[i, j]:
                vertex_map[i, j] = vertex_idx
                vertex_idx += 1

    # Erstelle Dreiecke
    for i in range(rows - 1):
        for j in range(cols - 1):
            # Prüfe ob alle 4 Eckpunkte valide sind
            v00 = vertex_map[i, j]
            v01 = vertex_map[i, j + 1]
            v10 = vertex_map[i + 1, j]
            v11 = vertex_map[i + 1, j + 1]

            if v00 >= 0 and v01 >= 0 and v10 >= 0 and v11 >= 0:
                # Zwei Dreiecke pro Quad
                faces.append([v00, v01, v11])
                faces.append([v00, v11, v10])

    if not faces:
        return None, None, None

    faces = np.array(faces)
    heights = vertices[:, 2]

    return vertices, faces, heights
