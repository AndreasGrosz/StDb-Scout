"""
Debug-Script für OMEN 8 Vergleich mit Excel-Werten
"""
import pandas as pd
from pathlib import Path
from emf_hotspot.loaders.omen_loader import load_omen_data
from emf_hotspot.loaders.pattern_loader import load_all_patterns
from emf_hotspot.physics.summation import calculate_total_e_field_at_point
from emf_hotspot.models import FacadePoint
from emf_hotspot.geometry.angles import calculate_relative_angles
import numpy as np

# OMEN 8 Excel-Daten (aus CSV)
OMEN8_CSV = "input/OMEN 8 version R37 clean.csv"

# Lade Antennendaten
antenna_system = load_omen_data(Path("input/OMEN R37 clean.xls"))
patterns = load_all_patterns(Path("msi-files"), antenna_system)

print("=" * 80)
print("OMEN 8 Debug-Analyse")
print("=" * 80)

# Finde OMEN 8 Location
omen8 = None
for omen in antenna_system.omen_locations:
    if omen.nr == 8:
        omen8 = omen
        break

if omen8 is None:
    print("ERROR: OMEN 8 nicht gefunden!")
    exit(1)

print(f"\nOMEN 8 Position: {omen8.position.e:.2f} / {omen8.position.n:.2f} / {omen8.position.h:.2f}")
print(f"Expected E-Field: {omen8.e_field_expected:.4f} V/m")
print(f"Building Attenuation: {omen8.building_attenuation_db:.2f} dB")

# Lade Excel-Werte aus CSV
df_excel = pd.read_csv(OMEN8_CSV)

# Excel-Werte auslesen (Zeilen-Nummern im CSV)
excel_data = {}
for idx, row in df_excel.iterrows():
    row_id = row.iloc[0]  # Erste Spalte ist die Zeilennummer
    if pd.notna(row_id):
        excel_data[row_id] = row

# Extrahiere Excel-Werte für 9 Antennen (Spalten 2-10)
print("\n" + "=" * 80)
print("Vergleich Excel vs. Python für jede Antenne:")
print("=" * 80)

# Erstelle FacadePoint für OMEN 8
point = FacadePoint(
    building_id="OMEN8",
    x=omen8.position.e,
    y=omen8.position.n,
    z=omen8.position.h,
    normal=np.array([0, 0, 1])
)

total_e_squared = 0.0

for ant_idx, antenna in enumerate(antenna_system.antennas, start=1):
    print(f"\n--- Antenne {ant_idx} ({antenna.frequency_band} MHz) ---")

    # Excel-Werte (Spalte 2-10 = Index 2-10)
    col_idx = ant_idx + 1

    excel_distance = float(excel_data[250].iloc[col_idx]) if 250 in excel_data else None
    excel_azimuth_omen = float(excel_data[260].iloc[col_idx]) if 260 in excel_data else None
    excel_elevation = float(excel_data[270].iloc[col_idx]) if 270 in excel_data else None
    excel_h_atten = float(excel_data[320].iloc[col_idx]) if 320 in excel_data else None
    excel_v_atten = float(excel_data[330].iloc[col_idx]) if 330 in excel_data else None
    excel_total_atten = float(excel_data[340].iloc[col_idx]) if 340 in excel_data else None
    excel_e_contrib = float(excel_data[390].iloc[col_idx]) if 390 in excel_data else None

    # Python-Berechnung mit Worst-Case-Tilt
    from emf_hotspot.loaders.pattern_loader import get_pattern_for_antenna
    pattern = get_pattern_for_antenna(patterns, antenna.antenna_type, antenna.frequency_band)

    # Worst-Case-Tilt-Suche
    min_v_attenuation = float('inf')
    critical_tilt = antenna.tilt_deg

    tilt_from = int(antenna.tilt_from_deg)
    tilt_to = int(antenna.tilt_to_deg)

    if tilt_from == tilt_to:
        tilt_range = [antenna.tilt_deg]
    else:
        tilt_range = range(tilt_from, tilt_to + 1)

    for tilt in tilt_range:
        distance, rel_azimuth, rel_elevation = calculate_relative_angles(
            antenna_pos=antenna.position,
            point_pos=point.to_array(),
            antenna_azimuth=antenna.azimuth_deg,
            antenna_tilt=tilt,
        )

        if pattern:
            v_atten = pattern.get_v_attenuation(rel_elevation)
        else:
            v_atten = 0.0

        if v_atten < min_v_attenuation:
            min_v_attenuation = v_atten
            critical_tilt = tilt
            critical_distance = distance
            critical_azimuth = rel_azimuth
            critical_elevation = rel_elevation

    # H-Dämpfung mit kritischem Azimut
    if pattern:
        h_atten = pattern.get_h_attenuation(critical_azimuth)
        v_atten = min_v_attenuation
    else:
        h_atten = 0.0
        v_atten = 0.0

    # E-Feld berechnen
    from emf_hotspot.physics.propagation import calculate_e_field_with_pattern
    e_field = calculate_e_field_with_pattern(
        erp_watts=antenna.erp_watts,
        distance_m=critical_distance,
        h_attenuation_db=h_atten,
        v_attenuation_db=v_atten,
        building_attenuation_db=omen8.building_attenuation_db,
    )

    total_e_squared += e_field ** 2

    # Ausgabe
    print(f"  Tilt-Bereich: {antenna.tilt_from_deg}° bis {antenna.tilt_to_deg}°")
    print(f"  Kritischer Tilt: {critical_tilt}°")
    print(f"  Distance:     Excel={excel_distance:.2f}m  Python={critical_distance:.2f}m")
    print(f"  Azimuth OMEN: Excel={excel_azimuth_omen:.1f}°  (absolut)")
    print(f"  Elevation:    Excel={excel_elevation:.1f}°  Python={critical_elevation:.1f}°")
    print(f"  H-Dämpfung:   Excel={excel_h_atten:.2f}dB  Python={h_atten:.2f}dB")
    print(f"  V-Dämpfung:   Excel={excel_v_atten:.2f}dB  Python={v_atten:.2f}dB")
    print(f"  Total Dämpf.: Excel={excel_total_atten:.2f}dB  Python={h_atten+v_atten:.2f}dB")
    print(f"  E-Beitrag:    Excel={excel_e_contrib:.2f}V/m  Python={e_field:.2f}V/m")

# Gesamt-E-Feld
total_e = np.sqrt(total_e_squared)
excel_total_e = omen8.e_field_expected

print("\n" + "=" * 80)
print("GESAMT-E-FELD:")
print("=" * 80)
print(f"Excel:  {excel_total_e:.4f} V/m")
print(f"Python: {total_e:.4f} V/m")
print(f"Abweichung: {total_e - excel_total_e:.4f} V/m ({((total_e / excel_total_e - 1) * 100):.2f}%)")
