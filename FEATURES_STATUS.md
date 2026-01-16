# StDb-Scout - Feature Status

## ✅ Produktiv (Aktiv)

### Basis-Funktionen
- ✅ 3D-Gebäudedaten (swissBUILDINGS3D 3.0)
- ✅ Antennendiagramme (ITU-R/3GPP)
- ✅ E-Feldstärke-Berechnung
- ✅ NISV-Grenzwertprüfung (5 V/m)
- ✅ Line-of-Sight-Analyse (3D Ray-Casting)
- ✅ Worst-Case-Tilt-Suche
- ✅ Hotspot-Identifikation
- ✅ CSV-Export mit EGID/Adressen
- ✅ 3D-Visualisierung (ParaView VTK/VTM)
- ✅ Heatmaps mit Swisstopo-Basemap
- ✅ OMEN-Validierung
- ✅ Projekt-basierte Outputs (nach Adresse)
- ✅ EGID-Adress-Validierung (Koordinaten-basiert)

## 🔧 Implementiert aber deaktiviert

### Virtuelle Gebäude (Baugrundstücke)
**Status:** Code fertig, temporär deaktiviert
**Grund:** API-Performance (geo.admin.ch Parzellen-Abruf dauert 5-10 Min)
**Aktivierung:** In `main.py` Zeile 219 setzen: `enable_virtual = True`

**Was es macht:**
- Lädt Katasterparzellen von geo.admin.ch
- Identifiziert leere Parzellen (ohne swissBUILDINGS3D-Gebäude)
- Generiert virtuelles Gebäude (3m Grenzabstand, Höhe vom höchsten Nachbarn)
- Berechnet virtuelle OMEN-Punkte an Fassaden
- Zeigt worst-case Szenarien für zukünftige Neubauten

**Verwendung:**
```python
# emf_hotspot/main.py Zeile 219
enable_virtual = True  # Aktivieren
```

**Output:**
- CSV: EGID beginnt mit "VIRTUAL_"
- VTK: Separate Layer für virtuelle Gebäude

### Terrain-Visualisierung (3D-Untergrund)
**Status:** Code fertig, temporär deaktiviert
**Grund:** Erhöht Ladezeit, optional für Visualisierung
**Aktivierung:** In `visualization.py` Zeile 1403 setzen: `enable_terrain = True`

**Was es macht:**
- Lädt SwissALTI3D Höhenmodell (2m Resolution)
- Erstellt 3D-Terrain-Mesh unter Gebäuden
- Wie im Beispiel-Bild: Texturierter Untergrund

**Verwendung:**
```python
# emf_hotspot/output/visualization.py Zeile 1403
enable_terrain = True  # Aktivieren
```

**Output:**
- VTK: "Terrain"-Layer in MultiBlock
- ParaView: Einfärbung nach Höhe (Elevation_m)

## 📊 Performance-Hinweise

### Ohne optionale Features (Standard)
- Laufzeit: ~2-3 Min
- Output: ~36 MB

### Mit virtuellen Gebäuden
- Laufzeit: +5-10 Min (Parzellen-API)
- Output: +10-20% mehr Messpunkte

### Mit Terrain-Visualisierung
- Laufzeit: +2-3 Min (Höhenmodell-Download)
- Output: +5-10 MB (Terrain-Mesh)

## 🚀 Zukünftige Optimierungen

### Virtuelle Gebäude
- [ ] Parzellen-Cache implementieren (lokal speichern)
- [ ] Async API-Calls (parallel statt sequentiell)
- [ ] CLI-Parameter: `--enable-virtual-buildings`

### Terrain
- [ ] Terrain-Cache implementieren
- [ ] Auflösung anpassbar machen (2m/5m/10m)
- [ ] CLI-Parameter: `--enable-terrain`

### Batch-Mode
- [ ] Mehrere Standorte in einem Lauf
- [ ] Parallele Verarbeitung

## 📝 Dokumentation

- **README.md** - Hauptdokumentation
- **VIRTUELLE_GEBAEUDE.md** - Detaillierte Anleitung für virtuelle Gebäude
- **PARAVIEW_ANLEITUNG.md** - Wird pro Analyse erstellt

## 🔗 Quellen

Alle Features basieren auf OpenData:
- **swissBUILDINGS3D 3.0**: [swisstopo.admin.ch](https://www.swisstopo.admin.ch/swissbuildings3d)
- **SwissALTI3D**: [swisstopo.admin.ch](https://www.swisstopo.admin.ch/swissalti3d)
- **Kataster**: [geo.admin.ch](https://www.geo.admin.ch/de/amtliche-vermessung)
- **NISV**: [SR 814.710](https://www.admin.ch/opc/de/classified-compilation/19996141/index.html)
