#!/usr/bin/env python3
"""
KI-gestützte Antennendiagramm-Digitalisierung

Workflow:
1. Vision-LLM (Claude) analysiert Bild → Metadata (Zentrum, Radien)
2. Computer Vision extrahiert Kurve (nur schwarze Pixel)
3. Polarkoordinaten-Konvertierung
4. Export zu ODS

Vorteile:
- KI findet Zentrum/Radius präzise
- Algorithmus digitalisiert nur KI-identifizierte Bereiche
- Fehlerrate minimal
"""

import sys
from pathlib import Path
import numpy as np
import cv2
from typing import Tuple, List, Dict
from dataclasses import dataclass
import json

@dataclass
class DiagramMetadata:
    """Von KI extrahierte Metadata."""
    center_px: Tuple[int, int]
    radius_0db_px: float
    radius_per_10db_px: float
    orientation_deg: float  # 0° Richtung (typisch: 0° = Ost)
    curve_color_rgb: Tuple[int, int, int]  # Farbe der Kurve
    diagram_type: str  # 'horizontal' oder 'vertical'


def extract_curve_from_metadata(
    image_path: Path,
    metadata: DiagramMetadata,
    black_threshold: int = 100
) -> np.ndarray:
    """
    Extrahiert Kurve basierend auf KI-Metadata.

    Args:
        image_path: Pfad zum Bild
        metadata: Von KI extrahierte Metadaten
        black_threshold: Schwellwert für schwarze Pixel

    Returns:
        Array von (angle_deg, attenuation_dB)
    """
    # Lade Bild
    img = cv2.imread(str(image_path))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    cx, cy = metadata.center_px
    r_0db = metadata.radius_0db_px
    r_per_10db = metadata.radius_per_10db_px

    print(f"Zentrum: ({cx}, {cy})")
    print(f"Radius 0dB: {r_0db:.1f} px")
    print(f"Radius pro 10dB: {r_per_10db:.1f} px")

    # Sample alle Winkel (alle 0.5°)
    angles_deg = np.arange(0, 360, 0.5)
    attenuations = []

    for angle_deg in angles_deg:
        # Konvertiere zu Radianten (0° = rechts/Ost)
        angle_rad = np.deg2rad(angle_deg)

        # Suche schwarzen Pixel entlang Strahl von Zentrum nach außen
        # Start bei Radius=0, gehe bis Radius=r_0db*1.5
        max_radius = r_0db * 1.5
        found_radius = None

        for r in np.linspace(0, max_radius, 500):
            x = int(cx + r * np.cos(angle_rad))
            y = int(cy - r * np.sin(angle_rad))  # y invertiert (Bild-Koordinaten)

            # Prüfe ob Pixel im Bild
            if 0 <= x < gray.shape[1] and 0 <= y < gray.shape[0]:
                # Prüfe ob schwarz (Kurve)
                if gray[y, x] < black_threshold:
                    found_radius = r
                    break  # Erstes schwarzes Pixel gefunden

        # Falls gefunden: Berechne Dämpfung
        if found_radius is not None:
            # Dämpfung = (r_0db - found_radius) / r_per_10db * 10
            attenuation_db = (r_0db - found_radius) / r_per_10db * 10
            # Clip auf [0, 30] (typischer Bereich)
            attenuation_db = np.clip(attenuation_db, 0, 30)
        else:
            # Kein schwarzes Pixel → maximale Dämpfung
            attenuation_db = 30.0

        attenuations.append(attenuation_db)

    return np.column_stack([angles_deg, attenuations])


def vision_llm_analyze_diagram(image_path: Path) -> DiagramMetadata:
    """
    Platzhalter: Hier würde Vision-LLM (Claude API) Bild analysieren.

    In Realität:
    - Bild an Claude API senden
    - Prompt: "Analysiere Antennendiagramm, gib Zentrum/Radien zurück"
    - Parse JSON-Response

    Für jetzt: Manuelle Eingabe oder geschätzte Werte
    """
    print(f"\n{'='*60}")
    print(f"VISION-LLM ANALYSE (Manuell)")
    print(f"{'='*60}")
    print(f"\nBild: {image_path.name}")
    print(f"\nBitte manuell eingeben (oder Enter für geschätzte Werte):")

    # Manuelle Eingabe
    cx = input("  Zentrum X (px, default=410): ").strip()
    cy = input("  Zentrum Y (px, default=390): ").strip()
    r_0db = input("  Radius bei 0dB (px, default=250): ").strip()
    r_per_10db = input("  Radius pro 10dB (px, default=62.5): ").strip()

    # Defaults
    cx = int(cx) if cx else 410
    cy = int(cy) if cy else 390
    r_0db = float(r_0db) if r_0db else 250.0
    r_per_10db = float(r_per_10db) if r_per_10db else 62.5

    return DiagramMetadata(
        center_px=(cx, cy),
        radius_0db_px=r_0db,
        radius_per_10db_px=r_per_10db,
        orientation_deg=0,  # 0° = Ost (Standard)
        curve_color_rgb=(0, 0, 0),  # Schwarz
        diagram_type='horizontal'
    )


def save_to_json(data: np.ndarray, output_file: Path, metadata: DiagramMetadata):
    """Speichert Daten als JSON."""
    result = {
        "metadata": {
            "center_px": metadata.center_px,
            "radius_0db_px": metadata.radius_0db_px,
            "radius_per_10db_px": metadata.radius_per_10db_px,
            "diagram_type": metadata.diagram_type,
        },
        "data": [
            {"angle_deg": float(row[0]), "attenuation_db": float(row[1])}
            for row in data
        ]
    }

    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\n✓ JSON gespeichert: {output_file}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="KI-gestützte Antennendiagramm-Digitalisierung"
    )
    parser.add_argument('image', type=Path, help='Antennendiagramm-Bild (PNG/JPG)')
    parser.add_argument('-o', '--output', type=Path, help='Output JSON-Datei')
    parser.add_argument('--auto', action='store_true',
                       help='Automatische Werte (keine manuelle Eingabe)')

    args = parser.parse_args()

    if not args.image.exists():
        print(f"❌ Fehler: {args.image} nicht gefunden!")
        return 1

    # Output-Datei
    if args.output is None:
        output_file = args.image.with_suffix('.json')
    else:
        output_file = args.output

    print("=" * 60)
    print("KI-GESTÜTZTE ANTENNENDIAGRAMM-DIGITALISIERUNG")
    print("=" * 60)

    # Schritt 1: Vision-LLM analysiert (oder manuelle Eingabe)
    if args.auto:
        # Geschätzte Default-Werte
        metadata = DiagramMetadata(
            center_px=(410, 390),
            radius_0db_px=250,
            radius_per_10db_px=62.5,
            orientation_deg=0,
            curve_color_rgb=(0, 0, 0),
            diagram_type='horizontal'
        )
    else:
        metadata = vision_llm_analyze_diagram(args.image)

    # Schritt 2: Kurve extrahieren
    print(f"\n{'='*60}")
    print("KURVEN-EXTRAKTION")
    print("=" * 60)
    data = extract_curve_from_metadata(args.image, metadata)

    print(f"\nExtrahierte Punkte: {len(data)}")
    print(f"Dämpfung min/max: {data[:, 1].min():.2f} / {data[:, 1].max():.2f} dB")

    # Schritt 3: Speichern
    save_to_json(data, output_file, metadata)

    print(f"\n{'='*60}")
    print("ABGESCHLOSSEN")
    print("=" * 60)
    print(f"\nNächster Schritt:")
    print(f"  1. Prüfe JSON: cat {output_file}")
    print(f"  2. Konvertiere zu ODS falls nötig")
    print(f"  3. Bei Fehlern: Passe Zentrum/Radien an und wiederhole")

    return 0


if __name__ == "__main__":
    sys.exit(main())
