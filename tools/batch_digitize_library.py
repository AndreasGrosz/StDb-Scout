#!/usr/bin/env python3
"""
Batch-Digitalisierung: Komplette CH-Antennen-Library erstellen

Workflow:
1. Scanne msi-files/ nach allen PDFs
2. Extrahiere Diagramme als PNGs
3. Digitalisiere mit Claude API (H + V)
4. Kombiniere zu vollständigen ODS-Dateien
5. Bereinige mit clean_msi_patterns.py

Ergebnis:
- pattern_library/AIR3268.ods (alle Frequenzen)
- pattern_library/AAU5613.ods
- pattern_library/... etc.

Einmalig für alle CH-Antennentypen → Dauerhaft verwendbar!
"""

import sys
from pathlib import Path
import subprocess
import json
from typing import List, Dict
import pandas as pd


# Häufigste CH-Antennentypen (Priorität)
ANTENNA_TYPES = [
    {
        "name": "AIR3268",
        "manufacturer": "Ericsson",
        "frequencies": ["738-921", "1427-2570", "3600"],
        "priority": 1
    },
    {
        "name": "AAU5613",
        "manufacturer": "Huawei",
        "frequencies": ["700-900", "1800-2100"],
        "priority": 2
    },
    {
        "name": "AAU5973",
        "manufacturer": "Huawei",
        "frequencies": ["3600"],
        "priority": 2
    },
    {
        "name": "AIR6449",
        "manufacturer": "Ericsson",
        "frequencies": ["700-2690"],
        "priority": 3
    },
]


def find_antenna_pdfs(msi_dir: Path) -> Dict[str, List[Path]]:
    """
    Sucht PDFs nach Antennentyp.

    Returns:
        Dict: antenna_name -> List[PDF-Paths]
    """
    result = {}

    for pdf in msi_dir.glob("**/*.pdf"):
        pdf_name = pdf.name.lower()

        # Matche gegen bekannte Typen
        for antenna_info in ANTENNA_TYPES:
            antenna_name = antenna_info["name"].lower()

            if antenna_name in pdf_name or antenna_name.replace("", "") in pdf_name:
                if antenna_info["name"] not in result:
                    result[antenna_info["name"]] = []
                result[antenna_info["name"]].append(pdf)
                break

    return result


def extract_diagrams_from_pdf(pdf_path: Path, output_dir: Path) -> List[Path]:
    """
    Extrahiert alle Diagramme aus PDF als PNGs.

    Args:
        pdf_path: PDF-Datei
        output_dir: Output-Verzeichnis

    Returns:
        Liste der PNG-Pfade
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = output_dir / pdf_path.stem

    # Extract mit pdfimages
    cmd = ["pdfimages", "-png", str(pdf_path), str(prefix)]
    subprocess.run(cmd, capture_output=True, check=True)

    # Finde generierte PNGs
    pngs = list(output_dir.glob(f"{pdf_path.stem}-*.png"))
    return sorted(pngs)


def batch_digitize_antenna_type(
    antenna_name: str,
    pdfs: List[Path],
    output_library_dir: Path
):
    """
    Digitalisiert alle Diagramme für einen Antennentyp.

    Args:
        antenna_name: Name (z.B. "AIR3268")
        pdfs: Liste von PDF-Pfaden
        output_library_dir: Output-Verzeichnis für Library
    """
    print(f"\n{'='*60}")
    print(f"DIGITALISIERE: {antenna_name}")
    print(f"{'='*60}")
    print(f"PDFs: {len(pdfs)}")

    # Temp-Verzeichnis für extrahierte Bilder
    temp_dir = Path(f"/tmp/antenna_diagrams_{antenna_name}")
    temp_dir.mkdir(parents=True, exist_ok=True)

    all_diagrams = []

    # Extrahiere alle Diagramme
    for pdf in pdfs:
        print(f"\n  Extrahiere: {pdf.name}")
        try:
            pngs = extract_diagrams_from_pdf(pdf, temp_dir)
            print(f"    → {len(pngs)} Diagramme gefunden")
            all_diagrams.extend(pngs)
        except Exception as e:
            print(f"    ⚠️ Fehler: {e}")

    if len(all_diagrams) == 0:
        print(f"\n  ⚠️ Keine Diagramme gefunden für {antenna_name}")
        return

    print(f"\n  Gesamt extrahiert: {len(all_diagrams)} Diagramme")

    # Digitalisiere mit Claude API
    print(f"\n  Digitalisiere mit Claude API...")
    print(f"  HINWEIS: Dies nutzt API-Credits!")
    print(f"  Kosten: ~{len(all_diagrams) * 0.05:.2f} USD (Schätzung)")

    response = input("\n  Fortfahren? (y/n): ").strip().lower()
    if response != 'y':
        print("  Abgebrochen.")
        return

    # TODO: Implementiere Claude API Calls für jedes Diagramm
    # (Würde hier claude_api_digitizer.py aufrufen)

    print(f"\n  ⚠️ TODO: Claude API Integration")
    print(f"  Manuelle Schritte:")
    print(f"    1. Für jedes PNG in {temp_dir}:")
    print(f"       python3 claude_api_digitizer.py <png> --antenna {antenna_name}")
    print(f"    2. Kombiniere alle ODS-Dateien")
    print(f"    3. Bereinige mit clean_msi_patterns.py")


def create_pattern_library_index(library_dir: Path):
    """
    Erstellt Index-Datei für Pattern-Library.

    library/
      index.json
      AIR3268.ods
      AAU5613.ods
      ...
    """
    index = {
        "library_version": "1.0",
        "created_by": "batch_digitize_library.py",
        "antenna_types": []
    }

    for ods_file in library_dir.glob("*.ods"):
        # Parse ODS um Frequenzen zu extrahieren
        try:
            df = pd.read_excel(ods_file, sheet_name='dB', engine='odf')
            frequencies = df['Frequenz-band'].unique().tolist()
            antenna_type = df['Antennen-Typ'].iloc[0]

            index["antenna_types"].append({
                "name": antenna_type,
                "file": ods_file.name,
                "frequencies": [str(f) for f in frequencies],
            })
        except Exception as e:
            print(f"  ⚠️ Fehler beim Parsen von {ods_file.name}: {e}")

    # Speichere Index
    index_file = library_dir / "index.json"
    with open(index_file, 'w') as f:
        json.dump(index, f, indent=2)

    print(f"\n✓ Library-Index erstellt: {index_file}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Batch-Digitalisierung aller CH-Antennentypen"
    )
    parser.add_argument('--msi-dir', type=Path, default=Path('msi-files'),
                       help='Verzeichnis mit PDF-Diagrammen')
    parser.add_argument('--library-dir', type=Path, default=Path('pattern_library'),
                       help='Output-Verzeichnis für Pattern-Library')
    parser.add_argument('--antenna', type=str,
                       help='Nur einen Antennentyp digitalisieren (z.B. AIR3268)')
    parser.add_argument('--scan-only', action='store_true',
                       help='Nur scannen, nicht digitalisieren')

    args = parser.parse_args()

    print("=" * 60)
    print("BATCH-DIGITALISIERUNG: CH-ANTENNEN PATTERN-LIBRARY")
    print("=" * 60)

    # Scanne msi-files/
    print(f"\n1. Scanne {args.msi_dir} nach Antennen-PDFs...")
    antenna_pdfs = find_antenna_pdfs(args.msi_dir)

    if len(antenna_pdfs) == 0:
        print(f"\n❌ Keine Antennen-PDFs gefunden in {args.msi_dir}")
        return 1

    print(f"\n   Gefundene Antennentypen:")
    for antenna_name, pdfs in sorted(antenna_pdfs.items()):
        print(f"     - {antenna_name}: {len(pdfs)} PDF(s)")

    if args.scan_only:
        print(f"\n✓ Scan abgeschlossen (--scan-only gesetzt)")
        return 0

    # Digitalisiere
    args.library_dir.mkdir(parents=True, exist_ok=True)

    if args.antenna:
        # Nur einen Typ
        if args.antenna in antenna_pdfs:
            batch_digitize_antenna_type(
                args.antenna,
                antenna_pdfs[args.antenna],
                args.library_dir
            )
        else:
            print(f"\n❌ Antennentyp '{args.antenna}' nicht gefunden!")
            return 1
    else:
        # Alle Typen (nach Priorität)
        for antenna_info in ANTENNA_TYPES:
            antenna_name = antenna_info["name"]
            if antenna_name in antenna_pdfs:
                batch_digitize_antenna_type(
                    antenna_name,
                    antenna_pdfs[antenna_name],
                    args.library_dir
                )

    # Erstelle Index
    print(f"\n{'='*60}")
    print("ERSTELLE LIBRARY-INDEX")
    print("=" * 60)
    create_pattern_library_index(args.library_dir)

    print(f"\n{'='*60}")
    print("ABGESCHLOSSEN")
    print("=" * 60)
    print(f"\nPattern-Library: {args.library_dir}")
    print(f"\nNutzung:")
    print(f"  1. Kopiere pattern_library/*.ods nach msi-files/")
    print(f"  2. Hotspot-Finder lädt automatisch passende Patterns")
    print(f"  3. Schweizweite Abdeckung mit echten Herstellerdaten!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
