
# Pflichtenheft: EMF-Hotspot-Finder

**Projekt:** Automatisierte Berechnung von NISV-Überschreitungen an Gebäudefassaden
**Version:** 1.0
**Datum:** 2026-01-08
**Auftraggeber:** Einsprecheberechtigte gegen Mobilfunkanlagen
**Ersteller:** 5Gfrei.ch

---

## 1. Projektübersicht

### 1.1 Ausgangslage

Kantone und Mobilfunkbetreiber erstellen Standortdatenblätter (StDB) für geplante Mobilfunkanlagen mit Berechnungen der elektromagnetischen Feldstärke (E-Feld) an kritischen Orten mit empfindlicher Nutzung (OMEN). Diese Berechnungen erfolgen derzeit:
- **Manuell** für einzelne ausgewählte Punkte (typisch 5-20 OMEN)
- **Unvollständig** - viele potenzielle Hotspots werden nicht erfasst
- **Intransparent** - Antennendiagramme werden nicht herausgegeben

Einsprecheberechtigte benötigen ein Werkzeug zur:
- **Vollständigen Analyse** aller Fassadenpunkte im Umkreis
- **Verifikation** der behördlichen Berechnungen
- **Identifikation** nicht deklarierter Hotspots

### 1.2 Zielsetzung

Entwicklung einer Python-Software, die:
1. Standortdatenblätter (digitalisiert als XLS) einliest
2. Selbst digitalisierte Antennendiagramme verwendet
3. 3D-Gebäudedaten von swisstopo bezieht
4. Flächendeckend E-Feldstärken an Fassaden berechnet
5. NISV-Überschreitungen (Anlagegrenzwert E ≥ 5 V/m) identifiziert
6. Ergebnisse als CSV, GeoJSON und 3D-Visualisierung exportiert
7. Die Gebäude gemäss swisstopo mit den Gebäuden aus dem NIS-Plan vergleicht und Abweichungen meldet: "im NIS-Plan fehlt Gebäude 2863"

---

## 2. Funktionale Anforderungen

### 2.1 Datenimport

#### FA-01: OMEN-XLS-Import
- die aktuellen Falldaten stehen im folder input/
- **Beschreibung:** Einlesen digitalisierter Standortdatenblätter im OMEN-Excel-Format
- **Eingabe:** XLS-Datei gemäß Template "OMEN R37 clean.xls"
- **Ausgabe:** AntennaSystem-Objekt mit allen Antennen
- **Pflichtfelder:**
  - Global Sheet: LV95-Koordinaten (Zeile 5, Spalte B: "E / N / H")
  - Antenna Sheet:
    - Zeile 120: ERP [W]
    - Zeile 140: Azimut [°]
    - Zeile 150: Tilt [°]
    - Zeile 60: Frequenzband [MHz]
    - Zeile 80: Antennentyp
    - Zeile 111-113: Mast-Offsets X, Y, Z [m]
- **Validierung:**
  - Koordinaten müssen im gültigen LV95-Bereich liegen (2'480'000-2'840'000 / 1'070'000-1'300'000)
  - ERP > 0 W
  - Azimut 0-360°

Ausserdem:
- Standortdatenblatt.pdf
- ein NIS-Plan.pdf oder als Bilddatei.

#### FA-02: Antennendiagramm-Import
- diese msi-Files sind im folder /msi-files/
- **Beschreibung:** Laden digitalisierter Antennendiagramme (H/V)
- **Eingabe:** CSV-Dateien im Format "Dämpfung;Winkel" (Komma als Dezimaltrenner)
- **Dateinamen-Konvention:** "{Antennentyp} {Frequenzband} {H|V}.csv"
  - Beispiel: "Hybrid AIR3268 3600 H.csv"
- **Ausgabe:** AntennaPattern-Objekt mit interpolierbaren Gain-Werten
- **Anforderungen:**
  - Automatisches Matching von Antennentyp zu Dateinamen
  - Fuzzy-Matching bei Namensabweichungen (z.B. "HybridAIR3268" → "Hybrid AIR3268")
  - Frequenzband-Normalisierung (700-900 → 738-921)
  - Winkel-Sortierung für Interpolation

späterer Milestone: wir erstellen eine DB mit allen Antennendämpfungsdaten: referenzID,hersteller,A-typ,frequenzband,vertikal-oder-Horizontal,radius,phi,db (ähnlich der msi-files/Antennendämpfungen Hybrid AIR3268 R5.ods"

#### FA-03: Gebäudedaten-Import
- **Beschreibung:** Bezug 3D-Gebäudedaten von swisstopo
- **Primärquelle:** swissBUILDINGS3D 3.0 Beta (CityGML 2.0)
- **Fallback:**
  - Lokale CityGML-Datei
  - OSM-Daten (geplant)
  - Test-Gebäude (für Entwicklung)
- **Ausgabe:** Liste von Building-Objekten mit WallSurface-Polygonen
- **Filterkriterien:**
  - Umkreis: konfigurierbar (default 100m)
  - Nur vertikale Flächen (|normal.z| < 0.7)

### 2.2 Geometrische Berechnungen

#### FA-04: Fassaden-Rasterung
- **Beschreibung:** Generierung von Messpunkten auf Gebäudefassaden
- **Algorithmus:**
  1. Projektion des Fassaden-Polygons auf lokale 2D-Ebene
  2. Erstellung eines gleichmäßigen Rasters (Auflösung konfigurierbar)
  3. Point-in-Polygon-Test (Ray-Casting)
  4. Rücktransformation in 3D-LV95-Koordinaten
- **Parameter:**
  - Auflösung: 0.1 - 5.0 m (default 0.5 m)
  - Nur Außenflächen (keine Dächer)
- **Ausgabe:** Liste von FacadePoint (x, y, z, normal)

#### FA-05: Winkelberechnung
- **Beschreibung:** Berechnung relativer Winkel zwischen Antenne und Messpunkt
- **Formeln:**
  - Azimut absolut: `arctan2(dx, dy)` (0° = Nord, im Uhrzeigersinn)
  - Azimut relativ: `Azimut_Punkt - Azimut_Antenne` (normalisiert auf [-180, 180]°)
  - Elevation absolut: `arctan2(dz, sqrt(dx² + dy²))`
  - Elevation relativ: `Elevation_Punkt - Tilt_Antenne`
- **Ausgabe:** (distance_3d, rel_azimuth, rel_elevation)

### 2.3 Physikalische Berechnungen

#### FA-06: E-Feldstärke-Berechnung
- **Beschreibung:** Berechnung der elektrischen Feldstärke pro Antenne und Punkt
- **Formel:**
  ```
  E_free = sqrt(30 * ERP) / d                    [Freiraum]
  A_h = Diagramm_H(azimut_rel)                    [Horizontaldämpfung]
  A_v = Diagramm_V(elevation_rel)                 [Vertikaldämpfung]
  E = E_free * 10^(-(A_h + A_v) / 20)            [Mit Dämpfung]
  ```
- **Parameter:**
  - ERP: Equivalent Radiated Power [W]
  - d: 3D-Abstand Antenne-Punkt [m], Minimum 0.1 m
  - A_h, A_v: Dämpfung aus Antennendiagramm [dB]
- **Validierung:** E >= 0 V/m

#### FA-07: Leistungsaddition
- **Beschreibung:** Summation der E-Felder aller Antennen (inkohärent)
- **Formel:**
  ```
  E_total = sqrt(Σ E_i²)    für alle Antennen i
  ```
- **Begründung:** Verschiedene Frequenzen → keine feste Phasenbeziehung
- **Ausgabe:** Gesamt-E-Feldstärke [V/m]

#### FA-08: Hotspot-Identifikation
- **Beschreibung:** Klassifikation nach NISV-Anlagegrenzwert
- **Grenzwert:** E ≥ 5.0 V/m (NISV Art. 13, Anhang 1)
- **Ausgabe:** Boolean "exceeds_limit"

### 2.4 Ergebnisexport

#### FA-09: CSV-Export
- **Beschreibung:** Export der Berechnungsergebnisse als CSV
- **Varianten:**
  1. **alle_punkte.csv:** Alle berechneten Punkte
  2. **hotspots.csv:** Nur Überschreitungen (E ≥ 5 V/m)
  3. **zusammenfassung.csv:** Statistik (Anzahl, Max, Mittelwert)
  4. **pro_gebaeude.csv:** Aggregation je Gebäude
- **Spalten (alle_punkte / hotspots):**
  - building_id
  - x, y, z (LV95)
  - e_field_vm
  - exceeds_limit
  - contributions (optional: "ant1:0.5;ant2:1.2;...")

#### FA-10: GeoJSON-Export
- **Beschreibung:** Export für GIS-Software (QGIS, ArcGIS)
- **Format:** GeoJSON FeatureCollection
- **CRS:** EPSG:2056 (LV95)
- **Properties pro Feature:**
  - building_id
  - e_field_vm
  - exceeds_limit
  - z

#### FA-11: Visualisierung
- **Beschreibung:** Grafische Darstellung der Ergebnisse
- **Varianten:**
  1. **3D-Visualisierung:** PyVista-Fenster
     - Fassadenpunkte mit Farbskala (grün → gelb → rot)
     - Antennen als blaue Kegel mit Ausrichtung
     - Gebäude als transparente Meshes
  2. **Heatmap (2D):** Draufsicht als PNG
     - Scatter-Plot der E-Werte
     - Hotspots als rote Kreuze markiert
  3. **Screenshot:** 3D-Ansicht als PNG

---

## 3. Nicht-funktionale Anforderungen

### 3.1 Performance

| Anforderung | Zielwert |
|-------------|----------|
| Verarbeitung 1000 Fassadenpunkte | < 30 Sekunden |
| Verarbeitung 10'000 Fassadenpunkte | < 5 Minuten |
| Speicherverbrauch | < 2 GB RAM |
| Gebäudedaten-Download | < 60 Sekunden (100m Radius) |

### 3.2 Usability

- **CLI-Interface:** Selbsterklärende Parameter mit Defaults
- **Fortschrittsanzeige:** Konsolenausgabe der 6 Hauptschritte
- **Fehlerbehandlung:** Klare Fehlermeldungen bei ungültigen Eingaben
- **Fallback:** keins!

### 3.3 Portabilität

- **Python-Version:** >= 3.10
- **Betriebssysteme:** Linux, macOS, Windows
- **Abhängigkeiten:** Nur standard PyPI-Pakete

### 3.4 Wartbarkeit

- **Modularität:** Klare Trennung Loader / Geometry / Physics / Output
- **Dokumentation:** Docstrings für alle öffentlichen Funktionen
- **Typisierung:** Type Hints wo sinnvoll
- **Tests:** Unit-Tests für kritische Berechnungen

---

## 4. Technische Spezifikation

### 4.1 Programmiersprache und Frameworks

| Komponente | Technologie | Version |
|------------|-------------|---------|
| Sprache | Python | >= 3.10 |
| Excel-Parsing | pandas, openpyxl, xlrd | latest |
| XML/CityGML | lxml | latest |
| Numerik | numpy, scipy | latest |
| Geometrie | shapely | latest |
| 3D-Visualisierung | pyvista | latest |
| 2D-Visualisierung | matplotlib | latest |
| CLI | argparse | stdlib |

### 4.2 Datenmodelle

#### Klasse: LV95Coordinate
```python
@dataclass
class LV95Coordinate:
    e: float  # Easting (2'xxx'xxx)
    n: float  # Northing (1'xxx'xxx)
    h: float  # Höhe über Meer [m]
```

#### Klasse: Antenna
```python
@dataclass
class Antenna:
    id: int
    mast_nr: int
    position: LV95Coordinate
    azimuth_deg: float  # Hauptstrahlrichtung [°]
    tilt_deg: float     # Neigung [°]
    erp_watts: float    # ERP [W]
    frequency_band: str # z.B. "3600"
    antenna_type: str   # z.B. "HybridAIR3268"
    is_adaptive: bool
    sub_arrays: int
```

#### Klasse: AntennaPattern
```python
@dataclass
class AntennaPattern:
    antenna_type: str
    frequency_band: str
    h_angles: np.ndarray  # [°]
    h_gains: np.ndarray   # [dB]
    v_angles: np.ndarray
    v_gains: np.ndarray

    def get_attenuation(azimuth_rel: float, elevation_rel: float) -> float
```

#### Klasse: HotspotResult
```python
@dataclass
class HotspotResult:
    building_id: str
    x: float  # LV95 E
    y: float  # LV95 N
    z: float  # Höhe [m]
    e_field_vm: float
    exceeds_limit: bool
    contributions: List[Tuple[int, float]]  # [(antenna_id, e_value), ...]
```

### 4.3 Modul-Architektur

```
emf_hotspot/
├── config.py                 # Konstanten
├── models.py                 # Datenklassen
├── main.py                   # CLI + Hauptlogik
├── loaders/
│   ├── omen_loader.py        # XLS → AntennaSystem
│   ├── pattern_loader.py     # CSV → AntennaPattern
│   └── building_loader.py    # CityGML → Buildings
├── geometry/
│   ├── coordinates.py        # LV95-Funktionen
│   ├── angles.py             # Azimut/Elevation
│   └── facade_sampling.py    # Polygon-Rasterung
├── physics/
│   ├── propagation.py        # E-Feld-Formeln
│   └── summation.py          # Leistungsaddition
└── output/
    ├── csv_export.py         # CSV-Generierung
    └── visualization.py      # 3D/2D-Plots, GeoJSON
```

---

## 5. Datenquellen und Formate

### 5.1 Eingabedaten

#### OMEN-XLS-Datei
- **Format:** Microsoft Excel (.xls)
- **Template:** "OMEN R37 clean.xls" (Verein 5Gfrei.ch)
- **Sheets:**
  - Global: Standortdaten, Koordinaten
  - Masten: Mast-Offsets
  - Antenna: Antennenparameter (9 Spalten = max. 9 Antennen)
  - Leistung: ERP-Berechnungen
  - Material: Gebäudedämpfungen (aktuell nicht verwendet)
- **Besonderheit:** Zeilen-basierter Zugriff (keine Header-Zeile)

#### Antennendiagramm-CSV
- **Format:** Text, Semikolon-getrennt, Komma-Dezimaltrenner
- **Struktur:** `Gain_dB;Winkel_Grad` (eine Zeile pro Messpunkt)
- **Winkel-Bereich:**
  - H-Diagramm: 0-360° (Azimut)
  - V-Diagramm: -90° bis +90° (Elevation, 0° = Horizont)
- **Gain-Interpretation:** Absolute Werte in dB (ca. 30 dB = Maximum)
- **Dateinamen:** "{Typ} {Frequenz} {H|V}.csv"

#### 3D-Gebäudedaten
- **Primär:** swissBUILDINGS3D 3.0 Beta (CityGML 2.0)
- **Bezug:** https://www.swisstopo.admin.ch (OpenData)
- **Kachelung:** 10 km × 10 km Tiles
- **Elemente:** Building → WallSurface (Polygon mit Koordinaten)
- **Koordinatensystem:** LV95 (EPSG:2056)
- **Verfügbarkeit:** AG, AI, AR, BE, BL, BS, FR, GL, JU, LU, NE, SG, SH, SO, SZ, TG, Stadt Zürich

### 5.2 Ausgabedaten

#### CSV-Dateien
- **Format:** UTF-8, Komma-getrennt
- **Dezimaltrenner:** Punkt (.)
- **Koordinaten:** LV95 (E, N, H) mit 2 Nachkommastellen
- **E-Werte:** 4 Nachkommastellen

#### GeoJSON
- **Standard:** RFC 7946
- **Encoding:** UTF-8
- **CRS:** Explizit als EPSG:2056 deklariert
- **Geometrie:** Point (3D)

#### PNG-Bilder
- **Auflösung:**
  - Heatmap: 1800 × 1500 px (150 dpi)
  - 3D-Screenshot: 1920 × 1080 px
- **Format:** PNG (verlustfrei)

---

## 6. Berechnungsmodell

### 6.1 Physikalische Grundlagen

#### Freiraum-Feldstärke
```
Leistungsdichte:  S = ERP / (4π d²)             [W/m²]
E-Feldstärke:     E² = S · Z₀ = S · 120π
Vereinfacht:      E = √(30 · ERP) / d           [V/m]

mit:
  ERP = Equivalent Radiated Power [W]
  d   = Abstand [m]
  Z₀  = 377 Ω (Freiraumimpedanz)
```

#### Antennendiagramm-Dämpfung
```
Relative Dämpfung:  A = A_h(φ) + A_v(θ)        [dB]

mit:
  φ = Azimut relativ zur Hauptstrahlrichtung
  θ = Elevation relativ zum Tilt
  A_h = max(Gain_H) - Gain_H(φ)
  A_v = max(Gain_V) - Gain_V(θ)
```

#### Dämpfungsanwendung
```
E_gedämpft = E_free · 10^(-A/20)
```

#### Leistungsaddition (inkohärent)
```
E_total = √(Σ E_i²)    für alle Antennen i

Begründung:
  - Verschiedene Frequenzen → keine Kohärenz
  - Leistungsaddition: P ∝ E²
  - E_total² = Σ E_i²
```

### 6.2 NISV-Grenzwerte

| Grenzwert | Frequenz | E-Feld | Anwendung |
|-----------|----------|--------|-----------|
| Anlagegrenzwert (AGW) | 400-2000 MHz | 4 - 6 V/m | OMEN (Wohnen, Aufenthalt) |
| Anlagegrenzwert (AGW) | 2000-300'000 MHz | 6 V/m | OMEN |
| Immissionsgrenzwert (IGW) | 400-2000 MHz | 58-87 V/m | Alle Orte | gesetzlicher AGW bei Frequenzmix ist 5 V/m

### 6.3 Koordinatensysteme

#### LV95 (EPSG:2056)
- **Projektion:** Oblique Mercator (Swiss Oblique Mercator)
- **Einheit:** Meter
- **Wertebereich:**
  - E (Easting): 2'480'000 - 2'840'000
  - N (Northing): 1'070'000 - 1'300'000
  - H (Höhe): 0 - 5'000 m.ü.M

#### Azimut-Konvention
- **0°** = Nord
- **90°** = Ost
- **180°** = Süd
- **270°** = West
- **Drehrichtung:** Im Uhrzeigersinn

#### Tilt-Konvention
- **0°** = Horizontal
- **Positiv** = Aufwärts
- **Negativ** = Abwärts (Downtilt, üblich bei Mobilfunk)

---

## 7. Schnittstellen

### 7.1 Kommandozeilen-Interface

```bash
python -m emf_hotspot.main <omen_file> [OPTIONS]

Pflicht-Argumente:
  omen_file              Pfad zur OMEN-XLS-Datei

Optionen:
  -p, --pattern-dir PATH     Verzeichnis mit Antennendiagrammen (default: .)
  -o, --output-dir PATH      Ausgabeverzeichnis (default: ./output)
  -c, --citygml PATH         Lokale CityGML-Datei (statt Download)
  -r, --radius FLOAT         Suchradius in Metern (default: 100)
  --resolution FLOAT         Fassaden-Auflösung in Metern (default: 0.5)
  -t, --threshold FLOAT      Schwellwert in V/m (default: 5.0)
  --no-download              Keine automatischen Gebäude-Downloads
  --no-viz                   Keine 3D-Visualisierung anzeigen

Beispiele:
  python -m emf_hotspot.main "OMEN R37.xls" -r 50 --resolution 1.0
  python -m emf_hotspot.main "OMEN R37.xls" -c gebaeude.gml --no-viz
```

### 7.2 Python-API

```python
from emf_hotspot.main import analyze_site
from pathlib import Path

results = analyze_site(
    omen_file=Path("OMEN R37.xls"),
    pattern_dir=Path("."),
    output_dir=Path("./output"),
    radius_m=100.0,
    resolution_m=0.5,
    threshold_vm=5.0,
    auto_download_buildings=True,
    visualize=True,
)

# results: List[HotspotResult]
for r in results:
    if r.exceeds_limit:
        print(f"Hotspot: {r.x:.0f}/{r.y:.0f}, E={r.e_field_vm:.2f} V/m")
```

---

## 8. Qualitätssicherung

### 8.1 Validierung

#### Vergleich mit OMEN-Sheets
- **Methode:** Nachrechnung der in O1-O20 berechneten E-Werte
- **Toleranz:** ±10% (aufgrund Rundungen und Diagramm-Interpolation)
- **Testfälle:** Mindestens 10 verschiedene Standorte

#### Grenzfall-Tests
- **Minimaldistanz:** d = 0.1 m (keine Division durch 0)
- **Maximaldistanz:** d = 1000 m (numerische Stabilität)
- **Extreme Winkel:** Azimut ±180°, Elevation ±90°
- **Null-ERP:** E = 0 V/m

#### Geometrie-Tests
- **Point-in-Polygon:** Bekannte Testfälle (Innen/Außen/Rand)
- **Koordinaten-Transformation:** Roundtrip-Test
- **Flächennormalen:** Rechte-Hand-Regel

### 8.2 Performance-Tests

| Test | Konfiguration | Zielwert |
|------|---------------|----------|
| Kleine Anlage | 3 Antennen, 5 Gebäude, 2m Auflösung | < 5 Sekunden |
| Mittlere Anlage | 9 Antennen, 20 Gebäude, 1m Auflösung | < 30 Sekunden |
| Große Anlage | 9 Antennen, 50 Gebäude, 0.5m Auflösung | < 5 Minuten |

### 8.3 Code-Qualität

- **Linting:** flake8, black (automatische Formatierung)
- **Type-Checking:** mypy (optional, für kritische Module)
- **Test-Coverage:** >= 70% für physics/ und geometry/

---

## 9. Offene Punkte und Einschränkungen

### 9.1 Bekannte Limitationen

#### Gebäudedaten-Download
- **Status:** Automatischer Download von swissBUILDINGS3D funktioniert nicht zuverlässig
- **Workaround:** Test-Gebäude oder manuelle CityGML-Datei
- **Geplante Lösung:**
  - Alternative API-Endpunkte evaluieren
  - OSM-Fallback implementieren
  - Manuelle Download-Anleitung dokumentieren

#### Gebäudedämpfung
- **Status:** Material-Dämpfung aus XLS wird nicht angewendet
- **Begründung:** OMEN-Sheets enthalten bereits gedämpfte Werte
- **Implementierung:** Für neue Fassadenpunkte außerhalb bekannter OMEN
  - Option A: Keine Dämpfung (konservativ, Worst-Case)
  - Option B: Pauschal 15 dB (Beton) für alle Gebäude
  - **Aktuell:** Option A

#### Mehrwegeausbreitung
- **Nicht implementiert:**
  - Reflexionen an Gebäuden
  - Beugung über Kanten
  - Streuung
- **Begründung:** Vereinfachtes Modell (wie in OMEN-Sheets)
- **Auswirkung:** Konservative Schätzung (tendenziell höhere E-Werte)

### 9.2 Zukünftige Erweiterungen

#### Phase 2 (geplant)
- [ ] Batch-Verarbeitung mehrerer Standorte: - nein, rausnehmen
- [ ] Automatische PDF-Extraktion aus Standortdatenblättern
- [ ] OCR für Antennendiagramme aus PDF: ja - ableitung der msi-files
- [ ] Web-Interface (Flask/Streamlit)
- [ ] Vergleichsreport: Berechnet vs. OMEN-Sheet
- NEU: erstellung der OMEN R37 clean.xls aus einem Standortdatenblatt.pdf

#### Phase 3 (optional)
- [ ] Integration mit GIS-Software (QGIS-Plugin)
- [ ] Zeitverlauf-Analyse (bei Änderungen)- nein, rausnehmen
- [ ] Mobile App für Feldmessungen - nein, rausnehmen
- [ ] Cloud-Deployment (Azure/AWS)- nein, rausnehmen

### 9.3 Abhängigkeiten von Dritten

| Dienst | Zweck | Kritikalität | Ausfallstrategie |
|--------|-------|--------------|------------------|
| swisstopo | 3D-Gebäude | Hoch | Lokale CityGML-Datei |
| PyPI | Python-Pakete | Mittel | requirements.txt mit Versionen |
| Internet | Download | Niedrig | Offline-Modus mit lokalen Daten |

---

## 10. Abnahmekriterien

### 10.1 Funktionale Abnahme

- [x] Import OMEN-XLS mit 9 Antennen erfolgreich
- [x] Import Antennendiagramme (H/V) mit Interpolation
- [ ] Automatischer Download swissBUILDINGS3D (Kachel Zürich)
- [x] Fassaden-Rasterung mit 0.5m Auflösung
- [x] E-Feld-Berechnung mit Leistungsaddition
- [x] Hotspot-Identifikation (E ≥ 5 V/m)
- [x] CSV-Export (alle Formate)
- [x] GeoJSON-Export (EPSG:2056)
- [x] Heatmap-PNG-Export
- [x] 3D-Visualisierung (PyVista)

### 10.2 Qualitäts-Abnahme

- [ ] Validierung gegen 10 OMEN-Berechnungen (±10% Toleranz)
- [ ] Performance-Test: 10'000 Punkte < 5 Minuten
- [ ] Keine Crashes bei ungültigen Eingaben
- [ ] Alle Docstrings vorhanden
- [ ] README mit Installationsanleitung

### 10.3 Dokumentations-Abnahme

- [x] Pflichtenheft (dieses Dokument)
- [ ] Benutzerhandbuch
- [ ] API-Dokumentation (Sphinx)
- [ ] Beispiel-Workflow mit Screenshots
- [ ] FAQ

---

## 11. Projektorganisation

### 11.1 Meilensteine

| Meilenstein | Status | Datum |
|-------------|--------|-------|
| M1: Datenmodelle und Loader | ✅ Abgeschlossen | 2026-01-08 |
| M2: Geometrie und Physik | ✅ Abgeschlossen | 2026-01-08 |
| M3: Output und CLI | ✅ Abgeschlossen | 2026-01-08 |
| M4: Gebäudedaten-Integration | 🔄 In Arbeit | - |
| M5: Validierung und Tests | ⏳ Offen | - |
| M6: Dokumentation | ⏳ Offen | - |

### 11.2 Deliverables

1. **Software:**
   - Python-Package `emf_hotspot`
   - CLI-Tool
   - requirements.txt

2. **Dokumentation:**
   - Pflichtenheft (dieses Dokument)
   - README.md
   - Installationsanleitung
   - Benutzerhandbuch

3. **Beispieldaten:**
   - OMEN R37 clean.xls
   - Antennendiagramme (Hybrid AIR3268)
   - Test-CityGML (falls verfügbar)

4. **Tests:**
   - Unit-Tests (pytest)
   - Validierungs-Report

---

## 12. Implementierungsstatus (Stand: 2026-01-08)

### 12.1 Vollständig implementierte Features

#### Datenverarbeitung
- ✅ **FA-01**: OMEN XLS-Parser mit Zeilennummer-basiertem Zugriff (Spalte A)
  - Extrahiert Antennendaten (Position, ERP, Azimut, Tilt)
  - Extrahiert 20 OMEN-Positionen mit Gebäudedämpfung (Zeilen 111-113, 370)
  - Mehrsprachig (DE/FR/EN/IT)

- ✅ **FA-02**: Antennendiagramm-Parser
  - CSV-Format mit Semikolon-Trenner
  - Fuzzy Matching für Antennentypen
  - Interpolation für beliebige Winkel

- ✅ **FA-03**: Gebäudedaten-Loader (Multi-Source)
  - ESRI FileGDB (13GB Gesamt-Schweiz) mit GDAL/OGR
  - CityGML 2.0 (Einzelne Kacheln)
  - Automatische Quellenwahl: GDB → CityGML → Download
  - WallSurface + RoofSurface Parsing

#### Geometrie und Physik
- ✅ **FA-04**: Fassaden-Sampling
  - Konfigurierbare Auflösung (default: 0.5m)
  - Point-in-Polygon mit Ray-Casting
  - Vertikale Flächen-Erkennung (|normal.z| < 0.7)

- ✅ **FA-11**: Dach-Sampling (NEU)
  - CityGML RoofSurface-Parsing
  - Geometrische Erkennung (|normal.z| > 0.5)
  - Kombinierte Methode für maximale Abdeckung

- ✅ **FA-05**: E-Feld-Berechnung
  - Freiraumdämpfung: E = sqrt(30*ERP)/d
  - Antennendiagramm-Dämpfung
  - Inkohärente Leistungsaddition: E_total = sqrt(Σ E_i²)

#### Output
- ✅ **FA-06**: CSV-Export
  - hotspots.csv mit Antenna-Contributions
  - alle_punkte.csv (vollständiges Raster)
  - pro_gebaeude.csv (aggregiert)
  - zusammenfassung.csv (Statistiken)

- ✅ **FA-07**: GeoJSON-Export (EPSG:2056)

- ✅ **FA-08**: Heatmap-Visualisierung (ERWEITERT)
  - 2D-Draufsicht mit Farbskala
  - **NEU**: Transparenter Hintergrund (Alphakanal)
  - **NEU**: Antennenstandort-Marker (blauer Stern)
  - **NEU**: Azimut-Pfeile für Sektoren
  - **NEU**: Maßstab 1:1000 @ 300 DPI (druckgenau)
  - **NEU**: Maßstabsbalken (50m)

- ✅ **FA-10**: 3D-Visualisierung (PyVista)
  - Point-Cloud mit Farbskala
  - Gebäude als transparente Meshes
  - Antennenmarker als Kegel

#### Konfiguration
- ✅ **config.json**
  - Alle Parameter extern konfigurierbar
  - Auflösung, Radius, Grenzwert
  - Dächer ein/aus, Maßstab, DPI
  - WMS-URLs, Cache-Verzeichnisse

### 12.2 In Arbeit

- 🔄 **FA-09**: OMEN-Validierung
  - E-Feld an OMEN-Punkten nachrechnen
  - Abweichungen zur XLS melden
  - CSV-Bericht erstellen

- 🔄 **Erweiterte CSV-Exports**
  - Z-Maximum-Spalte in hotspots.csv
  - OMEN-Nr in pro_gebaeude.csv
  - Postadresse aus Gebäude-Register

### 12.3 Geplant

- ⏳ **WMS-Integration**
  - Satellitenbild von geo.admin.ch
  - Straßenkarte als Hintergrund
  - Automatischer Download für Antennenposition

- ⏳ **NIS-Plan-Overlay**
  - PDF als Hintergrund-Layer
  - Georeferenzierung
  - Transparente Heatmap darüber

- ⏳ **Amtliche Vermessung**
  - Unbebaute Grundstücke in Bauzone als OMEN
  - WFS-API für Parzellen-Daten
  - Automatische OMEN-Generierung

- ⏳ **Erweiterte Dämpfung**
  - Fenster-Erkennung (wenn in swissBUILDINGS3D verfügbar)
  - Material-basierte Dämpfung
  - Mehrfach-Reflexionen

### 12.4 Bekannte Einschränkungen

1. **Gebäudedaten-Download**: swisstopo-API funktioniert nicht (404)
   - **Workaround**: Manueller Download oder Gesamt-GDB (13GB)

2. **Gebäudedämpfung**: Nur aus OMEN-Sheets verfügbar
   - Für neue Fassadenpunkte: 0 dB (konservativ, Worst-Case)

3. **Fenster-Erkennung**: Nicht in swissBUILDINGS3D enthalten
   - Annahme: Alle Fassaden haben Fenster → 0 dB Dämpfung

4. **GDB-Support**: Benötigt GDAL/OGR
   - Installation: `conda install -c conda-forge gdal`

### 12.5 Test-Ergebnisse

**Testfall: Zürich, Wehntalerstrasse 464**
- Standort: 2681044 / 1252266 / 462.2
- Antennen: 9 (3 Masten × 3 Sektoren)
- Frequenzen: 700-900, 1400-2600, 3600 MHz

**Mit realen Gebäudedaten (27 Gebäude, Auflösung 1m):**
- Geprüfte Punkte: 28,786
- Hotspots: 1,822 (6.33%)
- Max. Feldstärke: **31.46 V/m** (6.3× NISV)
- Betroffene Gebäude: 3

**Mit Dächern (Auflösung 2m):**
- Geprüfte Punkte: 9,415
- Hotspots: 568 (6.03%)
- Max. Feldstärke: **48.84 V/m** (9.8× NISV)

### 12.6 Änderungen gegenüber Pflichtenheft v1.0

1. **Dach-Support hinzugefügt** (nicht in Original-Spec)
   - Berücksichtigt RoofSurface aus CityGML
   - Geometrische Erkennung als Fallback

2. **GDB-Support hinzugefügt** (13GB Gesamt-Schweiz)
   - ESRI FileGDB mit GDAL/OGR
   - Automatische Kachel-Extraktion

3. **Heatmap deutlich verbessert**
   - Transparenter Hintergrund für Overlays
   - Antennenmarker und Azimut-Pfeile
   - Exakter Maßstab 1:1000 @ 300 DPI

4. **OMEN-Position-Extraktion**
   - Automatisches Auslesen aus O1-O20 Sheets
   - Gebäudedämpfung aus Zeile 370

5. **Konfigurationssystem**
   - `config.json` für alle Parameter
   - Keine Hardcoded-Werte mehr

---

## Anhang A: Glossar

| Begriff | Bedeutung |
|---------|-----------|
| **NISV** | Verordnung über den Schutz vor nichtionisierender Strahlung |
| **OMEN** | Ort mit empfindlicher Nutzung (Wohnungen, Schulen, etc.) |
| **StDB** | Standortdatenblatt |
| **AGW** | Anlagegrenzwert (5-6 V/m je nach Frequenz) |
| **IGW** | Immissionsgrenzwert (58-87 V/m) |
| **ERP** | Equivalent Radiated Power [W] |
| **LV95** | Schweizer Landesvermessung 1995 (EPSG:2056) |
| **Azimut** | Horizontaler Richtungswinkel (0° = Nord) |
| **Tilt** | Vertikaler Neigungswinkel (negativ = Downtilt) |
| **CityGML** | XML-basiertes 3D-Stadtmodell-Format |

---

## Anhang B: Referenzen

1. **NISV** (SR 814.710): https://www.fedlex.admin.ch/eli/cc/2000/329/de
2. **swissBUILDINGS3D 3.0 Beta**: https://www.swisstopo.admin.ch/en/landscape-model-swissbuildings3d-3-0-beta
3. **OMEN-Template**: Verein 5Gfrei.ch (http://www.5Gfrei.ch)
4. **BAFU - Mobilfunkanlagen**: https://www.bafu.admin.ch/mobilfunk

---

**Änderungshistorie:**

| Version | Datum | Autor | Änderung |
|---------|-------|-------|----------|
| 1.0 | 2026-01-08 | Claude Code | Initiale Erstellung |

---

**Genehmigung:**

| Rolle | Name | Datum | Unterschrift |
|-------|------|-------|--------------|
| Auftraggeber | | | |
| Projektleiter | | | |
| Technischer Lead | | | |
