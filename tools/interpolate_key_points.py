#!/usr/bin/env python3
"""
Interpoliert Schlüsselpunkte zu vollständiger Kurve

Nimmt JSON mit key_points (z.B. alle 5°) und interpoliert
kubisch auf 1° Auflösung (360 Punkte).

Usage:
    python interpolate_key_points.py input.json -o output.json
"""

import sys
from pathlib import Path
import json
import numpy as np
from scipy.interpolate import CubicSpline


def interpolate_to_1deg(key_points: list) -> list:
    """
    Interpoliert Schlüsselpunkte kubisch auf 1° Auflösung.

    Args:
        key_points: Liste von {"angle_deg": x, "attenuation_db": y}

    Returns:
        Liste von 360 Punkten (alle 1°)
    """
    # Extrahiere Winkel und Dämpfung
    angles = np.array([p['angle_deg'] for p in key_points])
    attenuation = np.array([p['attenuation_db'] for p in key_points])

    # Sortiere nach Winkel
    sort_idx = np.argsort(angles)
    angles = angles[sort_idx]
    attenuation = attenuation[sort_idx]

    # Für periodische Interpolation: Füge Anfangspunkt am Ende hinzu
    # (damit 359° → 0° glatt ist)
    if angles[0] == 0 and angles[-1] != 360:
        angles = np.append(angles, 360)
        attenuation = np.append(attenuation, attenuation[0])

    # Kubische Spline-Interpolation mit periodischen Randbedingungen
    cs = CubicSpline(angles, attenuation, bc_type='periodic')

    # Evaluiere auf 1° Grid
    angles_1deg = np.arange(0, 360, 1)
    attenuation_1deg = cs(angles_1deg)

    # Konvertiere zurück zu Liste von Dicts
    result = []
    for angle, atten in zip(angles_1deg, attenuation_1deg):
        result.append({
            'angle_deg': int(angle),
            'attenuation_db': float(atten)
        })

    return result


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Interpoliert Schlüsselpunkte auf 1° Auflösung"
    )
    parser.add_argument('input', type=Path,
                       help='Input JSON mit key_points')
    parser.add_argument('-o', '--output', type=Path,
                       help='Output JSON (default: <input>_interpolated.json)')

    args = parser.parse_args()

    if not args.input.exists():
        print(f"❌ Input nicht gefunden: {args.input}")
        return 1

    # Lade Input
    with open(args.input, 'r') as f:
        data = json.load(f)

    if 'key_points' not in data:
        print(f"❌ Keine 'key_points' in {args.input}")
        return 1

    key_points = data['key_points']

    print(f"✓ Geladen: {len(key_points)} Schlüsselpunkte")
    print(f"  Winkel: {key_points[0]['angle_deg']}° - {key_points[-1]['angle_deg']}°")

    # Interpoliere
    print(f"\nInterpoliere kubisch auf 1° Auflösung...")
    curve_points = interpolate_to_1deg(key_points)

    print(f"✓ {len(curve_points)} Punkte interpoliert")

    # Statistik
    angles = [p['angle_deg'] for p in curve_points]
    atten = [p['attenuation_db'] for p in curve_points]

    print(f"\nErgebnis:")
    print(f"  Winkel: {min(angles)}° - {max(angles)}°")
    print(f"  Dämpfung: {min(atten):.2f} - {max(atten):.2f} dB")
    print(f"  Mean: {np.mean(atten):.2f} dB")

    # Erstelle Output
    output_data = {
        'metadata': data['metadata'].copy(),
        'curve_points': curve_points
    }

    # Update metadata
    output_data['metadata']['method'] += ' → kubisch interpoliert auf 1°'
    output_data['metadata']['interpolation'] = 'cubic spline, periodic boundary'
    output_data['metadata']['resolution_deg'] = 1
    output_data['metadata']['num_points'] = len(curve_points)

    # Speichere
    if args.output is None:
        output_file = args.input.parent / (args.input.stem + '_interpolated.json')
    else:
        output_file = args.output

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\n✓ Gespeichert: {output_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
