"""
EMF-Hotspot-Finder: Hauptmodul und CLI

Berechnet NISV-Überschreitungen (E >= 5 V/m) an Gebäudefassaden
im Umkreis von Mobilfunkantennen.
"""

from pathlib import Path
from typing import Optional
import sys

from .config import AGW_LIMIT_VM, DEFAULT_RADIUS_M, DEFAULT_RESOLUTION_M
from .models import AntennaSystem, Building, FacadePoint, HotspotResult
from .loaders.omen_loader import load_omen_data
from .loaders.pattern_loader_ods import load_patterns_from_ods
from .loaders.pattern_adapter import load_patterns_with_standard_fallback
from .utils import ask_yes_no, error_and_exit
from .loaders.building_loader import (
    download_buildings_for_location,
    load_buildings_from_citygml,
)
from .geometry.facade_sampling import sample_all_facades, sample_all_roofs, filter_points_by_distance
from .physics.summation import calculate_all_points, calculate_hotspots
from .output.csv_export import (
    export_hotspots_csv,
    export_hotspots_with_antenna_details_csv,
    export_summary_csv,
    export_buildings_overview_csv,
    export_omen_validation_csv,
    export_hotspots_aggregated_csv,
    export_omen_assignment_validation_csv,
)
from .output.visualization import (
    visualize_hotspots,
    export_to_geojson,
    export_hotspots_for_geoadmin,
    export_hotspots_kml,
    create_heatmap_image,
    create_hotspot_marker_map,
    export_to_vtk,
)
from .output.omen_export import create_neuomen_workbooks


def analyze_site(
    omen_file: Path,
    pattern_dir: Path,
    output_dir: Path,
    citygml_file: Optional[Path] = None,
    radius_m: float = DEFAULT_RADIUS_M,
    resolution_m: float = DEFAULT_RESOLUTION_M,
    threshold_vm: float = AGW_LIMIT_VM,
    auto_download_buildings: bool = True,
    visualize: bool = False,  # Default: disabled (OpenGL issues on headless servers)
    parallel: bool = True,  # Parallele Berechnung (multiprocessing)
    n_workers: Optional[int] = None,  # Anzahl Worker (None = CPU-Kerne)
) -> list[HotspotResult]:
    """
    Führt eine vollständige Hotspot-Analyse für einen Standort durch.

    Args:
        omen_file: Pfad zur OMEN XLS-Datei
        pattern_dir: Verzeichnis mit Antennendiagramm-CSV-Dateien
        output_dir: Ausgabeverzeichnis für Ergebnisse
        citygml_file: Optional - Pfad zu lokaler CityGML-Datei
        radius_m: Suchradius um Antenne [m]
        resolution_m: Rasterauflösung auf Fassaden [m]
        threshold_vm: Schwellwert für Hotspots [V/m]
        auto_download_buildings: Ob Gebäude automatisch geladen werden
        visualize: Ob 3D-Visualisierung erstellt wird

    Returns:
        Liste aller HotspotResults
    """
    # 1. Antennendaten laden (müssen wir zuerst laden, um die Adresse zu bekommen)
    print("=" * 60)
    print("EMF-Hotspot-Finder")
    print("=" * 60)

    print(f"\n[1/6] Lade Antennendaten: {omen_file}")
    antenna_system = load_omen_data(Path(omen_file))
    print(f"  Standort: {antenna_system.name}")
    print(f"  Adresse: {antenna_system.address}")
    print(f"  Basisposition: {antenna_system.base_position.e:.0f} / {antenna_system.base_position.n:.0f}")
    print(f"  Antennen: {len(antenna_system.antennas)}")

    # 2. Output-Verzeichnis mit Projekt-Subdirectory erstellen
    import re

    # Clean address für Verzeichnisnamen (z.B. "Burgerrietstrasse 19 / 4730 Uznach" → "Burgerrietstrasse_19_4730_Uznach")
    clean_address = re.sub(r'[^\w\s-]', '', str(antenna_system.address))
    clean_address = re.sub(r'\s+', '_', clean_address.strip())

    # Erstelle Subdirectory unter output_dir
    output_dir = Path(output_dir) / clean_address
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"  Output: {output_dir}")

    for ant in antenna_system.antennas:
        # Tilt-Anzeige: Zeige Bereich falls vorhanden
        if ant.tilt_from_deg != ant.tilt_to_deg:
            tilt_info = f"Tilt {ant.tilt_from_deg:.0f}° bis {ant.tilt_to_deg:.0f}° (Worst-Case-Suche)"
        else:
            tilt_info = f"Tilt {ant.tilt_deg:.0f}°"

        print(f"    - Ant {ant.id}: {ant.frequency_band} MHz, {ant.erp_watts:.0f} W, "
              f"Azimut {ant.azimuth_deg}°, {tilt_info}")

    # 2. Antennendiagramme laden
    print(f"\n[2/6] Lade Antennendiagramme...")

    # Suche ODS-Datei an mehreren Orten (msi-files/ hat Priorität)
    ods_filename = "Antennendämpfungen Hybrid AIR3268 R5.ods"
    ods_candidates = [
        Path("msi-files") / ods_filename,          # Standard: msi-files/Antennendämpfungen...ods
        Path(pattern_dir) / ods_filename,          # Alternativ: --pattern-dir
        Path("input") / ods_filename,              # Alternativ: input/
    ]

    ods_file = None
    for candidate in ods_candidates:
        if candidate.exists():
            ods_file = candidate
            break

    if ods_file:
        print(f"  → Nutze ODS-Datei: {ods_file.name}")
        patterns = load_patterns_from_ods(ods_file, antenna_system)
    else:
        # ODS nicht gefunden - Frage nach Standard-Patterns
        use_standard = ask_yes_no(
            question="ODS-Datei nicht gefunden - Standard-Patterns verwenden?",
            details=f"""📁 Gesuchte Datei: {ods_filename}
   Gesuchte Orte:
   {chr(10).join([f'   - {c}' for c in ods_candidates])}

🔧 Standard-Patterns nutzen (ITU-R/3GPP):
   - Generische Sektor-Antennendiagramme (65° / 7°)
   - Konservative Dämpfungswerte
   - Geeignet für Screening-Berechnungen

⚠️  Abweichungen zu OMEN-Referenzwerten möglich (typisch 5-15%)

💡 Falls MSI-Daten vorhanden:
   - ODS-Datei anlegen: {ods_filename}
   - In einem der gesuchten Verzeichnisse ablegen
   - Dann wird diese automatisch verwendet
""",
            default=True  # Standard: Ja
        )

        if use_standard:
            patterns = load_patterns_with_standard_fallback(None, antenna_system)
        else:
            error_and_exit(f"""ODS-Datei erforderlich: {ods_filename}

Gesuchte Orte:
{chr(10).join([f'  - {c}' for c in ods_candidates])}

Optionen:
1. MSI-Daten als ODS anlegen (empfohlen)
   → In msi-files/ oder input/ ablegen
2. --pattern-dir FLAG nutzen mit anderem Verzeichnis
3. Analyse ohne Antennendiagramme nicht möglich
""")

    print(f"  Geladene Diagramme: {len(patterns)}")

    # 3. Gebäudedaten laden
    print(f"\n[3/6] Lade Gebäudedaten...")
    buildings = []

    if citygml_file and Path(citygml_file).exists():
        print(f"  Lade lokale CityGML: {citygml_file}")
        center = (antenna_system.base_position.e, antenna_system.base_position.n)
        buildings = load_buildings_from_citygml(Path(citygml_file), center, radius_m)
    elif auto_download_buildings:
        print(f"  Lade von swisstopo (Radius: {radius_m}m)...")
        try:
            buildings = download_buildings_for_location(
                antenna_system.base_position,
                radius_m,
            )
        except Exception as e:
            print(f"\n{'='*60}")
            print("FEHLER: Gebäude-Download fehlgeschlagen")
            print(f"{'='*60}")
            print(f"Grund: {e}")
            print()
            print("Mögliche Lösungen:")
            print("  1. Lokale CityGML-Datei verwenden: --citygml <pfad.gml>")
            print("  2. Internetverbindung prüfen")
            print("  3. swissBUILDINGS3D API-Status prüfen")
            print(f"{'='*60}")
            raise SystemExit(1)

    if not buildings:
        print(f"\n{'='*60}")
        print("FEHLER: Keine Gebäude gefunden")
        print(f"{'='*60}")
        print(f"Suchradius: {radius_m}m um {antenna_system.base_position.e:.0f} / {antenna_system.base_position.n:.0f}")
        print()
        print("Mögliche Ursachen:")
        print("  - Keine Gebäude im Suchradius vorhanden")
        print("  - Koordinaten außerhalb der Schweiz")
        print("  - Radius zu klein (Standard: 100m)")
        print()
        print("Lösungen:")
        print("  - Radius erhöhen: --radius 200")
        print("  - Lokale CityGML-Datei verwenden: --citygml <pfad.gml>")
        print(f"{'='*60}")
        raise SystemExit(1)

    print(f"  Gebäude geladen: {len(buildings)}")

    # 3b. Katasterparzellen laden und virtuelle Gebäude erstellen
    # TEMPORÄR DEAKTIVIERT wegen langer API-Ladezeiten
    virtual_buildings_list = []
    virtual_building_objects = []

    # Aktiviere virtuelle Gebäude mit: --enable-virtual-buildings
    enable_virtual = False  # TODO: Als CLI-Parameter hinzufügen

    if enable_virtual:
        print(f"\n[3b/6] Lade Katasterparzellen und erstelle virtuelle Gebäude...")
        try:
            from .loaders.parcel_loader import load_parcels_in_radius
            from .analysis.virtual_buildings import (
                find_empty_parcels_with_virtual_buildings,
                convert_virtual_to_building
            )

            print(f"  Lade Parzellen im Radius {radius_m}m...")
            parcels = load_parcels_in_radius(
                center_e=antenna_system.base_position.e,
                center_n=antenna_system.base_position.n,
                radius_m=radius_m
            )
            print(f"  → {len(parcels)} Parzellen gefunden")

            if parcels:
                print(f"  Analysiere leere Parzellen...")
                virtual_buildings_list = find_empty_parcels_with_virtual_buildings(
                    parcels=parcels,
                    buildings=buildings,
                    setback_m=3.0  # 3m Grenzabstand
                )
                print(f"  → {len(virtual_buildings_list)} leere Parzellen identifiziert")

                # Konvertiere zu Building-Objekten
                for vb in virtual_buildings_list:
                    building_obj = convert_virtual_to_building(vb)
                    virtual_building_objects.append(building_obj)

                if virtual_building_objects:
                    print(f"  → {len(virtual_building_objects)} virtuelle Gebäude erstellt")

        except ImportError as e:
            print(f"  WARNUNG: Shapely nicht installiert - virtuelle Gebäude übersprungen")
            print(f"  Install mit: pip install shapely")
        except Exception as e:
            print(f"  WARNUNG: Virtuelle Gebäude konnten nicht erstellt werden: {e}")

    # 4. Fassaden- und Dachpunkte generieren
    print(f"\n[4/6] Generiere Fassaden- und Dachpunkte (Auflösung: {resolution_m}m)...")
    all_points = []

    for building in buildings:
        # Fassaden
        facade_points = sample_all_facades(
            building.wall_surfaces,
            resolution_m,
            building.id,
        )
        all_points.extend(facade_points)

        # Dächer
        roof_points = sample_all_roofs(
            building.roof_surfaces,
            resolution_m,
            building.id,
        )
        all_points.extend(roof_points)

    # Virtuelle Gebäude samplen
    if virtual_building_objects:
        print(f"  Sample virtuelle Gebäude...")
        virtual_points_count = 0
        for virt_building in virtual_building_objects:
            # Fassaden
            facade_points = sample_all_facades(
                virt_building.wall_surfaces,
                resolution_m,
                virt_building.id,
            )
            all_points.extend(facade_points)
            virtual_points_count += len(facade_points)

        print(f"  → {virtual_points_count} virtuelle Messpunkte hinzugefügt")

    # Nach Radius filtern
    all_points = filter_points_by_distance(
        all_points,
        antenna_system.base_position.e,
        antenna_system.base_position.n,
        radius_m,
    )

    print(f"  Fassadenpunkte: {len(all_points)} ({len([p for p in all_points if 'VIRTUAL' in p.building_id])} virtuell)")

    # 5. E-Feldstärke berechnen
    print(f"\n[5/6] Berechne E-Feldstärken...")

    # Parallele oder serielle Berechnung
    if parallel and len(all_points) > 100:
        print(f"  → Parallele Berechnung mit {n_workers or 'allen'} CPU-Kernen...")
        from .physics.summation_parallel import calculate_all_points_parallel
        results = calculate_all_points_parallel(
            all_points, antenna_system, patterns, n_workers=n_workers
        )
    else:
        if parallel:
            print(f"  → Serielle Berechnung (zu wenige Punkte für Parallelisierung)")
        results = calculate_all_points(all_points, antenna_system, patterns)

    print(f"  Berechnete Punkte: {len(results)}")

    # 5b. Line-of-Sight Analyse (VOR Hotspot-Identifikation!)
    # Gebäude im LOS dämpfen die Strahlung → E-Feld reduzieren
    if results and buildings:
        print(f"  → LOS-Analyse...")
        from .geometry.line_of_sight import add_los_info_to_results

        # WICHTIG: Berechne Mast-Offset (Antennen sind typischerweise 3-5m über dem Dach)
        try:
            # Versuche die höchste Antennenposition zu finden
            antenna_heights = [ant.position.h for ant in antenna_system.antennas if hasattr(ant, 'position')]
            if antenna_heights:
                max_antenna_height = max(antenna_heights)
                mast_offset = max_antenna_height - antenna_system.base_position.h
            else:
                # Fallback: +3m Mast-Offset
                mast_offset = 3.0
        except:
            # Fallback: +3m Mast-Offset
            mast_offset = 3.0

        # Kombiniere reale und virtuelle Gebäude für LOS-Analyse
        all_buildings_for_los = buildings + virtual_building_objects

        add_los_info_to_results(
            results=results,
            antenna_position=antenna_system.base_position,  # Basis-Position
            buildings=all_buildings_for_los,  # Inkl. virtuelle Gebäude
            mast_height_offset=mast_offset,  # Offset wird in der Funktion angewendet
        )

        # Wende Gebäudedämpfung an: E_gedämpft = E_frei * 10^(-Dämpfung_dB/20)
        nlos_count = 0
        total_damped = 0

        for r in results:
            if hasattr(r, 'building_attenuation_db') and r.building_attenuation_db > 0:
                # Original E-Feld speichern
                r.e_field_free_vm = r.e_field_vm

                # Dämpfungsfaktor berechnen
                attenuation_factor = 10 ** (-r.building_attenuation_db / 20.0)

                # Gedämpftes E-Feld
                r.e_field_vm = r.e_field_vm * attenuation_factor

                # exceeds_limit neu bewerten
                r.exceeds_limit = r.e_field_vm >= threshold_vm

                nlos_count += 1
                total_damped += 1

        los_count = len(results) - nlos_count

        print(f"    LOS (freie Sicht): {los_count} Punkte")
        print(f"    NLOS (blockiert): {nlos_count} Punkte")
        if total_damped > 0:
            print(f"    → {total_damped} Punkte mit Gebäudedämpfung reduziert")

    # Hotspots NACH Dämpfungsanwendung identifizieren
    hotspots = [r for r in results if r.exceeds_limit]
    print(f"  Hotspots (E >= {threshold_vm} V/m): {len(hotspots)}")

    if results:
        max_e = max(r.e_field_vm for r in results)
        avg_e = sum(r.e_field_vm for r in results) / len(results)
        print(f"  Maximale Feldstärke: {max_e:.2f} V/m")
        print(f"  Mittlere Feldstärke: {avg_e:.2f} V/m")

    # 6. Ergebnisse exportieren
    print(f"\n[6/6] Exportiere Ergebnisse nach: {output_dir}")

    # CSV-Exporte
    export_hotspots_csv(
        results,
        output_dir / "alle_punkte.csv",
        include_contributions=True,
    )
    export_hotspots_csv(
        hotspots,
        output_dir / "hotspots.csv",
        include_contributions=True,
    )

    # Detaillierte Hotspots mit Antennen-Spalten (Tilt, Distanz, etc.)
    export_hotspots_with_antenna_details_csv(
        hotspots,
        output_dir / "hotspots_detailliert.csv",
        antenna_system=antenna_system,
        buildings=buildings,
    )

    export_summary_csv(results, output_dir / "zusammenfassung.csv")

    # Aggregierte Hotspots (Gebäude×Floor mit EGID und Adresse)
    export_hotspots_aggregated_csv(
        hotspots,
        output_dir / "hotspots_aggregated.csv",
        buildings=buildings,
        antenna_system=antenna_system,
        lookup_addresses=True,  # Adressen via geo.admin.ch nachschlagen
        floor_height_m=3.0,
    )

    # GeoJSON (alle Punkte)
    export_to_geojson(results, output_dir / "ergebnisse.geojson")

    # GeoJSON optimiert für geo.admin.ch (nur Hotspots mit Styling)
    export_hotspots_for_geoadmin(
        results,
        antenna_system,
        output_dir / "hotspots_geoadmin.geojson",
        threshold_vm=threshold_vm,
    )

    # KML für geo.admin.ch (akzeptiertes Format!)
    export_hotspots_kml(
        results,
        antenna_system,
        output_dir / "hotspots_geoadmin.kml",
        threshold_vm=threshold_vm,
    )

    # VTK-Export für Paraview (immer exportieren)
    try:
        # Erstelle sauberen Dateinamen aus Projektbezeichnung
        import re
        project_name_clean = re.sub(r'[^\w\-]', '_', antenna_system.name)
        vtk_filename = f"paraview-{project_name_clean}.vtm"

        # Bereite Pattern-Daten für 3D-Keulen auf
        pattern_data_for_lobes = {}
        for antenna in antenna_system.antennas:
            # Suche passendes Pattern
            pattern_key = (antenna.antenna_type, antenna.frequency_band)
            if pattern_key in patterns:
                pattern = patterns[pattern_key]
                pattern_data_for_lobes[antenna.id] = {
                    "h_angles": pattern.h_angles,
                    "h_gains": pattern.h_gains,
                    "v_angles": pattern.v_angles,
                    "v_gains": pattern.v_gains,
                    "max_gain_dbi": getattr(pattern, 'max_gain_dbi', 0.0),
                }

        export_to_vtk(
            results,
            output_dir / vtk_filename,
            antenna_system=antenna_system,
            buildings=buildings,
            threshold_vm=threshold_vm,
            point_size=resolution_m,  # Voxel-Größe = Sampling-Auflösung
            use_voxels=True,  # Würfel statt Punkte (besser sichtbar)
            enable_terrain=True,  # Terrain-Mesh (SwissALTI3D)
            enable_antenna_lobes=True,  # 3D-Antennendiagramm-Keulen
            pattern_data=pattern_data_for_lobes,  # Pattern-Daten für Keulen
        )

        # ParaView State File generieren (automatische Einstellungen)
        try:
            from .output.paraview_state import create_paraview_state, create_quick_guide_text

            create_paraview_state(
                vtk_file=output_dir / vtk_filename,
                output_state=output_dir / "paraview_preset.pvsm",
                color_field="E_field_Vm",
                color_range=(0.0, 6.0),
                glyph_scale=2.0,
                use_glyph=False,  # Nicht im State, User macht manuell
            )

            # Kurzanleitung als README
            guide = create_quick_guide_text(output_dir / vtk_filename)
            with open(output_dir / "PARAVIEW_ANLEITUNG.md", 'w', encoding='utf-8') as f:
                f.write(guide)
            print(f"  ParaView-Anleitung: {output_dir / 'PARAVIEW_ANLEITUNG.md'}")

        except Exception as e:
            print(f"  HINWEIS: ParaView State konnte nicht erstellt werden: {e}")

    except Exception as e:
        print(f"  WARNUNG: VTK-Export fehlgeschlagen: {e}")

    # OMEN-Validierung
    if antenna_system.omen_locations:
        try:
            export_omen_validation_csv(
                results,
                antenna_system,
                output_dir / "omen_validierung.csv",
                patterns,  # Antennendiagramme für E-Feld-Berechnung
                tolerance_m=5.0,  # Nicht verwendet (Kompatibilität)
                tolerance_percent=10.0,
            )
        except Exception as e:
            print(f"  WARNUNG: OMEN-Validierung fehlgeschlagen: {e}")
            import traceback
            traceback.print_exc()

        # OMEN-Zuordnungs-Validierung
        try:
            export_omen_assignment_validation_csv(
                output_dir / "omen_zuordnung.csv",
                antenna_system=antenna_system,
                buildings=buildings,
                results=results,
            )
        except Exception as e:
            print(f"  WARNUNG: OMEN-Zuordnung-Validierung fehlgeschlagen: {e}")
            import traceback
            traceback.print_exc()

        # NeuOmen-Berechnungsblätter (Excel-Export für Hotspots)
        try:
            # Finde Template und Input-Dateien
            template_file = Path(__file__).parent.parent / "OMEN R37 leer.xls"

            create_neuomen_workbooks(
                output_dir=output_dir,
                template_file=template_file,
                input_omen_file=Path(omen_file),
                hotspots_aggregated_csv=output_dir / "hotspots_aggregated.csv",
                results=results,
                antenna_system=antenna_system,
            )
        except Exception as e:
            print(f"  WARNUNG: NeuOmen-Export fehlgeschlagen: {e}")
            import traceback
            traceback.print_exc()

    # Gebäude-Validierung (Geschosshöhen, NISV-Formel-Check)
    building_analyses = None
    if buildings:
        try:
            from .analysis import (
                analyze_building_heights,
                print_building_validation_summary,
            )

            building_analyses = analyze_building_heights(
                buildings,
                antenna_system=antenna_system,
            )

            print_building_validation_summary(building_analyses)

        except Exception as e:
            print(f"  WARNUNG: Gebäude-Validierung fehlgeschlagen: {e}")
            import traceback
            traceback.print_exc()

    # Kombinierte Gebäude-Übersicht (ersetzt pro_gebaeude.csv + gebaeude_validierung.csv)
    export_buildings_overview_csv(
        results,
        output_dir / "gebaeude_uebersicht.csv",
        building_analyses=building_analyses,
        antenna_system=antenna_system,
        buildings=buildings,
    )

    # Heatmap
    try:
        create_heatmap_image(
            results,
            output_dir / "heatmap.png",
            antenna_system=antenna_system,
            buildings=buildings,
            resolution=resolution_m,
            threshold_vm=threshold_vm,
            scale="1:1000",
            dpi=300,
            use_alpha=True,
        )
    except Exception as e:
        print(f"  WARNUNG: Heatmap-Erstellung fehlgeschlagen: {e}")

    # Hotspot-Marker-Map (für Gutachten)
    try:
        create_hotspot_marker_map(
            output_dir / "hotspots_aggregated.csv",
            output_dir / "hotspots_marker_map.png",
            antenna_system=antenna_system,
            buildings=buildings,
            results=results,  # Für präzise Max-E-Punkte und BBox
            scale="1:1000",
            dpi=300,
        )
    except Exception as e:
        print(f"  WARNUNG: Hotspot-Marker-Map fehlgeschlagen: {e}")

    # 3D-Visualisierung
    if visualize:
        print("\n[Visualisierung] Erstelle 3D-Ansicht...")
        try:
            # Prüfe ob Display verfügbar (für interaktive Ansicht)
            import os
            has_display = bool(os.environ.get('DISPLAY'))

            visualize_hotspots(
                results,
                antenna_system,
                buildings,
                output_path=output_dir / "visualisierung_3d.png",
                show=has_display,  # Nur zeigen wenn Display verfügbar
                threshold_vm=threshold_vm,
            )

            if not has_display:
                print(f"  → Screenshot gespeichert (kein Display für interaktive Ansicht)")
        except Exception as e:
            print(f"  WARNUNG: Visualisierung fehlgeschlagen: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print("Analyse abgeschlossen!")
    print("=" * 60)

    return results


def main():
    """CLI-Einstiegspunkt."""
    import argparse

    parser = argparse.ArgumentParser(
        description="EMF-Hotspot-Finder: Berechnet NISV-Überschreitungen an Gebäudefassaden"
    )
    parser.add_argument(
        "omen_file",
        type=Path,
        help="Pfad zur OMEN XLS-Datei",
    )
    parser.add_argument(
        "-p", "--pattern-dir",
        type=Path,
        default=Path("msi-files"),
        help="Verzeichnis mit Antennendiagramm-CSV-Dateien (default: msi-files/)",
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=Path("./output"),
        help="Basis-Ausgabeverzeichnis (default: ./output). Subdirectory wird automatisch aus Adresse (Global C4) erstellt.",
    )
    parser.add_argument(
        "-c", "--citygml",
        type=Path,
        default=None,
        help="Pfad zu lokaler CityGML-Datei (statt Auto-Download)",
    )
    parser.add_argument(
        "-r", "--radius",
        type=float,
        default=DEFAULT_RADIUS_M,
        help=f"Suchradius in Metern (default: {DEFAULT_RADIUS_M})",
    )
    parser.add_argument(
        "--resolution",
        type=float,
        default=DEFAULT_RESOLUTION_M,
        help=f"Rasterauflösung in Metern (default: {DEFAULT_RESOLUTION_M})",
    )
    parser.add_argument(
        "-t", "--threshold",
        type=float,
        default=AGW_LIMIT_VM,
        help=f"Schwellwert für Hotspots in V/m (default: {AGW_LIMIT_VM})",
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Keine automatischen Gebäude-Downloads",
    )
    parser.add_argument(
        "--viz",
        action="store_true",
        help="3D-Visualisierung aktivieren (default: deaktiviert wegen OpenGL-Problemen auf Headless-Servern)",
    )
    parser.add_argument(
        "--no-viz",
        action="store_true",
        help="Kompatibilität: Entspricht Default (3D-Viz deaktiviert)",
    )
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Deaktiviere parallele Berechnung (für Debugging)",
    )
    parser.add_argument(
        "-j", "--workers",
        type=int,
        default=None,
        help="Anzahl paralleler Worker (default: alle CPU-Kerne)",
    )

    args = parser.parse_args()

    if not args.omen_file.exists():
        print(f"Fehler: Datei nicht gefunden: {args.omen_file}")
        sys.exit(1)

    analyze_site(
        omen_file=args.omen_file,
        pattern_dir=args.pattern_dir,
        output_dir=args.output_dir,
        citygml_file=args.citygml,
        radius_m=args.radius,
        resolution_m=args.resolution,
        threshold_vm=args.threshold,
        auto_download_buildings=not args.no_download,
        visualize=args.viz,  # Nur mit --viz aktivieren
        parallel=not args.no_parallel,  # Parallele Berechnung (default: aktiviert)
        n_workers=args.workers,  # Anzahl Worker (None = CPU-Kerne)
    )


if __name__ == "__main__":
    main()
