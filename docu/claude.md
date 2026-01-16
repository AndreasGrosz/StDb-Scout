# EMF-Hotspot-Finder - Projekt-Übersicht für Claude

## Projektziel

Python-Tool zur Identifikation von NISV-Überschreitungen (Nichtion

isierende Strahlung Verordnung) an Gebäudefassaden und Dächern in der Nähe von Mobilfunkantennen in der Schweiz.

**Grenzwert:** E-Feld ≥ 5.0 V/m (AGW = Anlagegrenzwert)

## Aktuelle Funktionen (Stand 2026-01-08)

### ✅ Implementiert

1. **OMEN XLS-Parser** (`emf_hotspot/loaders/omen_loader.py`)
   - Liest Standortdatenblätter (32 Sheets)
   - Extrahiert 9 Antennen (Position, ERP, Azimut, Tilt, Frequenz)
   - Extrahiert 20 OMEN-Positionen mit Gebäudedämpfung (Zeilen 111-113, 370)
   - Sprachunabhängig (Spalte A = feste Zeilennummer)

2. **Antennendiagramm-Loader** (`emf_hotspot/loaders/pattern_loader.py`)
   - Parst digitalisierte MSI-CSV-Dateien
   - Format: `Hybrid AIR3268 1427-2570 H.csv` (H=Horizontal, V=Vertikal)
   - Fuzzy Matching für Antennentypen
   - Interpolation für beliebige Winkel

3. **Gebäudedaten-Loader** (Multi-Source)
   - **GDB-Support** (`gdb_loader.py`): ESRI FileGDB (13GB Gesamt-Schweiz)
   - **CityGML-Support** (`building_loader.py`): Einzelne Kacheln (275MB/Kachel)
   - **Automatische Quellenwahl** (`find_buildings_auto()`): GDB → CityGML → Download
   - Parst WallSurfaces + RoofSurfaces

4. **Geometrie-Berechnungen** (`emf_hotspot/geometry/`)
   - Fassaden-Sampling mit konfigurierbarer Auflösung (default: 0.5m)
   - Dach-Sampling (horizontal + CityGML RoofSurface)
   - Relative Winkel-Berechnung (Azimut/Elevation zur Antenne)
   - Point-in-Polygon-Tests (Ray-Casting)

5. **Physik-Berechnungen** (`emf_hotspot/physics/`)
   - Freiraumdämpfung: `E = sqrt(30 * ERP) / distance`
   - Antennendiagramm-Dämpfung: `E * 10^(-(A_h + A_v)/20)`
   - Leistungsaddition: `E_total = sqrt(Σ E_i²)` (inkohärent)

6. **Output-Module** (`emf_hotspot/output/`)
   - **hotspots.csv**: Alle Punkte ≥ 5 V/m mit Antenna-Contributions
   - **alle_punkte.csv**: Vollständiges Raster
   - **pro_gebaeude.csv**: Aggregiert per Gebäude
   - **zusammenfassung.csv**: Statistiken
   - **ergebnisse.geojson**: GIS-kompatibel (EPSG:2056)
   - **heatmap.png**: 2D-Draufsicht (Maßstab 1:1000, 300 DPI, transparent)
   - **3D-Visualisierung**: PyVista (optional)

7. **Heatmap-Features**
   - Transparenter Hintergrund (Alphakanal)
   - Antennenstandort-Marker (blauer Stern)
   - Azimut-Pfeile (Sektoren)
   - Maßstabsbalken (50m bei 1:1000)
   - Korrekte DPI-Berechnung für Druck

8. **Konfiguration** (`config.json`)
   - Alle Parameter extern konfigurierbar
   - Auflösung, Radius, Grenzwert
   - Dächer ein/aus, Maßstab, DPI

## Verzeichnisstruktur

```
geo-plot/
├── emf_hotspot/              # Python-Paket
│   ├── config.py             # Konstanten
│   ├── models.py             # Dataclasses
│   ├── main.py               # CLI + Analyse-Pipeline
│   ├── loaders/              # Datei-Parser
│   │   ├── omen_loader.py
│   │   ├── pattern_loader.py
│   │   ├── building_loader.py
│   │   └── gdb_loader.py
│   ├── geometry/             # Geometrie-Berechnungen
│   │   ├── coordinates.py
│   │   ├── angles.py
│   │   └── facade_sampling.py
│   ├── physics/              # E-Feld-Berechnungen
│   │   ├── propagation.py
│   │   └── summation.py
│   └── output/               # Export-Module
│       ├── csv_export.py
│       └── visualization.py
├── input/
│   ├── OMEN R37 clean.xls    # Standortdatenblatt
│   └── NIS-Plan.pdf          # Amtlicher Plan (Overlay)
├── msi-files/                # Antennendiagramme
│   ├── Hybrid AIR3268 738-921 H.csv
│   └── ... (6 Dateien total)
├── swisstopo/                # Gebäudedaten
│   └── swissbuildings3d_3_0_2025_2056_5728.gdb.zip  # 13 GB
├── gebaeude_citygml/         # Lokale Kacheln (optional)
│   └── swissBUILDINGS3D_3-0_1091-12.gml
├── output/                   # Ergebnisse
├── config.json               # Konfiguration
├── PFLICHTENHEFT.md          # Spezifikation (91 KB)
└── claude.md                 # Diese Datei
```

## Verwendung

```bash
# Basis-Analyse (mit automatischer Quellenw

ahl)
python -m emf_hotspot.main 'input/OMEN R37 clean.xls' \
  -p msi-files \
  -o output \
  --radius 100 \
  --resolution 0.5

# Mit spezifischer CityGML-Datei
python -m emf_hotspot.main 'input/OMEN R37 clean.xls' \
  -c 'gebaeude_citygml/swissBUILDINGS3D_3-0_1091-12.gml' \
  -p msi-files \
  -o output

# Ohne 3D-Visualisierung
python -m emf_hotspot.main 'input/OMEN R37 clean.xls' \
  -p msi-files \
  -o output \
  --no-viz
```

## Datenquellen

### 1. OMEN XLS (Standortdatenblatt)
- **Sheets:** Global, Antenna, O1-O20, Helper, Leistung, etc.
- **Wichtige Zeilen in Antenna (Spalte A = ID):**
  - 40: Header (Laufnummer)
  - 60: Frequenzband
  - 80: Antennentyp
  - 111-113: Position-Offsets (X, Y, Z)
  - 120: ERP [W]
  - 140: Azimut [°]
  - 150: Tilt [°]
- **OMEN-Sheets (O1-O20):**
  - 111-113: OMEN-Position (Offsets)
  - 370: Gebäudedämpfung [dB]

### 2. Antennendiagramme (CSV)
- **Format:** `Gain_dB;Angle_Deg` (Komma als Dezimaltrenner)
- **Dateinamen:** `<Typ> <Frequenz> <H|V>.csv`
- **Beispiel:** `Hybrid AIR3268 3600 V.csv`

### 3. swissBUILDINGS3D
- **GDB:** Gesamte Schweiz (13 GB, ESRI FileGDB)
- **CityGML:** Einzelne Kacheln (10km × 10km Grid)
- **Formate:** WallSurface, RoofSurface mit 3D-Koordinaten (LV95)

## Bekannte Einschränkungen

1. **GDB-Support:** Benötigt GDAL/OGR (`conda install -c conda-forge gdal`)
2. **Gebäudedämpfung:** Nur aus OMEN-Sheets, sonst 0 dB (konservativ)
3. **Fenster-Erkennung:** Nicht verfügbar in swissBUILDINGS3D
4. **Download-API:** swisstopo-API funktioniert nicht (404)

## TODO (Priorität)

### Hoch
- [ ] **OMEN-Validierung:** E-Feld an OMEN-Punkten nachrechnen, Abweichungen melden
- [ ] **pro_gebaeude.csv:** OMEN-Nr + Postadresse ergänzen
- [ ] **hotspots.csv:** Spalte für Z-Maximum je Höhenstufe

### Mittel
- [ ] **WMS-API:** Satelliten-/Straßenkarten von geo.admin.ch laden
- [ ] **NIS-Plan-Overlay:** PDF als Hintergrund-Layer
- [ ] **3D-Visualisierung:** Antennenmarker, Farblegende, Animation

### Niedrig
- [ ] **Amtliche Vermessung:** Unbebaute Grundstücke als OMEN
- [ ] **Physik-Vergleich:** Formeln mit OMEN-XLS abgleichen

## Physikalische Formeln

### Freiraumdämpfung
```
E = sqrt(30 * ERP_watts) / distance_m
```

### Mit Antennendiagramm
```
E = E_free * 10^(-(A_h + A_v)/20)
```
- `A_h`: Horizontale Dämpfung aus Diagramm
- `A_v`: Vertikale Dämpfung aus Diagramm

### Leistungsaddition (inkohärent)
```
E_total = sqrt(Σ E_i²)
```

### Relative Winkel
```
azimut_abs = atan2(dx, dy)  // 0° = Nord
azimut_rel = azimut_abs - antenna_azimut
azimut_rel = ((azimut_rel + 180) % 360) - 180  // Normalisiert auf [-180, 180]

elevation = atan2(dz, sqrt(dx² + dy²)) - antenna_tilt
```

## Test-Ergebnisse (Zürich, Wehntalerstrasse 464)

**Mit realen Gebäudedaten (27 Gebäude):**
- Geprüfte Punkte: 28,786
- Hotspots: 1,822 (6.33%)
- Max. Feldstärke: **31.46 V/m** (6.3× NISV-Grenzwert)
- Betroffene Gebäude: 3

**Mit Dächern (Auflösung 2.0m):**
- Geprüfte Punkte: 9,415
- Hotspots: 568
- Max. Feldstärke: **48.84 V/m** (9.8× NISV-Grenzwert)

## Abhängigkeiten

```
pandas>=1.5.0
openpyxl>=3.0.0
xlrd>=2.0.0
numpy>=1.20.0
scipy>=1.7.0
matplotlib>=3.5.0
lxml>=4.9.0  # Optional: Schnelleres CityGML-Parsing
pyvista>=0.40.0  # Optional: 3D-Visualisierung
gdal>=3.5.0  # Optional: GDB-Support
```

## Kontakt

- **Projekt:** EMF-Hotspot-Finder
- **Zweck:** NISV-Nachweis für Einspracheberechtigte
- **Lizenz:** Open Source (geplant)
- **Kontakt:** admin@5gfrei.ch

## Änderungshistorie

### 2026-01-08
- ✅ Dach-Sampling implementiert (RoofSurface + geometrisch)
- ✅ OMEN-Loader erweitert (Positionen + Dämpfung)
- ✅ Heatmap verbessert (Alphakanal, Antennenmarker, 1:1000)
- ✅ GDB-Loader für Gesamt-Schweiz (13GB)
- ✅ Automatische Quellenwahl
- ✅ config.json für alle Parameter

### 2025-12-XX (Initial)
- ✅ Basis-Implementation
- ✅ CityGML-Parser
- ✅ OMEN XLS-Parser
- ✅ Antennendiagramm-Parser
- ✅ E-Feld-Berechnungen
- ✅ CSV/GeoJSON-Export
