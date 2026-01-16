#!/usr/bin/env python3
"""
MSI-Pattern Data Cleaner

Behebt typische Digitalisierungsfehler:
1. Negative Werte → Clip auf 0
2. Lücken → Interpolation (alle 0.5°)
3. Sprünge → Median-Filter (optional)
4. Duplikate → Mittelwert
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
from scipy.signal import medfilt

def clean_pattern_data(
    df: pd.DataFrame,
    antenna_type: str,
    freq_band: float,
    h_or_v: str,
    clip_negatives: bool = True,
    interpolate_gaps: bool = True,
    median_filter_size: int = 0,  # 0 = deaktiviert, 3/5 = aktiviert
    resolution_deg: float = 0.5,
) -> pd.DataFrame:
    """
    Bereinigt ein einzelnes Pattern.

    Args:
        df: Gesamt-DataFrame
        antenna_type: Antennentyp
        freq_band: Frequenzband
        h_or_v: 'h' oder 'v'
        clip_negatives: Negative Werte auf 0 setzen
        interpolate_gaps: Lücken interpolieren
        median_filter_size: Größe für Median-Filter (0=aus)
        resolution_deg: Winkel-Auflösung

    Returns:
        Bereinigtes DataFrame (nur dieses Pattern)
    """
    # Filtere Pattern
    subset = df[
        (df['Antennen-Typ'] == antenna_type) &
        (df['Frequenz-band'] == freq_band) &
        (df['vertical or horizontal'] == h_or_v)
    ].copy()

    if len(subset) == 0:
        print(f"  ⚠️  Keine Daten für {antenna_type} @ {freq_band} {h_or_v.upper()}")
        return pd.DataFrame()

    # Sortiere nach Winkel
    subset = subset.sort_values('Phi')

    angles = subset['Phi'].values
    values = subset['dB'].values

    print(f"\n  {antenna_type} @ {freq_band} {h_or_v.upper()}:")
    print(f"    Originale Punkte: {len(values)}")
    print(f"    Min/Max: {values.min():.3f} / {values.max():.3f} dB")

    # Schritt 1: Clip negative Werte
    if clip_negatives:
        negative_count = np.sum(values < 0)
        if negative_count > 0:
            print(f"    → Clip {negative_count} negative Werte auf 0")
            values = np.clip(values, 0, None)

    # Schritt 2: Median-Filter (optional, für Sprünge)
    if median_filter_size > 0:
        values_filtered = medfilt(values, kernel_size=median_filter_size)
        max_change = np.max(np.abs(values - values_filtered))
        if max_change > 0.1:
            print(f"    → Median-Filter (Kernel={median_filter_size}), max Änderung: {max_change:.2f} dB")
            values = values_filtered

    # Schritt 3: Duplikate entfernen (falls vorhanden)
    # Gruppiere nach Winkel und nimm Mittelwert
    df_temp = pd.DataFrame({'Phi': angles, 'dB': values})
    df_grouped = df_temp.groupby('Phi').mean().reset_index()
    angles_unique = df_grouped['Phi'].values
    values_unique = df_grouped['dB'].values

    if len(angles_unique) < len(angles):
        print(f"    → {len(angles) - len(angles_unique)} Duplikate entfernt (Mittelwert)")
        angles = angles_unique
        values = values_unique

    # Schritt 4: Interpolation für vollständige Winkelabdeckung
    if interpolate_gaps:
        expected_angles = np.arange(0, 360, resolution_deg)
        missing_count = len(set(expected_angles) - set(angles))

        if missing_count > 0:
            print(f"    → Interpoliere {missing_count} fehlende Winkel")

            # Erstelle Interpolator
            # Wichtig: Zyklisch (0° = 360°)
            # Füge 360° hinzu mit Wert von 0°
            angles_cyclic = np.append(angles, 360.0)
            values_cyclic = np.append(values, values[0])

            interpolator = interp1d(
                angles_cyclic,
                values_cyclic,
                kind='linear',
                bounds_error=False,
                fill_value='extrapolate'
            )

            # Interpoliere auf vollständiges Raster
            angles = expected_angles
            values = interpolator(angles)

            # Clip wieder (falls Interpolation negativ wurde)
            if clip_negatives:
                values = np.clip(values, 0, None)

    print(f"    Bereinigte Punkte: {len(values)}")
    print(f"    Min/Max: {values.min():.3f} / {values.max():.3f} dB")

    # Erstelle bereinigtes DataFrame
    cleaned_df = pd.DataFrame({
        'StDb-ID': subset['StDb-ID'].iloc[0] if 'StDb-ID' in subset.columns else '',
        'Antennen-Typ': antenna_type,
        'Frequenz-band': freq_band,
        'vertical or horizontal': h_or_v,
        'Phi': angles,
        'dB': values,
        'MSI-Filename': subset['MSI-Filename'].iloc[0] if 'MSI-Filename' in subset.columns else '',
        'Frequency-Range': subset['Frequency-Range'].iloc[0] if 'Frequency-Range' in subset.columns else '',
        'Created-By': 'clean_msi_patterns.py',
        'PDF-Path': subset['PDF-Path'].iloc[0] if 'PDF-Path' in subset.columns else '',
        'PDF-Filename': subset['PDF-Filename'].iloc[0] if 'PDF-Filename' in subset.columns else '',
    })

    return cleaned_df


def clean_ods_file(
    input_file: Path,
    output_file: Path,
    **cleaning_options
):
    """
    Bereinigt alle Patterns in einer ODS-Datei.

    Args:
        input_file: Input ODS
        output_file: Output ODS
        **cleaning_options: Optionen für clean_pattern_data()
    """
    print("=" * 80)
    print(f"MSI-PATTERN DATA CLEANER")
    print("=" * 80)
    print(f"\nInput:  {input_file}")
    print(f"Output: {output_file}")

    # Lade Original
    df = pd.read_excel(input_file, sheet_name='dB', engine='odf')

    # Normalisiere Spalten (entferne Leerzeichen)
    if 'Antennen-Typ' in df.columns:
        df['Antennen-Typ'] = df['Antennen-Typ'].astype(str).str.strip()
    if 'Frequenz-band' in df.columns:
        df['Frequenz-band'] = df['Frequenz-band'].astype(str).str.strip()
    if 'vertical or horizontal' in df.columns:
        df['vertical or horizontal'] = df['vertical or horizontal'].astype(str).str.strip().str.lower()

    print(f"\nOriginale Daten: {len(df)} Zeilen")

    # Sammle alle Kombinationen
    combinations = []
    for typ in df['Antennen-Typ'].unique():
        for freq in df['Frequenz-band'].unique():
            for hv in df['vertical or horizontal'].unique():
                subset = df[
                    (df['Antennen-Typ'] == typ) &
                    (df['Frequenz-band'] == freq) &
                    (df['vertical or horizontal'] == hv)
                ]
                if len(subset) > 0:
                    combinations.append((typ, freq, hv))

    print(f"\nGefundene Patterns: {len(combinations)}")

    # Bereinige jedes Pattern
    cleaned_dfs = []
    for typ, freq, hv in combinations:
        cleaned_df = clean_pattern_data(
            df, typ, freq, hv,
            **cleaning_options
        )
        if len(cleaned_df) > 0:
            cleaned_dfs.append(cleaned_df)

    # Kombiniere alle
    result_df = pd.concat(cleaned_dfs, ignore_index=True)

    print(f"\n{'='*80}")
    print(f"ERGEBNIS")
    print(f"{'='*80}")
    print(f"Bereinigte Daten: {len(result_df)} Zeilen")
    print(f"Zuwachs: +{len(result_df) - len(df)} Zeilen (durch Interpolation)")

    # Speichere
    with pd.ExcelWriter(output_file, engine='odf') as writer:
        result_df.to_excel(writer, sheet_name='dB', index=False)

    print(f"\n✓ Gespeichert: {output_file}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Bereinigt digitalisierte MSI-Pattern-Daten"
    )
    parser.add_argument(
        'input_file',
        type=Path,
        help='Input ODS-Datei'
    )
    parser.add_argument(
        '-o', '--output',
        type=Path,
        default=None,
        help='Output ODS-Datei (default: <input>_cleaned.ods)'
    )
    parser.add_argument(
        '--no-clip',
        action='store_true',
        help='Negative Werte NICHT auf 0 clippen'
    )
    parser.add_argument(
        '--no-interpolate',
        action='store_true',
        help='Lücken NICHT interpolieren'
    )
    parser.add_argument(
        '--median-filter',
        type=int,
        default=0,
        choices=[0, 3, 5, 7],
        help='Median-Filter-Größe (0=aus, 3/5/7=aktiviert)'
    )
    parser.add_argument(
        '--resolution',
        type=float,
        default=0.5,
        help='Winkel-Auflösung in Grad (default: 0.5)'
    )

    args = parser.parse_args()

    if not args.input_file.exists():
        print(f"❌ Fehler: {args.input_file} nicht gefunden!")
        return 1

    # Output-Datei
    if args.output is None:
        output_file = args.input_file.parent / (args.input_file.stem + '_cleaned.ods')
    else:
        output_file = args.output

    # Bereinige
    try:
        clean_ods_file(
            input_file=args.input_file,
            output_file=output_file,
            clip_negatives=not args.no_clip,
            interpolate_gaps=not args.no_interpolate,
            median_filter_size=args.median_filter,
            resolution_deg=args.resolution,
        )
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
