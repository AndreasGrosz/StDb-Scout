# StDb-Scout

**NISV-Grenzwertprüfung für Anwohner von Mobilfunkanlagen**

StDb-Scout analysiert Standortdatenblätter (StDB) von Mobilfunkbetreibern und berechnet E-Feldstärken an Gebäudefassaden mit 3D-Gebäudedaten von swissTopo.

## Features

### ✅ Implementiert

- **3D-Gebäudedaten**: Automatischer Download von swissBUILDINGS3D 3.0
- **Antennendiagramme**: Realistische Abstrahlcharakteristik (ITU-R/3GPP)
- **E-Feldstärke-Berechnung**: Freiraumdämpfung + Antennengewinn
- **NISV-Grenzwertprüfung**: 5 V/m für empfindliche Nutzung
- **Line-of-Sight-Analyse**: 3D Ray-Casting mit Gebäudedämpfung (12 dB/Gebäude)
- **Worst-Case-Tilt-Suche**: Findet ungünstigsten Antennenwinkel
- **Virtuelle Gebäude**: Automatische Berechnung für unbebaute Baugrundstücke
- **Katasterparzellen**: Integration von geo.admin.ch Parzellendaten
- **Hotspot-Identifikation**: Pro Gebäude Maximum + Koordinaten
- **CSV-Export**: Detaillierte Ergebnislisten mit EGID/Adressen
- **3D-Visualisierung**: ParaView VTK/VTM Export
- **Heatmaps**: Farbcodierte Karten mit Swisstopo-Basemap
- **OMEN-Validierung**: Vergleich mit StDB-Berechnungen
- **Projekt-basierte Outputs**: Automatische Ordnerstruktur nach Adresse

### 🔧 In Planung

- Worst-Case-Azimut-Suche (derzeit fix aus StDB)
- Multi-Standort-Batch-Verarbeitung
- Web-Interface für Anwohner

## Installation

```bash
cd /path/to/stdb-scout
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Verwendung

```bash
python -m emf_hotspot.main "input/OMEN R37 clean.xls"
```

### Optionen

```
--radius METER          Untersuchungsradius (default: 200m)
--resolution METER      Fassaden-Auflösung (default: 1.0m)
--threshold VM          NISV-Grenzwert (default: 5.0 V/m)
--citygml FILE          Lokale CityGML-Datei statt Auto-Download
--viz                   3D-Visualisierung aktivieren (benötigt X11)
--no-download           Gebäude-Download deaktivieren
```

## Eingabedaten

### StDB (Standortdatenblatt)
- Format: Excel XLS
- Quelle: Mobilfunkbetreiber (Swisscom, Sunrise, Salt)
- Enthält: Antennenkoordinaten, ERP, Azimut, Tilt, OMEN-Punkte

### Antennendiagramme
- Format: CSV (Horizontal + Vertikal)
- Quelle: Hersteller (z.B. Ericsson AIR3268)
- Ablage: `msi-files/` oder `input/`

## Ausgabedaten

Alle Dateien werden in `output/{Adresse}/` gespeichert:

### CSV-Dateien
- `hotspots_aggregated.csv` - Pro Gebäude ein Eintrag mit Maximum
- `hotspots_detailliert.csv` - Alle Punkte >= Grenzwert
- `alle_punkte.csv` - Sämtliche berechneten Messpunkte
- `gebaeude_uebersicht.csv` - Gebäudeliste mit NISV-Formel-Vergleich
- `omen_validierung.csv` - Abweichungen zu StDB-Werten

### 3D-Visualisierung
- `paraview-*.vtm` - Multi-Block VTK für ParaView
- `PARAVIEW_ANLEITUNG.md` - Kurzanleitung für ParaView

### Heatmaps
- `heatmap.png` - Farbcodierte Karte mit Swisstopo-Basemap
- `hotspots_marker_map.png` - Gebäude-Marker mit E-Werten

### OMEN-Sheets
- `NeuOmen.ods` - Neue OMEN-Punkte für StDB-Update

## Virtuelle Gebäude

StDb-Scout erstellt automatisch **virtuelle Gebäude für unbebaute Parzellen**:

1. Lädt Katasterparzellen von geo.admin.ch
2. Identifiziert leere Parzellen (ohne swissBUILDINGS3D-Gebäude)
3. Generiert virtuelles Gebäude (3m Grenzabstand, Höhe vom höchsten Nachbarn)
4. Berechnet virtuelle OMEN-Punkte an Fassaden
5. Integriert in Hotspot-Analyse

**Verwendung für Bauanträge:**
- Zeigt potenzielle Hotspots für geplante Neubauten
- Worst-Case-Szenario für Einsprachen
- CSV-Kennzeichnung: EGID beginnt mit "VIRTUAL_"

Siehe: [VIRTUELLE_GEBAEUDE.md](VIRTUELLE_GEBAEUDE.md)

## Technische Details

### E-Feldstärke-Berechnung
```
E [V/m] = sqrt(30 * ERP [W]) / Distanz [m]
        × 10^(-A_horizontal/20)
        × 10^(-A_vertikal/20)
        × 10^(-A_gebäude/20)  [falls LOS blockiert]
```

### Leistungsaddition
```
E_total = sqrt(sum(E_i²))  [über alle Antennen]
```

### Gebäudedämpfung (LOS)
- 12 dB pro Gebäude im Line-of-Sight (ITU-R P.2040)
- 3D Ray-Casting mit Möller-Trumbore Algorithmus
- Dämpfung wird VOR Hotspot-Identifikation angewendet

### Grenzabstand (virtuelle Gebäude)
- 3m zu allen Parzellengren zen
- Shapely `buffer(-3.0)` Operation
- Höhe vom höchsten Nachbarn (100m Umkreis)

## Abhängigkeiten

- Python 3.9+
- NumPy, SciPy, Matplotlib
- pandas, openpyxl (Excel)
- PyVista (3D-Visualisierung)
- GDAL/OGR (CityGML)
- shapely (Polygon-Operationen)
- Pillow (Image-Processing)

## Quellen

- **swissBUILDINGS3D 3.0**: [swisstopo.admin.ch](https://www.swisstopo.admin.ch/swissbuildings3d)
- **Kataster**: [geo.admin.ch Amtliche Vermessung](https://www.geo.admin.ch/de/amtliche-vermessung)
- **NISV**: [SR 814.710](https://www.admin.ch/opc/de/classified-compilation/19996141/index.html)
- **ITU-R P.2040**: Gebäudedämpfung

## Lizenz

Für private und non-profit Verwendung durch Mobilfunkkritiker und Anwohner.

---

**Developed für kritische Bürger. Powered by OpenData.**
