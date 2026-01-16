"""
swissBUILDINGS3D Loader

Lädt und parst 3D-Gebäudedaten von swisstopo.
Unterstützt CityGML und automatischen Download.
"""

import io
import json
import zipfile
from pathlib import Path
from typing import Generator, List, Optional
from urllib.request import urlopen, Request
from urllib.parse import urlencode
import numpy as np

try:
    from lxml import etree
except ImportError:
    import xml.etree.ElementTree as etree

from ..models import Building, WallSurface, LV95Coordinate
from ..utils import ask_yes_no, error_and_exit

# Versuche GDB-Loader zu importieren
try:
    from .gdb_loader import load_buildings_from_gdb
    GDB_AVAILABLE = True
except ImportError:
    GDB_AVAILABLE = False


# CityGML Namespaces
NAMESPACES = {
    "core": "http://www.opengis.net/citygml/2.0",
    "bldg": "http://www.opengis.net/citygml/building/2.0",
    "gml": "http://www.opengis.net/gml",
    "gen": "http://www.opengis.net/citygml/generics/2.0",
}

# STAC API für swissBUILDINGS3D 3.0
STAC_API_BASE = "https://data.geo.admin.ch/api/stac/v1"
STAC_COLLECTION_ID = "ch.swisstopo.swissbuildings3d_3_0"

# Alternative: WFS-Service (für kleinere Gebiete)
SWISSTOPO_WFS_URL = "https://wfs.geodienste.ch/buildings/collections/Building/items"


def load_buildings_from_citygml(
    filepath: Path,
    center: Optional[tuple] = None,  # (E, N) LV95
    radius: float = 100.0,
) -> List[Building]:
    """
    Lädt Gebäude aus einer CityGML-Datei.

    Args:
        filepath: Pfad zur CityGML-Datei (.gml oder .xml)
        center: Optional - Zentrum für Umkreisfilter (E, N) in LV95
        radius: Suchradius in Metern

    Returns:
        Liste von Building-Objekten
    """
    buildings = []

    for building in _parse_citygml_file(filepath):
        if center is None or _building_in_radius(building, center, radius):
            buildings.append(building)

    return buildings


def _parse_citygml_file(filepath: Path) -> Generator[Building, None, None]:
    """
    Parst CityGML-Datei und liefert Gebäude als Generator.
    """
    # Für große Dateien: iteratives Parsing
    try:
        # lxml iterparse (unterstützt tag-Parameter)
        context = etree.iterparse(
            str(filepath),
            events=("end",),
            tag="{http://www.opengis.net/citygml/building/2.0}Building",
        )

        for event, elem in context:
            building = _parse_building_element(elem)
            if building and building.wall_surfaces:
                yield building

            # Speicher freigeben
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]

    except (AttributeError, TypeError):
        # Fallback für xml.etree (kein tag-Parameter bei iterparse)
        print("  Info: Verwende ElementTree-XML-Parser (bei großen Dateien langsamer als lxml)...")
        tree = etree.parse(str(filepath))
        root = tree.getroot()

        for elem in root.iter("{http://www.opengis.net/citygml/building/2.0}Building"):
            building = _parse_building_element(elem)
            if building and building.wall_surfaces:
                yield building


def _parse_building_element(elem) -> Optional[Building]:
    """Parst ein einzelnes Building-Element."""
    # ID extrahieren
    building_id = elem.get("{http://www.opengis.net/gml}id", "unknown")

    # EGID extrahieren (swissBUILDINGS-spezifisch)
    # EGID kann als stringAttribute oder intAttribute vorliegen
    # Attributes sind im 'gen' (generics) Namespace
    egid = ""

    # Zuerst intAttribute versuchen (häufigster Fall)
    for attr in elem.findall(".//gen:intAttribute", NAMESPACES):
        if attr.get("name") == "EGID":
            value_elem = attr.find("gen:value", NAMESPACES)
            if value_elem is not None and value_elem.text:
                egid = value_elem.text
                break

    # Fallback: stringAttribute
    if not egid:
        for attr in elem.findall(".//gen:stringAttribute", NAMESPACES):
            if attr.get("name") == "EGID":
                value_elem = attr.find("gen:value", NAMESPACES)
                if value_elem is not None and value_elem.text:
                    egid = value_elem.text
                    break

    # Alternative EGID-Suche (ohne Namespace-Prefix, mit vollem Namespace-URI)
    if not egid:
        # IntAttribute
        egid_elem = elem.find(".//{http://www.opengis.net/citygml/generics/2.0}intAttribute[@name='EGID']/{http://www.opengis.net/citygml/generics/2.0}value", {})
        if egid_elem is not None and egid_elem.text:
            egid = egid_elem.text
        else:
            # StringAttribute
            egid_elem = elem.find(".//{http://www.opengis.net/citygml/generics/2.0}stringAttribute[@name='EGID']/{http://www.opengis.net/citygml/generics/2.0}value", {})
            if egid_elem is not None and egid_elem.text:
                egid = egid_elem.text

    # WallSurfaces sammeln
    wall_surfaces = []

    # Suche nach WallSurface-Elementen
    for wall_elem in elem.iter("{http://www.opengis.net/citygml/building/2.0}WallSurface"):
        wall_id = wall_elem.get("{http://www.opengis.net/gml}id", f"wall_{len(wall_surfaces)}")

        # Polygon-Koordinaten extrahieren
        for pos_list in wall_elem.iter("{http://www.opengis.net/gml}posList"):
            if pos_list.text:
                coords = _parse_pos_list(pos_list.text)
                if len(coords) >= 3:
                    wall_surfaces.append(WallSurface(
                        id=wall_id,
                        vertices=coords,
                    ))

    # RoofSurfaces sammeln
    roof_surfaces = []

    # Suche nach RoofSurface-Elementen
    for roof_elem in elem.iter("{http://www.opengis.net/citygml/building/2.0}RoofSurface"):
        roof_id = roof_elem.get("{http://www.opengis.net/gml}id", f"roof_{len(roof_surfaces)}")

        # Polygon-Koordinaten extrahieren
        for pos_list in roof_elem.iter("{http://www.opengis.net/gml}posList"):
            if pos_list.text:
                coords = _parse_pos_list(pos_list.text)
                if len(coords) >= 3:
                    roof_surfaces.append(WallSurface(  # Wiederverwendung von WallSurface
                        id=roof_id,
                        vertices=coords,
                    ))

    if not wall_surfaces and not roof_surfaces:
        return None

    return Building(
        id=building_id,
        egid=egid,
        wall_surfaces=wall_surfaces,
        roof_surfaces=roof_surfaces,
    )


def _parse_pos_list(text: str) -> np.ndarray:
    """
    Parst GML posList zu numpy Array.

    posList enthält Koordinaten als "x y z x y z ..." oder "x,y,z x,y,z ..."
    """
    text = text.strip()

    # Verschiedene Formate unterstützen
    if "," in text:
        # Format: "x,y,z x,y,z ..."
        points = text.split()
        values = []
        for p in points:
            values.extend([float(v) for v in p.split(",")])
    else:
        # Format: "x y z x y z ..."
        values = [float(v) for v in text.split()]

    if len(values) < 9:  # Mindestens 3 Punkte (9 Koordinaten)
        return np.array([]).reshape(0, 3)

    return np.array(values).reshape(-1, 3)


def _building_in_radius(building: Building, center: tuple, radius: float) -> bool:
    """Prüft ob Gebäude im Radius liegt."""
    if not building.wall_surfaces:
        return False

    all_coords = np.vstack([ws.vertices for ws in building.wall_surfaces])

    if len(all_coords) == 0:
        return False

    # Bounding-Box des Gebäudes
    min_e, min_n = all_coords[:, 0].min(), all_coords[:, 1].min()
    max_e, max_n = all_coords[:, 0].max(), all_coords[:, 1].max()

    # Nächster Punkt der Bounding-Box zum Zentrum
    closest_e = np.clip(center[0], min_e, max_e)
    closest_n = np.clip(center[1], min_n, max_n)

    distance = np.sqrt((closest_e - center[0]) ** 2 + (closest_n - center[1]) ** 2)
    return distance <= radius


def find_buildings_auto(
    position: LV95Coordinate,
    radius: float = 100.0,
    data_dir: Optional[Path] = None,
) -> List[Building]:
    """
    Lädt Gebäude automatisch aus der besten verfügbaren Quelle.

    Reihenfolge:
    1. Gesamt-Schweiz GDB (swissbuildings3d_3_0_2025_2056_5728.gdb.zip)
    2. Lokale CityGML-Kacheln
    3. Download von swisstopo

    Args:
        position: Zentrum in LV95-Koordinaten
        radius: Suchradius in Metern
        data_dir: Verzeichnis für Gebäudedaten (default: gebaeude_citygml/)

    Returns:
        Liste von Building-Objekten im Umkreis
    """
    if data_dir is None:
        data_dir = Path("gebaeude_citygml")

    # 1. Suche nach Gesamt-GDB
    gdb_candidates = [
        data_dir / "swissbuildings3d_3_0_2025_2056_5728.gdb.zip",
        Path("swisstopo") / "swissbuildings3d_3_0_2025_2056_5728.gdb.zip",
        Path(".") / "swissbuildings3d_3_0_2025_2056_5728.gdb.zip",
    ]

    for gdb_path in gdb_candidates:
        if gdb_path.exists() and GDB_AVAILABLE:
            print(f"  Verwende Gesamt-GDB: {gdb_path.name}")
            return load_buildings_from_gdb(
                gdb_path,
                center=(position.e, position.n),
                radius=radius,
            )

    # 2. Suche nach lokalen CityGML-Kacheln
    tile_id = _get_tile_id(position.e, position.n)
    citygml_candidates = [
        data_dir / f"swissBUILDINGS3D_3-0_{tile_id.replace('_', '-')}.gml",
        data_dir / f"swissbuildings3d_{tile_id}.gml",
    ]

    # Suche auch nach allen .gml Dateien im Verzeichnis
    if data_dir.exists():
        for gml_file in data_dir.glob("*.gml"):
            citygml_candidates.append(gml_file)

    for gml_path in citygml_candidates:
        if gml_path.exists():
            print(f"  Verwende lokale CityGML: {gml_path.name}")
            return load_buildings_from_citygml(
                gml_path,
                center=(position.e, position.n),
                radius=radius,
            )

    # 3. Fallback: Download
    use_download = ask_yes_no(
        question="Keine lokalen Gebäudedaten gefunden - Automatisch von swisstopo herunterladen?",
        details=f"""📁 Gesuchte Dateien:
   {", ".join([p.name for p in citygml_candidates])}

📥 Automatischer Download:
   - STAC API von data.geo.admin.ch
   - swissBUILDINGS3D 3.0 (OpenData)
   - CityGML-Format bevorzugt (ca. 275 MB pro Kachel)
   - Cache in ~/.cache/emf_hotspot/

⚠️  Benötigt Internetverbindung und ca. 1-2 Minuten Download-Zeit

💡 Alternative:
   - Manuell CityGML-Datei in input/citygml/ ablegen
   - Dann wird diese automatisch gefunden
""",
        default=True
    )

    if use_download:
        return download_buildings_for_location(position, radius)
    else:
        error_and_exit(f"""Gebäudedaten erforderlich aber nicht verfügbar.

Optionen:
1. Download erlauben (automatisch via STAC API)
2. Manuell CityGML-Datei bereitstellen in:
   {citygml_candidates[0].parent}/

   Dateiname: {citygml_candidates[0].name}
   Quelle: https://data.geo.admin.ch/browser/
""")


def download_buildings_for_location(
    position: LV95Coordinate,
    radius: float = 100.0,
    cache_dir: Optional[Path] = None,
) -> List[Building]:
    """
    Lädt Gebäude für eine Position automatisch von swisstopo.

    Args:
        position: Zentrum in LV95-Koordinaten
        radius: Suchradius in Metern
        cache_dir: Verzeichnis für Cache (optional)

    Returns:
        Liste von Building-Objekten im Umkreis
    """
    # Bestimme die Kachel-ID aus den Koordinaten
    tile_id = _get_tile_id(position.e, position.n)

    if cache_dir is None:
        cache_dir = Path.home() / ".cache" / "emf_hotspot"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Prüfe ob Kachel im Cache (CityGML oder GDB)
    cache_file_gml = cache_dir / f"swissbuildings3d_{tile_id}.gml"
    cache_file_gdb = cache_dir / f"swissbuildings3d_{tile_id}.gdb.zip"

    cache_file = None
    if cache_file_gml.exists():
        cache_file = cache_file_gml
    elif cache_file_gdb.exists():
        cache_file = cache_file_gdb
    else:
        # Download der Kachel
        print(f"Lade swissBUILDINGS3D Kachel {tile_id}...")
        _download_tile(tile_id, cache_file_gml)

        # Check welches Format heruntergeladen wurde
        if cache_file_gml.exists():
            cache_file = cache_file_gml
        elif cache_file_gdb.exists():
            cache_file = cache_file_gdb
        else:
            raise RuntimeError("Download fehlgeschlagen - keine Datei erstellt")

    # Parse je nach Format
    center = (position.e, position.n)

    if cache_file.suffix == ".gml":
        return load_buildings_from_citygml(cache_file, center, radius)
    elif cache_file.name.endswith(".gdb.zip"):
        if not GDB_AVAILABLE:
            error_and_exit(f"""GDB-Format heruntergeladen, aber GDAL nicht verfügbar

📁 Heruntergeladene Datei: {cache_file}

⚠️  Dieses sollte nicht passieren - der Code bevorzugt automatisch CityGML.
    Vermutlich ist für diese Kachel kein CityGML verfügbar.

Lösungen:

1. Manuelle Konvertierung mit QGIS (empfohlen):
   - QGIS öffnen (kostenlos: https://qgis.org)
   - Datei öffnen: {cache_file}
   - Exportieren als: {cache_file.with_suffix('.gml')}
   - Programm erneut ausführen

2. Alternative CityGML-Kachel manuell suchen:
   - https://data.geo.admin.ch/browser/
   - Suche nach Kachel: {tile_id}
   - Falls CityGML-Jahrgang verfügbar: Herunterladen
   - Als {cache_file.with_suffix('.gml')} speichern

3. GDAL-Support aktivieren (nur für Experten):
   - Neues venv mit system-python erstellen
   - sudo apt install libgdal-dev gdal-bin
   - pip install gdal
   - KANN Konflikte mit miniconda verursachen
""")
        return load_buildings_from_gdb(cache_file, center, radius)
    else:
        raise RuntimeError(f"Unbekanntes Dateiformat: {cache_file}")


def _get_tile_id(e: float, n: float) -> str:
    """
    Bestimmt die swissBUILDINGS3D Kachel-ID aus LV95-Koordinaten.

    Kacheln sind 1km x 1km und nach dem Schema benannt:
    swissbuildings3d_3_0_EEEE_NNNN
    wobei EEEE und NNNN die SW-Ecke der Kachel in km sind.
    """
    # Kachel-Größe: 1km
    tile_e = int(e // 1000)
    tile_n = int(n // 1000)

    # Format: z.B. "2681_1252" für Zürich
    return f"{tile_e}_{tile_n}"


def _lv95_to_wgs84(e: float, n: float) -> tuple:
    """
    Konvertiert LV95 (EPSG:2056) zu WGS84 (EPSG:4326).
    Verwendet die approximierte Formel von swisstopo.
    """
    # LV95 → LV03 (Hilfsvariable)
    y = (e - 2600000) / 1000000
    x = (n - 1200000) / 1000000

    # LV03 → WGS84
    lon = (2.6779094
           + 4.728982 * y
           + 0.791484 * y * x
           + 0.1306 * y * x * x
           - 0.0436 * y * y * y)

    lat = (16.9023892
           + 3.238272 * x
           - 0.270978 * y * y
           - 0.002528 * x * x
           - 0.0447 * y * y * x
           - 0.0140 * x * x * x)

    # Umrechnung in Dezimalgrad
    lon = lon * 100 / 36
    lat = lat * 100 / 36

    return (lon, lat)


def _download_tile(tile_id: str, output_file: Path) -> None:
    """
    Lädt eine swissBUILDINGS3D-Kachel über STAC API herunter.
    """
    try:
        # Parse tile_id zu Koordinaten
        parts = tile_id.split("_")
        e_km = int(parts[0])
        n_km = int(parts[1])

        # Bounding-Box für diese Kachel (1km × 1km) in LV95
        bbox_lv95 = [e_km * 1000, n_km * 1000, (e_km + 1) * 1000, (n_km + 1) * 1000]

        # Konvertiere zu WGS84 für STAC API
        sw_lon, sw_lat = _lv95_to_wgs84(bbox_lv95[0], bbox_lv95[1])
        ne_lon, ne_lat = _lv95_to_wgs84(bbox_lv95[2], bbox_lv95[3])

        # STAC bbox: minLon,minLat,maxLon,maxLat (WGS84)
        bbox_wgs84 = [sw_lon, sw_lat, ne_lon, ne_lat]
        bbox_str = ",".join(f"{v:.6f}" for v in bbox_wgs84)

        # STAC API Query
        items_url = f"{STAC_API_BASE}/collections/{STAC_COLLECTION_ID}/items?bbox={bbox_str}&limit=10"
        print(f"  STAC Query: {items_url}")

        # HTTP Request mit User-Agent
        req = Request(items_url)
        req.add_header("User-Agent", "EMF-Hotspot-Finder/2.0")

        response = urlopen(req, timeout=60)
        stac_data = json.loads(response.read().decode('utf-8'))

        if not stac_data.get("features"):
            raise ValueError(f"Keine STAC Items für Kachel {tile_id} gefunden")

        # Bestes Feature finden (neuestes mit bevorzugtem Format)
        # Priorität: 1. Neuestes mit CityGML, 2. Neuestes mit GDB, 3. Erstes verfügbare
        best_item = None
        best_item_has_citygml = False
        best_item_year = 0

        for feature in stac_data["features"]:
            assets = feature.get("assets", {})

            # Check welche Formate verfügbar sind
            has_citygml = any('citygml' in asset_name.lower() for asset_name in assets.keys())
            has_gdb = any('.gdb.zip' in asset_name.lower() for asset_name in assets.keys())

            # Extrahiere Jahrgang aus datetime
            datetime_str = feature.get("properties", {}).get("datetime", "2000-01-01")
            year = int(datetime_str[:4]) if datetime_str else 0

            # Wähle dieses Item nach folgender Priorität:
            # 1. Neueres Jahr (wichtiger als Format!)
            # 2. Bei gleichem Jahr: CityGML > GDB > DWG
            if best_item is None:
                best_item = feature
                best_item_has_citygml = any('citygml' in k.lower() for k in assets.keys())
                best_item_year = year
            elif year > best_item_year:
                # Neueres Jahr ist IMMER besser (auch GDB 2025 > CityGML 2019)
                best_item = feature
                best_item_has_citygml = has_citygml
                best_item_year = year
            elif year == best_item_year and has_citygml and not best_item_has_citygml:
                # Gleiches Jahr: CityGML ist besser als GDB
                best_item = feature
                best_item_has_citygml = has_citygml
                best_item_year = year

        item = best_item
        print(f"  Gewähltes Item: {item['id']} (Jahr {best_item_year})")

        # Asset finden (CityGML, GDB oder DWG)
        assets = item.get("assets", {})

        # Priorität: citygml > gdb > dwg
        asset_to_use = None
        asset_type = None

        # 1. Versuche CityGML
        for asset_name, asset_data in assets.items():
            if "citygml" in asset_name.lower():
                asset_to_use = asset_data
                asset_type = "citygml"
                break

        # 2. Fallback: GDB (wenn gdb_loader verfügbar)
        if not asset_to_use and GDB_AVAILABLE:
            for asset_name, asset_data in assets.items():
                if ".gdb.zip" in asset_name.lower():
                    asset_to_use = asset_data
                    asset_type = "gdb"
                    break

        # 3. Fallback: DWG (aktuell nicht unterstützt)
        if not asset_to_use:
            dwg_found = False
            for asset_name, asset_data in assets.items():
                if ".dwg.zip" in asset_name.lower():
                    dwg_found = True
                    break

            if dwg_found:
                error_and_exit(f"""Nur DWG-Format verfügbar - nicht unterstützt

📁 Kachel: {tile_id}

⚠️  Diese Kachel enthält nur DWG-CAD-Daten, keine 3D-Gebäudemodelle.

Lösungen:

1. Alternative Kachel mit CityGML suchen:
   - https://data.geo.admin.ch/browser/
   - Suche: "swissbuildings3d {tile_id}"
   - Andere Jahrgänge prüfen (2019-2025)

2. Manuelle Konvertierung:
   - AutoCAD oder FreeCAD öffnen
   - DWG → CityGML exportieren
   - Als {output_file} speichern

3. Anderen Standort wählen:
   - Möglicherweise liegt Position außerhalb der Abdeckung
""")
            else:
                raise ValueError(f"Kein unterstütztes Asset gefunden. Verfügbare: {list(assets.keys())}")

        download_url = asset_to_use["href"]
        print(f"  Download-URL: {download_url}")
        print(f"  Format: {asset_type.upper()}")

        # Download ZIP
        req = Request(download_url)
        req.add_header("User-Agent", "EMF-Hotspot-Finder/2.0")
        response = urlopen(req, timeout=120)
        data = response.read()

        # ZIP entpacken (je nach Format)
        if asset_type == "citygml":
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                # Suche nach .gml oder .xml Datei
                gml_files = [f for f in zf.namelist() if f.endswith((".gml", ".xml"))]

                if not gml_files:
                    raise ValueError(f"Keine GML-Datei im ZIP gefunden")

                # Erste GML-Datei extrahieren
                with zf.open(gml_files[0]) as src:
                    output_file.write_bytes(src.read())

            print(f"  ✅ Gespeichert: {output_file}")

        elif asset_type == "gdb":
            # GDB-ZIP direkt speichern (nicht entpacken)
            # gdb_loader kann mit .gdb.zip umgehen
            output_file = output_file.with_suffix('.gdb.zip')
            output_file.write_bytes(data)
            print(f"  ✅ Gespeichert: {output_file}")
            print(f"  ℹ️  GDB-Format - nutze gdb_loader bei Bedarf")

        else:
            raise ValueError(f"Unbekanntes Asset-Format: {asset_type}")

    except Exception as e:
        use_wfs = ask_yes_no(
            question="STAC-Download fehlgeschlagen - WFS-Alternative versuchen?",
            details=f"""❌ STAC API Fehler: {e}

🔄 WFS-Alternative:
   - Älterer WFS-Service (weniger robust)
   - Nur für kleinere Gebiete geeignet
   - Möglicherweise unvollständige Daten
   - Keine LOD2-Qualität garantiert

⚠️  Empfehlung:
   - Erst manuelle Lösung prüfen (data.geo.admin.ch)
   - WFS nur als letzter Ausweg

💡 Bessere Alternative:
   - https://data.geo.admin.ch/browser/
   - Kachel {tile_id} manuell herunterladen
   - Als {output_file} speichern
""",
            default=False  # Standard: Nein
        )

        if use_wfs:
            print("  Versuche WFS-Alternative...")
            _download_via_wfs(tile_id, output_file)
        else:
            error_and_exit(f"""STAC-Download fehlgeschlagen

Fehler: {e}

Manuelle Lösung:
1. Browser öffnen: https://data.geo.admin.ch/browser/
2. Suchen: "swissbuildings3d {tile_id}"
3. CityGML-Datei herunterladen
4. Speichern als: {output_file}
5. Programm erneut ausführen
""")


def _download_via_wfs(tile_id: str, output_file: Path) -> None:
    """
    Alternative: Lädt Gebäude über WFS-Service (für kleinere Gebiete).
    """
    # Parse tile_id zurück zu Koordinaten
    parts = tile_id.split("_")
    e_km = int(parts[0])
    n_km = int(parts[1])

    # Bounding-Box in LV95 (1km × 1km)
    bbox = f"{e_km * 1000},{n_km * 1000},{(e_km + 1) * 1000},{(n_km + 1) * 1000}"

    params = {
        "bbox": bbox,
        "f": "json",
        "limit": 10000,
    }

    url = f"{SWISSTOPO_WFS_URL}?{urlencode(params)}"

    try:
        req = Request(url)
        req.add_header("User-Agent", "EMF-Hotspot-Finder/2.0")
        response = urlopen(req, timeout=120)
        data = response.read()
        output_file.write_bytes(data)
        print(f"  ✅ WFS-Download erfolgreich: {output_file}")
    except Exception as e:
        raise RuntimeError(f"❌ WFS-Download fehlgeschlagen: {e}")


def create_simple_building(
    vertices_2d: List[tuple],  # [(x, y), ...]
    ground_height: float,
    building_height: float,
    building_id: str = "test",
) -> Building:
    """
    Erstellt ein einfaches Testgebäude (Quader) aus 2D-Grundriss.

    Nützlich für Tests ohne echte CityGML-Daten.
    """
    vertices = np.array(vertices_2d)
    n_points = len(vertices)

    wall_surfaces = []

    # Für jede Kante eine Wandfläche erstellen
    for i in range(n_points):
        j = (i + 1) % n_points

        # 4 Eckpunkte der Wand (unten-links, unten-rechts, oben-rechts, oben-links)
        wall_vertices = np.array([
            [vertices[i, 0], vertices[i, 1], ground_height],
            [vertices[j, 0], vertices[j, 1], ground_height],
            [vertices[j, 0], vertices[j, 1], ground_height + building_height],
            [vertices[i, 0], vertices[i, 1], ground_height + building_height],
            [vertices[i, 0], vertices[i, 1], ground_height],  # Geschlossenes Polygon
        ])

        wall_surfaces.append(WallSurface(
            id=f"{building_id}_wall_{i}",
            vertices=wall_vertices,
        ))

    return Building(
        id=building_id,
        egid=building_id,
        wall_surfaces=wall_surfaces,
    )
