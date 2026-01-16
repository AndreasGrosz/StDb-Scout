#!/usr/bin/env python3
"""
Traciert schwarze Kurve pixel-für-pixel aus Antennendiagramm

Extrahiert ALLE Pixel entlang der schwarzen Kurve und konvertiert
zu Polarkoordinaten (Winkel, Dämpfung).

Methode:
1. Lade Bild
2. Finde schwarze Pixel (Schwellwert)
3. Filtere nur Kurven-Pixel (nicht Grid-Linien)
4. Für jeden Pixel: Berechne Polarkoordinaten
5. Gruppiere nach Winkel (1°-Bins)
6. Mittelwert pro Winkel

Usage:
    python trace_curve_pixels.py diagram.png \
      --center 410 390 \
      --radius-0db 245 \
      --output curve.json
"""

import sys
from pathlib import Path
import json
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt


def load_image_grayscale(image_path: Path) -> np.ndarray:
    """Lädt Bild als Grayscale Array."""
    img = Image.open(image_path).convert('L')
    return np.array(img)


def find_black_pixels(img: np.ndarray, threshold: int = 50) -> np.ndarray:
    """
    Findet schwarze Pixel (Kurve) im Bild.

    Args:
        img: Grayscale image array
        threshold: Pixel < threshold gelten als schwarz

    Returns:
        Array of shape (N, 2) mit [y, x] Koordinaten
    """
    mask = img < threshold
    coords = np.argwhere(mask)  # Returns (y, x) pairs
    return coords


def filter_curve_region(coords: np.ndarray, center: tuple, min_radius: float, max_radius: float) -> np.ndarray:
    """
    Filtert Pixel die im relevanten Radius-Bereich liegen.

    Entfernt:
    - Zentrum-Markierungen (zu nah)
    - Äußere Grid-Linien (zu weit)
    - Text (außerhalb Diagramm)
    """
    cx, cy = center

    # Berechne Abstand vom Zentrum für alle Pixel
    distances = np.sqrt((coords[:, 1] - cx)**2 + (coords[:, 0] - cy)**2)

    # Filtere nach Radius
    mask = (distances >= min_radius) & (distances <= max_radius)

    return coords[mask]


def pixels_to_polar(coords: np.ndarray, center: tuple, radius_0db: float) -> list:
    """
    Konvertiert Pixel-Koordinaten zu Polarkoordinaten (Winkel, Dämpfung).

    Args:
        coords: Array of shape (N, 2) mit [y, x] Koordinaten
        center: (cx, cy) Zentrum in Pixeln
        radius_0db: Radius für 0dB in Pixeln

    Returns:
        Liste von {"angle_deg": float, "attenuation_db": float, "radius_px": float}
    """
    cx, cy = center

    result = []

    for y, x in coords:
        # Relativer Vektor zum Zentrum
        dx = x - cx
        dy = y - cy

        # Radius (Abstand vom Zentrum)
        r = np.sqrt(dx**2 + dy**2)

        # Winkel in Radiant
        # atan2(dy, dx) gibt Winkel in [-π, π]
        # 0° = rechts (Osten), 90° = oben, aber wir wollen 0° = oben
        # Also: theta = atan2(dx, -dy) für 0° = oben, im Uhrzeigersinn
        theta_rad = np.arctan2(dx, -dy)

        # Konvertiere zu [0, 2π]
        if theta_rad < 0:
            theta_rad += 2 * np.pi

        # Konvertiere zu Grad
        angle_deg = np.degrees(theta_rad)

        # Dämpfung: Je größer der Radius, desto MEHR Dämpfung
        # Bei Polardiagramm: Innen = 0dB (stark), Außen = hohe Dämpfung
        # Aber ACHTUNG: In vielen Diagrammen ist das umgekehrt!
        # Wir müssen prüfen: radius_0db ist der INNERSTE Kreis oder ÄUSSERSTE?

        # Standard-Konvention für Dämpfungs-Diagramme:
        # Zentrum = 0dB (Maximum), nach außen mehr Dämpfung
        # Also: attenuation = (r - radius_at_center) / radius_per_10db * 10

        # ABER: In diesen Diagrammen ist 0dB nicht im Zentrum!
        # Es gibt Labels: -30dB, -20dB, -10dB, 0dB
        # 0dB ist ein Kreis mit radius_0db
        # Nach innen = negative Dämpfung = Verstärkung (nicht möglich)
        # Nach außen = positive Dämpfung

        # Korrektur: radius_0db ist wo 0dB ist
        # Dämpfung = (r - radius_0db) / radius_per_10db * 10
        # Wir wissen noch nicht radius_per_10db, also speichern wir erstmal nur r

        result.append({
            'angle_deg': float(angle_deg),
            'radius_px': float(r)
        })

    return result


def bin_by_angle(polar_points: list, bin_size_deg: float = 1.0) -> list:
    """
    Gruppiert Punkte nach Winkel-Bins und mittelt.

    Args:
        polar_points: Liste von {"angle_deg": x, "radius_px": r}
        bin_size_deg: Bin-Größe in Grad

    Returns:
        Liste von {"angle_deg": center, "radius_px": mean, "count": n}
    """
    # Erstelle Bins
    bins = np.arange(0, 360, bin_size_deg)

    # Gruppiere
    binned = {}
    for p in polar_points:
        angle = p['angle_deg']
        bin_idx = int(angle / bin_size_deg)

        if bin_idx not in binned:
            binned[bin_idx] = []

        binned[bin_idx].append(p['radius_px'])

    # Mittelwert pro Bin
    result = []
    for bin_idx in sorted(binned.keys()):
        radii = binned[bin_idx]
        angle_center = (bin_idx + 0.5) * bin_size_deg

        result.append({
            'angle_deg': float(angle_center),
            'radius_px': float(np.mean(radii)),
            'radius_std': float(np.std(radii)),
            'count': len(radii)
        })

    return result


def radius_to_attenuation(binned_points: list, radius_0db: float, radius_per_10db: float) -> list:
    """
    Konvertiert Radius zu Dämpfung.

    Args:
        binned_points: Liste mit 'radius_px'
        radius_0db: Radius bei 0dB
        radius_per_10db: Radius-Änderung pro 10dB

    Returns:
        Liste mit zusätzlichem 'attenuation_db'
    """
    result = []

    for p in binned_points:
        r = p['radius_px']

        # Dämpfung = (r - radius_0db) / radius_per_10db * 10
        # Wenn r > radius_0db: positive Dämpfung
        # Wenn r < radius_0db: negative Dämpfung (clippen auf 0)

        atten_db = (r - radius_0db) / radius_per_10db * 10

        # Clippe negative Werte
        if atten_db < 0:
            atten_db = 0

        result.append({
            'angle_deg': p['angle_deg'],
            'attenuation_db': float(atten_db),
            'radius_px': p['radius_px'],
            'radius_std': p.get('radius_std', 0),
            'count': p.get('count', 1)
        })

    return result


def plot_diagnostic(img: np.ndarray, coords: np.ndarray, filtered_coords: np.ndarray,
                   center: tuple, radius_0db: float, output_path: Path):
    """Erstellt diagnostischen Plot."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))

    # Original mit markierten Pixeln
    axes[0].imshow(img, cmap='gray')
    axes[0].scatter(coords[:, 1], coords[:, 0], c='red', s=1, alpha=0.3, label='Alle schwarzen Pixel')
    axes[0].scatter(filtered_coords[:, 1], filtered_coords[:, 0], c='blue', s=1, alpha=0.5, label='Gefilterte Kurve')

    # Zentrum
    cx, cy = center
    axes[0].plot(cx, cy, 'go', markersize=10, label='Zentrum')

    # 0dB-Kreis
    theta = np.linspace(0, 2*np.pi, 100)
    x_circle = cx + radius_0db * np.cos(theta)
    y_circle = cy + radius_0db * np.sin(theta)
    axes[0].plot(x_circle, y_circle, 'g--', linewidth=2, label='0dB Radius')

    axes[0].set_title('Pixeldetection')
    axes[0].legend()
    axes[0].axis('equal')

    # Zoom auf Diagramm
    margin = 100
    axes[1].imshow(img, cmap='gray')
    axes[1].scatter(filtered_coords[:, 1], filtered_coords[:, 0], c='blue', s=2, alpha=0.8)
    axes[1].plot(cx, cy, 'go', markersize=10)
    axes[1].plot(x_circle, y_circle, 'g--', linewidth=2)
    axes[1].set_xlim(cx - radius_0db - margin, cx + radius_0db + margin)
    axes[1].set_ylim(cy + radius_0db + margin, cy - radius_0db - margin)
    axes[1].set_title('Zoom: Diagramm-Bereich')

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)

    print(f"  → Diagnostic plot: {output_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Traciert schwarze Kurve pixel-für-pixel"
    )
    parser.add_argument('image', type=Path, help='Antennendiagramm-Bild')
    parser.add_argument('--center', type=int, nargs=2, required=True,
                       metavar=('CX', 'CY'),
                       help='Zentrum in Pixeln (x y)')
    parser.add_argument('--radius-0db', type=float, required=True,
                       help='Radius für 0dB in Pixeln')
    parser.add_argument('--radius-per-10db', type=float,
                       help='Radius pro 10dB (default: auto aus max_radius)')
    parser.add_argument('--threshold', type=int, default=50,
                       help='Schwellwert für schwarze Pixel (default: 50)')
    parser.add_argument('--bin-size', type=float, default=1.0,
                       help='Winkel-Bin-Größe in Grad (default: 1.0)')
    parser.add_argument('-o', '--output', type=Path,
                       help='Output JSON (default: <image>_traced.json)')
    parser.add_argument('--diagnostic', action='store_true',
                       help='Erstelle diagnostischen Plot')

    args = parser.parse_args()

    if not args.image.exists():
        print(f"❌ Bild nicht gefunden: {args.image}")
        return 1

    print(f"Lade Bild: {args.image}")
    img = load_image_grayscale(args.image)
    print(f"  Größe: {img.shape[1]} x {img.shape[0]} px")

    # Finde schwarze Pixel
    print(f"\nFinde schwarze Pixel (Threshold: {args.threshold})...")
    coords = find_black_pixels(img, args.threshold)
    print(f"  Gefunden: {len(coords)} schwarze Pixel")

    # Filtere Kurven-Bereich
    center = tuple(args.center)
    min_radius = args.radius_0db * 0.3  # Mindestens 30% von 0dB-Radius
    max_radius = args.radius_0db * 1.8  # Maximal 180% von 0dB-Radius

    print(f"\nFiltere Kurven-Bereich...")
    print(f"  Zentrum: {center}")
    print(f"  Radius-Bereich: {min_radius:.1f} - {max_radius:.1f} px")

    filtered_coords = filter_curve_region(coords, center, min_radius, max_radius)
    print(f"  Gefiltert: {len(filtered_coords)} Kurven-Pixel")

    # Konvertiere zu Polarkoordinaten
    print(f"\nKonvertiere zu Polarkoordinaten...")
    polar_points = pixels_to_polar(filtered_coords, center, args.radius_0db)
    print(f"  {len(polar_points)} Polar-Punkte")

    # Gruppiere nach Winkel
    print(f"\nGruppiere nach Winkel (Bin-Size: {args.bin_size}°)...")
    binned = bin_by_angle(polar_points, args.bin_size)
    print(f"  {len(binned)} Winkel-Bins")

    # Statistik
    radii = [p['radius_px'] for p in binned]
    print(f"\n  Radius: {min(radii):.1f} - {max(radii):.1f} px")
    print(f"  Mean: {np.mean(radii):.1f} px")

    # Berechne radius_per_10db falls nicht gegeben
    if args.radius_per_10db is None:
        # Schätze aus max_radius - radius_0db
        # Annahme: max_radius entspricht ~40dB
        max_r = max(radii)
        estimated_max_db = 40  # Typisch für Antennendiagramme
        radius_per_10db = (max_r - args.radius_0db) / (estimated_max_db / 10)
        print(f"\n  Auto-berechnet: radius_per_10db = {radius_per_10db:.2f} px")
    else:
        radius_per_10db = args.radius_per_10db

    # Konvertiere zu Dämpfung
    print(f"\nKonvertiere Radius zu Dämpfung...")
    print(f"  0dB-Radius: {args.radius_0db:.1f} px")
    print(f"  Pro 10dB: {radius_per_10db:.2f} px")

    curve_points = radius_to_attenuation(binned, args.radius_0db, radius_per_10db)

    atten_values = [p['attenuation_db'] for p in curve_points]
    print(f"\n  Dämpfung: {min(atten_values):.2f} - {max(atten_values):.2f} dB")
    print(f"  Mean: {np.mean(atten_values):.2f} dB")

    # Speichere
    if args.output is None:
        output_file = args.image.parent / (args.image.stem + '_traced.json')
    else:
        output_file = args.output

    output_data = {
        'metadata': {
            'source_image': args.image.name,
            'digitized_by': 'trace_curve_pixels.py (pixel-by-pixel tracing)',
            'method': 'Black pixel detection + polar coordinate conversion',
            'center_px': list(center),
            'radius_0db_px': args.radius_0db,
            'radius_per_10db_px': radius_per_10db,
            'threshold': args.threshold,
            'bin_size_deg': args.bin_size,
            'num_points': len(curve_points)
        },
        'curve_points': curve_points
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\n✓ Gespeichert: {output_file}")

    # Diagnostic plot
    if args.diagnostic:
        diag_path = output_file.parent / (output_file.stem + '_diagnostic.png')
        print(f"\nErstelle Diagnostic Plot...")
        plot_diagnostic(img, coords, filtered_coords, center, args.radius_0db, diag_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
