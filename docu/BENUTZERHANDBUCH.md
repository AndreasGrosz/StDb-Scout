# EMF-Hotspot-Finder - Benutzerhandbuch

## Übersicht

**EMF-Hotspot-Finder** analysiert elektromagnetische Feldstärken (EMF) von Mobilfunkantennen gemäß Schweizer NISV-Verordnung (AGW: 5.0 V/m). Das Tool berechnet E-Feldstärken an Gebäudefassaden und identifiziert Hotspots, die den Grenzwert überschreiten.

**Hauptfunktionen:**
- Laden von Antennendaten aus OMEN-Excel-Sheets
- Integration von Antennendiagrammen (MSI-Daten oder Standard-Patterns)
- 3D-Gebäudedaten aus swissBUILDINGS3D (CityGML)
- E-Feld-Berechnung mit Freiraumdämpfung und Antennendiagrammen
- Worst-Case-Analyse über Tilt-Bereiche
- Berücksichtigung von Gebäudedämpfung
- Ausgabe: CSV-Listen, 2D-Heatmaps, 3D-Visualisierungen (VTK/ParaView)

---

## Schnellstart (Fish-Shell)

### 1. Virtual Environment aktivieren

```fish
cd /media/synology/files/projekte/kd0241-py/geo-plot
source venv/bin/activate.fish
```

**Alias einrichten** (in `~/.config/fish/config.fish`):
```fish
function geo-plot
    cd /media/synology/files/projekte/kd0241-py/geo-plot
    source venv/bin/activate.fish
end
```

Dann einfach:
```fish
geo-plot
```

### 2. Analyse ausführen

```fish
# Mit lokalem CityGML
python3 -m emf_hotspot.main \
    input/OMEN\ R37\ clean.xls \
    -o output \
    --citygml gebaeude_citygml/swissBUILDINGS3D_3-0_1091-12.gml \
    --threshold 5.0 \
    --resolution 0.5

# Mit Antennendiagrammen (falls vorhanden)
python3 -m emf_hotspot.main \
    input/OMEN\ R37\ clean.xls \
    -o output \
    --pattern-file "input/Antennendämpfungen Hybrid AIR3268 R5.ods"
```

### 3. Ergebnisse prüfen

```fish
ls -lh output/
cat output/hotspots_aggregated.csv
open output/heatmap.png  # oder: xdg-open auf Linux
```

---

## Projektstruktur

```
geo-plot/
├── emf_hotspot/              # Hauptmodul
│   ├── main.py               # CLI-Einstiegspunkt
│   ├── config.py             # Konstanten (AGW=5V/m, etc.)
│   ├── models.py             # Datenklassen (Antenna, Building, etc.)
│   ├── loaders/              # Datenimport
│   │   ├── omen_loader.py    # Excel-Parser für OMEN-Sheets
│   │   ├── pattern_loader.py # Antennendiagramme (ODS/CSV)
│   │   ├── building_loader.py# CityGML-Parser
│   │   └── geoadmin_api.py   # WMS/Gebäudeadressen
│   ├── geometry/             # Geometrische Berechnungen
│   │   ├── coordinates.py    # LV95-Koordinaten
│   │   ├── angles.py         # Azimut/Elevation relativ zu Antenne
│   │   └── facade_sampling.py# Fassaden-Rasterung
│   ├── physics/              # Physikalische Berechnungen
│   │   ├── propagation.py    # E-Feld-Formel
│   │   ├── pattern.py        # Diagramm-Interpolation
│   │   └── summation.py      # Leistungsaddition über Antennen
│   └── output/               # Export und Visualisierung
│       ├── csv_export.py     # CSV-Exporte
│       ├── visualization.py  # Heatmaps, 3D-Plots
│       └── paraview_state.py # ParaView-Konfiguration
│
├── input/                    # Eingabedaten
│   ├── OMEN R37 clean.xls    # Antennendaten
│   └── Antennendämpfungen*.ods # Antennendiagramme (optional)
│
├── gebaeude_citygml/         # CityGML-Dateien (lokal)
│
├── output/                   # Ergebnisse (letzte Analyse)
│
├── venv/                     # Virtual Environment
│
├── requirements.txt          # Python-Dependencies
├── setup_venv.sh             # Automatisches venv-Setup (Bash)
├── check_environment.py      # Environment-Diagnose
│
└── BENUTZERHANDBUCH.md       # Dieses Dokument
```

---

## Alle Skripte und ihre Zwecke

### Analyse-Skripte

#### `python3 -m emf_hotspot.main`
**Hauptprogramm** - Führt vollständige EMF-Analyse durch.

**Minimales Beispiel:**
```fish
python3 -m emf_hotspot.main input/OMEN\ R37\ clean.xls -o output
```

**Parameter:**
- `INPUT_XLS` - OMEN-Excel-Datei (Pflicht)
- `-o, --output DIR` - Ausgabeverzeichnis
- `--citygml FILE.gml` - Lokale CityGML-Datei (statt API-Download)
- `--pattern-file FILE.ods` - Antennendiagramme (optional, sonst Standard-Pattern)
- `--threshold N` - AGW-Grenzwert in V/m (default: 5.0)
- `--resolution N` - Fassaden-Auflösung in m (default: 0.5)
- `--radius N` - Gebäude-Suchradius in m (default: 100.0)

**Output:** Siehe Abschnitt "Ausgabedateien"

---

### Setup-Skripte

#### `setup_venv.sh`
**Automatisches Virtual Environment Setup** (Bash-Skript).

```fish
bash setup_venv.sh
```

**Funktion:**
1. Prüft Python-Version (≥3.10)
2. Erstellt `venv/` Verzeichnis
3. Installiert alle Dependencies aus `requirements.txt`
4. Testet Installation

**Alternative für Fish:**
```fish
python3 -m venv venv
source venv/bin/activate.fish
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

#### `check_environment.py`
**Environment-Diagnose** - Prüft Python-Umgebung und installierte Packages.

```fish
python3 check_environment.py
```

**Zeigt:**
- Python-Version und Pfad
- Ob venv aktiv ist
- Wo Packages installiert sind (venv vs. global)
- Welche Packages fehlen

**Farbcodierung:**
- ✅ Grün = venv, alles OK
- ⚠️ Gelb = global installiert (Warnung)
- ❌ Rot = fehlt

---

### Test- und Validierungs-Skripte

#### `validate_omen.py`
**OMEN-Validierung** - Vergleicht berechnete E-Werte mit Excel-Referenzwerten.

```fish
python3 validate_omen.py
```

**Funktion:**
- Liest OMEN O1-O20 aus Excel
- Berechnet E-Werte mit unserem Algorithmus
- Vergleicht mit Excel-Werten
- Zeigt prozentuale Abweichungen

**Ausgabe:** `output/omen_validierung.csv`

#### `test_*.py`
**Unit-Tests** (falls vorhanden).

```fish
pytest tests/
```

---

## Eingabedaten

### 1. OMEN-Excel-Datei (`OMEN R37 clean.xls`)

**Format:** Excel-Workbook mit mehreren Sheets.

**Wichtige Sheets:**
- **Global** (B5): LV95-Koordinaten `"2681044 / 1252266 / 462.20"`
- **Antenna** (multiple columns): Antennendaten
  - Zeile 60: Frequenzband
  - Zeile 111-113: Mast-Offsets (X, Y, Z)
  - Zeile 120: ERP in Watt
  - Zeile 140: Azimut in Grad
  - Zeile 150: Tilt in Grad
- **O1-O20** (OMEN-Sheets): Kritische Punkte mit Referenzwerten
  - Zeile 21: Koordinaten
  - Zeile 113: Berechnete E-Feldstärke

**Struktur:**
```
| Sheet | Inhalt |
|-------|--------|
| Global | Standortdaten |
| Antenna | 3 Sektoren à 3 Frequenzbänder = 9 Antennen |
| O1-O20 | Orte mit empfindlicher Nutzung |
```

### 2. Antennendiagramme (optional)

**Datei:** `Antennendämpfungen Hybrid AIR3268 R5.ods`

**Format:** ODS-Spreadsheet mit Sheets pro Frequenzband:
- H-Diagramme (Azimut): 0-360°
- V-Diagramme (Elevation): -90 bis +90°

**Struktur je Sheet:**
```
Zeile→Dämpfung_dB;Winkel_Grad
1→0,00000;0,00000
2→0,12345;1,00000
```

**Falls nicht vorhanden:** Nutzt Standard-Patterns (3GPP TR 36.814, Sektor 65°/7°).

### 3. CityGML-Gebäudedaten

**Quelle:** swissBUILDINGS3D 3.0 (swisstopo OpenData)

**Formate:**
- Lokal: `gebaeude_citygml/*.gml` (falls API nicht verfügbar)
- API: Automatischer Download basierend auf Koordinaten (derzeit 404-Fehler)

**Inhalt:**
- 3D-Gebäudegeometrie (LOD2)
- Fassadenflächen
- EGID (ab swissBUILDINGS3D 3.0, Dez 2022)
- Geschosszahlen, Nutzung

**Verwendung:**
```fish
# Lokale Datei
--citygml gebaeude_citygml/swissBUILDINGS3D_3-0_1091-12.gml

# API (falls verfügbar)
# Automatisch, kein Parameter nötig
```

---

## Ausgabedateien

Alle Dateien landen im Ausgabeverzeichnis (z.B. `output/`).

### CSV-Dateien

#### `hotspots.csv`
**Alle Einzelpunkte über AGW-Grenzwert.**

```csv
building_id,egid,x,y,z,e_field_vm,num_antennas,dominant_antenna,dominant_freq_mhz
bldg_0001,,2681050.2,1252270.5,468.3,5.23,3,Ant6,2100.0
```

**Spalten:**
- `building_id` - Interne Gebäude-ID
- `egid` - Eidgenössischer Gebäudeidentifikator (leer bei alten CityGML)
- `x, y, z` - LV95-Koordinaten (Ost, Nord, Höhe ü.M.)
- `e_field_vm` - E-Feldstärke in V/m
- `num_antennas` - Anzahl Antennen, die zu diesem Punkt beitragen
- `dominant_antenna` - Antenne mit größtem Beitrag
- `dominant_freq_mhz` - Frequenz der dominanten Antenne

#### `hotspots_aggregated.csv`
**Zusammenfassung pro Gebäude** (nur Gebäude mit Hotspots).

```csv
building_id,egid,num_points,num_hotspots,max_e_vm,avg_e_vm,dominant_antenna
bldg_0001,,1234,42,5.23,4.87,Ant6
```

**Spalten:**
- `num_points` - Gesamtzahl berechneter Punkte am Gebäude
- `num_hotspots` - Anzahl Hotspots (>5.0 V/m)
- `max_e_vm` - Maximale E-Feldstärke
- `avg_e_vm` - Durchschnitt über alle Hotspots

#### `pro_gebaeude.csv`
**Alle Gebäude** (auch ohne Hotspots) mit OMEN-Zuordnung.

```csv
building_id,egid,address,omen_nr,num_floors,num_points,num_hotspots,max_e_vm,avg_e_vm,height_m
bldg_0001,,Wehntalerstrasse 464,O7,4,1234,42,5.23,3.45,12.5
bldg_0002,,,O12,3,890,0,4.87,2.31,9.0
```

**Neue Spalten:**
- `address` - Gebäudeadresse von geo.admin.ch (falls EGID vorhanden)
- `omen_nr` - Zugeordnetes OMEN (O1-O20, falls < 50m entfernt)
- `num_floors` - Geschosszahl (height_m / 3.0)
- `height_m` - Gebäudehöhe in Metern

#### `omen_validierung.csv`
**Vergleich mit Excel-Referenzwerten.**

```csv
omen_id,excel_e_vm,calculated_e_vm,difference_vm,difference_percent
O1,4.523,4.612,0.089,1.97
```

**Spalten:**
- `excel_e_vm` - Wert aus OMEN-Sheet (Zeile 113)
- `calculated_e_vm` - Unser berechneter Wert
- `difference_vm` - Absolute Abweichung
- `difference_percent` - Prozentuale Abweichung

#### `alle_punkte.csv`
**Alle berechneten Punkte** (auch unter Grenzwert) - **Warnung: große Datei!**

Gleiche Struktur wie `hotspots.csv`, aber mit allen ~20k-100k Punkten.

---

### Visualisierungen (2D)

#### `heatmap.png`
**2D-Heatmap** auf geo.admin.ch Basiskarte (Pixelkarte).

**Inhalt:**
- Basiskarte von geo.admin.ch WMS
- E-Feld als Farbverlauf (rot = hoch, grün = niedrig)
- Gebäudegrenzen als schwarze Konturen
- OMEN-Labels (O1-O20) neben Gebäuden (1:1-Mapping)
- Antennenposition als schwarzes X

**Farbskala:** 0-6 V/m (kann mit `--threshold` angepasst werden)

#### `hotspots_marker_map.png`
**Marker-Karte** mit Punkten pro Gebäude.

**Inhalt:**
- geo.admin.ch Basiskarte
- Jedes Gebäude = 1 Marker
- Größe = Anzahl Hotspots
- Farbe = Max. E-Feldstärke
- Legende rechts außerhalb der Karte

**Bereinigtes Layout:**
- Keine Achsenbeschriftungen
- Keine Colorbar
- Kein Grid
- Nur Karte + Legende

---

### Visualisierungen (3D)

#### `ergebnisse.vtm` + `ergebnisse/`
**VTK Multiblock Dataset** für ParaView/PyVista.

**Struktur:**
```
ergebnisse.vtm               # Multiblock Index
ergebnisse/
├── hotspots.vtp             # Hotspot-Punkte (>5V/m) als Voxel
├── all_points.vtp           # Alle Punkte (falls <50k)
├── buildings.vtp            # Gebäudeflächen als Mesh
└── antennas.vtp             # Antennen-Marker
```

**Datenfelder:**
- `E_field_Vm` - E-Feldstärke (für Farbcodierung)
- `building_id` - Gebäude-Zuordnung
- `num_antennas` - Anzahl Antennen

**Geometrie:**
- Punkte als Voxel/Würfel (Größe = `--resolution`)
- Automatisch für <50k Punkte
- Sichtbar ohne manuelle Skalierung

#### `PARAVIEW_ANLEITUNG.md`
**ParaView Quick Guide** mit Screenshots und Schritt-für-Schritt-Anleitung.

**Inhalt:**
1. VTM-Datei öffnen
2. Multiblock-Ansicht aktivieren
3. E_field_Vm für Farbcodierung wählen
4. Farbskala auf 0-6 V/m setzen
5. Glyph-Filter für Punktvergrößerung (falls nötig)

---

### GeoJSON (optional)

#### `ergebnisse.geojson`
**GeoJSON-Export** für QGIS/Web-Mapping.

**Inhalt:**
- Alle Hotspot-Punkte als Point-Features
- Properties: `e_field_vm`, `building_id`
- CRS: EPSG:2056 (LV95)

**Verwendung:**
```fish
# In QGIS laden
# Oder Web-Mapping-Tools
```

---

## Workflows

### Standard-Analyse

```fish
# 1. venv aktivieren
source venv/bin/activate.fish

# 2. Analyse starten
python3 -m emf_hotspot.main \
    input/OMEN\ R37\ clean.xls \
    -o output \
    --citygml gebaeude_citygml/swissBUILDINGS3D_3-0_1091-12.gml \
    --resolution 0.5

# 3. Ergebnisse prüfen
cat output/hotspots_aggregated.csv
open output/heatmap.png

# 4. 3D-Visualisierung in ParaView
paraview output/ergebnisse.vtm
```

---

### Mit Antennendiagrammen (MSI-Daten)

Falls Sie MSI-Daten haben (z.B. von Antennenherstellern):

```fish
# 1. MSI-Daten in ODS konvertieren (manuell oder mit Tool)
#    → Antennendämpfungen Hybrid AIR3268 R5.ods

# 2. Analyse mit Pattern-File
python3 -m emf_hotspot.main \
    input/OMEN\ R37\ clean.xls \
    -o output \
    --pattern-file "input/Antennendämpfungen Hybrid AIR3268 R5.ods" \
    --citygml gebaeude_citygml/swissBUILDINGS3D_3-0_1091-12.gml

# 3. Validierung gegen OMEN
python3 validate_omen.py
cat output/omen_validierung.csv
```

**Erwartete Abweichung:** <5% zu Excel-Werten (bei korrekten MSI-Daten)

---

### Worst-Case-Analyse (Tilt-Bereich)

```fish
# Antenne mit tilt_from bis tilt_to (z.B. 0-6°)
# → Automatisch Worst-Case für jeden Punkt

python3 -m emf_hotspot.main \
    input/OMEN\ R37\ clean.xls \
    -o output_worst_case \
    --resolution 0.5 \
    --threshold 5.0

# Vergleich mit fester Tilt-Einstellung (Gutachten)
# → Siehe omen_validierung.csv für Abweichungen
```

---

### Batch-Verarbeitung mehrerer Standorte

```fish
# Loop über alle XLS-Dateien
for xls in input/*.xls
    set basename (basename $xls .xls)
    python3 -m emf_hotspot.main $xls -o output_$basename
end
```

---

### Eigene CityGML-Daten verwenden

Falls Sie neuere swissBUILDINGS3D-Daten haben:

```fish
# Download von swisstopo (manuell)
# https://www.swisstopo.admin.ch/de/geodata/landscape/buildings3d3.html

# Unzip
unzip swissbuildings3d_3_0_2680_1250_citygml.zip -d gebaeude_citygml/

# Analyse mit lokaler Datei
python3 -m emf_hotspot.main \
    input/OMEN\ R37\ clean.xls \
    -o output \
    --citygml gebaeude_citygml/swissbuildings3d_3_0_2680_1250.gml
```

---

## Physikalische Grundlagen

### E-Feld-Berechnung

**Freiraumdämpfung:**
```
E_free = sqrt(30 * ERP_watts) / distance_m
```

**Mit Antennendiagramm:**
```
E = E_free * 10^(-A_h/20) * 10^(-A_v/20)
```

- `A_h` = Horizontale Dämpfung aus H-Diagramm (Azimut)
- `A_v` = Vertikale Dämpfung aus V-Diagramm (Elevation)

**Leistungsaddition über alle Antennen:**
```
E_total = sqrt(sum(E_i^2))
```

### Relative Winkel zur Antenne

```python
# Punkt P relativ zu Antenne A
delta = P - A.position

# Absoluter Azimut (0° = Nord)
azimut_abs = atan2(delta.x, delta.y)

# Relativ zu Antennen-Azimut
azimut_rel = azimut_abs - A.azimut

# Elevation (relativ zu Horizontal)
horiz_dist = sqrt(delta.x^2 + delta.y^2)
elevation = atan2(delta.z, horiz_dist) - A.tilt
```

### Worst-Case-Tilt

Falls Antenne Tilt-Bereich hat (z.B. 0-6°):
- Für jeden Punkt: Alle Tilts durchprobieren
- Maximum = Worst-Case für diesen Punkt

### Gebäudedämpfung

Aus OMEN-Sheets übernommen:
- Glas: 0 dB
- Fassade: 3-6 dB (je nach Material)
- Beton: 10-15 dB

**Anwendung:**
- Nur für OMEN-Punkte (O1-O20) aus Excel
- Neue Fassadenpunkte: Keine Dämpfung (konservativ/Worst-Case)

---

## Konfiguration

### `config.py`

**Wichtige Konstanten:**

```python
AGW_LIMIT_VM = 5.0              # NISV-Grenzwert
DEFAULT_RESOLUTION_M = 0.5      # Fassaden-Raster
DEFAULT_RADIUS_M = 100.0        # Gebäude-Suchradius
FLOOR_HEIGHT_M = 3.0            # Annahme für Stockwerke
MAX_TILT_RANGE = 10.0           # Max. Tilt-Bereich
```

**Anpassen:**
```fish
# Im Code editieren
nano emf_hotspot/config.py

# Oder per CLI-Parameter
--threshold 6.0
--resolution 0.25
--radius 150.0
```

---

## Troubleshooting

### Problem: `ModuleNotFoundError`

**Symptom:**
```
ModuleNotFoundError: No module named 'numpy'
```

**Lösung:**
```fish
# venv aktivieren!
source venv/bin/activate.fish

# Packages installieren
pip install -r requirements.txt
```

---

### Problem: API 404-Fehler

**Symptom:**
```
HTTP Error 404: Not Found
swissBUILDINGS3D API-Download fehlgeschlagen
```

**Lösung:**
```fish
# Lokale CityGML verwenden
--citygml gebaeude_citygml/swissBUILDINGS3D_3-0_1091-12.gml
```

---

### Problem: OMEN-Abweichungen >10%

**Symptom:**
```csv
O7,4.523,5.123,0.600,13.26%
```

**Mögliche Ursachen:**
1. **Antennendiagramme fehlen** → Nutzt Standard-Pattern
   - Lösung: MSI-Daten als ODS bereitstellen (`--pattern-file`)

2. **Gebäudedämpfung nicht berücksichtigt**
   - Nur für OMEN-Punkte aus Excel aktiv
   - Prüfen: Zeile 23 in O7-Sheet (Dämpfung eingetragen?)

3. **Tilt-Bereich unterschiedlich**
   - Excel: Fester Tilt
   - Unser Tool: Worst-Case über Tilt-Bereich
   - Erwartbar: Unser Wert leicht höher

4. **Koordinaten-Rundung**
   - LV95-Koordinaten auf 0.1m genau?
   - Prüfen: OMEN-Sheet Zeile 21

---

### Problem: ParaView zeigt keine Punkte

**Symptom:** VTK-Datei öffnet, aber 3D-Ansicht leer.

**Lösung:**
```
1. Multiblock expandieren → "hotspots" anklicken
2. "Apply" Button klicken
3. Eye-Icon aktivieren
4. Zoom to Data (Kamera-Icon)
```

Siehe: `PARAVIEW_ANLEITUNG.md`

---

### Problem: venv aktiviert, aber globale Packages werden genutzt

**Symptom:**
```
⚠️  numpy ... (global: /home/res/miniconda3/...)
```

**Lösung:**
```fish
# venv neu erstellen
rm -rf venv/
python3 -m venv venv
source venv/bin/activate.fish
pip install -r requirements.txt

# Prüfen
python3 check_environment.py
```

---

### Problem: "Permission denied" bei setup_venv.sh

**Symptom:**
```
bash: setup_venv.sh: Permission denied
```

**Lösung:**
```fish
# Executable machen
chmod +x setup_venv.sh

# Oder direkt mit Bash
bash setup_venv.sh
```

**Alternative für Fish:**
Siehe "Setup-Skripte" → Manuelle Befehle für Fish

---

## Fish-Shell-Spezifika

### venv aktivieren

**Bash:**
```bash
source venv/bin/activate
```

**Fish:**
```fish
source venv/bin/activate.fish
```

### Umgebungsvariablen

**Bash:**
```bash
export PYTHONPATH=/path/to/module
```

**Fish:**
```fish
set -x PYTHONPATH /path/to/module
```

### Funktionen statt Alias

**Fish config** (`~/.config/fish/config.fish`):
```fish
function geo-plot
    cd /media/synology/files/projekte/kd0241-py/geo-plot
    source venv/bin/activate.fish
    echo "✅ EMF-Hotspot-Finder Environment"
end
```

### For-Loop

**Bash:**
```bash
for file in *.xls; do
    echo $file
done
```

**Fish:**
```fish
for file in *.xls
    echo $file
end
```

---

## Weiterentwicklung / TODOs

### Geplante Features

1. **Virtuelle Gebäude** (siehe `TODO_VIRTUELLE_GEBAEUDE.md`)
   - Katasterparzellen von geo.admin.ch
   - Leere Parzellen identifizieren
   - Virtuelle Gebäude mit 3m Grenzabstand
   - OMEN-Nummerierung: V1, V2, V3...

2. **Antenna Types Table**
   - Tabellarische Übersicht pro Antennentyp
   - Tilt-Bereiche, Frequenzen, Pmax
   - Heatmaps pro Tilt-Einstellung
   - Heatmap auf Pmax-Basis

3. **EGID/Adressen-Integration**
   - Neuere swissBUILDINGS3D (≥Dez 2022)
   - Automatische Adress-Lookup
   - Grundbuch-Informationen

4. **Interaktive Web-Visualisierung**
   - Leaflet/OpenLayers mit GeoJSON
   - Interaktive Heatmap
   - Building-Popup mit Details

---

## Weiterführende Ressourcen

### Dokumentation

- Python venv: https://docs.python.org/3/library/venv.html
- Fish Shell: https://fishshell.com/docs/current/
- ParaView: https://www.paraview.org/documentation/
- PyVista: https://docs.pyvista.org/

### Datenquellen

- swissBUILDINGS3D: https://www.swisstopo.admin.ch/de/geodata/landscape/buildings3d3.html
- geo.admin.ch WMS: https://api3.geo.admin.ch/services/sdiservices.html
- NISV Verordnung: https://www.admin.ch/opc/de/classified-compilation/19996141/

### Support

- GitHub Issues: (falls Repo public)
- Projektdokumentation: Dieses Verzeichnis

---

## Changelog

### Version 2.0 (Januar 2026)
- ✅ Virtual Environment Setup
- ✅ Fish-Shell-Kompatibilität
- ✅ pro_gebaeude.csv: EGID, Adresse, Stockwerke
- ✅ Heatmap OMEN-Nummerierung 1:1 gefixt
- ✅ hotspots_marker_map: Bereinigtes Layout
- ✅ ParaView: Voxel-Export + State Files
- ✅ Umfassendes Benutzerhandbuch

### Version 1.0 (Dezember 2025)
- Initiale Version mit Kern-Features
- OMEN-Excel-Parser
- Antennendiagramm-Integration
- CityGML-Loader
- E-Feld-Berechnung mit Worst-Case-Tilt
- CSV/VTK/PNG-Exports

---

## Kontakt

Projektverzeichnis: `/media/synology/files/projekte/kd0241-py/geo-plot`

Bei Fragen: Siehe README.md oder Projektdokumentation.
