# 3D-Visualisierung - Setup und Troubleshooting

## Empfohlene Lösung: VTK-Export für Paraview ⭐

**NEU:** Die beste Lösung für Server ohne Display ist der **VTK-Export**:

```bash
python3 -m emf_hotspot.main 'input/OMEN R37 clean.xls' \
  -c 'gebaeude_citygml/...' \
  -p msi-files \
  -o output \
  --radius 100 \
  --resolution 2.0

# Ergebnis: output/ergebnisse.vtm (VTK MultiBlock)
```

**Vorteile:**
- ✅ Keine OpenGL-Probleme auf Headless-Servern
- ✅ Offline-Visualisierung auf lokalem Desktop
- ✅ Paraview kann 20+ Millionen Punkte flüssig darstellen
- ✅ Professionelle Post-Processing-Tools
- ✅ Python-Scripting mit PyVista möglich

**Visualisierung (lokal):**
```bash
# VTM-Datei vom Server kopieren
scp user@server:/path/output/ergebnisse.vtm .

# Mit Paraview öffnen
paraview ergebnisse.vtm
```

Siehe [PARAVIEW_ANLEITUNG.md](PARAVIEW_ANLEITUNG.md) für Details.

---

## Problem: OpenGL-Fehler auf Headless-Servern

Wenn Sie die **interaktive** 3D-Visualisierung auf einem Server ohne Display (SSH, Remote) ausführen, erhalten Sie möglicherweise:

```
vtkXOpenGLRenderWindow: Could not find a decent config
SIGSEGV (Adressbereichsfehler)
```

**Hinweis:** Die interaktive Visualisierung ist seit v2.0 standardmäßig **deaktiviert**. Verwenden Sie stattdessen den VTK-Export (siehe oben).

## Lösungen für interaktive Visualisierung

### Option 1: Nur Screenshot (empfohlen für Server)

Das Tool erstellt automatisch nur einen Screenshot, wenn kein Display verfügbar ist:

```bash
python3 -m emf_hotspot.main 'input/OMEN R37 clean.xls' \
  -c 'gebaeude_citygml/...' \
  -p msi-files \
  -o output \
  --radius 100 \
  --resolution 2.0  # Wichtig: 2m statt 0.5m!

# Ergebnis: output/visualisierung_3d.png
```

### Option 2: Xvfb (Virtual Framebuffer)

Installieren Sie Xvfb für virtuelles Display:

```bash
# Ubuntu/Debian
sudo apt-get install xvfb

# Dann:
xvfb-run -a python3 -m emf_hotspot.main '...'
```

### Option 3: OSMesa (Software-Rendering)

Installieren Sie PyVista mit OSMesa-Support:

```bash
# Mit conda (empfohlen)
conda install -c conda-forge pyvista osmesa

# Oder mit pip
pip install pyvista[osmesa]
```

### Option 4: Lokal mit X11-Forwarding

Für interaktive Ansicht über SSH:

```bash
# SSH mit X11-Forwarding
ssh -X user@server

# Dann normal ausführen
python3 -m emf_hotspot.main '...'
```

## Performance-Tipp: Auflösung anpassen

**Problem:** 150.000 Punkte bei 0.5m Auflösung

**Lösung:** Verwenden Sie 2.0m für Übersicht:

```bash
# Standard (in config.json geändert auf 2.0m)
python3 -m emf_hotspot.main '...'  # → 9.415 Punkte

# Explizit setzen
python3 -m emf_hotspot.main '...' --resolution 2.0

# Für Detailanalyse kritischer Gebäude
python3 -m emf_hotspot.main '...' --resolution 0.5  # → 150.000 Punkte
```

**Empfehlung:**
- **Screening/Übersicht:** 2.0m (9k Punkte)
- **Detailanalyse:** 1.0m (38k Punkte)
- **Feinanalyse:** 0.5m (150k Punkte) - nur für kritische Bereiche

## Ausgabedateien

Die 3D-Visualisierung wird in `output/visualisierung_3d.png` gespeichert und zeigt:

- **Point-Cloud** mit Farbskala (Grün → Gelb → Rot)
- **Gebäude** (Wände: lightgray, Dächer: darkgray)
- **Antennenmasten** als blaue Zylinder
- **Antennen** als farbcodierte Kegel:
  - Cyan: 700-900 MHz
  - Orange: 1400-2600 MHz
  - Purple: 3600 MHz
- **Hotspots** als rote Punkte hervorgehoben
- **Farblegende** rechts

## Alternative: 2D-Heatmap

Wenn die 3D-Visualisierung nicht funktioniert, nutzen Sie die 2D-Heatmap:

```bash
# Mit --no-viz überspringen
python3 -m emf_hotspot.main '...' --no-viz

# Ergebnis: output/heatmap.png (2D, Maßstab 1:1000)
```

Die Heatmap ist:
- ✅ Druckfertig (300 DPI, 1:1000)
- ✅ Transparent (für Overlays)
- ✅ Mit Antennenmarker + Azimut-Pfeilen
- ✅ Funktioniert immer (kein OpenGL nötig)

## Test

```bash
# Minimaler Test
python3 -c "
import pyvista as pv
pv.start_xvfb()
sphere = pv.Sphere()
plotter = pv.Plotter(off_screen=True)
plotter.add_mesh(sphere)
plotter.screenshot('test_3d.png')
print('Erfolg! test_3d.png erstellt.')
"
```

Wenn das funktioniert, sollte auch die Hauptanalyse funktionieren.
