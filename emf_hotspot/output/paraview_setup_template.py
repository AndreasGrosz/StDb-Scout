"""
ParaView Setup Script - Auto-konfiguriert Ansicht mit Voreinstellungen

Dieses Script kann in ParaView ausgeführt werden um automatisch:
- Extract Block Filter für Lobes anzuwenden
- Lobes mit Opacity 20% zu setzen
- E_field_Vm Coloring mit Range 4-5 V/m zu setzen
- Alle Blocks korrekt zu konfigurieren

Verwendung in ParaView:
1. Datei laden: paraview {vtk_file}
2. Tools → Python Shell
3. Run Script → paraview_setup.py
"""

from paraview.simple import *

# Lade VTK-Datei
vtm_file = "{vtk_file}"
reader = XMLMultiBlockDataReader(FileName=vtm_file)
reader.UpdatePipeline()

# Extract Block Filter für alle Blocks erstellen
extract_results = ExtractBlock(Input=reader)
extract_results.BlockIndices = [0]  # Results
Show(extract_results)

extract_buildings = ExtractBlock(Input=reader)
extract_buildings.BlockIndices = [4]  # Buildings
buildings_display = Show(extract_buildings)

extract_lobes = ExtractBlock(Input=reader)
extract_lobes.BlockIndices = [5]  # Antenna_Lobes
lobes_display = Show(extract_lobes)

# Lobes: Opacity 20%, kein Coloring (einfarbig)
lobes_display.Opacity = 0.2
lobes_display.AmbientColor = [0.9, 0.9, 0.9]  # Hellgrau
lobes_display.DiffuseColor = [0.9, 0.9, 0.9]

# Results (Punkte): E_field_Vm Coloring, Range 4-5 V/m
results_display = Show(extract_results)
ColorBy(results_display, ('POINTS', 'E_field_Vm'))

# Color Range 4-5 V/m setzen
e_field_lut = GetColorTransferFunction('E_field_Vm')
e_field_lut.RescaleTransferFunction(4.0, 5.0)
e_field_lut.ApplyPreset('Cool to Warm', True)  # Blau=niedrig, Rot=hoch

# Opacity Transfer Function (optional - macht hohe Werte sichtbarer)
e_field_pwf = GetOpacityTransferFunction('E_field_Vm')
e_field_pwf.Points = [4.0, 0.3, 0.5, 0.0,  # Bei 4 V/m: 30% opacity
                      5.0, 1.0, 0.5, 0.0]  # Bei 5 V/m: 100% opacity

# Buildings: Einfarbig grau, keine Transparenz
buildings_display.AmbientColor = [0.7, 0.7, 0.7]
buildings_display.DiffuseColor = [0.7, 0.7, 0.7]
buildings_display.Opacity = 1.0

# Kamera-Position anpassen
view = GetActiveView()
view.ResetCamera()
view.CameraPosition = [{camera_x}, {camera_y}, {camera_z}]
view.CameraFocalPoint = [{focal_x}, {focal_y}, {focal_z}]

# Color Bar (Legende) anzeigen
results_display.SetScalarBarVisibility(view, True)

# Render
Render()

print("✅ ParaView Setup abgeschlossen!")
print("  - Lobes: 20% Opacity, hellgrau")
print("  - Results: E_field_Vm Coloring, 4-5 V/m Range")
print("  - Buildings: Grau, opak")
