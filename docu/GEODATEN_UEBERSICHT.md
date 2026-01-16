# geo.admin.ch Geodaten-Übersicht für EMF-Hotspot-Finder

Überblick über verfügbare Geodaten von geo.admin.ch / swisstopo für das EMF-Projekt.

---

## Zusammenfassung nach Relevanz

| Datensatz | Relevanz | Genauigkeit | API | Download |
|-----------|----------|-------------|-----|----------|
| **swissBUILDINGS3D 3.0** | ⭐⭐⭐ Hoch | LOD2, ~1m | ✅ STAC | ✅ CityGML |
| **Gebäudeadressen (EGID)** | ⭐⭐⭐ Hoch | Punkt | ✅ REST | ✅ CSV/Shapefile |
| **Amtliche Vermessung (Kataster)** | ⭐⭐⭐ Hoch | 10cm | ✅ WMS | ⚠️ Kantonal |
| **swissALTI3D** | ⭐⭐ Mittel | 50cm | ✅ STAC | ✅ GeoTIFF |
| **swissBOUNDARIES3D** | ⭐ Niedrig | - | ✅ STAC | ✅ Shapefile |

**10cm-Genauigkeit:** Amtliche Vermessung (Kataster) - aber nur als WMS visualisierbar, kein direkter Download!

---

## 1. API-Dienste (Online-Zugriff)

### 1.1 REST API (Suchfunktionen)

**Base URL:** `https://api3.geo.admin.ch/rest/services/api/`

**Hauptfunktionen:**
- **SearchServer:** Textsuche nach Orten, Adressen, Parzellen
- **Find:** Attributsuche in Layern
- **Identify:** Punkt-Abfrage (Reverse-Geocoding)
- **Feature Service:** Geometrie-Abfrage einzelner Objekte

**Relevante Layer:**

| Layer-ID | Inhalt | Verwendung |
|----------|--------|------------|
| `ch.bfs.gebaeude_wohnungs_register` | EGID, Gebäudeadressen | EGID-Lookup |
| `ch.swisstopo.amtliches-gebaeudeadressverzeichnis` | Offizielle Adressen | Adress-Suche |
| `ch.swisstopo-vd.amtliche-vermessung` | Katasterparzellen | Visualisierung |
| `ch.kantone.cadastralwebmap-farbe` | Kataster (farbig) | Visualisierung |

**Beispiel - EGID-Suche:**
```fish
curl "https://api3.geo.admin.ch/rest/services/api/MapServer/find?\
layer=ch.bfs.gebaeude_wohnungs_register&\
searchText=123164&\
searchField=egid&\
returnGeometry=true"
```

**Beispiel - Reverse-Geocoding (Adresse von Koordinaten):**
```fish
curl "https://api3.geo.admin.ch/rest/services/api/MapServer/identify?\
geometryType=esriGeometryPoint&\
geometry=2681044,1252266&\
layers=all:ch.bfs.gebaeude_wohnungs_register&\
tolerance=10&\
sr=2056"
```

**Dokumentation:** [API REST Services](https://api3.geo.admin.ch/services/sdiservices.html)

---

### 1.2 WMS (Web Map Service) - Visualisierung

**Base URL:** `https://wms.geo.admin.ch/`

**GetCapabilities:**
```fish
curl "https://wms.geo.admin.ch/?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities"
```

**Hohe Auflösung verfügbar:**
- Zoom Level 27: 0.25m Auflösung
- Zoom Level 28: **0.1m Auflösung** (10cm!)

**Verfügbar für:**
- `ch.kantone.cadastralwebmap-farbe` (Kataster)
- `ch.swisstopo.swissimage` (Orthofotos)

**Beispiel - GetMap Request:**
```fish
curl "https://wms.geo.admin.ch/?SERVICE=WMS&VERSION=1.3.0&\
REQUEST=GetMap&\
LAYERS=ch.swisstopo-vd.amtliche-vermessung&\
CRS=EPSG:2056&\
BBOX=2681000,1252000,2682000,1253000&\
WIDTH=1000&HEIGHT=1000&\
FORMAT=image/png"
```

**Wichtig für EMF-Projekt:**
- Katasterparzellen als Overlay für Heatmaps
- Hohe Auflösung für Detail-Ansichten
- **ABER:** Nur Bilddaten, keine Vektoren!

**Dokumentation:** [Web Map Service (WMS)](https://docs.geo.admin.ch/visualize-data/wms.html)

---

### 1.3 STAC API (Download-Service)

**Base URL:** `https://data.geo.admin.ch/api/stac/v1/`

**Browser:** [https://data.geo.admin.ch/browser/](https://data.geo.admin.ch/browser/)

**Was ist STAC?**
Spatial Temporal Asset Catalog - standardisierte API für Geodaten-Downloads.

**Verfügbare Collections:**

| Collection-ID | Inhalt | Format |
|---------------|--------|--------|
| `ch.swisstopo.swissbuildings3d_3_0` | 3D-Gebäude LOD2 (BETA) | CityGML |
| `ch.swisstopo.swissalti3d` | Höhenmodell 50cm | GeoTIFF, XYZ |
| `ch.swisstopo.swissboundaries3d` | Gemeindegrenzen 3D | Shapefile, GeoPackage |
| `ch.swisstopo.swissimage` | Orthofotos 10cm | GeoTIFF |

**Beispiel - swissBUILDINGS3D 3.0 Collection:**
```fish
curl "https://data.geo.admin.ch/api/stac/v1/collections/ch.swisstopo.swissbuildings3d_3_0"
```

**Beispiel - Items in einer Kachel:**
```fish
# Kacheln sind nach LV95-Kilometern benannt: 2680_1250
curl "https://data.geo.admin.ch/api/stac/v1/collections/\
ch.swisstopo.swissbuildings3d_3_0/items?bbox=2680000,1250000,2681000,1251000"
```

**Download-URL-Struktur:**
```
https://data.geo.admin.ch/ch.swisstopo.swissbuildings3d_3_0/
swissbuildings3d_3_0_2680_1250/
swissbuildings3d_3_0_2680_1250_citygml.zip
```

**Status:** STAC API v0.9 wird deprecated, läuft aber mindestens bis **Ende 2026**.

**Dokumentation:** [REST Interface: STAC API](https://www.geo.admin.ch/en/rest-interface-stac-api)

---

## 2. Download-Dienste (File-Downloads)

### 2.1 data.geo.admin.ch (STAC Browser)

**URL:** [https://data.geo.admin.ch/browser/](https://data.geo.admin.ch/browser/)

**Vorteile:**
- Visueller Browser
- Direkte Download-Links
- Kachel-basierte Struktur
- Vorschau der Datenextents

**Workflow:**
1. Browser öffnen
2. Collection auswählen (z.B. swissBUILDINGS3D 3.0)
3. Kachel nach Koordinaten suchen (2680_1250)
4. Asset auswählen (CityGML, GeoPackage, etc.)
5. Download-Link kopieren

**Beispiel - swissBUILDINGS3D 3.0:**
```
Collection: ch.swisstopo.swissbuildings3d_3_0
Item: 2680_1250
Assets:
  - citygml.zip (~800 MB)
  - gpkg.zip (~200 MB)
  - kml.kmz
```

---

### 2.2 opendata.swiss

**URL:** [https://opendata.swiss](https://opendata.swiss)

**Verfügbare Datasets:**

| Dataset | Formate | Aktualisierung |
|---------|---------|----------------|
| **Amtliche Vermessung (AV)** | INTERLIS, GeoPackage, Shapefile, DXF | Kantonal |
| **Gebäudeadressen** | CSV, Shapefile, GeoPackage | Monatlich |
| **swissBUILDINGS3D 3.0** | CityGML, GeoPackage | Jährlich |
| **swissALTI3D** | GeoTIFF, ASCII XYZ | 6 Jahre |
| **swissBOUNDARIES3D** | Shapefile, GeoPackage | Jährlich |

**Amtliche Vermessung (Kataster):**
- **Genauigkeit:** ±10cm (Lage), ±5cm (Höhe)
- **Inhalt:** Liegenschaften, Gebäude, Bodenbedeckung, Nomenklatur
- **Problem:** Kantonal organisiert, keine zentrale Download-Quelle
- **Link:** [Cadastral Surveying OpenData](https://opendata.swiss/en/dataset/amtliche-vermessung-opendata)

**Gebäudeadressen (EGID):**
- **Genauigkeit:** Punkt-Koordinate
- **Inhalt:** EGID, Adresse, PLZ, Ort, Koordinaten
- **Format:** CSV, Shapefile
- **Link:** [Official directory of building addresses](https://opendata.swiss/en/dataset/amtliches-verzeichnis-der-gebaudeadressen)

---

### 2.3 swisstopo Shop (OGD)

**URL:** [https://shop.swisstopo.admin.ch/en/free-geodata](https://shop.swisstopo.admin.ch/en/free-geodata)

**Kostenlose Geobasisdaten (Open Government Data):**

| Produkt | Beschreibung | Format |
|---------|--------------|--------|
| **swissBUILDINGS3D 3.0** | 3D-Gebäude LOD2 | CityGML, GeoPackage, IFC |
| **swissALTI3D** | Höhenmodell 50cm | GeoTIFF, ASCII XYZ |
| **swissTLM3D** | Topografisches Landschaftsmodell | INTERLIS, Shapefile |
| **swissBOUNDARIES3D** | Landes-/Kantons-/Gemeindegrenzen | Shapefile, GeoPackage |
| **swissIMAGE** | Orthofotos 10cm | GeoTIFF |

**Download-Optionen:**
1. Einzelne Kacheln (über data.geo.admin.ch)
2. Ganze Schweiz (Zip-Archive, mehrere GB)
3. WFS/WCS-Dienste (für automatisierte Abfragen)

**Lizenz:** CC0 oder CC-BY - kommerzielle Nutzung erlaubt!

**Dokumentation:** [Free basic geodata (OGD)](https://www.swisstopo.admin.ch/en/free-geodata-ogd)

---

## 3. Detaillierte Datensatz-Beschreibungen

### 3.1 swissBUILDINGS3D 3.0 ⭐⭐⭐

**Status:** BETA (seit 2024)

**Beschreibung:**
- 3D-Gebäudemodelle mit Dachgeometrie und Dachüberständen
- Zwei Varianten:
  - **Solid:** Geschlossene Körper
  - **Elements:** Einzelne Elemente (Dach, Fassaden, Grundriss)

**Datenqualität:**
- **LOD:** Level of Detail 2 (detaillierte Dächer)
- **Genauigkeit:** ~1m (basiert auf Orthofotos + Laserscan)
- **EGID:** Ab Dezember 2022 integriert
- **Aktualisierung:** Jährlich

**Formate:**
- **CityGML:** XML-basiert, Standard für 3D-Stadtmodelle (~800 MB/Kachel)
- **GeoPackage:** SQLite-Datenbank, kompakter (~200 MB/Kachel)
- **KML/KMZ:** Google Earth
- **IFC:** BIM-Format (Building Information Modeling)

**Kachel-Struktur:**
- Raster: 1km × 1km (LV95-Kilometergitter)
- Benennung: `2680_1250` = Ost 2680km, Nord 1250km

**API-Zugriff:**
```fish
# Collection-Metadaten
curl "https://data.geo.admin.ch/api/stac/v1/collections/ch.swisstopo.swissbuildings3d_3_0"

# Items (Kacheln) in Bounding Box
curl "https://data.geo.admin.ch/api/stac/v1/collections/\
ch.swisstopo.swissbuildings3d_3_0/items?\
bbox=2680000,1250000,2681000,1251000"
```

**Download-Beispiel:**
```fish
# Direkt-Download einer Kachel
wget "https://data.geo.admin.ch/\
ch.swisstopo.swissbuildings3d_3_0/\
swissbuildings3d_3_0_2680_1250/\
swissbuildings3d_3_0_2680_1250_citygml.zip"

# Entpacken
unzip swissbuildings3d_3_0_2680_1250_citygml.zip
```

**Verwendung im Projekt:**
- ✅ Bereits implementiert in `building_loader.py`
- ❌ Alte API-URL funktioniert nicht mehr (404)
- ✅ Neue STAC-API-Integration möglich

---

### 3.2 Amtliche Vermessung (Kataster) ⭐⭐⭐

**Offizieller Name:** Amtliche Vermessung / MOpublic

**Beschreibung:**
- Parzellengeometrie (Liegenschaften)
- Gebäudegrundrisse (2D)
- Bodenbedeckung, Einzelobjekte
- Nomenklatur (Flurnamen, Strassennamen)

**Datenqualität:**
- **Genauigkeit:** ±10cm (Lage), ±5cm (Höhe)
- **Aktualisierung:** Laufend (durch Gemeinden)
- **Koordinatensystem:** LV95 (EPSG:2056)

**Formate:**
- **INTERLIS 2:** Schweizer Standard (XML-basiert)
- **GeoPackage:** SQLite-Datenbank
- **Shapefile:** ESRI-Format
- **DXF:** CAD-Austauschformat

**Problem:**
- **Kantonal organisiert:** Keine zentrale Download-Quelle
- **WMS verfügbar:** `ch.swisstopo-vd.amtliche-vermessung`
- **WMS-Auflösung:** Bis zu **0.1m (10cm)** bei Zoom 28!

**WMS-Zugriff:**
```fish
# GetCapabilities
curl "https://wms.geo.admin.ch/?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities"

# GetMap (Katasterkarte)
curl "https://wms.geo.admin.ch/?SERVICE=WMS&VERSION=1.3.0&\
REQUEST=GetMap&\
LAYERS=ch.swisstopo-vd.amtliche-vermessung&\
CRS=EPSG:2056&\
BBOX=2681000,1252000,2682000,1253000&\
WIDTH=4000&HEIGHT=4000&\
FORMAT=image/png" > kataster.png
```

**Kantonal-Download:**
- Jeder Kanton hat eigenen Geodaten-Shop
- Beispiel Zürich: [GIS-Browser Kanton Zürich](https://maps.zh.ch/)
- Beispiel Bern: [Geoportal Kanton Bern](https://www.be.ch/geoportal)

**Alternative - geodienste.ch:**
- Gemeinsame Plattform mehrerer Kantone
- WFS-Dienste verfügbar
- URL: [https://www.geodienste.ch/](https://www.geodienste.ch/)

**Verwendung im Projekt:**
- 🔮 **TODO:** Für "Virtuelle Gebäude" Feature
- Parzellengeometrie → Leere Parzellen identifizieren
- Grenzabstand berechnen (3m)
- Virtuelle Gebäudegrundrisse erstellen

---

### 3.3 Gebäudeadressen (EGID) ⭐⭐⭐

**Offizieller Name:** Amtliches Gebäudeadressverzeichnis

**Beschreibung:**
- Eidgenössischer Gebäudeidentifikator (EGID)
- Vollständige Adressen (Strasse, Hausnummer, PLZ, Ort)
- Koordinaten (LV95)
- EGID eingeführt: Dezember 2022

**Datenqualität:**
- **Genauigkeit:** Punkt-Koordinate (Gebäudeeingang)
- **Vollständigkeit:** ~2.5 Millionen Gebäude
- **Aktualisierung:** Monatlich

**API-Zugriff:**

**Layer:**
- `ch.bfs.gebaeude_wohnungs_register` (Bundesamt für Statistik)
- `ch.swisstopo.amtliches-gebaeudeadressverzeichnis` (swisstopo)

**Beispiel - EGID-Suche:**
```fish
curl "https://api3.geo.admin.ch/rest/services/api/MapServer/find?\
layer=ch.bfs.gebaeude_wohnungs_register&\
searchText=123164&\
searchField=egid&\
returnGeometry=true&\
sr=2056"
```

**Beispiel - Adress-Suche:**
```fish
curl "https://api3.geo.admin.ch/rest/services/api/SearchServer?\
searchText=Wehntalerstrasse%20464%20Zürich&\
type=locations"
```

**Beispiel - Reverse-Geocoding (Koordinate → Adresse):**
```fish
curl "https://api3.geo.admin.ch/rest/services/api/MapServer/identify?\
geometryType=esriGeometryPoint&\
geometry=2681044,1252266&\
layers=all:ch.bfs.gebaeude_wohnungs_register&\
tolerance=10&\
sr=2056"
```

**Download (opendata.swiss):**
```fish
# CSV-Download (ganze Schweiz, ~300 MB)
wget "https://data.geo.admin.ch/ch.swisstopo.amtliches-gebaeudeadressverzeichnis/\
csv/2056/ch.swisstopo.amtliches-gebaeudeadressverzeichnis.zip"
```

**Verwendung im Projekt:**
- ✅ Bereits implementiert in `geoadmin_api.py`
- Funktion: `lookup_address_by_egid(egid: str)`
- Output: `pro_gebaeude.csv` mit Adress-Spalte

---

### 3.4 swissALTI3D (Höhenmodell) ⭐⭐

**Beschreibung:**
- Digitales Höhenmodell der Schweiz
- Oberfläche ohne Vegetation und Gebäude
- Laserscanning-basiert

**Datenqualität:**
- **Auflösung:** 50cm Raster (0.5m)
- **Höhengenauigkeit:** ±30cm
- **Aktualisierung:** Alle 6 Jahre
- **Koordinatensystem:** LV95 (EPSG:2056)

**Formate:**
- **GeoTIFF:** Georeferenziertes Bild (~2 GB/Kachel)
- **ASCII XYZ:** Punkt-Cloud-Format
- **LAZ:** LASzip-komprimiert

**Kachel-Struktur:**
- Raster: 1km × 1km

**API-Zugriff:**
```fish
# Collection
curl "https://data.geo.admin.ch/api/stac/v1/collections/ch.swisstopo.swissalti3d"

# Download
wget "https://data.geo.admin.ch/ch.swisstopo.swissalti3d/\
swissalti3d_2019_2680-1250/\
swissalti3d_2019_2680-1250_0.5_2056_5728.tif"
```

**Alternative - swissALTIRegio:**
- **Auflösung:** 10m (nicht 10cm!)
- Für großräumige Analysen

**Verwendung im Projekt:**
- ⚠️ Aktuell nicht verwendet
- 💡 Mögliche Verwendung: Terrain für 3D-Visualisierung
- 💡 Sichtlinien-Analyse (Line-of-Sight)

---

### 3.5 swissBOUNDARIES3D ⭐

**Beschreibung:**
- Verwaltungsgrenzen (Gemeinden, Kantone, Land)
- 3D-Geometrie (mit Höheninformation)

**Datenqualität:**
- **Genauigkeit:** ~1m
- **Aktualisierung:** Jährlich

**Formate:**
- Shapefile
- GeoPackage
- KML

**API-Zugriff:**
```fish
curl "https://data.geo.admin.ch/api/stac/v1/collections/ch.swisstopo.swissboundaries3d"
```

**Verwendung im Projekt:**
- ⚠️ Aktuell nicht verwendet
- 💡 Mögliche Verwendung: Gemeindegrenzen für Batch-Verarbeitung

---

## 4. Genauigkeits-Übersicht

| Datensatz | Lage-Genauigkeit | Höhen-Genauigkeit | Auflösung |
|-----------|------------------|-------------------|-----------|
| **Amtliche Vermessung (Kataster)** | ±10cm | ±5cm | 10cm (WMS) |
| **swissALTI3D** | ±50cm | ±30cm | 50cm Raster |
| **swissBUILDINGS3D 3.0** | ~1m | ~1m | LOD2 |
| **swissIMAGE (Orthofotos)** | ±25cm | - | 10cm Pixel |
| **Gebäudeadressen (EGID)** | ~1-5m | - | Punkt |

**10cm-Genauigkeit erreichen:**
- ✅ **WMS Amtliche Vermessung:** Visualisierung mit 10cm-Pixeln
- ✅ **swissIMAGE:** Orthofotos mit 10cm-Auflösung
- ❌ **Vektordaten:** Keine zentral verfügbaren Vektordaten mit 10cm-Genauigkeit

---

## 5. Empfehlungen für EMF-Projekt

### Sofort umsetzbar:

1. **swissBUILDINGS3D 3.0 über STAC-API laden**
   - Ersetzt fehlerhafte alte API
   - Neuere Daten (mit EGID)
   - Code-Anpassung in `building_loader.py`

2. **EGID-Lookup erweitern**
   - Bereits implementiert
   - Funktioniert für neuere CityGML (≥Dez 2022)

3. **WMS-Kataster als Heatmap-Overlay**
   - Parzellenlinien in `heatmap.png` einzeichnen
   - 10cm-Auflösung verfügbar

### Mittelfristig (für "Virtuelle Gebäude"):

4. **Katasterdaten-Download**
   - Kantonal: geodienste.ch oder Kantonsportale
   - Format: GeoPackage oder Shapefile
   - Parzellengeometrie für Leerstandserkennung

5. **WFS-Integration**
   - Automatischer Parzellendownload per WFS
   - Bbox-basierte Abfrage

### Langfristig:

6. **swissALTI3D für Terrain**
   - 3D-Visualisierung mit Gelände
   - Sichtlinien-Analyse

---

## 6. Code-Beispiele

### 6.1 swissBUILDINGS3D 3.0 Download (Python)

```python
import requests
from pathlib import Path

def download_buildings_via_stac(easting: float, northing: float, output_dir: Path):
    """Download swissBUILDINGS3D 3.0 via STAC API."""

    # Kachel-Koordinaten (auf 1km abrunden)
    tile_e = int(easting // 1000)
    tile_n = int(northing // 1000)
    tile_name = f"{tile_e}_{tile_n}"

    # STAC Collection
    collection_id = "ch.swisstopo.swissbuildings3d_3_0"

    # Items abfragen
    bbox = f"{tile_e*1000},{tile_n*1000},{(tile_e+1)*1000},{(tile_n+1)*1000}"
    items_url = f"https://data.geo.admin.ch/api/stac/v1/collections/{collection_id}/items?bbox={bbox}"

    response = requests.get(items_url)
    data = response.json()

    if not data.get("features"):
        raise ValueError(f"Keine Daten für Kachel {tile_name}")

    # Erstes Item (sollte nur eins sein)
    item = data["features"][0]

    # Asset "citygml" finden
    if "citygml" not in item["assets"]:
        raise ValueError("CityGML-Asset nicht gefunden")

    download_url = item["assets"]["citygml"]["href"]

    # Download
    print(f"Download: {download_url}")
    zip_path = output_dir / f"buildings_{tile_name}.zip"

    with requests.get(download_url, stream=True) as r:
        r.raise_for_status()
        with open(zip_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    print(f"✅ Gespeichert: {zip_path}")
    return zip_path
```

### 6.2 EGID-Lookup (Python)

```python
import requests

def lookup_address_by_egid(egid: str) -> dict:
    """Lädt Adresse zu EGID von geo.admin.ch."""

    url = "https://api3.geo.admin.ch/rest/services/api/MapServer/find"
    params = {
        "layer": "ch.bfs.gebaeude_wohnungs_register",
        "searchText": egid,
        "searchField": "egid",
        "returnGeometry": "true",
        "sr": "2056"
    }

    response = requests.get(url, params=params)
    data = response.json()

    if not data.get("results"):
        return None

    result = data["results"][0]
    attrs = result["attributes"]

    return {
        "egid": attrs.get("egid"),
        "address": f"{attrs.get('strname')} {attrs.get('deinr')}",
        "plz": attrs.get("plz4"),
        "ort": attrs.get("plzname"),
        "e": result["geometry"]["x"],
        "n": result["geometry"]["y"]
    }

# Beispiel
info = lookup_address_by_egid("123164")
print(info)
# {'egid': '123164', 'address': 'Bahnhofstrasse 12', 'plz': '8001', 'ort': 'Zürich', ...}
```

### 6.3 WMS-Kataster als PNG (Python)

```python
import requests
from pathlib import Path

def download_cadastral_wms(bbox: tuple, width: int, height: int, output: Path):
    """Lädt Katasterkarte als PNG."""

    wms_url = "https://wms.geo.admin.ch/"
    params = {
        "SERVICE": "WMS",
        "VERSION": "1.3.0",
        "REQUEST": "GetMap",
        "LAYERS": "ch.swisstopo-vd.amtliche-vermessung",
        "CRS": "EPSG:2056",
        "BBOX": ",".join(map(str, bbox)),  # minE,minN,maxE,maxN
        "WIDTH": width,
        "HEIGHT": height,
        "FORMAT": "image/png"
    }

    response = requests.get(wms_url, params=params)
    response.raise_for_status()

    with open(output, 'wb') as f:
        f.write(response.content)

    print(f"✅ Katasterkarte: {output}")

# Beispiel
download_cadastral_wms(
    bbox=(2681000, 1252000, 2682000, 1253000),  # 1km × 1km
    width=4000,   # 4000 Pixel = 0.25m/Pixel
    height=4000,
    output=Path("kataster.png")
)
```

---

## 7. Links und Ressourcen

### Dokumentation

- [GeoAdmin API 3.0 Documentation](https://api3.geo.admin.ch/services/sdiservices.html)
- [STAC API Overview](https://docs.geo.admin.ch/download-data/stac-api/overview.html)
- [Web Map Service (WMS)](https://docs.geo.admin.ch/visualize-data/wms.html)
- [Search Documentation](https://docs.geo.admin.ch/access-data/search.html)

### Datenquellen

- [data.geo.admin.ch STAC Browser](https://data.geo.admin.ch/browser/)
- [opendata.swiss](https://opendata.swiss/en/organization/bundesamt-fur-landestopografie-swisstopo)
- [swisstopo Free Geodata](https://www.swisstopo.admin.ch/en/free-geodata-ogd)
- [Cadastral Parcels Information](https://www.geo.admin.ch/en/cadastral-parcels)

### APIs

- [REST API Base](https://api3.geo.admin.ch/rest/services)
- [STAC API Base](https://data.geo.admin.ch/api/stac/v1/)
- [WMS GetCapabilities](https://wms.geo.admin.ch/?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities)

### Tools

- [Swiss Geo Downloader (QGIS Plugin)](https://plugins.qgis.org/plugins/swissgeodownloader/)
- [Swiss Locator (QGIS Plugin)](https://plugins.qgis.org/plugins/swiss_locator/)

---

## 8. Changelog

- **2026-01-11:** Erstellt - Umfassende Übersicht aller geo.admin.ch Geodaten
