"""
Gebäude-Validierung und NISV-Formel-Checks

Prüft ob Gebäude höher sind als OMEN-Annahmen und ob
die NISV-Standardformel für Geschosshöhen zu kurz greift.
"""

from dataclasses import dataclass
from typing import List, Tuple
import numpy as np

from ..models import Building, AntennaSystem, OMENLocation


# NISV-Standardformel: z = Geschosszahl × 2.90m + 1.50m + 1.00m
NISV_FLOOR_HEIGHT_M = 2.90
NISV_MEASUREMENT_HEIGHT_M = 1.50  # Höhe des Messpunkts (NISV: Bauchhöhe)
NISV_GROUND_OFFSET_M = 1.00       # Erdgeschoss über Boden

# Konservativere Annahmen (von oben)
CONSERVATIVE_MEASUREMENT_HEIGHT_M = 1.80  # Kopfhöhe bei 1.90m Körpergröße

# Toleranzen
FLOOR_HEIGHT_TOLERANCE_M = 0.30   # ±30cm für Geschosshöhe
FLOOR_HEIGHT_WARNING_M = 3.20     # Warnung ab >3.2m pro Geschoss
TOP_FLOOR_TOLERANCE_M = 1.00      # Toleranz für oberste Geschoss


@dataclass
class BuildingAnalysis:
    """Analyse-Ergebnis für ein Gebäude"""
    building_id: str
    egid: str
    min_z: float
    max_z: float
    height_m: float
    estimated_floors: int
    real_floor_height_m: float
    has_high_ceilings: bool
    ceiling_warning: str

    # Messpunkt-Berechnungen
    z_top_floor_nisv: float = None      # Oberster Messpunkt nach NISV (1.50m, von unten)
    z_top_floor_conservative: float = None  # Oberster Messpunkt konservativ (1.80m, von oben)

    # OMEN-Vergleich (falls OMEN vorhanden)
    omen_nr: int = None
    omen_floors: int = None
    omen_z_nisv: float = None           # Z nach NISV-Formel (von unten)
    omen_z_conservative: float = None   # Z nach konservativer Methode (von oben)
    omen_z_given: float = None          # Z aus OMEN-Sheet
    missing_floors: int = 0             # Fehlende Geschosse in OMEN
    z_deviation_nisv: float = 0.0       # Abweichung: OMEN-Z vs NISV-Z
    z_deviation_conservative: float = 0.0  # Abweichung: Conservative vs OMEN-Z

    # Hallen-Erkennung
    is_likely_hall: bool = False        # True wenn wahrscheinlich Industriehalle (keine Multi-Floor-Struktur)


def analyze_building_heights(
    buildings: List[Building],
    antenna_system: AntennaSystem = None,
) -> List[BuildingAnalysis]:
    """
    Analysiert alle Gebäude auf Geschosshöhen und OMEN-Abweichungen.

    Args:
        buildings: Liste von Building-Objekten
        antenna_system: Optional - für OMEN-Vergleich

    Returns:
        Liste von BuildingAnalysis mit Warnungen
    """
    results = []

    # OMEN-Map erstellen (Gebäude → OMEN)
    omen_map = {}
    if antenna_system and antenna_system.omen_locations:
        for omen in antenna_system.omen_locations:
            # Finde nächstes Gebäude
            min_dist = float('inf')
            closest_building = None

            for building in buildings:
                # Gebäude-Zentrum
                center = _get_building_center(building)
                dist = np.sqrt(
                    (omen.position.e - center[0])**2 +
                    (omen.position.n - center[1])**2
                )

                if dist < min_dist:
                    min_dist = dist
                    closest_building = building

            # Zuordnung (nur wenn < 50m)
            if closest_building and min_dist < 50:
                omen_map[closest_building.id] = omen

    # Analysiere jedes Gebäude
    for building in buildings:
        # Gebäudehöhen aus Geodaten
        min_z, max_z = _get_building_height_range(building)
        height_m = max_z - min_z

        # Geschätzte Geschosszahl (3m Annahme)
        estimated_floors = max(1, int(height_m / 3.0))

        # Reale Geschosshöhe
        real_floor_height = height_m / estimated_floors

        # Hohe Decken?
        has_high_ceilings = real_floor_height > FLOOR_HEIGHT_WARNING_M

        ceiling_warning = ""
        if has_high_ceilings:
            ceiling_warning = (
                f"Hohe Räume: {real_floor_height:.2f}m/Geschoss "
                f"(NISV: {NISV_FLOOR_HEIGHT_M}m). "
                f"NISV-Formel unterschätzt Höhe um {(real_floor_height - NISV_FLOOR_HEIGHT_M) * estimated_floors:.1f}m!"
            )

        # Berechne oberste Messpunkt-Position (beide Methoden)

        # Methode 1: NISV von unten (alte Methode)
        # z = min_z + 1.0m + (floors-1) × 2.90m + 1.50m
        z_top_nisv = (
            min_z +
            NISV_GROUND_OFFSET_M +
            (estimated_floors - 1) * NISV_FLOOR_HEIGHT_M +
            NISV_MEASUREMENT_HEIGHT_M
        )

        # Methode 2: Konservativ von oben (neue Methode)
        # z = max_z - (Geschosshöhe - Messpunkt-Höhe)
        # z = max_z - (2.90m - 1.80m) = max_z - 1.10m
        z_top_conservative = max_z - (NISV_FLOOR_HEIGHT_M - CONSERVATIVE_MEASUREMENT_HEIGHT_M)

        analysis = BuildingAnalysis(
            building_id=building.id,
            egid=building.egid,
            min_z=min_z,
            max_z=max_z,
            height_m=height_m,
            estimated_floors=estimated_floors,
            real_floor_height_m=real_floor_height,
            has_high_ceilings=has_high_ceilings,
            ceiling_warning=ceiling_warning,
            z_top_floor_nisv=z_top_nisv,
            z_top_floor_conservative=z_top_conservative,
        )

        # OMEN-Vergleich (falls vorhanden)
        if building.id in omen_map:
            omen = omen_map[building.id]
            omen_z_given = omen.position.h

            # OMEN-Geschosszahl zurückrechnen (von unten nach NISV)
            omen_floors_calc = int((omen_z_given - min_z - NISV_MEASUREMENT_HEIGHT_M - NISV_GROUND_OFFSET_M) / NISV_FLOOR_HEIGHT_M)
            omen_floors_calc = max(1, omen_floors_calc)

            # NISV-Z für dieses Gebäude (von unten)
            omen_z_nisv = (
                min_z +
                NISV_GROUND_OFFSET_M +
                omen_floors_calc * NISV_FLOOR_HEIGHT_M +
                NISV_MEASUREMENT_HEIGHT_M
            )

            # Konservativ-Z (von oben) - sollte verwendet werden!
            omen_z_conservative = z_top_conservative

            # Abweichungen
            z_deviation_nisv = omen_z_given - omen_z_nisv  # OMEN vs NISV
            z_deviation_conservative = z_top_conservative - omen_z_given  # Conservative vs OMEN

            # Fehlende Geschosse?
            missing_floors = estimated_floors - omen_floors_calc

            analysis.omen_nr = omen.nr
            analysis.omen_floors = omen_floors_calc
            analysis.omen_z_nisv = omen_z_nisv
            analysis.omen_z_conservative = omen_z_conservative
            analysis.omen_z_given = omen_z_given
            analysis.missing_floors = missing_floors
            analysis.z_deviation_nisv = z_deviation_nisv
            analysis.z_deviation_conservative = z_deviation_conservative

            # Hallen-Erkennung (nach OMEN-Zuordnung)
            # Erkenne Industriehallen anhand mehrerer Indikatoren:
            # 1. Geschosshöhe > 6m (eindeutig Halle)
            # 2. OMEN=1 Stockwerk, aber GIS schätzt 3+ Stockwerke (wahrscheinlich hohe Halle)
            # 3. Gebäudehöhe > 8m bei geschätzten 2-3 Stockwerken (ungewöhnlich hoch)
            analysis.is_likely_hall = (
                analysis.real_floor_height_m > 6.0 or
                (omen_floors_calc == 1 and estimated_floors >= 3) or
                (height_m > 8.0 and 2 <= estimated_floors <= 3)
            )

        results.append(analysis)

    return results


def export_building_validation_csv(
    analyses: List[BuildingAnalysis],
    output_path,
    buildings=None,  # Optional: Liste von Buildings für Koordinaten
) -> None:
    """
    Exportiert Gebäude-Validierung als CSV.

    Args:
        analyses: Liste von BuildingAnalysis
        output_path: Pfad für CSV-Datei
        buildings: Optional - Liste von Buildings für Adress-Lookup
    """
    import csv

    # Lade Adressen für alle Gebäude mit EGID
    address_cache = {}
    if buildings:
        from ..loaders.geoadmin_api import lookup_address_by_egid, lookup_address_by_coordinates

        # Erstelle Building-Map
        building_map = {b.id: b for b in buildings}

        print(f"  Lade Adressen für {len(analyses)} Gebäude...")

        for analysis in analyses:
            if analysis.egid and analysis.egid != "":
                # Versuche EGID-Lookup mit Koordinaten-Validierung
                building = building_map.get(analysis.building_id)
                if building:
                    center = _get_building_center(building)
                    addr = lookup_address_by_egid(analysis.egid, building_e=center[0], building_n=center[1])
                else:
                    # Keine Koordinaten verfügbar - ohne Validierung
                    addr = lookup_address_by_egid(analysis.egid)

                if addr:
                    address_cache[analysis.building_id] = addr['full_address']
                else:
                    # Fallback: Koordinaten-Lookup
                    if building:
                        center = _get_building_center(building)
                        addr = lookup_address_by_coordinates(center[0], center[1])
                        if addr:
                            address_cache[analysis.building_id] = addr.get('full_address', '')
            else:
                # Kein EGID: Koordinaten-Lookup
                building = building_map.get(analysis.building_id)
                if building:
                    center = _get_building_center(building)
                    addr = lookup_address_by_coordinates(center[0], center[1])
                    if addr:
                        address_cache[analysis.building_id] = addr.get('full_address', '')

    fieldnames = [
        "building_id",
        "egid",
        "address",
        "min_z",
        "max_z",
        "height_m",
        "estimated_floors",
        "real_floor_height_m",
        "has_high_ceilings",
        "is_likely_hall",
        "ceiling_warning",
        "z_top_floor_nisv",
        "z_top_floor_conservative",
        "omen_nr",
        "omen_floors",
        "omen_z_given",
        "omen_z_nisv",
        "omen_z_conservative",
        "missing_floors",
        "z_deviation_nisv",
        "z_deviation_conservative",
        "recommendation",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for analysis in analyses:
            # Empfehlung generieren
            recommendation = ""

            if analysis.has_high_ceilings:
                recommendation += "⚠️ Hohe Decken: NISV-Formel prüfen! "

            if analysis.omen_nr:
                if analysis.missing_floors > 0:
                    recommendation += f"⚠️ {analysis.missing_floors} Geschoss(e) fehlen in OMEN! "

                # Konservative Methode zeigt, wie viel höher der Messpunkt sein sollte
                if analysis.z_deviation_conservative > TOP_FLOOR_TOLERANCE_M:
                    recommendation += f"⚠️ Konservativ {analysis.z_deviation_conservative:.1f}m höher als OMEN-Z! "

                # NISV vs OMEN (nur zur Info)
                if abs(analysis.z_deviation_nisv) > TOP_FLOOR_TOLERANCE_M:
                    recommendation += f"(NISV weicht {analysis.z_deviation_nisv:.1f}m ab) "

            if not recommendation:
                recommendation = "✓ OK"

            writer.writerow({
                "building_id": analysis.building_id,
                "egid": analysis.egid,
                "address": address_cache.get(analysis.building_id, ""),
                "min_z": f"{analysis.min_z:.2f}",
                "max_z": f"{analysis.max_z:.2f}",
                "height_m": f"{analysis.height_m:.2f}",
                "estimated_floors": analysis.estimated_floors,
                "real_floor_height_m": f"{analysis.real_floor_height_m:.2f}",
                "has_high_ceilings": "Ja" if analysis.has_high_ceilings else "Nein",
                "is_likely_hall": "Ja" if analysis.is_likely_hall else "Nein",
                "ceiling_warning": analysis.ceiling_warning,
                "z_top_floor_nisv": f"{analysis.z_top_floor_nisv:.2f}" if analysis.z_top_floor_nisv else "",
                "z_top_floor_conservative": f"{analysis.z_top_floor_conservative:.2f}" if analysis.z_top_floor_conservative else "",
                "omen_nr": f"O{analysis.omen_nr}" if analysis.omen_nr else "",
                "omen_floors": analysis.omen_floors if analysis.omen_floors else "",
                "omen_z_given": f"{analysis.omen_z_given:.2f}" if analysis.omen_z_given else "",
                "omen_z_nisv": f"{analysis.omen_z_nisv:.2f}" if analysis.omen_z_nisv else "",
                "omen_z_conservative": f"{analysis.omen_z_conservative:.2f}" if analysis.omen_z_conservative else "",
                "missing_floors": analysis.missing_floors if analysis.omen_nr else "",
                "z_deviation_nisv": f"{analysis.z_deviation_nisv:.2f}" if analysis.omen_nr else "",
                "z_deviation_conservative": f"{analysis.z_deviation_conservative:.2f}" if analysis.omen_nr else "",
                "recommendation": recommendation,
            })


def print_building_validation_summary(analyses: List[BuildingAnalysis]) -> None:
    """
    Gibt Zusammenfassung der Gebäude-Validierung aus.
    """
    high_ceiling_count = sum(1 for a in analyses if a.has_high_ceilings)
    missing_floors_count = sum(1 for a in analyses if a.missing_floors > 0)
    z_deviation_conservative_count = sum(
        1 for a in analyses
        if a.omen_nr and a.z_deviation_conservative > TOP_FLOOR_TOLERANCE_M
    )

    # Maximale Abweichungen finden
    # ABER: Ignoriere Hallen/Industriegebäude
    max_conservative_dev = 0.0
    worst_building = None

    for a in analyses:
        # Überspringe Hallen-Gebäude (schon in BuildingAnalysis berechnet)
        if a.omen_nr and a.z_deviation_conservative > max_conservative_dev and not a.is_likely_hall:
            max_conservative_dev = a.z_deviation_conservative
            worst_building = a

    print("\n" + "=" * 70)
    print("GEBÄUDE-VALIDIERUNG (NISV-Formel vs Geodaten)")
    print("=" * 70)
    print(f"  Analysierte Gebäude: {len(analyses)}")
    print(f"  Hohe Decken (>{FLOOR_HEIGHT_WARNING_M}m): {high_ceiling_count}")

    print("\n  BERECHNUNGSMETHODEN:")
    print(f"  • NISV-Methode (von unten): Bauchhöhe {NISV_MEASUREMENT_HEIGHT_M}m")
    print(f"  • Konservativ (von oben):   Kopfhöhe {CONSERVATIVE_MEASUREMENT_HEIGHT_M}m")

    if missing_floors_count > 0:
        print(f"\n  ⚠️  {missing_floors_count} OMEN-Gebäude mit fehlenden Geschossen!")

    if z_deviation_conservative_count > 0:
        print(f"\n  ⚠️  {z_deviation_conservative_count} OMEN-Gebäude mit >1m zu niedrigen Messpunkten!")
        print(f"      (Konservative Methode zeigt höhere Messpunkte)")

        if worst_building:
            print(f"\n  KRITISCHSTES GEBÄUDE:")
            print(f"      OMEN O{worst_building.omen_nr}")
            print(f"      EGID: {worst_building.egid}")
            print(f"      OMEN-Z: {worst_building.omen_z_given:.2f}m")
            print(f"      Konservativ-Z: {worst_building.omen_z_conservative:.2f}m")
            print(f"      → {max_conservative_dev:.1f}m HÖHER als OMEN!")
            print(f"      → Höhere E-Feldstärken zu erwarten!")

    if high_ceiling_count > 0:
        print(f"\n  ⚠️  {high_ceiling_count} Gebäude mit hohen Räumen (>{FLOOR_HEIGHT_WARNING_M}m/Geschoss):")
        print("      → NISV-Formel (2.90m) unterschätzt die Höhe!")
        print("      → Konservative Methode empfohlen!")

    print("\n  💡 EMPFEHLUNG:")
    print("      Nutzen Sie 'z_top_floor_conservative' statt NISV-Formel")
    print("      für konservativere (sicherere) Messpunkt-Positionierung!")
    print("=" * 70)


def _get_building_center(building: Building) -> Tuple[float, float]:
    """Berechnet Gebäude-Zentrum (E, N)."""
    all_vertices = []

    for wall in building.wall_surfaces:
        all_vertices.extend(wall.vertices[:, :2])  # Nur E, N

    if not all_vertices:
        return (0, 0)

    vertices_array = np.array(all_vertices)
    center_e = np.mean(vertices_array[:, 0])
    center_n = np.mean(vertices_array[:, 1])

    return (center_e, center_n)


def _get_building_height_range(building: Building) -> Tuple[float, float]:
    """Ermittelt Min- und Max-Höhe eines Gebäudes."""
    all_z = []

    for wall in building.wall_surfaces:
        all_z.extend(wall.vertices[:, 2])  # Z-Koordinaten

    for roof in building.roof_surfaces:
        all_z.extend(roof.vertices[:, 2])

    if not all_z:
        return (0.0, 0.0)

    return (min(all_z), max(all_z))
