# Changelog - EMF-Hotspot-Finder

## [2.2] - 2026-01-13

### Added
- **User Interaction Utilities:** Neue `utils.py` mit farbigen Dialogen
  - `ask_yes_no()` - Farbige Ja/Nein-Fragen mit Standardwerten
  - `warn_fallback()` - Farbige Warnungen ohne Frage
  - `error_and_exit()` - Farbige Fehlermeldungen mit Exit
- **msi-files/README.md:** Dokumentation für MSI-Antennendiagramme
  - Erklärung der Ordner-Struktur
  - Dateiformat-Spezifikation
  - Planung für zukünftige Multi-Typ-Datenbank
- **Detaillierter CSV-Export:** `hotspots_detailliert.csv`
  - Für jeden Hotspot-Punkt: E-Feld pro Antenne
  - **Kritischer Tilt:** Tatsächlich verwendeter Tilt-Winkel (Worst-Case)
  - **Distanz:** Entfernung Antenne → Punkt
  - **Dämpfungen:** H- und V-Dämpfung aus Antennendiagramm
  - Format: Separate Spalten pro Antenne (ant1_e_vm, ant1_tilt_deg, ant1_dist_m, ...)
- **AntennaContribution Model:** Strukturierte Datenklasse statt Tupel
  - Bessere Code-Dokumentation und Type-Hints
  - Leichter erweiterbar für zukünftige Features
- **Gebäude-Validierung:** Neues Analyse-Modul `analysis/building_validation.py`
  - Erkennt hohe Räume (Altbauten, Industriehallen)
  - Prüft NISV-Formel vs Realität
  - Identifiziert fehlende OMEN-Geschosse
  - Output: `gebaeude_validierung.csv`
- **ROADMAP_VERBESSERUNGEN.md:** Strukturierter Plan für zukünftige Features
  - MSI-Kalibrierung (-4% Abweichung)
  - Virtuelle OMEN auf Bauplätzen
  - Prioritäten und Zeitschätzungen

### Changed
- **Keine automatischen Fallbacks mehr:** Alle kritischen Fallbacks fragen jetzt nach
  - ODS-Pattern nicht gefunden → Frage ob Standard-Patterns verwenden
  - Lokale Gebäudedaten nicht gefunden → Frage ob Download erlauben
  - STAC-Download fehlgeschlagen → Frage ob WFS-Alternative versuchen
  - GDB ohne GDAL → Klare Fehlermeldung mit Lösungsoptionen
  - DWG-Format → Klare Fehlermeldung mit Alternativen
- **msi-files/ als Standard:** `--pattern-dir` default ist jetzt `msi-files/`
  - Suchreihenfolge: 1. msi-files/, 2. --pattern-dir, 3. input/
  - ODS-Dateien werden automatisch in msi-files/ gefunden

### Improved
- **Bessere Fehlermeldungen:** Alle Error-Meldungen mit konkreten Lösungswegen
- **Farbige Ausgaben:** Gelb für Warnungen, Rot für Fehler, Grün für Erfolg
- **Keine stillen Überraschungen:** Benutzer wird vor jeder wichtigen Entscheidung gefragt
- **Intelligente ODS-Suche:** Findet Dateien in msi-files/ auch ohne --pattern-dir
- **Terminal-Output:** Zeigt jetzt Tilt-Bereich statt nur Referenzwert
  - Vorher: `Tilt 0.0°` (irreführend)
  - Jetzt: `Tilt -12° bis -2° (Worst-Case-Suche)` (klar)
- **CSV-Export:** Kompaktformat mit allen Details in einer Spalte
  - Format: `ant1:E=0.5,tilt=-12,dist=50;ant2:E=0.3,tilt=-10,dist=75`
- **Nachvollziehbarkeit:** Jeder Hotspot dokumentiert, mit welchem Tilt er berechnet wurde
- **EGID/Adressen:** Jetzt in ALLEN CSV-Exporten (nicht nur OMEN-Gebäude)

### Known Issues
- **MSI-Dämpfung:** Systematische Unterschätzung von -4%
  - `omen_validierung.csv` zeigt: E_calculated im Mittel 4% unter E_expected
  - MSI-Dateien zu großzügig (zu hohe Dämpfungswerte)
  - **Geplante Lösung:** Kalibrierung der MSI-ODS-Dateien (siehe ROADMAP)

---

## [2.1] - 2026-01-11

### Fixed
- **swissBUILDINGS3D API:** Ersetzt fehlerhafte alte API durch STAC API
  - Alte URL gab HTTP 404
  - Neue STAC API: `https://data.geo.admin.ch/api/stac/v1/`
  - Automatische Koordinatenkonvertierung LV95 → WGS84

### Added
- **Multi-Format-Support:** CityGML, GDB, DWG-Erkennung
- **LV95 → WGS84 Konvertierung:** Neue Funktion `_lv95_to_wgs84()`
- **Intelligente Asset-Auswahl:** Priorität CityGML > GDB > DWG
- **Hilfreiche Fehlermeldungen:** Workaround-Anleitung bei GDB-Format
- **Dokumentation:** `STAC_API_STATUS.md` mit vollständiger Anleitung

### Changed
- **Kachelgröße korrigiert:** 1km × 1km statt 10km × 10km
- **Download-Funktion:** `_download_tile()` nutzt jetzt STAC API
- **User-Agent hinzugefügt:** "EMF-Hotspot-Finder/2.0" für alle API-Requests
- **Cache-Struktur:** Unterstützt `.gml` und `.gdb.zip` Dateien

### Known Issues
- ~~**GDAL-Installation:** Konflikt mit miniconda's libstdc++~~ → ✅ **GELÖST**
  - ~~GDB-Format kann nicht geparst werden~~
  - **Lösung:** Intelligente Item-Auswahl findet automatisch CityGML-Alternativen
  - STAC API liefert oft mehrere Jahrgänge, nicht alle haben CityGML
  - Code bevorzugt jetzt automatisch neuestes Item MIT CityGML

### Details
**Datei:** `emf_hotspot/loaders/building_loader.py`

**Vor:**
```python
SWISSTOPO_DOWNLOAD_URL = (
    "https://data.geo.admin.ch/ch.swisstopo.swissbuildings3d_3_0/"
    "swissbuildings3d_3_0_{tile_id}/swissbuildings3d_3_0_{tile_id}_citygml.zip"
)
```
→ **Fehler:** HTTP 404

**Nach:**
```python
STAC_API_BASE = "https://data.geo.admin.ch/api/stac/v1"
STAC_COLLECTION_ID = "ch.swisstopo.swissbuildings3d_3_0"
```
→ **Funktioniert:** Download via STAC Items

**Intelligente Item-Auswahl:**
- Durchsucht alle verfügbaren Jahrgänge
- Bevorzugt neuestes Item MIT CityGML
- Fallback: Neuestes Item mit GDB

**Test-Ergebnisse:**

| Standort | Jahrgang | Format | Download | Parsing | Status |
|----------|----------|--------|----------|---------|--------|
| Zürich (input/) | 2019 | CityGML | ✅ | ✅ | **Funktioniert perfekt** |
| Uznach (input2/) | 2022 | CityGML | ✅ | ✅ | **Funktioniert perfekt** |

**Früher vs. Jetzt:**
- ❌ Alt: Uznach → 2019 GDB → GDAL benötigt → Fehler
- ✅ Neu: Uznach → 2022 CityGML → Funktioniert automatisch!

---

## [2.0] - 2026-01-11

### Added
- **Virtual Environment Setup:** Fish-Shell & Bash Support
- **Umfassende Dokumentation:**
  - `documentation/BENUTZERHANDBUCH.md` - Vollständige Anleitung
  - `documentation/DATEI_UEBERSICHT.md` - Schnellreferenz
  - `documentation/GEODATEN_UEBERSICHT.md` - geo.admin.ch APIs
  - `documentation/SETUP_ENVIRONMENT.md` - venv Setup
- **Fish-Shell-Kompatibilität:** setup_venv.fish, activate.fish
- **Environment Check:** check_environment.py mit Shell-Erkennung

### Changed
- **pro_gebaeude.csv:** Neue Spalten
  - `egid` - Eidgenössischer Gebäudeidentifikator
  - `address` - Gebäudeadresse von geo.admin.ch
  - `num_floors` - Geschosszahl (height_m / 3.0)
  - `height_m` - Gebäudehöhe in Metern
- **OMEN-Nummerierung:** 1:1-Mapping (jedes OMEN → ein Gebäude)
- **hotspots_marker_map.png:** Bereinigtes Layout
  - Keine Achsenbeschriftungen
  - Keine Colorbar
  - Legende rechts außerhalb

### Fixed
- **ParaView Visualisierung:** Voxel-Export für bessere Sichtbarkeit
- **Projekt-Organisation:** Dokumentation in `documentation/` Ordner

---

## [1.0] - 2025-12

### Initial Release
- OMEN-Excel-Parser
- Antennendiagramm-Integration (ODS/CSV)
- CityGML-Loader (swissBUILDINGS3D)
- E-Feld-Berechnung mit Worst-Case-Tilt
- CSV/VTK/PNG-Exports
- 2D-Heatmaps auf geo.admin.ch Basiskarten
- 3D-Visualisierung (PyVista/ParaView)
