"""
ParaView State File Generator

Erstellt .pvsm-Dateien mit vordefinierten Einstellungen für ParaView.
"""

from pathlib import Path
import xml.etree.ElementTree as ET
from typing import Optional


def create_paraview_state(
    vtk_file: Path,
    output_state: Path,
    color_field: str = "E_field_Vm",
    color_range: tuple = (0.0, 6.0),
    glyph_scale: float = 2.0,
    use_glyph: bool = True,
) -> None:
    """
    Erstellt einen ParaView State File (.pvsm) mit vordefinierten Einstellungen.

    Args:
        vtk_file: Pfad zur VTK-Datei (.vtm)
        output_state: Pfad für den State File (.pvsm)
        color_field: Welches Feld für Farbcodierung ("E_field_Vm")
        color_range: Min/Max für Farbleiste (0, 6)
        glyph_scale: Skalierungsfaktor für Glyph-Filter
        use_glyph: Ob Glyph-Filter aktiv sein soll
    """

    # Minimaler ParaView State (XML)
    # Dieser State lädt die VTK-Datei mit vordefinierten Einstellungen

    state_xml = f"""<?xml version="1.0"?>
<ParaView version="5.10.0">
  <ServerManagerState version="5.10.0">

    <!-- VTK-Reader -->
    <Proxy group="sources" type="XMLMultiBlockDataReader" id="0" servers="1">
      <Property name="FileName" id="0.FileName" number_of_elements="1">
        <Element index="0" value="{vtk_file.absolute()}"/>
      </Property>
    </Proxy>

    <!-- Glyph-Filter (falls gewünscht) -->
    {_glyph_filter_xml(glyph_scale) if use_glyph else ""}

    <!-- Farbcodierung -->
    <Proxy group="representations" type="GeometryRepresentation" id="100" servers="1">
      <Property name="ColorArrayName" id="100.ColorArrayName" number_of_elements="5">
        <Element index="0" value="0"/>
        <Element index="1" value=""/>
        <Element index="2" value=""/>
        <Element index="3" value="0"/>
        <Element index="4" value="{color_field}"/>
      </Property>

      <!-- Color Transfer Function -->
      <Property name="LookupTable" id="100.LookupTable">
        <Proxy group="lookup_tables" type="PVLookupTable" id="200" servers="1">
          <Property name="RGBPoints" id="200.RGBPoints" number_of_elements="8">
            <Element index="0" value="{color_range[0]}"/>
            <Element index="1" value="0.0"/>
            <Element index="2" value="0.0"/>
            <Element index="3" value="1.0"/>
            <Element index="4" value="{color_range[1]}"/>
            <Element index="5" value="1.0"/>
            <Element index="6" value="0.0"/>
            <Element index="7" value="0.0"/>
          </Property>
          <Property name="ColorSpace" id="200.ColorSpace" number_of_elements="1">
            <Element index="0" value="3"/>
          </Property>
          <Property name="ScalarRangeInitialized" id="200.ScalarRangeInitialized" number_of_elements="1">
            <Element index="0" value="1"/>
          </Property>
        </Proxy>
      </Property>

      <!-- Point Size -->
      <Property name="PointSize" id="100.PointSize" number_of_elements="1">
        <Element index="0" value="8.0"/>
      </Property>
    </Proxy>

    <!-- Kamera-Position -->
    <Proxy group="views" type="RenderView" id="300" servers="1">
      <Property name="CameraPosition" id="300.CameraPosition" number_of_elements="3">
        <Element index="0" value="2681044"/>
        <Element index="1" value="1252266"/>
        <Element index="2" value="800"/>
      </Property>
      <Property name="CameraFocalPoint" id="300.CameraFocalPoint" number_of_elements="3">
        <Element index="0" value="2681044"/>
        <Element index="1" value="1252266"/>
        <Element index="2" value="470"/>
      </Property>
      <Property name="Background" id="300.Background" number_of_elements="3">
        <Element index="0" value="1.0"/>
        <Element index="1" value="1.0"/>
        <Element index="2" value="1.0"/>
      </Property>
    </Proxy>

  </ServerManagerState>
</ParaView>
"""

    # XML schreiben
    with open(output_state, 'w', encoding='utf-8') as f:
        f.write(state_xml)

    print(f"  ParaView State File erstellt: {output_state}")
    print(f"  → Öffne mit: paraview --state={output_state}")


def _glyph_filter_xml(scale: float) -> str:
    """Erstellt XML für Glyph-Filter."""
    return f"""
    <!-- Glyph-Filter für größere Punkte -->
    <Proxy group="filters" type="Glyph" id="50" servers="1">
      <Property name="Input" id="50.Input">
        <Proxy value="0"/>
      </Property>
      <Property name="ScaleFactor" id="50.ScaleFactor" number_of_elements="1">
        <Element index="0" value="{scale}"/>
      </Property>
      <Property name="GlyphType" id="50.GlyphType">
        <Proxy group="glyph_sources" type="SphereSource" id="51" servers="1">
          <Property name="Radius" id="51.Radius" number_of_elements="1">
            <Element index="0" value="1.0"/>
          </Property>
          <Property name="ThetaResolution" id="51.ThetaResolution" number_of_elements="1">
            <Element index="0" value="8"/>
          </Property>
          <Property name="PhiResolution" id="51.PhiResolution" number_of_elements="1">
            <Element index="0" value="8"/>
          </Property>
        </Proxy>
      </Property>
      <Property name="ScaleMode" id="50.ScaleMode" number_of_elements="1">
        <Element index="0" value="0"/>
      </Property>
    </Proxy>
    """


def create_quick_guide_text(vtk_file: Path) -> str:
    """
    Erstellt eine Kurzanleitung für ParaView.

    Returns:
        Markdown-Text mit Anleitung
    """
    return f"""# ParaView Kurzanleitung - EMF-Hotspot-Visualisierung

## Datei öffnen
```bash
paraview {vtk_file}
```

## Option 1: Punkte vergrößern (schnell)

1. **Representation** → "Point Gaussian" oder "3D Glyphs"
2. **Point Size** → 8-12

## Option 2: Glyph-Filter (beste Qualität)

1. Filter → **Glyph** anwenden
2. **Glyph Type**: Sphere oder Box
3. **Scale Factor**: 2.0-5.0 (je nach Auflösung)
4. **Scale Mode**: "off" (uniform)
5. Apply

## Farbcodierung einstellen

1. Toolbar oben: **Color by** → "E_field_Vm" auswählen
2. **Edit Color Map** (Zahnrad-Icon)
3. **Rescale to Custom Range**:
   - Min: 0
   - Max: 6
4. **Color Map**: "Cool to Warm" oder "Rainbow"

## Hotspots hervorheben

1. Filter → **Threshold**
2. **Scalars**: E_field_Vm
3. **Minimum**: 5.0 (AGW-Grenzwert)
4. Apply

## Gebäude transparent machen

1. Im **Pipeline Browser**: "Buildings" auswählen
2. **Opacity**: 0.3
3. **Color**: Lightgray

## Kamera-Einstellungen

- **+Z Achse** = Nach oben (Höhe)
- **View**: +Z Axis → Draufsicht
- **Camera**: Parallel Projection → Orthogonale Ansicht

## Performance-Tipps

- Bei >100k Punkten: "Point Gaussian" statt Glyph (schneller)
- Gebäude ausblenden wenn nicht nötig
- LOD (Level of Detail) aktivieren: View → Settings → Render View

## Export für Berichte

- File → Save Screenshot (PNG, 300 DPI)
- File → Export Scene (für PowerPoint/Word)
"""
