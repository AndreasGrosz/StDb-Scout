#!/usr/bin/env python3
"""
Polar-Diagramm-Visualisierer aus ODS

Liest digitalisierte Antennendiagramme aus ODS und plottet sie als Polardiagramme.

Usage:
    python plot_pattern_from_ods.py <patterns.ods>
    python plot_pattern_from_ods.py <patterns.ods> --antenna AIR3268 --freq 738-921 --hv h
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from typing import Optional


def plot_polar_pattern(
    angles: np.ndarray,
    attenuation_db: np.ndarray,
    title: str,
    show_grid: bool = True
):
    """
    Plottet ein Antennendiagramm als Polarplot.

    Args:
        angles: Winkel in Grad [0-360]
        attenuation_db: Dämpfung in dB [0-30]
        title: Diagramm-Titel
        show_grid: Grid-Kreise (3dB, 10dB, 20dB) anzeigen
    """
    fig = plt.figure(figsize=(10, 10))
    ax = fig.add_subplot(111, projection='polar')

    # Konvertiere Winkel zu Radiant
    # Antennendiagramm-Konvention: 0° = Osten (rechts), 90° = Norden (oben)
    # Matplotlib Polar default: 0° = Osten, aber wir setzen es auf Osten
    angles_rad = np.deg2rad(angles)

    # Radius = 30 - Dämpfung (Mittelpunkt=0dB, Außen=30dB)
    radius = 30 - attenuation_db

    # Plot Hauptkurve
    ax.plot(angles_rad, radius, 'b-', linewidth=3, label='Digitalisiert')

    # Grid-Kreise
    if show_grid:
        for db_value, color, style in [(3, 'green', '--'), (10, 'orange', '--'), (20, 'red', '--')]:
            r_circle = 30 - db_value
            circle_angles = np.linspace(0, 2*np.pi, 360)
            ax.plot(circle_angles, [r_circle]*360, color=color, linestyle=style,
                   linewidth=1.5, alpha=0.7, label=f'{db_value} dB')

    # Sektor-Linien (30°)
    if show_grid:
        for sector_deg in range(0, 360, 30):
            sector_rad = np.deg2rad(sector_deg)
            ax.plot([sector_rad, sector_rad], [0, 30], 'gray', linestyle=':',
                   linewidth=1, alpha=0.5)

    # Achsen-Konfiguration: 0° = Osten (rechts)
    ax.set_ylim(0, 30)
    ax.set_theta_zero_location('E')  # 0° = Osten (rechts)
    ax.set_theta_direction(-1)  # Uhrzeigersinn (Antennendiagramm-Konvention)

    # Radiale Labels (dB-Werte)
    ax.set_yticks([0, 3, 10, 20, 30])
    ax.set_yticklabels(['30 dB (Mitte)', '27 dB', '20 dB', '10 dB', '0 dB (Außen)'], fontsize=11)

    # Winkel-Labels (Grad)
    ax.set_xticks(np.deg2rad([0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330]))
    ax.set_xticklabels(['0°', '30°', '60°', '90°', '120°', '150°',
                        '180°', '210°', '240°', '270°', '300°', '330°'], fontsize=11)

    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=11)
    ax.grid(True, alpha=0.4, linewidth=0.8)

    return fig


def load_and_plot(
    ods_file: Path,
    antenna_type: Optional[str] = None,
    freq_band: Optional[str] = None,
    h_or_v: Optional[str] = None
):
    """
    Lädt ODS und plottet alle passenden Diagramme.

    Args:
        ods_file: Pfad zur ODS-Datei
        antenna_type: Filter für Antennentyp (None = alle)
        freq_band: Filter für Frequenzband (None = alle)
        h_or_v: Filter für H/V (None = alle)
    """
    print(f"Lade ODS: {ods_file}")

    # Lade DataFrame
    df = pd.read_excel(ods_file, sheet_name='dB', engine='odf')

    print(f"  Gesamt: {len(df)} Datenpunkte")

    # Verfügbare Kombinationen
    print(f"\nVerfügbare Antennentypen: {df['Antennen-Typ'].unique().tolist()}")
    print(f"Verfügbare Frequenzbänder: {df['Frequenz-band'].unique().tolist()}")
    print(f"Verfügbare H/V: {df['vertical or horizontal'].unique().tolist()}")

    # Filter anwenden
    df_filtered = df.copy()

    if antenna_type:
        df_filtered = df_filtered[df_filtered['Antennen-Typ'] == antenna_type]
        print(f"\nFilter: Antennentyp = {antenna_type}")

    if freq_band:
        # Robuste Filterung: Konvertiere zu float (ODS speichert als float64)
        try:
            freq_band_float = float(freq_band)
            df_filtered = df_filtered[df_filtered['Frequenz-band'] == freq_band_float]
            print(f"Filter: Frequenzband = {freq_band_float}")
        except ValueError:
            # Fallback: String-Vergleich
            df_filtered = df_filtered[df_filtered['Frequenz-band'].astype(str) == freq_band]
            print(f"Filter: Frequenzband = {freq_band}")

    if h_or_v:
        df_filtered = df_filtered[df_filtered['vertical or horizontal'] == h_or_v.lower()]
        print(f"Filter: H/V = {h_or_v.upper()}")

    if len(df_filtered) == 0:
        print("\nKeine Daten nach Filterung!")
        return

    print(f"\nNach Filterung: {len(df_filtered)} Datenpunkte")

    # Gruppiere nach Antennentyp, Frequenz, H/V
    grouped = df_filtered.groupby(['Antennen-Typ', 'Frequenz-band', 'vertical or horizontal'])

    print(f"\nPlotte {len(grouped)} Diagramme...\n")

    for (ant_type, freq, hv), group_df in grouped:
        # Sortiere nach Phi
        group_df = group_df.sort_values('Phi')

        angles = group_df['Phi'].values
        attenuation = group_df['dB'].values

        title = f"{ant_type} | {freq} MHz | {hv.upper()}-Polarisation"

        print(f"  {title}")
        print(f"    Winkel: {len(angles)} Punkte, {angles.min():.1f}° - {angles.max():.1f}°")
        print(f"    Dämpfung: {attenuation.min():.1f} - {attenuation.max():.1f} dB")

        # Statistik
        mean_db = attenuation.mean()
        median_db = np.median(attenuation)

        # Finde maximale Sprünge (für Qualitätsprüfung)
        angle_diffs = np.diff(angles)
        db_diffs = np.abs(np.diff(attenuation))
        max_jump_idx = np.argmax(db_diffs)
        max_jump = db_diffs[max_jump_idx]

        print(f"    Mean: {mean_db:.1f} dB, Median: {median_db:.1f} dB")
        print(f"    Max Sprung: {max_jump:.1f} dB bei {angles[max_jump_idx]:.1f}°")

        if max_jump > 5.0:
            print(f"    ⚠️  WARNUNG: Große Sprünge (>{max_jump:.1f} dB) - Qualität prüfen!")

        # Plot
        fig = plot_polar_pattern(angles, attenuation, title)

        plt.tight_layout()

        # Speichere als PNG
        output_name = f"pattern_{ant_type}_{freq}_{hv}.png"
        output_path = ods_file.parent / output_name
        fig.savefig(output_path, dpi=200, bbox_inches='tight')
        print(f"    → Gespeichert: {output_path}")

        plt.close(fig)

    print("\n✓ Fertig!")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Visualisiert digitalisierte Antennendiagramme aus ODS"
    )
    parser.add_argument('ods_file', type=Path, help='Pfad zur ODS-Datei')
    parser.add_argument('--antenna', type=str, help='Filter: Antennentyp (z.B. AIR3268)')
    parser.add_argument('--freq', type=str, help='Filter: Frequenzband (z.B. 738-921)')
    parser.add_argument('--hv', type=str, choices=['h', 'v'],
                       help='Filter: H oder V Polarisation')

    args = parser.parse_args()

    if not args.ods_file.exists():
        print(f"Fehler: Datei nicht gefunden: {args.ods_file}")
        sys.exit(1)

    load_and_plot(
        args.ods_file,
        antenna_type=args.antenna,
        freq_band=args.freq,
        h_or_v=args.hv
    )


if __name__ == "__main__":
    main()
