"""
Findet die größten Pattern-Dämpfungs-Abweichungen zwischen Excel und MSI-Files
"""
import pandas as pd
import numpy as np
from pathlib import Path
from emf_hotspot.loaders.omen_loader import load_omen_data
from emf_hotspot.loaders.pattern_loader import load_all_patterns, get_pattern_for_antenna
from emf_hotspot.geometry.angles import calculate_relative_angles

# Lade Daten
antenna_system = load_omen_data(Path("input/OMEN R37 clean.xls"))
patterns = load_all_patterns(Path("msi-files"), antenna_system)
xls = pd.ExcelFile("input/OMEN R37 clean.xls")

omen_numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

print("=" * 100)
print("Pattern-Abweichungs-Analyse: Excel vs. MSI-Interpolation")
print("=" * 100)

# Sammle alle Abweichungen
deviations = []

for omen_nr in omen_numbers:
    sheet_name = f"O{omen_nr}"
    if sheet_name not in xls.sheet_names:
        continue

    df_excel = pd.read_excel(xls, sheet_name=sheet_name, header=None)

    def get_row_by_id(row_id):
        for idx in range(len(df_excel)):
            try:
                if pd.notna(df_excel.iloc[idx, 0]) and int(df_excel.iloc[idx, 0]) == row_id:
                    return idx
            except (ValueError, TypeError):
                continue
        return None

    omen = [o for o in antenna_system.omen_locations if o.nr == omen_nr][0]
    point_pos = np.array([omen.position.e, omen.position.n, omen.position.h])

    for ant_idx, antenna in enumerate(antenna_system.antennas, start=1):
        col_idx = ant_idx + 1

        # Excel-Werte
        row_320 = get_row_by_id(320)
        row_330 = get_row_by_id(330)
        row_290 = get_row_by_id(290)  # Kritischer Tilt

        if row_320 is None or row_330 is None:
            continue

        excel_h_atten = float(df_excel.iloc[row_320, col_idx])
        excel_v_atten = float(df_excel.iloc[row_330, col_idx])

        # Kritischer Tilt aus Excel
        excel_critical_tilt = float(df_excel.iloc[row_290, col_idx]) if row_290 is not None else antenna.tilt_deg

        # Python: Worst-Case-Tilt-Suche
        pattern = get_pattern_for_antenna(patterns, antenna.antenna_type, antenna.frequency_band)

        if not pattern:
            continue

        min_v_attenuation = float('inf')
        critical_tilt = antenna.tilt_deg
        critical_azimuth = 0.0
        critical_elevation = 0.0

        tilt_from = int(antenna.tilt_from_deg)
        tilt_to = int(antenna.tilt_to_deg)
        tilt_range = [antenna.tilt_deg] if tilt_from == tilt_to else range(tilt_from, tilt_to + 1)

        for tilt in tilt_range:
            distance, rel_azimuth, rel_elevation = calculate_relative_angles(
                antenna_pos=antenna.position,
                point_pos=point_pos,
                antenna_azimuth=antenna.azimuth_deg,
                antenna_tilt=tilt,
            )

            v_atten = pattern.get_v_attenuation(rel_elevation)

            if v_atten < min_v_attenuation:
                min_v_attenuation = v_atten
                critical_tilt = tilt
                critical_azimuth = rel_azimuth
                critical_elevation = rel_elevation

        # Python-Dämpfungen
        python_h_atten = pattern.get_h_attenuation(critical_azimuth)
        python_v_atten = min_v_attenuation

        # Abweichungen
        h_diff = python_h_atten - excel_h_atten
        v_diff = python_v_atten - excel_v_atten
        total_diff = abs(h_diff) + abs(v_diff)

        deviations.append({
            'omen': f'O{omen_nr}',
            'ant': ant_idx,
            'freq': antenna.frequency_band,
            'type': antenna.antenna_type,
            'tilt_excel': excel_critical_tilt,
            'tilt_python': critical_tilt,
            'azimuth': critical_azimuth,
            'elevation': critical_elevation,
            'excel_h': excel_h_atten,
            'python_h': python_h_atten,
            'h_diff': h_diff,
            'excel_v': excel_v_atten,
            'python_v': python_v_atten,
            'v_diff': v_diff,
            'total_diff': total_diff,
        })

# Sortiere nach totaler Abweichung
deviations.sort(key=lambda x: x['total_diff'], reverse=True)

# Zeige Top 10
print("\nTop 10 größte Pattern-Abweichungen:")
print("=" * 100)
print(f"{'Rank':<5} {'OMEN':<6} {'Ant':<4} {'Freq':<15} {'Tilt':<8} "
      f"{'Azimut':<8} {'Elev':<8} {'H_diff':<10} {'V_diff':<10} {'Total':<10}")
print("-" * 100)

for i, dev in enumerate(deviations[:10], start=1):
    print(f"{i:<5} {dev['omen']:<6} {dev['ant']:<4} {dev['freq']:<15} "
          f"{dev['tilt_python']:>4.0f}°/{dev['tilt_excel']:>4.0f}°  "
          f"{dev['azimuth']:>7.1f}°  {dev['elevation']:>7.1f}°  "
          f"{dev['h_diff']:>9.2f}dB {dev['v_diff']:>9.2f}dB {dev['total_diff']:>9.2f}dB")

# Detaillierte Ausgabe der Top 3
print("\n" + "=" * 100)
print("DETAILLIERTE ANALYSE DER TOP 3 ABWEICHUNGEN")
print("=" * 100)

for i, dev in enumerate(deviations[:3], start=1):
    print(f"\n{'='*100}")
    print(f"#{i}: OMEN {dev['omen']}, Antenne {dev['ant']}, Frequenz {dev['freq']} MHz")
    print(f"{'='*100}")
    print(f"Antennentyp: {dev['type']}")
    print(f"Kritischer Tilt: Excel={dev['tilt_excel']:.0f}°  Python={dev['tilt_python']:.0f}°")
    print(f"Relativer Azimut:    {dev['azimuth']:>7.1f}°")
    print(f"Relative Elevation:  {dev['elevation']:>7.1f}°")
    print()
    print(f"{'':30} {'Excel':>12} {'Python (MSI)':>15} {'Differenz':>12}")
    print(f"{'-'*70}")
    print(f"{'H-Dämpfung (Azimut):':<30} {dev['excel_h']:>11.2f} dB {dev['python_h']:>14.2f} dB "
          f"{dev['h_diff']:>11.2f} dB")
    print(f"{'V-Dämpfung (Elevation):':<30} {dev['excel_v']:>11.2f} dB {dev['python_v']:>14.2f} dB "
          f"{dev['v_diff']:>11.2f} dB")
    print(f"{'TOTAL Dämpfung:':<30} {dev['excel_h']+dev['excel_v']:>11.2f} dB "
          f"{dev['python_h']+dev['python_v']:>14.2f} dB "
          f"{(dev['python_h']+dev['python_v'])-(dev['excel_h']+dev['excel_v']):>11.2f} dB")
    print()
    print("→ BITTE PRÜFEN:")
    print(f"  - Antennendiagramm: {dev['type']} @ {dev['freq']} MHz")
    print(f"  - H-Kurve bei Azimut {dev['azimuth']:.1f}° → Sollte {dev['excel_h']:.1f} dB sein, MSI liefert {dev['python_h']:.1f} dB")
    print(f"  - V-Kurve bei Elevation {dev['elevation']:.1f}° → Sollte {dev['excel_v']:.1f} dB sein, MSI liefert {dev['python_v']:.1f} dB")
