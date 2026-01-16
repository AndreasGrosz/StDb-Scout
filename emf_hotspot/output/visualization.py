"""
3D-Visualisierung der Hotspot-Ergebnisse und VTK-Export für Paraview
"""

from pathlib import Path
from typing import List, Optional
import numpy as np
import urllib.request
import urllib.parse
from io import BytesIO

from ..models import HotspotResult, AntennaSystem, Building
from ..config import AGW_LIMIT_VM


def visualize_hotspots(
    results: List[HotspotResult],
    antenna_system: AntennaSystem,
    buildings: Optional[List[Building]] = None,
    output_path: Optional[Path] = None,
    show: bool = True,
    threshold_vm: float = AGW_LIMIT_VM,
) -> None:
    """
    Erstellt eine 3D-Visualisierung der Hotspot-Ergebnisse.

    Args:
        results: Liste von HotspotResult
        antenna_system: AntennaSystem für Antennenposition
        buildings: Optional - Gebäude für Kontext
        output_path: Optional - Pfad für Screenshot
        show: Ob das Fenster angezeigt werden soll
        threshold_vm: Schwellwert für Farbskala
    """
    try:
        import pyvista as pv
    except ImportError:
        print("PyVista nicht installiert. Installiere mit: pip install pyvista")
        return

    # Offscreen-Rendering aktivieren (für Remote/Headless)
    # WICHTIG: Muss VOR Plotter-Erstellung gesetzt werden
    if not show:
        try:
            pv.start_xvfb()  # Virtuelles Display
        except Exception as e:
            print(f"  HINWEIS: Xvfb nicht verfügbar: {e}")

    # Plotter erstellen - mit zusätzlichem Segfault-Schutz
    try:
        # Test ob OpenGL überhaupt verfügbar ist
        import os
        os.environ.setdefault('PYVISTA_OFF_SCREEN', 'true' if not show else 'false')

        plotter = pv.Plotter(off_screen=(not show), window_size=[800, 600])
        plotter.set_background("white")
    except (Exception, SystemError, OSError) as e:
        print(f"  FEHLER: 3D-Visualisierung nicht möglich auf diesem System.")
        print(f"  Grund: {e}")
        print(f"  → Verwenden Sie stattdessen die 2D-Heatmap (output/heatmap.png)")
        print(f"  → Oder führen Sie die Analyse mit --no-viz aus")
        return  # Beende Funktion sauber

    # Ergebnispunkte als PointCloud
    if results:
        _add_result_points(plotter, results, threshold_vm)

    # Antennenposition
    _add_antenna_markers(plotter, antenna_system)

    # Gebäude (falls vorhanden)
    if buildings:
        _add_buildings(plotter, buildings)

    # Koordinatenachsen und Beschriftung
    plotter.add_axes()
    plotter.add_title(f"EMF-Hotspot-Analyse: {antenna_system.name}")

    # Speichern oder anzeigen
    if output_path:
        plotter.screenshot(str(output_path))
        print(f"Screenshot gespeichert: {output_path}")

    if show:
        plotter.show()
    else:
        plotter.close()


def _add_result_points(
    plotter,
    results: List[HotspotResult],
    threshold_vm: float,
) -> None:
    """Fügt Ergebnispunkte mit Farbskala hinzu."""
    import pyvista as pv

    if not results:
        return

    # Punkte und E-Werte extrahieren
    points = np.array([[r.x, r.y, r.z] for r in results])
    e_values = np.array([r.e_field_vm for r in results])

    # PolyData erstellen
    cloud = pv.PolyData(points)
    cloud["E-Feld [V/m]"] = e_values

    # Farbskala: Grün (0) -> Gelb (threshold/2) -> Rot (threshold+)
    plotter.add_mesh(
        cloud,
        scalars="E-Feld [V/m]",
        cmap="RdYlGn_r",  # Rot-Gelb-Grün umgekehrt
        clim=[0, threshold_vm * 1.5],
        point_size=8,
        render_points_as_spheres=True,
        scalar_bar_args={
            "title": "E-Feld [V/m]",
            "title_font_size": 16,
            "label_font_size": 12,
            "n_labels": 6,
            "fmt": "%.1f",
            "position_x": 0.85,
            "position_y": 0.05,
            "width": 0.1,
            "height": 0.7,
        },
    )

    # Hotspots extra hervorheben
    hotspot_mask = e_values >= threshold_vm
    if np.any(hotspot_mask):
        hotspot_points = points[hotspot_mask]
        hotspot_cloud = pv.PolyData(hotspot_points)
        plotter.add_mesh(
            hotspot_cloud,
            color="red",
            point_size=12,
            render_points_as_spheres=True,
            opacity=0.7,
        )


def _add_antenna_markers(plotter, antenna_system: AntennaSystem) -> None:
    """Fügt Antennenposition als Marker hinzu."""
    import pyvista as pv

    # Gruppiere Antennen nach Position (Mast)
    antennas_by_mast = {}
    for antenna in antenna_system.antennas:
        key = (round(antenna.position.e, 1), round(antenna.position.n, 1), round(antenna.position.h, 1))
        if key not in antennas_by_mast:
            antennas_by_mast[key] = []
        antennas_by_mast[key].append(antenna)

    # Für jeden Mast
    for (e, n, h), antennas in antennas_by_mast.items():
        # Mast als vertikaler Zylinder
        mast_height = 3.0
        cylinder = pv.Cylinder(
            center=(e, n, h - mast_height/2),
            direction=(0, 0, 1),
            radius=0.3,
            height=mast_height,
        )
        plotter.add_mesh(cylinder, color="darkblue", opacity=0.9)

        # Für jede Antenne am Mast: Kegel in Azimut-Richtung
        for i, antenna in enumerate(antennas):
            cone = pv.Cone(
                center=(e, n, h + i * 0.5),  # Leicht versetzt übereinander
                direction=_azimuth_to_direction(antenna.azimuth_deg),
                height=4.0,
                radius=1.5,
            )
            # Farbe je nach Frequenzband
            if "3600" in antenna.frequency_band:
                color = "purple"
            elif "1400" in antenna.frequency_band or "1800" in antenna.frequency_band:
                color = "orange"
            else:
                color = "cyan"

            plotter.add_mesh(cone, color=color, opacity=0.7)

        # Label mit Mastinfo
        point = np.array([[e, n, h + mast_height]])
        mast_nr = antennas[0].mast_nr if antennas else "?"
        label = f"Mast {mast_nr}\n{len(antennas)} Ant."
        plotter.add_point_labels(
            point,
            [label],
            font_size=12,
            point_color="blue",
            point_size=15,
            text_color="white",
            shape_color="darkblue",
            shape_opacity=0.8,
        )


def _add_buildings(plotter, buildings: List[Building]) -> None:
    """Fügt Gebäude als transparente Meshes hinzu."""
    import pyvista as pv

    for building in buildings:
        # Wände
        for wall in building.wall_surfaces:
            if len(wall.vertices) < 3:
                continue

            try:
                # Polygon erstellen
                points = wall.vertices
                n_points = len(points)

                # Faces: Polygon als Triangle-Fan
                faces = []
                for i in range(1, n_points - 1):
                    faces.extend([3, 0, i, i + 1])

                if faces:
                    mesh = pv.PolyData(points, faces=faces)
                    plotter.add_mesh(
                        mesh,
                        color="lightgray",
                        opacity=0.3,
                        show_edges=True,
                        edge_color="gray",
                    )
            except Exception:
                # Fehlerhafte Geometrie überspringen
                continue

        # Dächer (mit anderer Farbe)
        for roof in building.roof_surfaces:
            if len(roof.vertices) < 3:
                continue

            try:
                points = roof.vertices
                n_points = len(points)

                faces = []
                for i in range(1, n_points - 1):
                    faces.extend([3, 0, i, i + 1])

                if faces:
                    mesh = pv.PolyData(points, faces=faces)
                    plotter.add_mesh(
                        mesh,
                        color="darkgray",
                        opacity=0.4,
                        show_edges=True,
                        edge_color="gray",
                    )
            except Exception:
                continue


def _azimuth_to_direction(azimuth_deg: float) -> tuple:
    """Konvertiert Azimut (0°=Nord) in Richtungsvektor."""
    azimuth_rad = np.radians(azimuth_deg)
    # Azimut: 0°=Nord(+y), 90°=Ost(+x)
    return (np.sin(azimuth_rad), np.cos(azimuth_rad), 0)


def create_hotspot_marker_map(
    aggregated_csv: Path,
    output_path: Path,
    antenna_system: Optional[AntennaSystem] = None,
    buildings: Optional[List[Building]] = None,
    results: Optional[List] = None,
    scale: str = "1:1000",
    dpi: int = 300,
) -> None:
    """
    Erstellt eine 2D-Karte mit X-Markern für aggregierte Hotspots (Gebäude×Floor).

    Ideal für Gutachten: Zeigt jeden Hotspot-Floor mit X-Marker auf Basemap.

    Args:
        aggregated_csv: Pfad zur hotspots_aggregated.csv
        output_path: Pfad für die PNG-Datei
        antenna_system: AntennaSystem für Antennenmarker
        buildings: Optional - Gebäudeliste
        results: Optional - Alle HotspotResults für präzise BBox und Max-E-Punkte
        scale: Maßstab z.B. "1:1000"
        dpi: DPI für Ausgabe (300 für Druck)
    """
    import csv
    try:
        import matplotlib.pyplot as plt
        from matplotlib.colors import LinearSegmentedColormap
        import matplotlib.patches as mpatches
    except ImportError:
        print("Matplotlib nicht installiert.")
        return

    if not aggregated_csv.exists():
        print(f"Aggregierte Hotspot-CSV nicht gefunden: {aggregated_csv}")
        return

    # Lade aggregierte Hotspots (zur Validierung)
    aggregated_hotspots = []
    with open(aggregated_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            aggregated_hotspots.append({
                'building_id': row['building_id'],
                'e_vm': float(row['max_e_vm']),
            })

    if not aggregated_hotspots:
        print("Keine aggregierten Hotspots gefunden.")
        return

    # Wenn results vorhanden: Zeige Max-E-Punkt pro Gebäude (wenn >= AGW)
    if results:
        from collections import defaultdict

        # Gruppiere alle Punkte nach building_id
        by_building = defaultdict(list)
        for r in results:
            by_building[r.building_id].append(r)

        # Pro Gebäude: Finde Punkt mit max E-Feldstärke
        # Zeige nur Gebäude mit max_e >= 5.0 V/m
        hotspots = []
        for building_id, building_points in by_building.items():
            max_point = max(building_points, key=lambda p: p.e_field_vm)

            # Nur Gebäude mit Grenzwertüberschreitung anzeigen
            if max_point.e_field_vm >= 5.0:
                hotspots.append({
                    'x': max_point.x,
                    'y': max_point.y,
                    'z': max_point.z,
                    'e_vm': max_point.e_field_vm,
                    'building_id': building_id,
                })

        # BBox von ALLEN Punkten (nicht nur Hotspots) - wie heatmap
        all_x = np.array([r.x for r in results])
        all_y = np.array([r.y for r in results])
        margin = 10  # Meter Rand
        x_min, x_max = all_x.min() - margin, all_x.max() + margin
        y_min, y_max = all_y.min() - margin, all_y.max() + margin
    else:
        # Fallback: Nutze center aus aggregated CSV
        hotspots = []
        with open(aggregated_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                hotspots.append({
                    'x': float(row['center_x']),
                    'y': float(row['center_y']),
                    'z': float(row['center_z']),
                    'e_vm': float(row['max_e_vm']),
                })

        # BBox nur von Hotspots
        x = np.array([h['x'] for h in hotspots])
        y = np.array([h['y'] for h in hotspots])
        margin = 20  # Größerer Rand wenn nur Hotspots
        x_min, x_max = x.min() - margin, x.max() + margin
        y_min, y_max = y.min() - margin, y.max() + margin

    extent_x_m = x_max - x_min
    extent_y_m = y_max - y_min

    # Maßstab berechnen
    scale_ratio = int(scale.split(":")[1])
    meters_per_cm = scale_ratio / 100
    pixels_per_cm = dpi / 2.54
    pixels_per_meter = pixels_per_cm / meters_per_cm

    fig_width_pixels = extent_x_m * pixels_per_meter
    fig_height_pixels = extent_y_m * pixels_per_meter
    fig_width_inches = fig_width_pixels / dpi
    fig_height_inches = fig_height_pixels / dpi

    print(f"  Hotspot-Marker-Map: {scale} @ {dpi} DPI")
    print(f"  Ausdehnung: {extent_x_m:.1f}m × {extent_y_m:.1f}m")
    print(f"  Bildgröße: {fig_width_pixels:.0f} × {fig_height_pixels:.0f} Pixel")

    # Figure erstellen
    fig, ax = plt.subplots(figsize=(fig_width_inches, fig_height_inches))

    # WMS Basemap laden
    basemap = _fetch_wms_basemap(
        bbox=(x_min, y_min, x_max, y_max),
        width=int(fig_width_pixels),
        height=int(fig_height_pixels),
        layer="ch.swisstopo.pixelkarte-farbe",
    )

    if basemap is not None:
        ax.imshow(
            basemap,
            extent=[x_min, x_max, y_min, y_max],
            origin='upper',
            aspect='equal',
            alpha=0.8,
        )

    # LOS/NLOS-Linien von Antenne zu Hotspots (ZUERST, als Hintergrund)
    if antenna_system:
        # Lade LOS-Status aus hotspots_aggregated.csv
        los_info_by_building = {}
        if aggregated_csv.exists():
            with open(aggregated_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    building_id = row.get('building_id', '')
                    los_status = row.get('los_status', 'LOS')
                    if building_id:
                        los_info_by_building[building_id] = los_status

        # Zeichne Linien zu allen Hotspots
        for h in hotspots:
            building_id = h.get('building_id', '')
            los_status = los_info_by_building.get(building_id, 'LOS')

            # Linienstil abhängig von LOS-Status
            if los_status == 'NLOS':
                linestyle = '--'  # Gestrichelt
                color = 'gray'
                alpha = 0.4
                linewidth = 1.0
            else:
                linestyle = '-'  # Durchgezogen
                color = 'red'
                alpha = 0.5
                linewidth = 1.2

            ax.plot(
                [antenna_system.base_position.e, h['x']],
                [antenna_system.base_position.n, h['y']],
                linestyle=linestyle,
                color=color,
                alpha=alpha,
                linewidth=linewidth,
                zorder=5,  # Hinter Markern
            )

    # Lade hotspots_short.csv für OMEN-Nummern und LOS-Status (falls vorhanden)
    hotspot_omen_nrs = {}
    hotspot_los_status = {}
    hotspots_short_csv = aggregated_csv.parent / "hotspots_short.csv"
    if hotspots_short_csv.exists():
        with open(hotspots_short_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                building_id = row.get('building_id', '')
                omen_nr = row.get('omen_nr', '')
                los_status = row.get('los_status', 'LOS')  # Default: LOS
                if building_id and omen_nr:
                    hotspot_omen_nrs[building_id] = omen_nr
                    hotspot_los_status[building_id] = los_status

    # Hotspots als fette X-Marker plotten
    # Farbcodierung nach E-Feldstärke
    e_values = np.array([h['e_vm'] for h in hotspots])
    norm = plt.Normalize(vmin=5.0, vmax=e_values.max())
    cmap = plt.get_cmap('YlOrRd')  # Gelb→Orange→Rot

    for h in hotspots:
        color = cmap(norm(h['e_vm']))
        ax.plot(
            h['x'], h['y'],
            marker='x',
            markersize=12,  # Größer für bessere Sichtbarkeit (war 5)
            markeredgewidth=3.0,  # Fetter für bessere Sichtbarkeit (war 0.8)
            color=color,
            markeredgecolor='darkred',
            zorder=10,
        )

        # Beschriftung mit OMEN-Nummer (falls vorhanden)
        building_id = h.get('building_id', '')
        if building_id and building_id in hotspot_omen_nrs:
            omen_nr = hotspot_omen_nrs[building_id]
            ax.text(
                h['x'], h['y'] + 3,  # Leicht versetzt nach oben
                omen_nr,
                fontsize=10,
                fontweight='bold',
                color='black',
                ha='center',
                va='bottom',
                bbox=dict(facecolor='white', alpha=0.9, boxstyle='round,pad=0.3',
                         edgecolor='darkred', linewidth=1.5),
                zorder=11,
            )

    # Antennenposition (kleiner als vorher)
    if antenna_system:
        ax.plot(
            antenna_system.base_position.e,
            antenna_system.base_position.n,
            marker='*',
            markersize=10,  # Kleiner (vorher 20)
            color='blue',
            markeredgecolor='black',
            markeredgewidth=1.0,
            label='Antenne',
            zorder=15,
        )

        # Hauptstrahlrichtungen als farbige dünne Pfeile
        seen_azimuths = set()
        arrow_length = 80.0  # 80m
        colors_by_band = {
            "700-900": "cyan",
            "1400-2600": "orange",
            "1800-2600": "orange",
            "3600": "purple",
        }

        for antenna in antenna_system.antennas[:9]:  # Max 9 Sektoren
            if antenna.azimuth_deg not in seen_azimuths:
                seen_azimuths.add(antenna.azimuth_deg)
                az_rad = np.radians(antenna.azimuth_deg)
                # Richtung: 0°=Nord=+y
                dx = np.sin(az_rad) * arrow_length
                dy = np.cos(az_rad) * arrow_length

                # Farbe nach Frequenzband
                arrow_color = colors_by_band.get(antenna.frequency_band, "gray")

                ax.arrow(
                    antenna_system.base_position.e,
                    antenna_system.base_position.n,
                    dx, dy,
                    head_width=4,  # Zarte Pfeilspitze (klein)
                    head_length=3,
                    fc=arrow_color,
                    ec=arrow_color,
                    linewidth=1.0,  # Dünne Linie
                    alpha=0.6,
                    zorder=14,
                )

    # OMEN-Punkte: Präzise auf den OMEN-Koordinaten
    if antenna_system and antenna_system.omen_locations:
        for omen in antenna_system.omen_locations:
            # Marker auf exakter OMEN-Position
            ax.plot(
                omen.position.e,
                omen.position.n,
                marker='s',
                markersize=5,
                color='yellow',
                markeredgecolor='black',
                markeredgewidth=0.5,
                zorder=8,
            )
            # Label direkt auf Position (nicht versetzt)
            ax.text(
                omen.position.e,
                omen.position.n,
                f'O{omen.nr}',
                fontsize=8,
                fontweight='bold',
                color='black',
                ha='center',
                va='center',
                bbox=dict(facecolor='yellow', alpha=0.8, boxstyle='round,pad=0.3',
                         edgecolor='black', linewidth=0.8),
                zorder=9,
            )

    # KEINE Colorbar (entfernt für Gutachten)

    # Achsen und Titel
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)

    # KEINE Achsen-Labels (entfernt für Gutachten)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel('')
    ax.set_ylabel('')

    # KEIN Standard-Title (entfernt)

    # Legende: 5 Items in 2 Zeilen
    legend_elements = [
        plt.Line2D([0], [0], marker='x', color='w', markerfacecolor='red', markeredgecolor='darkred',
                   markeredgewidth=2, markersize=10, label='Hotspot (AGW-Überschreitung)'),
        plt.Line2D([0], [0], marker='*', color='w', markerfacecolor='blue', markeredgecolor='black',
                   markersize=12, label='Antennenmast'),
        plt.Line2D([0], [0], marker='s', color='w', markerfacecolor='yellow', markeredgecolor='black',
                   markersize=6, label='OMEN-Punkt'),
        plt.Line2D([0], [0], color='red', linewidth=1.5, linestyle='-', label='LOS (freie Sicht)'),
        plt.Line2D([0], [0], color='gray', linewidth=1.5, linestyle='--', label='NLOS (blockiert)'),
    ]
    # Layout: 3 Items erste Zeile, 2 Items zweite Zeile
    ax.legend(
        handles=legend_elements,
        loc='lower center',
        bbox_to_anchor=(0.5, 0.06),  # 6% von unten
        fontsize=9,  # Etwas kleiner für 5 Items
        ncol=3,  # 3 Items pro Zeile
        frameon=True,
        fancybox=True,
        shadow=True,
    )

    # Titel: Standort-Name unten, hinterlegt für Lesbarkeit
    if antenna_system:
        ax.text(
            0.5, 0.005,  # Zentriert, 0.5% von unten
            f"Standort: {antenna_system.name}",
            transform=ax.transAxes,  # Relative Koordinaten
            fontsize=10,  # Größer für Lesbarkeit (war 8)
            ha='center',
            va='bottom',
            bbox=dict(
                boxstyle='round,pad=0.4',
                facecolor='white',
                edgecolor='gray',
                alpha=0.9,
                linewidth=1.0
            ),
        )

    # KEIN Grid (entfernt für saubere Karte)

    # Maßstabsleiste hinzufügen (unten rechts)
    import matplotlib.lines as mlines

    # Maßstabslänge: 50m für 1:1000
    scale_ratio = int(scale.split(":")[1])
    if scale_ratio == 1000:
        bar_length_m = 50
        tick_interval = 10  # 10m Schritte
    elif scale_ratio == 500:
        bar_length_m = 25
        tick_interval = 5
    else:
        bar_length_m = max(10, int((x_max - x_min) / 10))
        tick_interval = bar_length_m // 5

    # Position: unten rechts
    bar_x_start = x_max - bar_length_m - (x_max - x_min) * 0.05
    bar_y = y_min + (y_max - y_min) * 0.05

    # Hauptbalken zeichnen
    line = mlines.Line2D(
        [bar_x_start, bar_x_start + bar_length_m],
        [bar_y, bar_y],
        linewidth=3, color='black', zorder=20
    )
    ax.add_line(line)

    # Tick-Markierungen und Labels
    num_ticks = int(bar_length_m / tick_interval) + 1
    for i in range(num_ticks):
        tick_x = bar_x_start + i * tick_interval
        tick_label = f"{i * tick_interval}"

        # Vertikaler Tick
        tick_line = mlines.Line2D(
            [tick_x, tick_x],
            [bar_y - 1, bar_y + 1],
            linewidth=2, color='black', zorder=20
        )
        ax.add_line(tick_line)

        # Label
        ax.text(
            tick_x,
            bar_y - (y_max - y_min) * 0.015,
            tick_label + "m" if i == num_ticks - 1 else tick_label,
            ha='center', va='top', fontsize=8,
            color='black',
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8, linewidth=0),
            zorder=21
        )

    # Speichern (ohne tight_layout um schwarze Linien zu vermeiden)
    # Setze stattdessen manuelle Ränder
    fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.12)
    plt.savefig(output_path, dpi=dpi, bbox_inches=None, pad_inches=0.1)
    plt.close()

    print(f"  Hotspot-Marker-Map gespeichert: {output_path}")


def export_to_geojson(
    results: List[HotspotResult],
    output_path: Path,
    threshold_vm: float = AGW_LIMIT_VM,
) -> None:
    """
    Exportiert Ergebnisse als GeoJSON für GIS-Software.
    """
    import json

    features = []

    for r in results:
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(r.x), float(r.y), float(r.z)],  # LV95
            },
            "properties": {
                "building_id": str(r.building_id),
                "e_field_vm": round(float(r.e_field_vm), 4),
                "exceeds_limit": bool(r.exceeds_limit),
                "z": round(float(r.z), 2),
            },
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:EPSG::2056"},  # LV95
        },
        "features": features,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)

    print(f"GeoJSON exportiert: {output_path}")


def _fetch_wms_basemap(
    bbox: tuple[float, float, float, float],
    width: int,
    height: int,
    layer: str = "ch.swisstopo.pixelkarte-farbe",
) -> Optional[np.ndarray]:
    """
    Lädt Hintergrundkarte von geo.admin.ch WMS.

    Args:
        bbox: (min_e, min_n, max_e, max_n) in LV95
        width: Bildbreite in Pixeln
        height: Bildhöhe in Pixeln
        layer: WMS Layer (default: Straßenkarte)

    Returns:
        NumPy Array (RGB) oder None bei Fehler
    """
    try:
        # WMS GetMap Request
        base_url = "https://wms.geo.admin.ch/"
        params = {
            "SERVICE": "WMS",
            "VERSION": "1.3.0",
            "REQUEST": "GetMap",
            "LAYERS": layer,
            "CRS": "EPSG:2056",  # LV95
            "BBOX": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
            "WIDTH": str(width),
            "HEIGHT": str(height),
            "FORMAT": "image/png",
            "TRANSPARENT": "FALSE",
        }

        url = base_url + "?" + urllib.parse.urlencode(params)

        print(f"  Lade Basemap von geo.admin.ch...")

        # Request mit Timeout
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'EMF-Hotspot-Finder/2.0')

        with urllib.request.urlopen(req, timeout=30) as response:
            image_data = response.read()

        # PNG zu NumPy Array
        from PIL import Image
        img = Image.open(BytesIO(image_data))
        img_array = np.array(img)

        print(f"  → Basemap geladen ({width}×{height} Pixel)")
        return img_array

    except Exception as e:
        print(f"  WARNUNG: Basemap-Download fehlgeschlagen: {e}")
        return None


def create_heatmap_image(
    results: List[HotspotResult],
    output_path: Path,
    antenna_system: Optional[AntennaSystem] = None,
    buildings: Optional[List[Building]] = None,
    resolution: float = 1.0,
    threshold_vm: float = AGW_LIMIT_VM,
    scale: str = "1:1000",
    dpi: int = 300,
    use_alpha: bool = True,
) -> None:
    """
    Erstellt ein 2D-Heatmap-Bild (Draufsicht) der E-Feldstärken.

    Args:
        results: Liste von HotspotResult
        buildings: Optional - Gebäudeliste für OMEN-Beschriftung
        output_path: Pfad für die PNG-Datei
        antenna_system: AntennaSystem für Antennenmarker
        resolution: Sampling-Auflösung (für Punktgröße)
        threshold_vm: NISV-Grenzwert
        scale: Maßstab z.B. "1:1000"
        dpi: DPI für Ausgabe (300 für Druck)
        use_alpha: Transparenter Hintergrund statt weiß
    """
    try:
        import matplotlib.pyplot as plt
        from matplotlib.colors import LinearSegmentedColormap
        import matplotlib.patches as mpatches
    except ImportError:
        print("Matplotlib nicht installiert.")
        return

    if not results:
        print("Keine Ergebnisse für Heatmap.")
        return

    # Extrahiere X, Y, E-Werte
    x = np.array([r.x for r in results])
    y = np.array([r.y for r in results])
    e = np.array([r.e_field_vm for r in results])

    # Bounding Box mit Rand
    margin = 20  # Meter Rand
    x_min, x_max = x.min() - margin, x.max() + margin
    y_min, y_max = y.min() - margin, y.max() + margin

    extent_x_m = x_max - x_min
    extent_y_m = y_max - y_min

    # Maßstab berechnen: 1:1000 bedeutet 1cm auf Papier = 10m in Realität
    # Bei 300 DPI: 1 inch = 2.54 cm = 300 Pixel
    # 1 cm = 300/2.54 = 118.11 Pixel
    # 10 m sollen 1 cm sein → Auflösung: 11.811 Pixel/Meter
    scale_ratio = int(scale.split(":")[1])  # z.B. 1000
    meters_per_cm = scale_ratio / 100  # z.B. 10 m/cm
    pixels_per_cm = dpi / 2.54  # z.B. 118.11 Pixel/cm
    pixels_per_meter = pixels_per_cm / meters_per_cm  # z.B. 11.811 Pixel/m

    # Figure-Größe in Inches berechnen
    fig_width_pixels = extent_x_m * pixels_per_meter
    fig_height_pixels = extent_y_m * pixels_per_meter
    fig_width_inches = fig_width_pixels / dpi
    fig_height_inches = fig_height_pixels / dpi

    print(f"  Heatmap-Maßstab: {scale} @ {dpi} DPI")
    print(f"  Ausdehnung: {extent_x_m:.1f}m × {extent_y_m:.1f}m")
    print(f"  Bildgröße: {fig_width_pixels:.0f} × {fig_height_pixels:.0f} Pixel")

    # Figure erstellen
    fig, ax = plt.subplots(figsize=(fig_width_inches, fig_height_inches))

    # WMS Basemap als Hintergrund laden
    basemap = _fetch_wms_basemap(
        bbox=(x_min, y_min, x_max, y_max),
        width=int(fig_width_pixels),
        height=int(fig_height_pixels),
        layer="ch.swisstopo.pixelkarte-farbe",  # Straßenkarte
    )

    if basemap is not None:
        # Basemap anzeigen
        ax.imshow(
            basemap,
            extent=[x_min, x_max, y_min, y_max],
            aspect='equal',
            alpha=0.4,  # Halbtransparent damit Punkte sichtbar bleiben
            zorder=0,  # Hinterste Ebene
        )

    # Transparenter Hintergrund
    if use_alpha:
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)

    # Scatter-Plot mit Farbskala
    scatter = ax.scatter(
        x, y, c=e,
        cmap="RdYlGn_r",
        vmin=0,
        vmax=threshold_vm * 1.5,
        s=100,  # Größere Punkte für bessere Sichtbarkeit
        alpha=0.8,
        edgecolors='none',
    )

    # Hotspots extra markieren
    hotspot_mask = e >= threshold_vm
    if np.any(hotspot_mask):
        ax.scatter(
            x[hotspot_mask],
            y[hotspot_mask],
            c="red",
            s=150,
            marker="x",
            linewidths=3,
            alpha=1.0,
            label=f"Hotspot (≥ {threshold_vm} V/m)",
        )

    # Antennenposition markieren
    if antenna_system:
        ant_e = antenna_system.base_position.e
        ant_n = antenna_system.base_position.n
        ant_h = antenna_system.base_position.h

        # Antenne als Säule (Kreis mit Outline für Mast)
        from matplotlib.patches import Circle
        circle = Circle((ant_e, ant_n), radius=2,
                       facecolor='darkblue', edgecolor='black', linewidth=2,
                       label='Antennenmast', zorder=100)
        ax.add_patch(circle)

        # Höhe als Text
        ax.text(ant_e, ant_n + 8, f'{ant_h:.0f}m ü.M.',
               ha='center', va='bottom', fontsize=9,
               bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8),
               zorder=101)

        # Azimut-Pfeile für Sektoren (nur Hauptantennen) - VIEL LÄNGER
        seen_azimuths = set()
        arrow_length = 80.0  # 80m lange Pfeile (war 15m)
        for antenna in antenna_system.antennas[:9]:  # Maximal 9 Sektoren
            if antenna.azimuth_deg not in seen_azimuths:
                seen_azimuths.add(antenna.azimuth_deg)
                az_rad = np.radians(antenna.azimuth_deg)
                # Pfeil in Azimut-Richtung (0°=Nord=+y)
                dx = np.sin(az_rad) * arrow_length
                dy = np.cos(az_rad) * arrow_length
                ax.arrow(ant_e, ant_n, dx, dy,
                        head_width=8, head_length=6,
                        fc='darkblue', ec='black', linewidth=1.5,
                        alpha=0.7, zorder=99)

    # Colorbar
    cbar = plt.colorbar(scatter, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("E-Feld [V/m]", fontsize=12)

    # Achsen und Beschriftung
    ax.set_xlabel("LV95 Easting [m]", fontsize=12)
    ax.set_ylabel("LV95 Northing [m]", fontsize=12)
    ax.set_title("EMF-Hotspot-Analyse (Draufsicht)", fontsize=14, pad=20)
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)

    # Gebäude mit OMEN-Nr beschriften
    if buildings and antenna_system and antenna_system.omen_locations:
        _add_building_omen_labels(ax, results, buildings, antenna_system)

    # Legende
    if antenna_system or np.any(hotspot_mask):
        ax.legend(loc='upper right', fontsize=10, framealpha=0.9)

    # Himmelsrichtungen hinzufügen
    _add_compass(ax, x_min, x_max, y_min, y_max)

    # Maßstabsbalken hinzufügen
    _add_scale_bar(ax, scale, x_min, x_max, y_min)

    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, transparent=use_alpha, bbox_inches='tight')
    plt.close()

    print(f"Heatmap gespeichert: {output_path}")


def _add_scale_bar(ax, scale: str, x_min: float, x_max: float, y_min: float) -> None:
    """Fügt einen Maßstabsbalken hinzu."""
    import matplotlib.patches as mpatches
    import matplotlib.lines as mlines

    # Maßstabslänge: 50m bei 1:1000
    scale_ratio = int(scale.split(":")[1])
    if scale_ratio == 1000:
        bar_length_m = 50
    elif scale_ratio == 500:
        bar_length_m = 25
    else:
        bar_length_m = max(10, int((x_max - x_min) / 10))

    # Position: unten links
    bar_x_start = x_min + (x_max - x_min) * 0.05
    bar_y = y_min + (ax.get_ylim()[1] - y_min) * 0.05

    # Balken zeichnen
    line = mlines.Line2D(
        [bar_x_start, bar_x_start + bar_length_m],
        [bar_y, bar_y],
        linewidth=3, color='black'
    )
    ax.add_line(line)

    # Beschriftung
    ax.text(
        bar_x_start + bar_length_m / 2,
        bar_y + (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.02,
        f"{bar_length_m} m",
        ha='center', va='bottom', fontsize=10,
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8)
    )


def _add_compass(ax, x_min: float, x_max: float, y_min: float, y_max: float) -> None:
    """
    Fügt Himmelsrichtungen (N/O/S/W) am Rand der Karte hinzu.

    Args:
        ax: Matplotlib Axes
        x_min, x_max: X-Achsen-Grenzen (Easting)
        y_min, y_max: Y-Achsen-Grenzen (Northing)
    """
    extent_x = x_max - x_min
    extent_y = y_max - y_min
    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2

    # Offset vom Rand (5% des Bereichs)
    offset_x = extent_x * 0.05
    offset_y = extent_y * 0.05

    # Himmelsrichtungen platzieren
    compass_markers = [
        ('N', center_x, y_max - offset_y, 'center', 'bottom'),  # Nord (oben)
        ('O', x_max - offset_x, center_y, 'right', 'center'),    # Ost (rechts)
        ('S', center_x, y_min + offset_y, 'center', 'top'),      # Süd (unten)
        ('W', x_min + offset_x, center_y, 'left', 'center'),     # West (links)
    ]

    for label, x, y, ha, va in compass_markers:
        ax.text(
            x, y, label,
            fontsize=14, fontweight='bold',
            ha=ha, va=va,
            color='darkred',
            bbox=dict(boxstyle='circle,pad=0.3', facecolor='white',
                     edgecolor='darkred', linewidth=2, alpha=0.9),
            zorder=102
        )


def _add_building_omen_labels(ax, results, buildings, antenna_system) -> None:
    """
    Beschriftet Gebäude mit ihren OMEN-Nummern (1:1-Zuordnung).

    Jeder OMEN-Punkt bekommt genau ein Gebäude zugeordnet (das nächste).

    Args:
        ax: Matplotlib Axes
        results: Liste von HotspotResult
        buildings: Liste von Building
        antenna_system: AntennaSystem mit OMEN-Locations
    """
    from collections import defaultdict

    # Gruppiere Ergebnisse nach Gebäude-ID
    by_building = defaultdict(list)
    for r in results:
        by_building[r.building_id].append(r)

    # OMEN→Gebäude 1:1-Mapping erstellen
    omen_to_building = {}
    for omen in antenna_system.omen_locations:
        min_dist = float('inf')
        closest_building_id = None
        closest_building_center = None

        # Für jedes Gebäude: Zentroid berechnen
        for building_id, building_results in by_building.items():
            if not building_results:
                continue

            building_center_e = np.mean([r.x for r in building_results])
            building_center_n = np.mean([r.y for r in building_results])

            # Distanz zu OMEN
            dist = np.sqrt(
                (omen.position.e - building_center_e)**2 +
                (omen.position.n - building_center_n)**2
            )

            if dist < min_dist:
                min_dist = dist
                closest_building_id = building_id
                closest_building_center = (building_center_e, building_center_n)

        # Zuordnung speichern (nur wenn < 50m)
        if closest_building_id and min_dist < 50:
            omen_to_building[closest_building_id] = (f"O{omen.nr}", closest_building_center)

    # Labels plotten (nur für zugeordnete Gebäude)
    for building_id, (omen_label, center) in omen_to_building.items():
        ax.text(
            center[0], center[1], omen_label,
            fontsize=12, fontweight='bold',
            ha='center', va='center',
            color='darkblue',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='yellow',
                     edgecolor='darkblue', linewidth=2, alpha=0.85),
            zorder=103
        )


def export_to_vtk(
    results: List[HotspotResult],
    output_path: Path,
    antenna_system: Optional[AntennaSystem] = None,
    buildings: Optional[List[Building]] = None,
    threshold_vm: float = AGW_LIMIT_VM,
    point_size: float = 1.0,  # Größe der Voxel (in Metern)
    use_voxels: bool = True,  # Punkte als Würfel statt Punkte
) -> None:
    """
    Exportiert Ergebnisse als VTK-Datei für Paraview/PyVista Visualisierung.

    Vorteile:
    - Keine OpenGL-Probleme auf Headless-Servern
    - Offline-Visualisierung auf lokalem Rechner
    - Paraview kann 20+ Millionen Punkte flüssig darstellen
    - Professionelle Post-Processing-Möglichkeiten

    Args:
        results: Liste von HotspotResult
        output_path: Pfad für VTU-Datei (Unstructured Grid)
        antenna_system: Optional - AntennaSystem für Antennenpositionen
        buildings: Optional - Gebäude für Kontext
        threshold_vm: Schwellwert für Hotspot-Markierung
        point_size: Größe der Voxel in Metern (wenn use_voxels=True)
        use_voxels: Ob Punkte als Würfel (True) oder als Punkte (False) exportiert werden
    """
    try:
        import pyvista as pv
    except ImportError:
        print("  HINWEIS: PyVista nicht installiert - VTK-Export übersprungen")
        print("  Installiere mit: pip install pyvista")
        return

    if not results:
        print("  WARNUNG: Keine Ergebnisse zum Exportieren")
        return

    # Daten vorbereiten
    points = np.array([[r.x, r.y, r.z] for r in results])
    e_values = np.array([r.e_field_vm for r in results])
    exceeds = np.array([int(r.exceeds_limit) for r in results])
    building_ids = np.array([hash(r.building_id) % 10000 for r in results])  # Als Zahlen für Coloring

    if use_voxels and len(points) < 50000:
        # Erstelle Würfel/Voxel für jeden Punkt (nur für <50k Punkte, sonst zu langsam)
        print(f"  Erstelle Voxel-Geometrie (Größe: {point_size}m)...")

        # Effiziente Methode: Unstructured Grid mit Hexahedern
        from vtk import VTK_HEXAHEDRON

        # Pro Punkt: 8 Eckpunkte eines Würfels
        half = point_size / 2
        offsets = np.array([
            [-half, -half, -half],
            [+half, -half, -half],
            [+half, +half, -half],
            [-half, +half, -half],
            [-half, -half, +half],
            [+half, -half, +half],
            [+half, +half, +half],
            [-half, +half, +half],
        ])

        all_points = []
        cells = []
        cell_types = []

        for i, pt in enumerate(points):
            # 8 Eckpunkte für diesen Würfel
            start_idx = i * 8
            for offset in offsets:
                all_points.append(pt + offset)

            # Hexahedron cell (8 Indizes)
            cells.append(8)  # Anzahl Punkte
            cells.extend(range(start_idx, start_idx + 8))
            cell_types.append(VTK_HEXAHEDRON)

            if (i + 1) % 10000 == 0:
                print(f"    {i+1}/{len(points)} Voxel erstellt...")

        # UnstructuredGrid erstellen
        cloud = pv.UnstructuredGrid(cells, cell_types, np.array(all_points))

        # Daten auf Cell-Level (nicht Point-Level)
        cloud.cell_data["E_field_Vm"] = e_values
        cloud.cell_data["Exceeds_Limit"] = exceeds
        cloud.cell_data["Building_ID"] = building_ids

    elif use_voxels and len(points) >= 50000:
        # Zu viele Punkte für Voxel-Geometrie → Warnung und PointCloud
        print(f"  HINWEIS: {len(points)} Punkte - zu viele für Voxel-Modus")
        print(f"  → Nutze PointCloud (besser Performance)")
        print(f"  → In ParaView: Glyph-Filter anwenden für größere Punkte")

        cloud = pv.PolyData(points)
        cloud["E_field_Vm"] = e_values
        cloud["Exceeds_Limit"] = exceeds
        cloud["Building_ID"] = building_ids
        cloud["Point_Size_m"] = np.full(len(points), point_size)  # Metadaten für Glyph-Filter

    else:
        # Klassische PointCloud (klein in ParaView)
        cloud = pv.PolyData(points)
        cloud["E_field_Vm"] = e_values
        cloud["Exceeds_Limit"] = exceeds
        cloud["Building_ID"] = building_ids
        cloud["Point_Size_m"] = np.full(len(points), point_size)  # Metadaten

    # MultiBlock für mehrere Objekte
    multiblock = pv.MultiBlock()
    multiblock["Results"] = cloud

    # Antennen als hellblaue Würfel hinzufügen (besser sichtbar)
    if antenna_system:
        antenna_cubes = []
        cube_size = 2.0  # 2m Kantenlänge pro Antenne

        for ant in antenna_system.antennas:
            # Würfel an Antennenposition
            cube = pv.Cube(
                center=(ant.position.e, ant.position.n, ant.position.h),
                x_length=cube_size,
                y_length=cube_size,
                z_length=cube_size,
            )

            # Metadaten pro Antenne
            cube["Antenna_ID"] = np.full(cube.n_cells, ant.id)

            # Parse frequency (z.B. "700-900" → 800)
            freq_parts = ant.frequency_band.replace(" MHz", "").split("-")
            freq_mid = sum(float(f) for f in freq_parts) / len(freq_parts)
            cube["Frequency_MHz"] = np.full(cube.n_cells, freq_mid)

            cube["Power_W"] = np.full(cube.n_cells, ant.erp_watts)
            cube["Azimuth_deg"] = np.full(cube.n_cells, ant.azimuth_deg)

            # Hellblau RGB (0.5, 0.7, 1.0)
            cube["RGB"] = np.tile([0.5, 0.7, 1.0], (cube.n_cells, 1))

            antenna_cubes.append(cube)

        # Kombiniere alle Antennen-Würfel
        if antenna_cubes:
            combined_antennas = antenna_cubes[0]
            for cube in antenna_cubes[1:]:
                combined_antennas = combined_antennas.merge(cube)
            multiblock["Antennas"] = combined_antennas

        # Antennenmast als 3D-Zylinder
        base_pos = antenna_system.base_position
        max_antenna_height = max(ant.position.h for ant in antenna_system.antennas)
        mast_height = max_antenna_height - base_pos.h + 2  # +2m über höchster Antenne
        mast_top_height = max_antenna_height + 2  # Absolute Höhe der Mastspitze

        mast = pv.Cylinder(
            center=(base_pos.e, base_pos.n, base_pos.h + mast_height/2),
            direction=(0, 0, 1),
            radius=0.5,  # 0.5m Durchmesser (schmaler)
            height=mast_height,
            resolution=20,
        )
        multiblock["Antenna_Mast"] = mast

        # Azimut-Pfeile als 3D-Linien mit Kegeln (Hauptstrahlrichtungen) in Hellblau
        # Gruppiere Antennen nach Azimut und verwende mittleren Tilt
        azimuth_to_antennas = {}
        for antenna in antenna_system.antennas[:9]:
            if antenna.azimuth_deg not in azimuth_to_antennas:
                azimuth_to_antennas[antenna.azimuth_deg] = []
            azimuth_to_antennas[antenna.azimuth_deg].append(antenna)

        arrow_meshes = []
        arrow_length = 80.0  # 80m lang

        for azimuth_deg, antennas_group in azimuth_to_antennas.items():
            # Verwende erste Antenne dieser Gruppe für Position
            ref_antenna = antennas_group[0]

            # Mittlerer Tilt über alle Antennen dieser Azimut-Richtung
            avg_tilt = sum((ant.tilt_from_deg + ant.tilt_to_deg) / 2 for ant in antennas_group) / len(antennas_group)

            # Richtungsvektor berechnen mit Azimut UND Tilt
            # Azimut: 0°=Nord=+Y, 90°=Ost=+X
            az_rad = np.radians(azimuth_deg)
            tilt_rad = np.radians(avg_tilt)

            # Horizontale Komponente (durch Tilt reduziert)
            horiz_length = arrow_length * np.cos(tilt_rad)
            dx = np.sin(az_rad) * horiz_length
            dy = np.cos(az_rad) * horiz_length

            # Vertikale Komponente (Tilt negativ = nach unten)
            dz = arrow_length * np.sin(tilt_rad)

            # Startpunkt an Antennenposition (nicht Mastspitze!)
            start = np.array([ref_antenna.position.e, ref_antenna.position.n, ref_antenna.position.h])
            end = start + np.array([dx, dy, dz])

            # Pfeil als Linie + Kegel an der Spitze
            line = pv.Line(start, end)
            # Hellblau färben (RGB)
            line["RGB"] = np.tile([0.5, 0.7, 1.0], (line.n_cells, 1))
            arrow_meshes.append(line)

            # Kegel als Pfeilspitze (verkleinert)
            cone_center = end - np.array([dx, dy, dz]) * 0.05  # 5% zurück
            cone = pv.Cone(
                center=cone_center,
                direction=(dx, dy, dz),
                height=4.0,  # Verkleinert von 8.0 auf 4.0
                radius=1.5,  # Verkleinert von 3.0 auf 1.5
                resolution=10,
            )
            # Hellblau färben (RGB)
            cone["RGB"] = np.tile([0.5, 0.7, 1.0], (cone.n_cells, 1))
            arrow_meshes.append(cone)

        if arrow_meshes:
            # Kombiniere mit + operator (behält RGB)
            combined_arrows = arrow_meshes[0]
            for mesh in arrow_meshes[1:]:
                combined_arrows = combined_arrows + mesh

            # Setze RGB für alle Cells (falls beim Kombinieren verloren)
            if "RGB" not in combined_arrows.array_names and combined_arrows.n_cells > 0:
                combined_arrows["RGB"] = np.tile([0.5, 0.7, 1.0], (combined_arrows.n_cells, 1))

            multiblock["Azimuth_Arrows"] = combined_arrows

    # Gebäude als PolyData - ORIGINAL CityGML Geometrie
    # Zeigt echte Dachformen, aber fragmentiert
    if buildings:
        building_meshes = []

        for building in buildings:
            # Wände
            for wall in building.wall_surfaces:
                if len(wall.vertices) < 3:
                    continue

                try:
                    points_wall = wall.vertices
                    n_points = len(points_wall)

                    # Triangle Fan
                    faces = []
                    for i in range(1, n_points - 1):
                        faces.extend([3, 0, i, i + 1])

                    if faces:
                        mesh = pv.PolyData(points_wall, faces=faces)
                        mesh["Type"] = np.full(mesh.n_cells, 0)  # 0 = Wall
                        building_meshes.append(mesh)
                except:
                    continue

            # Dächer
            for roof in building.roof_surfaces:
                if len(roof.vertices) < 3:
                    continue

                try:
                    points_roof = roof.vertices
                    n_points = len(points_roof)

                    faces = []
                    for i in range(1, n_points - 1):
                        faces.extend([3, 0, i, i + 1])

                    if faces:
                        mesh = pv.PolyData(points_roof, faces=faces)
                        mesh["Type"] = np.full(mesh.n_cells, 1)  # 1 = Roof
                        building_meshes.append(mesh)
                except:
                    continue

        if building_meshes:
            combined_buildings = building_meshes[0]
            for mesh in building_meshes[1:]:
                combined_buildings = combined_buildings.merge(mesh)
            multiblock["Buildings"] = combined_buildings

    # Terrain-Mesh hinzufügen (SwissALTI3D)
    # TEMPORÄR DEAKTIVIERT für schnellere Tests
    enable_terrain = False  # TODO: Als Parameter hinzufügen

    if antenna_system and enable_terrain:
        try:
            from ..loaders.terrain_loader import load_terrain_mesh
            print(f"  Lade Terrain-Daten (SwissALTI3D)...")

            # Berechne Radius basierend auf Ergebnissen
            if results:
                result_e = [r.x for r in results]
                result_n = [r.y for r in results]
                radius = max(
                    max(abs(e - antenna_system.base_position.e) for e in result_e),
                    max(abs(n - antenna_system.base_position.n) for n in result_n)
                ) + 50  # +50m Puffer
            else:
                radius = 200

            vertices, faces, heights = load_terrain_mesh(
                center_e=antenna_system.base_position.e,
                center_n=antenna_system.base_position.n,
                radius_m=radius,
                resolution_m=2.0  # 2m SwissALTI3D Resolution
            )

            if vertices is not None and faces is not None:
                # Erstelle PolyData aus Vertices und Faces
                terrain = pv.PolyData(vertices, np.column_stack([
                    np.full(len(faces), 3),  # Triangle marker
                    faces
                ]).ravel())

                # Höhe als Scalar für Colormap
                terrain["Elevation_m"] = heights

                multiblock["Terrain"] = terrain
                print(f"  → Terrain: {len(vertices)} Vertices, {len(faces)} Dreiecke")

        except Exception as e:
            print(f"  HINWEIS: Terrain konnte nicht geladen werden: {e}")
            # Optional: print(f"  → Traceback:"); import traceback; traceback.print_exc()

    # Maßstab hinzufügen (50m Referenz) - am äußersten Rand vorne, auf Bodenhöhe
    if antenna_system and buildings:
        scale_length = 50.0  # 50m lang

        base_pos = antenna_system.base_position

        # Finde minimale Y-Koordinate (südlichster Punkt = vorne in der Szene)
        all_y = []
        for building in buildings:
            for surface in building.wall_surfaces + building.roof_surfaces:
                for vertex in surface.vertices:
                    all_y.append(vertex[1])

        min_y = min(all_y) if all_y else base_pos.n

        # Platziere Maßstab 10m vor dem südlichsten Gebäude, zentriert auf Antenne
        scale_y = min_y - 10.0
        scale_z = base_pos.h  # Auf Bodenhöhe

        scale_start = np.array([base_pos.e - scale_length/2, scale_y, scale_z])
        scale_end = np.array([base_pos.e + scale_length/2, scale_y, scale_z])

        # Hauptlinie als dickes Rohr (schwarz)
        scale_tube = pv.Tube(pointa=scale_start, pointb=scale_end, radius=1.0, n_sides=8)
        scale_tube["RGB"] = np.tile([0.0, 0.0, 0.0], (scale_tube.n_cells, 1))

        # Marker alle 10m: 0, 10, 20, 30, 40, 50m als haarfeine vertikale Linien
        marker_height = 3.0  # 3m hoch
        marker_radius = 0.1  # Sehr dünn (10cm)
        markers = []
        text_labels = []

        text_height = 2.0  # 2m hoch (kleiner als vorher)
        text_offset_z = 3.5  # 3.5m über dem Boden
        text_offset_y = -1.5  # 1.5m hinter dem Maßstab

        for i, distance in enumerate([0, 10, 20, 30, 40, 50]):
            # Position entlang der Linie berechnen
            t = distance / scale_length  # 0.0 bis 1.0
            marker_pos = scale_start + t * (scale_end - scale_start)

            # Vertikale Linie (haarfein)
            line_start = marker_pos.copy()
            line_end = marker_pos + np.array([0, 0, marker_height])

            line = pv.Cylinder(
                center=(line_start + line_end) / 2,
                direction=[0, 0, 1],
                radius=marker_radius,
                height=marker_height
            )
            line["RGB"] = np.tile([0.0, 0.0, 0.0], (line.n_cells, 1))
            markers.append(line)

            # Text-Label
            text = pv.Text3D(f"{distance}m", depth=0.3)
            text.points *= text_height
            text_center = text.center
            text.points += marker_pos + np.array([0, text_offset_y, text_offset_z]) - text_center
            text["RGB"] = np.tile([0.0, 0.0, 0.0], (text.n_cells, 1))
            text_labels.append(text)

        # Kombiniere alle Elemente
        scale_bar = scale_tube
        for marker in markers:
            scale_bar = scale_bar + marker
        for text in text_labels:
            scale_bar = scale_bar + text

        # Setze RGB für alle Cells (falls beim Kombinieren verloren)
        if "RGB" not in scale_bar.array_names and scale_bar.n_cells > 0:
            scale_bar["RGB"] = np.tile([0.0, 0.0, 0.0], (scale_bar.n_cells, 1))

        multiblock["Scale_Bar_50m"] = scale_bar

    # Speichern
    multiblock.save(str(output_path))
    print(f"  VTK-Export: {output_path}")
    print(f"    → Öffnen mit: paraview {output_path}")
    print(f"    → Oder: python -m pyvista {output_path}")
    print(f"    → {len(results)} Punkte, {len(multiblock)} Objekte")
