# Paraview-Visualisierung

## Export

Das Tool exportiert automatisch eine **VTK MultiBlock Datei** (`ergebnisse.vtm`) mit:

- **Results** (9415 Punkte): E-Feld Berechnungen mit Attributen:
  - `E_field_Vm`: E-Feldstärke [V/m]
  - `Exceeds_Limit`: 1=Hotspot (≥5V/m), 0=normal
  - `Building_ID`: Gebäude-Zuordnung

- **Antennas** (9 Punkte): Antennenpositionen mit:
  - `Antenna_ID`: Antennennummer
  - `Frequency_MHz`: Mittenfrequenz
  - `Power_W`: ERP Leistung
  - `Azimuth_deg`: Abstrahlrichtung

- **Buildings** (27 Gebäude): 3D-Geometrie mit:
  - `Type`: 0=Wand, 1=Dach

## Installation

```bash
# Ubuntu/Debian
sudo apt install paraview

# macOS
brew install --cask paraview

# Windows
# Download von https://www.paraview.org/download/
```

## Öffnen

```bash
paraview output/ergebnisse.vtm
```

Oder: In Paraview GUI → File → Open → `ergebnisse.vtm`

## Visualisierung - Schritt für Schritt

### 1. E-Feld-Punkte darstellen

1. Im Pipeline Browser: **Results** auswählen
2. Klick auf **Apply** (grüner Haken)
3. Representation → **Point Gaussian**
4. Coloring → **E_field_Vm**
5. Edit Colormap:
   - Preset: **Warm to Cool** oder **Rainbow Desaturated**
   - Data Range: 0 bis 10 V/m
   - Check "Use Log Scale" für besseren Kontrast

### 2. Hotspots hervorheben

1. Filter → **Threshold** auf Results anwenden:
   - Scalar: `E_field_Vm`
   - Minimum: `5.0` (NISV-Grenzwert)
   - Apply
2. Representation: **Points** oder **Point Gaussian**
3. Color: Rot
4. Point Size: 5

### 3. Gebäude anzeigen

1. Im Pipeline Browser: **Buildings** auswählen
2. Apply
3. Representation: **Surface**
4. Opacity: 0.3 (transparent)
5. Color: Lightgray

### 4. Antennen markieren

1. Im Pipeline Browser: **Antennas** auswählen
2. Apply
3. Representation: **3D Glyphs**
4. Glyph Type: **Sphere** oder **Cone**
5. Scale Factor: 5.0
6. Color by: **Frequency_MHz**

### 5. Kamera-Einstellung

- **Orthographic Projection**: View → Camera → Projection → Parallel
- **Top View**: Y-Achse nach oben (Reset Camera)
- **Rotate**: Linke Maustaste
- **Pan**: Shift + Linke Maustaste
- **Zoom**: Mausrad

## Erweiterte Analysen

### Schnittebenen (Slices)

1. Filter → **Slice** auf Results:
   - Plane: Z Normal (horizontal)
   - Origin: [0, 0, 465] (Erdgeschoss-Höhe)
2. Color by E_field_Vm

### Konturlinien (Iso-Contours)

1. Filter → **Contour** auf Results:
   - Contour By: E_field_Vm
   - Value Range: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 V/m

### Volumen-Rendering (für dichte Gitter)

1. Representation → **Volume**
2. Transfer Function Editor öffnen
3. Opacity mapping anpassen

## Performance-Tipps

- **Große Datensätze (>1M Punkte)**:
  - Decimation Filter verwenden (z.B. 10:1)
  - Level of Detail (LOD) aktivieren

- **Rendering beschleunigen**:
  - View → Render View → Use Offscreen Rendering
  - Edit → Settings → Render View → Remote/Parallel Rendering

## Export aus Paraview

### Screenshot
- File → Save Screenshot → PNG (300 DPI)
- Transparent Background: Check

### Animation
- View → Animation View
- Camera → Orbit (360°)
- File → Save Animation → AVI/MP4

### Daten exportieren
- File → Save Data → CSV (für Tabellen)
- File → Export Scene → X3D/VRML (für Web)

## Python-Scripting

Paraview kann auch per Python ferngesteuert werden:

```python
from paraview.simple import *

# VTM laden
reader = XMLMultiBlockDataReader(FileName='output/ergebnisse.vtm')
reader.UpdatePipeline()

# Results extrahieren
results = ExtractBlock(Input=reader)
results.BlockIndices = [0]  # Results = Block 0

# Threshold für Hotspots
threshold = Threshold(Input=results)
threshold.Scalars = ['POINTS', 'E_field_Vm']
threshold.LowerThreshold = 5.0

# Screenshot
view = GetActiveView()
SaveScreenshot('hotspots.png', view, ImageResolution=[1920, 1080])
```

## Troubleshooting

**Problem**: Punkte nicht sichtbar
- Lösung: Representation → Point Gaussian, Gaussian Radius erhöhen

**Problem**: Gebäude verdecken Punkte
- Lösung: Buildings Opacity auf 0.2 reduzieren, oder ausblenden

**Problem**: Farben unpassend
- Lösung: Edit Colormap → Preset wählen (Jet, Rainbow, Viridis)

**Problem**: Zu langsam bei großen Daten
- Lösung: Extract Subset Filter verwenden (z.B. nur jeder 5. Punkt)

## Alternative: PyVista (Python)

Für Skripting ohne GUI:

```python
import pyvista as pv

# Laden
mesh = pv.read('output/ergebnisse.vtm')

# Plotten
plotter = pv.Plotter()
plotter.add_mesh(
    mesh['Results'],
    scalars='E_field_Vm',
    cmap='RdYlGn_r',
    point_size=10,
)
plotter.add_mesh(mesh['Buildings'], opacity=0.3)
plotter.show()
```

## Weiterführende Ressourcen

- Paraview Tutorial: https://www.paraview.org/Wiki/The_ParaView_Tutorial
- PyVista Examples: https://docs.pyvista.org/examples/
- VTK Format Spec: https://vtk.org/wp-content/uploads/2015/04/file-formats.pdf
