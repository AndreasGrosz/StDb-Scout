"""
CSV-Export für Hotspot-Ergebnisse
"""

import csv
from pathlib import Path
from typing import List, Optional
import numpy as np

from ..models import HotspotResult, AntennaSystem
from ..config import AGW_LIMIT_VM


def export_hotspots_csv(
    results: List[HotspotResult],
    output_path: Path,
    include_contributions: bool = False,
    floor_height_m: float = 3.0,
) -> None:
    """
    Exportiert Hotspot-Ergebnisse als CSV-Datei.

    Args:
        results: Liste von HotspotResult
        output_path: Ausgabepfad für CSV
        include_contributions: Ob Einzelbeiträge der Antennen exportiert werden
        floor_height_m: Geschosshöhe für Floor-Level-Berechnung (default: 3m)
    """
    from collections import defaultdict
    import numpy as np

    # Berechne Floor-Levels pro Gebäude
    by_building = defaultdict(list)
    for r in results:
        by_building[r.building_id].append(r)

    # Für jedes Gebäude: Floor-Levels und Z-Max pro Level bestimmen
    floor_info = {}  # (building_id, z) -> (floor_level, floor_z_max)

    for building_id, building_results in by_building.items():
        # Min-Z des Gebäudes als Referenz (Erdgeschoss)
        z_coords = [r.z for r in building_results]
        z_min = min(z_coords)
        z_max = max(z_coords)

        # Stratifiziere in Floor-Levels
        levels_in_building = defaultdict(list)
        for r in building_results:
            floor_level = int((r.z - z_min) / floor_height_m)
            levels_in_building[floor_level].append(r.z)

        # Z-Max für jedes Level
        level_z_max = {level: max(z_list) for level, z_list in levels_in_building.items()}

        # Zuordnung für alle Punkte
        for r in building_results:
            floor_level = int((r.z - z_min) / floor_height_m)
            floor_info[(building_id, r.z)] = (floor_level, level_z_max[floor_level])

    fieldnames = [
        "building_id",
        "x",
        "y",
        "z",
        "floor_level",
        "floor_z_max",
        "e_field_vm",
        "exceeds_limit",
        "los_status",
        "num_buildings_blocking",
        "building_attenuation_db",
    ]

    if include_contributions:
        fieldnames.append("contributions")

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            # Floor-Level und Z-Max abrufen
            floor_level, floor_z_max = floor_info.get(
                (result.building_id, result.z),
                (0, result.z)  # Fallback
            )

            # LOS-Information (falls vorhanden)
            has_los = getattr(result, 'has_los', True)
            num_blocking = getattr(result, 'num_buildings_blocking', 0)
            building_atten = getattr(result, 'building_attenuation_db', 0.0)

            row = {
                "building_id": result.building_id,
                "x": f"{result.x:.2f}",
                "y": f"{result.y:.2f}",
                "z": f"{result.z:.2f}",
                "floor_level": floor_level,
                "floor_z_max": f"{floor_z_max:.2f}",
                "e_field_vm": f"{result.e_field_vm:.4f}",
                "exceeds_limit": result.exceeds_limit,
                "los_status": "LOS" if has_los else "NLOS",
                "num_buildings_blocking": num_blocking,
                "building_attenuation_db": f"{building_atten:.1f}",
            }

            if include_contributions:
                # Format: "ant1:E=0.5,tilt=-12,dist=50;ant2:..."
                contrib_str = ";".join(
                    f"{c.antenna_id}:E={c.e_field_vm:.4f},tilt={c.critical_tilt_deg:.1f},dist={c.distance_m:.1f}"
                    for c in result.contributions
                )
                row["contributions"] = contrib_str

            writer.writerow(row)


def export_hotspots_with_antenna_details_csv(
    results: List[HotspotResult],
    output_path: Path,
    antenna_system: AntennaSystem,
    buildings=None,  # Optional: Liste von Buildings für EGID
) -> None:
    """
    Exportiert Hotspots mit detaillierten Antennenbeiträgen als separate Spalten.

    Args:
        results: Liste von HotspotResult
        output_path: Ausgabepfad für CSV
        antenna_system: AntennaSystem für Antennen-IDs
        buildings: Optional - Liste von Buildings für EGID/Adresse
    """
    if not results:
        return

    # EGID-Map und Koordinaten-Map erstellen
    egid_map = {}
    building_coords = {}  # building_id -> (e, n)

    if buildings:
        for building in buildings:
            egid_map[building.id] = building.egid
            # Speichere zentrale Koordinaten des Gebäudes (Mittelwert aller Walls)
            if building.wall_surfaces:
                e_coords = []
                n_coords = []
                for wall in building.wall_surfaces:
                    # vertices ist numpy array mit shape (N, 3) - [E, N, H]
                    if len(wall.vertices) > 0:
                        e_coords.extend(wall.vertices[:, 0])  # E-Koordinaten
                        n_coords.extend(wall.vertices[:, 1])  # N-Koordinaten
                if e_coords and n_coords:
                    building_coords[building.id] = (sum(e_coords) / len(e_coords), sum(n_coords) / len(n_coords))

    # Adressen laden (falls EGIDs vorhanden)
    address_cache = {}

    # Erstelle Map von EGID zu building_id und Koordinaten
    egid_to_building = {}
    for building_id, egid in egid_map.items():
        if egid and egid != "":
            egid_to_building[egid] = (building_id, building_coords.get(building_id))

    if egid_to_building:
        from ..loaders.geoadmin_api import lookup_address_by_egid
        print(f"  Lade Adressen für {len(egid_to_building)} Gebäude via EGID...")

        for egid, (building_id, coords) in egid_to_building.items():
            # Übergebe Koordinaten für Validierung falls vorhanden
            if coords:
                addr = lookup_address_by_egid(egid, building_e=coords[0], building_n=coords[1])
            else:
                addr = lookup_address_by_egid(egid)

            if addr:
                address_cache[egid] = addr['full_address']

    # Fallback: Koordinaten-basierte Lookups für Gebäude ohne EGID/Adresse
    from ..loaders.geoadmin_api import lookup_address_by_coordinates
    buildings_without_address = []

    for result in results:
        egid = egid_map.get(result.building_id, "")
        has_address = (egid and egid in address_cache)

        if not has_address:
            buildings_without_address.append((result.building_id, result.x, result.y))

    if buildings_without_address:
        print(f"  Lade Adressen für {len(buildings_without_address)} Gebäude via Koordinaten...")

        for building_id, x, y in buildings_without_address:
            addr = lookup_address_by_coordinates(x, y)
            if addr and addr['full_address']:
                # Store in address_cache with building_id as key (since no EGID)
                address_cache[f"coord_{building_id}"] = addr['full_address']

    # Bestimme maximale Anzahl an Antennen
    max_antennas = len(antenna_system.antennas)

    # Basis-Felder
    fieldnames = [
        "building_id",
        "egid",
        "address",
        "x",
        "y",
        "z",
        "e_field_total_vm",
        "exceeds_limit",
        "los_status",
        "num_buildings_blocking",
        "building_attenuation_db",
    ]

    # Für jede Antenne: E-Feld, Tilt, Distanz, Dämpfungen
    for i in range(1, max_antennas + 1):
        fieldnames.extend([
            f"ant{i}_e_vm",
            f"ant{i}_tilt_deg",
            f"ant{i}_dist_m",
            f"ant{i}_h_atten_db",
            f"ant{i}_v_atten_db",
        ])

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            # EGID und Adresse nachschlagen
            egid = egid_map.get(result.building_id, "")
            address = address_cache.get(egid, "")

            # Fallback: Koordinaten-basierte Adresse
            if not address:
                address = address_cache.get(f"coord_{result.building_id}", "")

            # LOS-Information (falls vorhanden)
            has_los = getattr(result, 'has_los', True)
            num_blocking = getattr(result, 'num_buildings_blocking', 0)
            building_atten = getattr(result, 'building_attenuation_db', 0.0)

            row = {
                "building_id": result.building_id,
                "egid": egid,
                "address": address,
                "x": f"{result.x:.2f}",
                "y": f"{result.y:.2f}",
                "z": f"{result.z:.2f}",
                "e_field_total_vm": f"{result.e_field_vm:.4f}",
                "exceeds_limit": result.exceeds_limit,
                "los_status": "LOS" if has_los else "NLOS",
                "num_buildings_blocking": num_blocking,
                "building_attenuation_db": f"{building_atten:.1f}",
            }

            # Antennenbeiträge als Spalten
            for contrib in result.contributions:
                ant_id = contrib.antenna_id
                row[f"ant{ant_id}_e_vm"] = f"{contrib.e_field_vm:.4f}"
                row[f"ant{ant_id}_tilt_deg"] = f"{contrib.critical_tilt_deg:.1f}"
                row[f"ant{ant_id}_dist_m"] = f"{contrib.distance_m:.1f}"
                row[f"ant{ant_id}_h_atten_db"] = f"{contrib.h_attenuation_db:.2f}"
                row[f"ant{ant_id}_v_atten_db"] = f"{contrib.v_attenuation_db:.2f}"

            writer.writerow(row)


def export_summary_csv(
    results: List[HotspotResult],
    output_path: Path,
) -> None:
    """
    Exportiert eine Zusammenfassung der Hotspot-Analyse.
    """
    total_points = len(results)
    hotspots = [r for r in results if r.exceeds_limit]
    num_hotspots = len(hotspots)

    if results:
        max_e = max(r.e_field_vm for r in results)
        avg_e = sum(r.e_field_vm for r in results) / total_points
    else:
        max_e = 0.0
        avg_e = 0.0

    # Gebäude mit Hotspots
    buildings_with_hotspots = set(r.building_id for r in hotspots)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Parameter", "Wert"])
        writer.writerow(["Geprüfte Punkte", total_points])
        writer.writerow(["Hotspots (E >= 5 V/m)", num_hotspots])
        writer.writerow(["Anteil Hotspots", f"{num_hotspots / max(total_points, 1) * 100:.2f}%"])
        writer.writerow(["Maximale Feldstärke [V/m]", f"{max_e:.4f}"])
        writer.writerow(["Mittlere Feldstärke [V/m]", f"{avg_e:.4f}"])
        writer.writerow(["Grenzwert [V/m]", AGW_LIMIT_VM])
        writer.writerow(["Gebäude mit Hotspots", len(buildings_with_hotspots)])


def export_buildings_overview_csv(
    results: List[HotspotResult],
    output_path: Path,
    building_analyses=None,  # Optional: Liste von BuildingAnalysis aus building_validation
    antenna_system=None,  # Optional: AntennaSystem für OMEN-Zuordnung
    buildings=None,  # Optional: Liste von Buildings für EGID/Adresse
) -> None:
    """
    Exportiert kombinierte Gebäude-Übersicht mit Hotspot-Statistik und NISV-Validierung.

    Vereint die Daten aus pro_gebaeude.csv und gebaeude_validierung.csv in einer Datei.

    Args:
        results: Liste von HotspotResult
        output_path: Pfad für CSV-Datei
        building_analyses: Optional - BuildingAnalysis-Daten aus building_validation
        antenna_system: Optional - AntennaSystem für OMEN-Zuordnung
        buildings: Optional - Liste von Buildings für EGID-Zuordnung
    """
    from collections import defaultdict
    import numpy as np

    # Gruppiere nach Gebäude
    by_building = defaultdict(list)
    for r in results:
        by_building[r.building_id].append(r)

    # BuildingAnalysis in Dict umwandeln für schnellen Zugriff
    analysis_map = {}
    if building_analyses:
        for analysis in building_analyses:
            analysis_map[analysis.building_id] = analysis

    # EGID-Map und Building-Map erstellen (falls buildings vorhanden)
    egid_map = {}
    building_map = {}
    if buildings:
        for building in buildings:
            egid_map[building.id] = building.egid
            building_map[building.id] = building

    # OMEN→Gebäude N:1-Mapping: Point-in-Building Check
    # Mehrere OMENs können zum selben Gebäude gehören (eine OMEN pro Wohnung)
    omen_to_building = defaultdict(list)

    def point_in_polygon_2d(x, y, polygon_points):
        """Ray-casting algorithm für Point-in-Polygon Test"""
        n = len(polygon_points)
        inside = False
        p1x, p1y = polygon_points[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon_points[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside

    if antenna_system and antenna_system.omen_locations:
        # Für jeden OMEN: Prüfe ob Punkt INNERHALB eines Gebäudes liegt
        for omen in antenna_system.omen_locations:
            for building_id, building_results in by_building.items():
                building_obj = building_map.get(building_id)
                if not building_obj:
                    continue

                # 1. Höhencheck: OMEN muss innerhalb Gebäudehöhe liegen
                if building_obj.wall_surfaces or building_obj.roof_surfaces:
                    all_surfaces = building_obj.wall_surfaces + building_obj.roof_surfaces
                    all_z = [v[2] for surface in all_surfaces for v in surface.vertices]
                    building_min_z = min(all_z)
                    building_max_z = max(all_z)
                else:
                    # Fallback
                    building_min_z = min(r.z for r in building_results)
                    building_max_z = max(r.z for r in building_results)

                # Kleine Toleranz für Messungenauigkeiten (±0.5m)
                height_tolerance = 0.5
                if not ((building_min_z - height_tolerance) <= omen.position.h <= (building_max_z + height_tolerance)):
                    continue

                # 2. Point-in-Polygon Check: OMEN muss horizontal innerhalb Grundriss liegen
                all_surfaces = building_obj.wall_surfaces + building_obj.roof_surfaces
                if not all_surfaces:
                    continue

                # Sammle alle 2D-Punkte und erstelle ConvexHull
                all_points_2d = set()
                for surface in all_surfaces:
                    for vertex in surface.vertices:
                        all_points_2d.add((round(vertex[0], 2), round(vertex[1], 2)))

                if len(all_points_2d) < 3:
                    continue

                # ConvexHull approximation via sorted points
                points_list = list(all_points_2d)
                from scipy.spatial import ConvexHull
                try:
                    hull = ConvexHull(points_list)
                    hull_points = [points_list[i] for i in hull.vertices]
                except:
                    # Fallback: Nutze alle Punkte
                    hull_points = points_list

                # Prüfe ob OMEN-Punkt innerhalb liegt
                if point_in_polygon_2d(omen.position.e, omen.position.n, hull_points):
                    omen_to_building[building_id].append(f"O{omen.nr}")
                    break  # OMEN kann nur in einem Gebäude sein

    # Adress-Lookup (falls gewünscht)
    address_cache = {}

    # Erstelle Map von EGID zu building_id und Koordinaten
    egid_to_building_coords = {}
    for building_id, egid in egid_map.items():
        if egid and egid != "":
            building_results = by_building.get(building_id, [])
            if building_results:
                # Nutze Mittelpunkt des Gebäudes
                center_x = np.mean([r.x for r in building_results])
                center_y = np.mean([r.y for r in building_results])
                egid_to_building_coords[egid] = (center_x, center_y)

    if egid_to_building_coords:
        from ..loaders.geoadmin_api import lookup_address_by_egid
        print(f"  Lade Adressen für {len(egid_to_building_coords)} Gebäude via EGID...")

        for egid, (center_e, center_n) in egid_to_building_coords.items():
            # Übergebe Koordinaten für Validierung
            addr = lookup_address_by_egid(egid, building_e=center_e, building_n=center_n)
            if addr:
                address_cache[egid] = addr['full_address']

    # Fallback: Koordinaten-basierte Lookups für Gebäude ohne EGID/Adresse
    from ..loaders.geoadmin_api import lookup_address_by_coordinates
    buildings_without_address = []

    for building_id, building_results in by_building.items():
        egid = egid_map.get(building_id, "")
        has_address = (egid and egid in address_cache)

        if not has_address and building_results:
            # Nutze Mittelpunkt des Gebäudes
            center_x = np.mean([r.x for r in building_results])
            center_y = np.mean([r.y for r in building_results])
            buildings_without_address.append((building_id, center_x, center_y))

    if buildings_without_address:
        print(f"  Lade Adressen für {len(buildings_without_address)} Gebäude via Koordinaten...")

        for building_id, x, y in buildings_without_address:
            addr = lookup_address_by_coordinates(x, y)
            if addr and addr['full_address']:
                address_cache[f"coord_{building_id}"] = addr['full_address']

    # Spalten-Definition: Kombination aus beiden CSVs
    fieldnames = [
        # Identifikation
        "building_id",
        "egid",
        "address",
        # Max-Hotspot Geodaten
        "max_hotspot_x",
        "max_hotspot_y",
        "omen_nr",
        # Geometrie
        "min_z",
        "max_z",
        "height_m",
        "num_floors",
        "estimated_floors",
        "real_floor_height_m",
        # Hotspot-Statistik
        "num_points",
        "num_hotspots",
        "max_e_vm",
        "avg_e_vm",
        # NISV-Validierung
        "z_top_floor_nisv",
        "z_top_floor_conservative",
        # OMEN-Vergleich
        "omen_floors",
        "omen_z_given",
        "omen_z_nisv",
        "omen_z_conservative",
        "missing_floors",
        "z_deviation_nisv",
        "z_deviation_conservative",
        # Warnungen
        "has_high_ceilings",
        "is_likely_hall",
        "ceiling_warning",
        "recommendation",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for idx, (building_id, building_results) in enumerate(sorted(by_building.items())):
            # Hotspot-Statistik berechnen
            num_points = len(building_results)
            num_hotspots = sum(1 for r in building_results if r.exceeds_limit)
            max_e = max(r.e_field_vm for r in building_results)
            avg_e = sum(r.e_field_vm for r in building_results) / num_points
            min_z = min(r.z for r in building_results)
            max_z = max(r.z for r in building_results)

            # Finde Punkt mit max E-Feldstärke (für Geodaten)
            max_e_point = max(building_results, key=lambda r: r.e_field_vm)
            max_hotspot_x = max_e_point.x
            max_hotspot_y = max_e_point.y

            # Gebäudehöhe und Stockwerke
            height_m = max_z - min_z
            num_floors = max(1, int(height_m / 3.0))  # Annahme: 3m pro Stockwerk

            # EGID
            egid = egid_map.get(building_id, "")

            # Adresse
            address = address_cache.get(egid, "")

            # Fallback: Koordinaten-basierte Adresse
            if not address:
                address = address_cache.get(f"coord_{building_id}", "")

            # OMEN-Nr(n) - mehrere OMENs möglich (eine pro Wohnung)
            omen_nr = ",".join(omen_to_building.get(building_id, []))

            # BuildingAnalysis-Daten (falls vorhanden)
            analysis = analysis_map.get(building_id)

            # Empfehlung berechnen (gleiche Logik wie in building_validation.py)
            recommendation = ""
            if analysis:
                if analysis.has_high_ceilings:
                    recommendation += "⚠️ Hohe Decken: NISV-Formel prüfen! "

                if analysis.missing_floors and analysis.missing_floors > 0:
                    recommendation += f"⚠️ {analysis.missing_floors} Geschoss(e) fehlen in OMEN! "

                if analysis.z_deviation_conservative and abs(analysis.z_deviation_conservative) > 1.0:
                    recommendation += f"⚠️ Konservativ {analysis.z_deviation_conservative:.1f}m höher als OMEN-Z! "

                if analysis.z_deviation_nisv and abs(analysis.z_deviation_nisv) > 1.0 and abs(analysis.z_deviation_nisv) > abs(analysis.z_deviation_conservative or 0):
                    recommendation += f"(NISV weicht {analysis.z_deviation_nisv:.1f}m ab) "

            if not recommendation:
                recommendation = "✓ OK"

            row = {
                # Identifikation
                "building_id": building_id,
                "egid": egid,
                "address": address,
                # Max-Hotspot Geodaten
                "max_hotspot_x": f"{max_hotspot_x:.2f}",
                "max_hotspot_y": f"{max_hotspot_y:.2f}",
                "omen_nr": omen_nr,
                # Geometrie
                "min_z": f"{min_z:.2f}",
                "max_z": f"{max_z:.2f}",
                "height_m": f"{height_m:.2f}",
                "num_floors": num_floors,
                "estimated_floors": analysis.estimated_floors if analysis else "",
                "real_floor_height_m": f"{analysis.real_floor_height_m:.2f}" if analysis and analysis.real_floor_height_m is not None else "",
                # Hotspot-Statistik
                "num_points": num_points,
                "num_hotspots": num_hotspots,
                "max_e_vm": f"{max_e:.4f}",
                "avg_e_vm": f"{avg_e:.4f}",
                # NISV-Validierung
                "z_top_floor_nisv": f"{analysis.z_top_floor_nisv:.2f}" if analysis and analysis.z_top_floor_nisv is not None else "",
                "z_top_floor_conservative": f"{analysis.z_top_floor_conservative:.2f}" if analysis and analysis.z_top_floor_conservative is not None else "",
                # OMEN-Vergleich
                "omen_floors": analysis.omen_floors if analysis and analysis.omen_floors is not None else "",
                "omen_z_given": f"{analysis.omen_z_given:.2f}" if analysis and analysis.omen_z_given is not None else "",
                "omen_z_nisv": f"{analysis.omen_z_nisv:.2f}" if analysis and analysis.omen_z_nisv is not None else "",
                "omen_z_conservative": f"{analysis.omen_z_conservative:.2f}" if analysis and analysis.omen_z_conservative is not None else "",
                "missing_floors": analysis.missing_floors if analysis and analysis.missing_floors is not None else "",
                "z_deviation_nisv": f"{analysis.z_deviation_nisv:.2f}" if analysis and analysis.z_deviation_nisv is not None else "",
                "z_deviation_conservative": f"{analysis.z_deviation_conservative:.2f}" if analysis and analysis.z_deviation_conservative is not None else "",
                # Warnungen
                "has_high_ceilings": analysis.has_high_ceilings if analysis else "",
                "is_likely_hall": analysis.is_likely_hall if analysis else "",
                "ceiling_warning": analysis.ceiling_warning if analysis else "",
                "recommendation": recommendation,
            }

            writer.writerow(row)


def export_hotspots_aggregated_csv(
    results: List[HotspotResult],
    output_path: Path,
    buildings=None,  # Optional: Liste von Buildings für EGID
    antenna_system=None,  # Optional: AntennaSystem für OMEN
    lookup_addresses: bool = False,  # Ob Adressen via API nachgeschlagen werden
    floor_height_m: float = 3.0,
) -> None:
    """
    Exportiert Hotspots aggregiert auf Gebäude-Ebene.

    Für jedes Gebäude: Maximale E-Feldstärke über alle Stockwerke.
    Mit EGID, Adresse (optional) und OMEN-Nr.

    Args:
        results: Liste von HotspotResult (nur Hotspots)
        output_path: Pfad für CSV-Datei
        buildings: Optional - Liste von Buildings für EGID
        antenna_system: Optional - AntennaSystem für OMEN-Zuordnung
        lookup_addresses: Ob Adressen via geo.admin.ch nachgeschlagen werden
        floor_height_m: Geschosshöhe (aktuell ungenutzt, für Kompatibilität beibehalten)
    """
    from collections import defaultdict
    import numpy as np

    if not results:
        print("  HINWEIS: Keine Hotspots zum Exportieren.")
        return

    # Gruppiere nach Gebäude
    by_building = defaultdict(list)
    for r in results:
        by_building[r.building_id].append(r)

    # EGID-Map und Building-Map für Höhen
    egid_map = {}
    building_map = {}
    if buildings:
        for building in buildings:
            egid_map[building.id] = building.egid
            building_map[building.id] = building

    # OMEN→Gebäude N:1-Mapping: Point-in-Building Check
    # Mehrere OMENs können zum selben Gebäude gehören (eine OMEN pro Wohnung)
    omen_to_building = defaultdict(list)

    def point_in_polygon_2d(x, y, polygon_points):
        """Ray-casting algorithm für Point-in-Polygon Test"""
        n = len(polygon_points)
        inside = False
        p1x, p1y = polygon_points[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon_points[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside

    if antenna_system and antenna_system.omen_locations:
        # Für jeden OMEN: Prüfe ob Punkt INNERHALB eines Gebäudes liegt
        for omen in antenna_system.omen_locations:
            for building_id, building_results in by_building.items():
                building_obj = building_map.get(building_id)
                if not building_obj:
                    continue

                # 1. Höhencheck: OMEN muss innerhalb Gebäudehöhe liegen
                if building_obj.wall_surfaces or building_obj.roof_surfaces:
                    all_surfaces = building_obj.wall_surfaces + building_obj.roof_surfaces
                    all_z = [v[2] for surface in all_surfaces for v in surface.vertices]
                    building_min_z = min(all_z)
                    building_max_z = max(all_z)
                else:
                    # Fallback
                    building_min_z = min(r.z for r in building_results)
                    building_max_z = max(r.z for r in building_results)

                # Kleine Toleranz für Messungenauigkeiten (±0.5m)
                height_tolerance = 0.5
                if not ((building_min_z - height_tolerance) <= omen.position.h <= (building_max_z + height_tolerance)):
                    continue

                # 2. Point-in-Polygon Check: OMEN muss horizontal innerhalb Grundriss liegen
                all_surfaces = building_obj.wall_surfaces + building_obj.roof_surfaces
                if not all_surfaces:
                    continue

                # Sammle alle 2D-Punkte und erstelle ConvexHull
                all_points_2d = set()
                for surface in all_surfaces:
                    for vertex in surface.vertices:
                        all_points_2d.add((round(vertex[0], 2), round(vertex[1], 2)))

                if len(all_points_2d) < 3:
                    continue

                # ConvexHull via scipy
                points_list = list(all_points_2d)
                from scipy.spatial import ConvexHull
                try:
                    hull = ConvexHull(points_list)
                    hull_points = [points_list[i] for i in hull.vertices]
                except:
                    # Fallback: Nutze alle Punkte
                    hull_points = points_list

                # Prüfe ob OMEN-Punkt innerhalb liegt
                if point_in_polygon_2d(omen.position.e, omen.position.n, hull_points):
                    omen_to_building[building_id].append(f"O{omen.nr}")
                    break  # OMEN kann nur in einem Gebäude sein

    # Adress-Cache
    address_cache = {}
    if lookup_addresses:
        from ..loaders.geoadmin_api import lookup_address_by_egid
        print("  Lade Adressen von geo.admin.ch...")

        for building_id in by_building.keys():
            egid = egid_map.get(building_id, "")
            if egid:
                building_results = by_building[building_id]
                if building_results:
                    # Nutze Mittelpunkt des Gebäudes für Validierung
                    center_x = np.mean([r.x for r in building_results])
                    center_y = np.mean([r.y for r in building_results])
                    addr = lookup_address_by_egid(egid, building_e=center_x, building_n=center_y)
                else:
                    addr = lookup_address_by_egid(egid)

                if addr:
                    address_cache[building_id] = addr['full_address']

    fieldnames = [
        "building_id",
        "egid",
        "address",
        "omen_nr",
        "max_e_vm",
        "center_x",
        "center_y",
        "center_z",
        "los_status",
        "num_buildings_blocking",
        "building_attenuation_db",
    ]

    aggregated_rows = []

    for building_id, building_results in sorted(by_building.items()):
        # EGID
        egid = egid_map.get(building_id, "")

        # Adresse
        address = address_cache.get(building_id, "")

        # OMEN-Nr(n) - mehrere OMENs möglich (eine pro Wohnung)
        omen_nr = ",".join(omen_to_building.get(building_id, []))

        # Max E-Feld über gesamtes Gebäude
        max_point = max(building_results, key=lambda r: r.e_field_vm)

        # LOS-Informationen vom Max-Punkt
        has_los = getattr(max_point, 'has_los', True)
        num_blocking = getattr(max_point, 'num_buildings_blocking', 0)
        building_atten = getattr(max_point, 'building_attenuation_db', 0.0)

        aggregated_rows.append({
            "building_id": building_id,
            "egid": egid,
            "address": address,
            "omen_nr": omen_nr,
            "max_e_vm": f"{max_point.e_field_vm:.4f}",
            "center_x": f"{max_point.x:.2f}",
            "center_y": f"{max_point.y:.2f}",
            "center_z": f"{max_point.z:.2f}",
            "los_status": "LOS" if has_los else "NLOS",
            "num_buildings_blocking": num_blocking,
            "building_attenuation_db": f"{building_atten:.1f}",
        })

    # CSV schreiben
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(aggregated_rows)

    print(f"  Aggregierte Hotspots: {len(aggregated_rows)} Gebäude")


def export_omen_validation_csv(
    results: List[HotspotResult],
    antenna_system: AntennaSystem,
    output_path: Path,
    patterns: dict,  # Antennendiagramme
    tolerance_m: float = 0.5,
    tolerance_percent: float = 10.0,
) -> None:
    """
    Erstellt einen Validierungsbericht für OMEN-Punkte.

    Berechnet E-Feldstärken DIREKT an OMEN-Positionen (nicht am nächsten Fassadenpunkt!)
    und vergleicht mit Referenzwerten aus dem OMEN-Sheet.

    Args:
        results: Liste von HotspotResult (nur für Kontext, nicht für Berechnung)
        antenna_system: AntennaSystem mit OMEN-Locations
        output_path: Pfad für CSV-Datei
        patterns: Antennendiagramme für Berechnung
        tolerance_m: Nicht verwendet (Kompatibilität)
        tolerance_percent: Prozentuale Abweichungstoleranz für Warnung
    """
    from ..physics.summation import calculate_total_e_field_at_point
    from ..models import FacadePoint

    if not antenna_system.omen_locations:
        print("  HINWEIS: Keine OMEN-Locations im Antennensystem gefunden.")
        return

    # Filter für OMEN-Locations mit Referenzwert
    omen_with_ref = [
        omen for omen in antenna_system.omen_locations
        if omen.e_field_expected is not None
    ]

    if not omen_with_ref:
        print("  HINWEIS: Keine OMEN-Locations mit Referenzwerten gefunden.")
        return

    fieldnames = [
        "omen_nr",
        "omen_x",
        "omen_y",
        "omen_z",
        "e_expected_vm",
        "e_calculated_vm",
        "deviation_vm",
        "deviation_percent",
        "status",
    ]

    validation_results = []

    for omen in omen_with_ref:
        # Erstelle FacadePoint an OMEN-Position
        omen_point = FacadePoint(
            building_id=f"OMEN_{omen.nr}",
            x=omen.position.e,
            y=omen.position.n,
            z=omen.position.h,
            normal=np.array([0, 0, 1]),  # Dummy-Normal
        )

        # Berechne E-Feld DIREKT an dieser Position
        result = calculate_total_e_field_at_point(
            omen_point,
            antenna_system,
            patterns,
            building_attenuation_db=omen.building_attenuation_db,
        )

        e_calculated = result.e_field_vm
        deviation_vm = e_calculated - omen.e_field_expected
        deviation_percent = (deviation_vm / omen.e_field_expected) * 100

        if abs(deviation_percent) <= tolerance_percent:
            status = "OK"
        else:
            status = "DEVIATION"

        validation_results.append({
            "omen_nr": f"O{omen.nr}",
            "omen_x": f"{omen.position.e:.2f}",
            "omen_y": f"{omen.position.n:.2f}",
            "omen_z": f"{omen.position.h:.2f}",
            "e_expected_vm": f"{omen.e_field_expected:.4f}",
            "e_calculated_vm": f"{e_calculated:.4f}",
            "deviation_vm": f"{deviation_vm:.4f}",
            "deviation_percent": f"{deviation_percent:.2f}",
            "status": status,
        })

    # CSV schreiben
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(validation_results)

    # Zusammenfassung ausgeben
    status_counts = {}
    for result in validation_results:
        status = result["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    print(f"  OMEN-Validierung: {len(validation_results)} Punkte geprüft")
    for status, count in sorted(status_counts.items()):
        print(f"    {status}: {count}")


def export_omen_assignment_validation_csv(
    output_path: Path,
    antenna_system: Optional[AntennaSystem] = None,
    buildings=None,
    results: Optional[List[HotspotResult]] = None,
) -> None:
    """
    Exportiert OMEN-Zuordnungs-Validierung: Zeigt welche OMENs einem Gebäude zugeordnet wurden.

    Hilft zu identifizieren:
    - OMENs ohne Gebäudezuordnung (fehlende/veraltete Gebäudedaten)
    - Bauplatz-OMENs (Gebäude noch nicht gebaut)
    - OMENs außerhalb des Suchradius

    Args:
        output_path: Pfad für CSV-Datei
        antenna_system: AntennaSystem mit OMEN-Locations
        buildings: Liste von Buildings für Zuordnung
        results: Optional - HotspotResults für Gebäude-Identifikation
    """
    from collections import defaultdict

    if not antenna_system or not antenna_system.omen_locations:
        print("  HINWEIS: Keine OMEN-Locations zum Validieren.")
        return

    if not buildings:
        print("  HINWEIS: Keine Gebäude für OMEN-Zuordnung verfügbar.")
        return

    # Gruppiere results nach Gebäude
    by_building = defaultdict(list)
    if results:
        for r in results:
            by_building[r.building_id].append(r)

    # Building-Map für schnellen Zugriff
    building_map = {}
    egid_map = {}
    for building in buildings:
        building_map[building.id] = building
        egid_map[building.id] = building.egid

    # Point-in-Polygon Helper
    def point_in_polygon_2d(x, y, polygon_points):
        """Ray-casting algorithm für Point-in-Polygon Test"""
        n = len(polygon_points)
        inside = False
        p1x, p1y = polygon_points[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon_points[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside

    # OMEN-Zuordnung durchführen (gleiche Logik wie in anderen Export-Funktionen)
    omen_to_building = defaultdict(list)

    # Verwende results falls vorhanden, sonst alle buildings
    buildings_to_check = by_building if by_building else {b.id: [] for b in buildings}

    for omen in antenna_system.omen_locations:
        assigned = False

        for building_id in buildings_to_check.keys():
            building_obj = building_map.get(building_id)
            if not building_obj:
                continue

            # 1. Höhencheck
            if building_obj.wall_surfaces or building_obj.roof_surfaces:
                all_surfaces = building_obj.wall_surfaces + building_obj.roof_surfaces
                all_z = [v[2] for surface in all_surfaces for v in surface.vertices]
                building_min_z = min(all_z)
                building_max_z = max(all_z)
            else:
                continue

            height_tolerance = 0.5
            if not ((building_min_z - height_tolerance) <= omen.position.h <= (building_max_z + height_tolerance)):
                continue

            # 2. Point-in-Polygon Check
            all_surfaces = building_obj.wall_surfaces + building_obj.roof_surfaces
            if not all_surfaces:
                continue

            all_points_2d = set()
            for surface in all_surfaces:
                for vertex in surface.vertices:
                    all_points_2d.add((round(vertex[0], 2), round(vertex[1], 2)))

            if len(all_points_2d) < 3:
                continue

            points_list = list(all_points_2d)
            from scipy.spatial import ConvexHull
            try:
                hull = ConvexHull(points_list)
                hull_points = [points_list[i] for i in hull.vertices]
            except:
                hull_points = points_list

            if point_in_polygon_2d(omen.position.e, omen.position.n, hull_points):
                omen_to_building[f"O{omen.nr}"] = building_id
                assigned = True
                break

        if not assigned:
            omen_to_building[f"O{omen.nr}"] = None

    # CSV schreiben
    fieldnames = [
        "omen_nr",
        "position_x",
        "position_y",
        "position_z",
        "zugeordnet",
        "building_id",
        "egid",
        "grund",
    ]

    rows = []
    not_assigned_count = 0

    for omen in sorted(antenna_system.omen_locations, key=lambda o: o.nr):
        omen_nr = f"O{omen.nr}"
        building_id = omen_to_building.get(omen_nr)

        if building_id:
            egid = egid_map.get(building_id, "")
            rows.append({
                "omen_nr": omen_nr,
                "position_x": f"{omen.position.e:.2f}",
                "position_y": f"{omen.position.n:.2f}",
                "position_z": f"{omen.position.h:.2f}",
                "zugeordnet": "Ja",
                "building_id": building_id,
                "egid": egid,
                "grund": "",
            })
        else:
            not_assigned_count += 1
            rows.append({
                "omen_nr": omen_nr,
                "position_x": f"{omen.position.e:.2f}",
                "position_y": f"{omen.position.n:.2f}",
                "position_z": f"{omen.position.h:.2f}",
                "zugeordnet": "Nein",
                "building_id": "",
                "egid": "",
                "grund": "Kein Gebäude in 3D-Raum gefunden (fehlt in Geodaten oder außerhalb Radius)",
            })

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    # Warnung ausgeben wenn OMENs fehlen
    total = len(antenna_system.omen_locations)
    assigned = total - not_assigned_count

    print(f"  OMEN-Zuordnung: {assigned}/{total} OMENs zugeordnet")

    if not_assigned_count > 0:
        print(f"  ⚠️  WARNUNG: {not_assigned_count} OMEN(s) ohne Gebäudezuordnung!")
        print(f"      → Siehe {output_path.name} für Details")
        print(f"      Mögliche Gründe:")
        print(f"        - Gebäude fehlt in swissBUILDINGS3D")
        print(f"        - Bauplatz-OMEN (Gebäude noch nicht gebaut)")
        print(f"        - OMEN außerhalb {100}m Suchradius")
