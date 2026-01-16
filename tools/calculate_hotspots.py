#!/usr/bin/env python3
"""
Quick-Start: Hotspot-Berechnung für OMEN R37

Nutzt Standard-Patterns (ITU-R/3GPP) als Fallback wenn keine ODS vorhanden.
"""

import sys
from pathlib import Path

# Füge emf_hotspot zum Path hinzu
sys.path.insert(0, str(Path(__file__).parent))

from emf_hotspot.main import analyze_site

def main():
    """Führt Hotspot-Analyse durch."""

    # Eingabedaten
    omen_file = Path("input/OMEN R37 clean.xls")
    pattern_dir = Path("input")  # Hier würde ODS liegen
    output_dir = Path("output")

    # Prüfe ob OMEN-Datei existiert
    if not omen_file.exists():
        print(f"❌ Fehler: {omen_file} nicht gefunden!")
        print(f"   Bitte erstelle die Datei oder passe den Pfad an.")
        return 1

    print("=" * 60)
    print("HOTSPOT-FINDER - QUICK START")
    print("=" * 60)
    print(f"\n📂 OMEN-Datei: {omen_file}")
    print(f"📂 Output: {output_dir}")
    print(f"\n⚠️  HINWEIS: Nutzt Standard-Patterns (ITU-R/3GPP)")
    print(f"   Falls ODS vorhanden → wird automatisch geladen\n")

    # Führe Analyse durch
    try:
        results = analyze_site(
            omen_file=omen_file,
            pattern_dir=pattern_dir,
            output_dir=output_dir,
            radius_m=100,  # 100m Radius
            resolution_m=2.0,  # 2m Raster
            threshold_vm=5.0,  # AGW = 5 V/m
            auto_download_buildings=True,  # swissBUILDINGS3D automatisch laden
            visualize=False,  # Keine 3D-Viz (wegen OpenGL-Problemen)
        )

        print(f"\n✅ Analyse abgeschlossen!")
        print(f"   Hotspots: {sum(1 for r in results if r.exceeds_limit)}")
        print(f"   Gesamt Punkte: {len(results)}")
        print(f"\n📊 Ergebnisse in: {output_dir}/")

    except SystemExit as e:
        # Fehler wurden bereits ausgegeben
        return e.code
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
