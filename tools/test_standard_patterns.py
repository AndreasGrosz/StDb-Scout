#!/usr/bin/env python3
"""
Test-Script für Standard-Antennendiagramme.

Demonstriert:
1. Standard-Patterns erstellen
2. Mit ODS-Patterns vergleichen
3. Polar-Plots generieren
"""

import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

# Füge emf_hotspot zum Path hinzu
sys.path.insert(0, str(Path(__file__).parent.parent))

from emf_hotspot.patterns import (
    StandardPattern,
    ericsson_air3268_standard,
    PatternLoader,
    load_antenna_patterns,
)


def plot_pattern_comparison(
    pattern_standard: 'PatternData',
    pattern_ods: 'PatternData' = None,
    output_file: Path = None
):
    """
    Plottet Standard-Pattern vs. ODS-Pattern (falls vorhanden).
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6),
                                    subplot_kw={'projection': 'polar'})

    # Azimut (H)
    angles_rad = np.deg2rad(pattern_standard.angles_deg)
    radius_std = 30 - pattern_standard.attenuation_dB  # Umrechnung für Polar

    ax1.plot(angles_rad, radius_std, 'b-', linewidth=2, label='Standard (ITU-R)')

    if pattern_ods:
        angles_ods_rad = np.deg2rad(pattern_ods.angles_deg)
        radius_ods = 30 - pattern_ods.attenuation_dB
        ax1.plot(angles_ods_rad, radius_ods, 'r--', linewidth=1, alpha=0.7,
                label='Digitalisiert (ODS)')

    # Grid-Kreise
    for db_value, color in [(3, 'green'), (10, 'orange'), (20, 'red')]:
        r_circle = 30 - db_value
        circle_angles = np.linspace(0, 2*np.pi, 360)
        ax1.plot(circle_angles, [r_circle]*360, color=color, linestyle=':',
                linewidth=1, alpha=0.4, label=f'{db_value} dB')

    ax1.set_ylim(0, 30)
    ax1.set_theta_zero_location('E')
    ax1.set_theta_direction(-1)
    ax1.set_title(f'Azimut (H-Polarisation)\n{pattern_standard.antenna_type}',
                  fontsize=12, fontweight='bold')
    ax1.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=9)
    ax1.grid(True, alpha=0.3)

    # Elevation (V) - nur Standard
    pattern_v = PatternLoader.from_standard(
        ericsson_air3268_standard(), 'elevation'
    )
    angles_v_rad = np.deg2rad(pattern_v.angles_deg)
    radius_v = 30 - pattern_v.attenuation_dB

    ax2.plot(angles_v_rad, radius_v, 'b-', linewidth=2, label='Standard (ITU-R)')

    for db_value, color in [(3, 'green'), (10, 'orange'), (20, 'red')]:
        r_circle = 30 - db_value
        circle_angles = np.linspace(0, 2*np.pi, 360)
        ax2.plot(circle_angles, [r_circle]*360, color=color, linestyle=':',
                linewidth=1, alpha=0.4, label=f'{db_value} dB')

    ax2.set_ylim(0, 30)
    ax2.set_theta_zero_location('E')
    ax2.set_theta_direction(-1)
    ax2.set_title('Elevation (V-Polarisation)\n(Standard-Modell)',
                  fontsize=12, fontweight='bold')
    ax2.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=9)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    if output_file:
        plt.savefig(output_file, dpi=200, bbox_inches='tight')
        print(f"✓ Plot gespeichert: {output_file}")
    else:
        plt.show()

    plt.close()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Testet Standard-Antennendiagramme und vergleicht mit ODS"
    )
    parser.add_argument('--ods', type=Path,
                       help='ODS-Datei mit digitalisierten Patterns')
    parser.add_argument('--antenna', type=str, default='AIR3268',
                       help='Antennentyp')
    parser.add_argument('--freq', type=float, default=1805,
                       help='Frequenz in MHz')
    parser.add_argument('-o', '--output', type=Path,
                       help='Output PNG-Datei')

    args = parser.parse_args()

    print("="*60)
    print("STANDARD-PATTERN TEST")
    print("="*60)

    # Erstelle Standard-Pattern
    print("\n1. Standard-Pattern erstellen...")
    standard = ericsson_air3268_standard()
    print(standard)

    # Lade H-Pattern
    print(f"\n2. Pattern laden (ODS: {args.ods})...")
    pattern_h_std = PatternLoader.from_standard(standard, 'azimuth')

    pattern_h_ods = None
    if args.ods:
        pattern_h_ods = PatternLoader.from_ods(
            args.ods, args.antenna, args.freq, 'h'
        )

    # Vergleich
    print(f"\n3. Standard-Pattern:")
    print(pattern_h_std)

    if pattern_h_ods:
        print(f"\n4. ODS-Pattern:")
        print(pattern_h_ods)

        # Vergleiche Dämpfung bei verschiedenen Winkeln
        print(f"\n5. Vergleich bei typischen Winkeln:")
        print(f"{'Winkel':>10s} {'Standard':>12s} {'ODS':>12s} {'Delta':>12s}")
        print("-" * 50)
        for angle in [0, 30, 60, 90, 120, 150, 180]:
            att_std = pattern_h_std.get_attenuation(angle)
            att_ods = pattern_h_ods.get_attenuation(angle)
            delta = att_ods - att_std
            print(f"{angle:>10.0f}° {att_std:>10.1f} dB {att_ods:>10.1f} dB {delta:>+10.1f} dB")

    # Plot
    print(f"\n6. Erstelle Plot...")
    output_file = args.output or Path('test_patterns.png')
    plot_pattern_comparison(pattern_h_std, pattern_h_ods, output_file)

    # Beispiel: Dämpfung berechnen
    print(f"\n7. Beispiel-Berechnungen:")
    print(f"\nAzimut-Dämpfung (H):")
    print(f"  0° (Hauptstrahl):   {pattern_h_std.get_attenuation(0):.1f} dB")
    print(f"  30° (Randbereich):  {pattern_h_std.get_attenuation(30):.1f} dB")
    print(f"  90° (Seite):        {pattern_h_std.get_attenuation(90):.1f} dB")
    print(f"  180° (Rückseite):   {pattern_h_std.get_attenuation(180):.1f} dB")

    pattern_v = PatternLoader.from_standard(standard, 'elevation')
    print(f"\nElevation-Dämpfung (V):")
    print(f"  0° (Horizont):      {pattern_v.get_attenuation(0):.1f} dB")
    print(f"  10° (leicht unten): {pattern_v.get_attenuation(350):.1f} dB")  # 350° = -10°
    print(f"  90° (Zenith):       {pattern_v.get_attenuation(90):.1f} dB")

    print(f"\n{'='*60}")
    print("✓ TEST ABGESCHLOSSEN")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
