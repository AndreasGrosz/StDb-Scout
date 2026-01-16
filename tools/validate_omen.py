#!/usr/bin/env python3
"""
OMEN-Validierung: Vergleicht berechnete E-Werte mit OMEN-Sheet-Werten.

Braucht KEINE Gebäudedaten, nur OMEN XLS.
"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from emf_hotspot.loaders.omen_loader import load_omen_data
from emf_hotspot.loaders.pattern_adapter import load_patterns_with_standard_fallback
from emf_hotspot.geometry.angles import calculate_relative_angles
from emf_hotspot.physics.propagation import calculate_e_field_with_pattern
from emf_hotspot.physics.summation import sum_e_fields
from emf_hotspot.loaders.pattern_loader_ods import get_pattern_for_antenna


def main():
    """Validiert OMEN-Punkte gegen XLS-Erwartungen."""

    # Lade OMEN-Daten
    omen_file = Path("input/OMEN R37 clean.xls")
    if not omen_file.exists():
        print(f"❌ {omen_file} nicht gefunden!")
        return 1

    print("=" * 80)
    print("OMEN-VALIDIERUNG (ohne Gebäude)")
    print("=" * 80)

    antenna_system = load_omen_data(omen_file)
    print(f"\nStandort: {antenna_system.name}")
    print(f"Adresse: {antenna_system.address}")
    print(f"Antennen: {len(antenna_system.antennas)}")
    print(f"OMEN-Punkte: {len(antenna_system.omen_locations)}")

    # Lade Patterns (versuche bereinigte ODS zuerst)
    ods_files = [
        Path("msi-files/Antennendämpfungen Hybrid AIR3268 R5_cleaned.ods"),
        Path("msi-files/Antennendämpfungen Hybrid AIR3268 R5.ods"),
        Path("msi-files/patterns_clockwise.ods"),
    ]

    ods_file = None
    for candidate in ods_files:
        if candidate.exists():
            ods_file = candidate
            break

    if ods_file:
        print(f"\nLade Antennendiagramme aus ODS: {ods_file.name}")
        patterns = load_patterns_with_standard_fallback(ods_file, antenna_system)
    else:
        print(f"\nLade Antennendiagramme (Standard-Patterns)...")
        patterns = load_patterns_with_standard_fallback(None, antenna_system)

    # Berechne E-Felder für OMEN-Punkte
    print(f"\n{'='*80}")
    print("E-FELD-BERECHNUNG FÜR OMEN-PUNKTE")
    print("=" * 80)
    print(f"{'OMEN':<6s} {'Distanz':>10s} {'E (berechnet)':>15s} {'E (erwartet)':>15s} "
          f"{'Delta':>10s} {'AGW':>10s}")
    print("-" * 80)

    results = []

    for omen in antenna_system.omen_locations:
        omen_pos = omen.position.to_array()

        # Berechne E-Feld von allen Antennen
        e_contributions = []

        for antenna in antenna_system.antennas:
            # Hole Pattern
            pattern = get_pattern_for_antenna(
                patterns,
                antenna.antenna_type,
                antenna.frequency_band,
            )

            if pattern is None:
                continue

            # Relative Winkel
            distance, rel_azimuth, rel_elevation = calculate_relative_angles(
                antenna_pos=antenna.position,
                point_pos=omen_pos,
                antenna_azimuth=antenna.azimuth_deg,
                antenna_tilt=antenna.tilt_deg,
            )

            # Dämpfungen
            h_atten = pattern.get_h_attenuation(rel_azimuth)
            v_atten = pattern.get_v_attenuation(rel_elevation)

            # E-Feld für diese Antenne
            e_field = calculate_e_field_with_pattern(
                erp_watts=antenna.erp_watts,
                distance_m=distance,
                h_attenuation_db=h_atten,
                v_attenuation_db=v_atten,
                building_attenuation_db=omen.building_attenuation_db,
            )

            e_contributions.append(e_field)

        # Summiere (Leistungsaddition)
        e_total = sum_e_fields(e_contributions)

        # Vergleich mit erwartetem Wert
        if omen.e_field_expected is not None:
            delta = e_total - omen.e_field_expected
            delta_pct = (delta / omen.e_field_expected) * 100 if omen.e_field_expected > 0 else 0
            expected_str = f"{omen.e_field_expected:.2f} V/m"
            delta_str = f"{delta:+.2f} V/m"
        else:
            expected_str = "N/A"
            delta_str = "-"

        # Distanz zur ersten Antenne (als Referenz)
        ref_dist = np.linalg.norm(
            omen.position.to_array() - antenna_system.antennas[0].position.to_array()
        )

        # AGW-Check
        exceeds = "⚠️ JA" if e_total >= 5.0 else "✓ Nein"

        print(f"O{omen.nr:<5d} {ref_dist:>9.1f}m {e_total:>13.2f} V/m {expected_str:>15s} "
              f"{delta_str:>10s} {exceeds:>10s}")

        results.append({
            'omen_nr': omen.nr,
            'e_calculated': e_total,
            'e_expected': omen.e_field_expected,
        })

    # Zusammenfassung
    print("\n" + "=" * 80)
    print("ZUSAMMENFASSUNG")
    print("=" * 80)

    hotspots = [r for r in results if r['e_calculated'] >= 5.0]
    print(f"Berechnete OMEN-Punkte: {len(results)}")
    print(f"AGW-Überschreitungen (≥5 V/m): {len(hotspots)}")

    if len(hotspots) > 0:
        print(f"\n⚠️  HOTSPOTS gefunden:")
        for r in results:
            if r['e_calculated'] >= 5.0:
                print(f"  - OMEN O{r['omen_nr']}: {r['e_calculated']:.2f} V/m")

    print(f"\n📊 Pattern-Quelle:")
    print(f"   3GPP TR 36.814 V9.2.0 (LTE/4G Standard-Sektorantenne 65°/7°)")
    print(f"\n💡 Hinweis:")
    print(f"   - Standard-Patterns sind KONSERVATIV (weniger Dämpfung)")
    print(f"   - Falls AGW-Überschreitungen → auch mit echten MSI wahrscheinlich")
    print(f"   - Für gerichtsfeste Beweise: BAKOM/BAFU um MSI-Files anfragen")

    print("\n" + "=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
