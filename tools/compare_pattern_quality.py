#!/usr/bin/env python3
"""
Antennendiagramm-Qualitätsvergleich

Vergleicht mehrere Digitalisierungen desselben Antennendiagramms:
- ODS-Dateien (cleaned)
- JSON-Dateien (neue Digitalisierungen)
- Überlagert alle Kurven in einem Plot

Usage:
    python compare_pattern_quality.py \
      --ods "msi-files/Antennendämpfungen Hybrid AIR3268 R5_cleaned.ods" \
      --json "msi-files/AIR3268_738-921_PRECISION_1DEG.json" \
      --freq 738-921 --hv h
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import json
from typing import Optional, List, Tuple


def load_from_ods(
    ods_file: Path,
    freq_band: str,
    h_or_v: str
) -> Tuple[np.ndarray, np.ndarray, str]:
    """
    Lädt Pattern aus ODS-Datei.

    Returns:
        (angles, attenuation_db, label)
    """
    df = pd.read_excel(ods_file, sheet_name='dB', engine='odf')

    # Filter
    df_filtered = df[
        (df['Frequenz-band'] == freq_band) &
        (df['vertical or horizontal'] == h_or_v.lower())
    ]

    if len(df_filtered) == 0:
        raise ValueError(f"Keine Daten in ODS für {freq_band} {h_or_v}")

    df_filtered = df_filtered.sort_values('Phi')

    angles = df_filtered['Phi'].values
    attenuation = df_filtered['dB'].values

    label = f"ODS: {ods_file.stem}"

    return angles, attenuation, label


def load_from_json(
    json_file: Path,
    freq_band: str,
    h_or_v: str
) -> Tuple[np.ndarray, np.ndarray, str]:
    """
    Lädt Pattern aus JSON-Datei.

    Unterstützt drei Formate:
    1. AIR3268_ALL_FREQUENCIES_DIGITIZED.json (frequencies -> curve)
    2. AIR3268_738-921_PRECISION_1DEG.json (horizontal/vertical -> curve_points)
    3. AIR3268_738-921_H_CORRECTED_1DEG.json (curve_points direkt)

    Returns:
        (angles, attenuation_db, label)
    """
    with open(json_file, 'r') as f:
        data = json.load(f)

    # Format 1: frequencies -> freq_band -> horizontal/vertical
    if 'frequencies' in data:
        if freq_band not in data['frequencies']:
            raise ValueError(f"Frequenzband {freq_band} nicht in JSON gefunden")

        freq_data = data['frequencies'][freq_band]
        hv_key = 'horizontal' if h_or_v.lower() == 'h' else 'vertical'

        if hv_key not in freq_data:
            raise ValueError(f"{hv_key} nicht in JSON für {freq_band}")

        curve = freq_data[hv_key]['curve']

        # Format: [{"angle": 0, "atten": 0.1}, ...]
        angles = np.array([p['angle'] for p in curve])
        attenuation = np.array([p['atten'] for p in curve])

    # Format 2: horizontal/vertical -> curve_points
    elif 'horizontal' in data or 'vertical' in data:
        hv_key = 'horizontal' if h_or_v.lower() == 'h' else 'vertical'

        if hv_key not in data:
            raise ValueError(f"{hv_key} nicht in JSON")

        curve_points = data[hv_key]['curve_points']

        # Format: [{"angle_deg": 0, "attenuation_db": 0.1}, ...]
        angles = np.array([p['angle_deg'] for p in curve_points])
        attenuation = np.array([p['attenuation_db'] for p in curve_points])

    # Format 3: curve_points direkt
    elif 'curve_points' in data:
        # Prüfe ob Polarisation im metadata passt
        if 'metadata' in data and 'polarization' in data['metadata']:
            pol = data['metadata']['polarization']
            expected_pol = 'horizontal' if h_or_v.lower() == 'h' else 'vertical'
            if pol != expected_pol:
                raise ValueError(f"Polarisation {pol} passt nicht zu {h_or_v}")

        curve_points = data['curve_points']

        # Format: [{"angle_deg": 0, "attenuation_db": 0.1}, ...]
        angles = np.array([p['angle_deg'] for p in curve_points])
        attenuation = np.array([p['attenuation_db'] for p in curve_points])

    else:
        raise ValueError("Unbekanntes JSON-Format")

    label = f"JSON: {json_file.stem}"

    return angles, attenuation, label


def plot_comparison(
    patterns: List[Tuple[np.ndarray, np.ndarray, str]],
    freq_band: str,
    h_or_v: str,
    output_file: Optional[Path] = None
):
    """
    Plottet mehrere Patterns überlagert.

    Args:
        patterns: Liste von (angles, attenuation, label)
        freq_band: Frequenzband für Titel
        h_or_v: H oder V für Titel
        output_file: Optionaler Speicherpfad
    """
    fig = plt.figure(figsize=(12, 12))
    ax = fig.add_subplot(111, projection='polar')

    colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown']
    linestyles = ['-', '--', '-.', ':']

    max_atten = 0

    # Plotte alle Kurven
    for i, (angles, attenuation, label) in enumerate(patterns):
        # Konvertiere zu Radiant
        angles_rad = np.deg2rad(angles)

        # Radius = max_db - Dämpfung
        # Wir finden erstmal das Maximum über alle Kurven
        max_atten = max(max_atten, attenuation.max())

    # Runde auf nächste 10er
    max_db = int(np.ceil(max_atten / 10) * 10)

    # Jetzt plotten mit richtigem Radius
    for i, (angles, attenuation, label) in enumerate(patterns):
        angles_rad = np.deg2rad(angles)
        radius = max_db - attenuation

        color = colors[i % len(colors)]
        linestyle = linestyles[i % len(linestyles)]

        ax.plot(angles_rad, radius, color=color, linestyle=linestyle,
               linewidth=2, label=label, alpha=0.8)

    # Grid-Kreise
    for db_value in [3, 10, 20, 30]:
        if db_value <= max_db:
            r_circle = max_db - db_value
            circle_angles = np.linspace(0, 2*np.pi, 360)
            ax.plot(circle_angles, [r_circle]*360, color='gray',
                   linestyle='--', linewidth=1, alpha=0.3)

            # Label für Grid-Kreis
            ax.text(0, r_circle, f' {db_value}dB', fontsize=9,
                   color='gray', ha='left', va='center')

    # Sektor-Linien (30°)
    for sector_deg in range(0, 360, 30):
        sector_rad = np.deg2rad(sector_deg)
        ax.plot([sector_rad, sector_rad], [0, max_db], 'gray',
               linestyle=':', linewidth=0.8, alpha=0.4)

    # Achsen-Konfiguration
    ax.set_ylim(0, max_db)
    ax.set_theta_zero_location('E')  # 0° = Osten (rechts)
    ax.set_theta_direction(-1)  # Uhrzeigersinn

    # Winkel-Labels
    ax.set_xticks(np.deg2rad([0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330]))
    ax.set_xticklabels(['0°', '30°', '60°', '90°', '120°', '150°',
                        '180°', '210°', '240°', '270°', '300°', '330°'],
                       fontsize=11)

    # Titel
    title = f"Qualitätsvergleich: {freq_band} MHz | {h_or_v.upper()}-Polarisation"
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)

    # Legende
    ax.legend(loc='upper right', bbox_to_anchor=(1.35, 1.1),
             fontsize=11, framealpha=0.9)

    ax.grid(True, alpha=0.3, linewidth=0.8)

    plt.tight_layout()

    # Speichern
    if output_file:
        fig.savefig(output_file, dpi=200, bbox_inches='tight')
        print(f"✓ Gespeichert: {output_file}")

    return fig


def compute_statistics(
    patterns: List[Tuple[np.ndarray, np.ndarray, str]]
):
    """
    Berechnet Statistiken für alle Patterns.
    """
    print("\n" + "="*70)
    print("STATISTIKEN")
    print("="*70)

    for angles, attenuation, label in patterns:
        print(f"\n{label}:")
        print(f"  Punkte: {len(angles)}")
        print(f"  Winkel-Bereich: {angles.min():.1f}° - {angles.max():.1f}°")
        print(f"  Dämpfung: {attenuation.min():.2f} - {attenuation.max():.2f} dB")
        print(f"  Mean: {attenuation.mean():.2f} dB")
        print(f"  Median: {np.median(attenuation):.2f} dB")
        print(f"  Std: {attenuation.std():.2f} dB")

        # Max Sprünge
        if len(angles) > 1:
            db_diffs = np.abs(np.diff(attenuation))
            max_jump_idx = np.argmax(db_diffs)
            max_jump = db_diffs[max_jump_idx]
            print(f"  Max Sprung: {max_jump:.2f} dB bei {angles[max_jump_idx]:.1f}°")

            if max_jump > 5.0:
                print(f"  ⚠️  WARNUNG: Große Sprünge!")

    # Vergleich: Wenn 2+ Patterns
    if len(patterns) >= 2:
        print("\n" + "="*70)
        print("VERGLEICH")
        print("="*70)

        # Interpoliere alle auf gemeinsames Grid (1° Schritte)
        common_angles = np.arange(0, 360, 1)

        interpolated = []
        for angles, attenuation, label in patterns:
            interp_atten = np.interp(common_angles, angles, attenuation, period=360)
            interpolated.append((label, interp_atten))

        # Berechne Differenzen zwischen erstem und allen anderen
        ref_label, ref_atten = interpolated[0]

        for label, atten in interpolated[1:]:
            diff = atten - ref_atten
            rmse = np.sqrt(np.mean(diff**2))
            mae = np.mean(np.abs(diff))
            max_diff = np.max(np.abs(diff))
            max_diff_angle = common_angles[np.argmax(np.abs(diff))]

            print(f"\n{label} vs. {ref_label}:")
            print(f"  RMSE: {rmse:.2f} dB")
            print(f"  MAE: {mae:.2f} dB")
            print(f"  Max Diff: {max_diff:.2f} dB bei {max_diff_angle}°")

            # Bewertung
            if rmse < 0.5:
                print(f"  ✓ Sehr gut (<0.5 dB RMSE)")
            elif rmse < 1.0:
                print(f"  ✓ Gut (<1.0 dB RMSE)")
            elif rmse < 2.0:
                print(f"  ⚠️ Akzeptabel (<2.0 dB RMSE)")
            else:
                print(f"  ❌ Schlecht (>2.0 dB RMSE)")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Vergleicht mehrere Digitalisierungen eines Antennendiagramms"
    )
    parser.add_argument('--ods', type=Path, action='append',
                       help='ODS-Datei (mehrfach möglich)')
    parser.add_argument('--json', type=Path, action='append',
                       help='JSON-Datei (mehrfach möglich)')
    parser.add_argument('--freq', type=str, required=True,
                       help='Frequenzband (z.B. 738-921)')
    parser.add_argument('--hv', type=str, required=True, choices=['h', 'v'],
                       help='H oder V Polarisation')
    parser.add_argument('-o', '--output', type=Path,
                       help='Output PNG (default: comparison_<freq>_<hv>.png)')

    args = parser.parse_args()

    # Lade alle Patterns
    patterns = []

    if args.ods:
        for ods_file in args.ods:
            if not ods_file.exists():
                print(f"❌ ODS nicht gefunden: {ods_file}")
                continue

            try:
                angles, atten, label = load_from_ods(ods_file, args.freq, args.hv)
                patterns.append((angles, atten, label))
                print(f"✓ Geladen: {label} ({len(angles)} Punkte)")
            except Exception as e:
                print(f"❌ Fehler beim Laden von {ods_file}: {e}")

    if args.json:
        for json_file in args.json:
            if not json_file.exists():
                print(f"❌ JSON nicht gefunden: {json_file}")
                continue

            try:
                angles, atten, label = load_from_json(json_file, args.freq, args.hv)
                patterns.append((angles, atten, label))
                print(f"✓ Geladen: {label} ({len(angles)} Punkte)")
            except Exception as e:
                print(f"❌ Fehler beim Laden von {json_file}: {e}")

    if len(patterns) == 0:
        print("\n❌ Keine Patterns geladen!")
        return 1

    print(f"\n✓ {len(patterns)} Patterns geladen")

    # Statistiken
    compute_statistics(patterns)

    # Plot
    if args.output is None:
        output_file = Path(f"comparison_{args.freq}_{args.hv}.png")
    else:
        output_file = args.output

    print("\n" + "="*70)
    print("PLOT")
    print("="*70)

    fig = plot_comparison(patterns, args.freq, args.hv, output_file)

    print("\n✓ Fertig!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
