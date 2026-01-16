"""
OMEN-Validierung mit Excel-Dämpfungswerten

Übernimmt H/V-Dämpfung direkt aus Excel (Zeile 320/330),
um Pattern-Interpolations-Fehler zu eliminieren und nur
Geometrie + Formel zu testen.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from emf_hotspot.loaders.omen_loader import load_omen_data
from emf_hotspot.physics.propagation import calculate_e_field_with_pattern

# Lade Antennensystem
antenna_system = load_omen_data(Path("input/OMEN R37 clean.xls"))

# Öffne Excel-Datei einmal
xls = pd.ExcelFile("input/OMEN R37 clean.xls")

# Liste der OMEN-Punkte (inkl. O1 = OKA)
omen_numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

print("=" * 80)
print("OMEN-Validierung mit Excel-Dämpfungswerten")
print("(Dämpfung direkt aus Excel, nur Geometrie + Formel testen)")
print("=" * 80)
print()

results = []

for omen_nr in omen_numbers:
    print(f"\n{'='*80}")
    print(f"OMEN {omen_nr}")
    print(f"{'='*80}")

    # Lade OMEN-Sheet aus XLS
    sheet_name = f"O{omen_nr}"
    if sheet_name not in xls.sheet_names:
        print(f"  WARNUNG: Sheet {sheet_name} nicht gefunden - überspringe")
        continue

    df_excel = pd.read_excel(xls, sheet_name=sheet_name, header=None)

    # Baue Index: row_id -> DataFrame-Index
    # Spalte A (Index 0) enthält Zeilennummern (250, 320, 330, 390, etc.)
    def get_row_by_id(row_id):
        """Findet DataFrame-Zeile mit gegebener ID in Spalte A"""
        for idx in range(len(df_excel)):
            try:
                cell_val = df_excel.iloc[idx, 0]
                if pd.notna(cell_val) and int(cell_val) == row_id:
                    return idx
            except (ValueError, TypeError):
                continue
        return None

    # OMEN-Position und Expected E-Field
    omen = [o for o in antenna_system.omen_locations if o.nr == omen_nr][0]
    excel_total_e = omen.e_field_expected

    print(f"Position: {omen.position.e:.2f} / {omen.position.n:.2f} / {omen.position.h:.2f}")
    print(f"Expected E-Field: {excel_total_e:.4f} V/m")
    print(f"Building Attenuation: {omen.building_attenuation_db:.2f} dB")
    print()

    # Berechne E-Feld pro Antenne MIT EXCEL-DÄMPFUNGSWERTEN
    e_squared_sum = 0.0

    for ant_idx, antenna in enumerate(antenna_system.antennas, start=1):
        col_idx = ant_idx + 1  # Spalte C = Index 2, D = 3, etc.

        # Excel-Werte aus Zeilen 250, 320, 330, 390
        row_250 = get_row_by_id(250)
        row_320 = get_row_by_id(320)
        row_330 = get_row_by_id(330)
        row_390 = get_row_by_id(390)

        excel_distance = float(df_excel.iloc[row_250, col_idx]) if row_250 is not None else None
        excel_h_atten = float(df_excel.iloc[row_320, col_idx]) if row_320 is not None else 0.0
        excel_v_atten = float(df_excel.iloc[row_330, col_idx]) if row_330 is not None else 0.0
        excel_e_contrib = float(df_excel.iloc[row_390, col_idx]) if row_390 is not None else None

        # Python-Berechnung MIT EXCEL-DÄMPFUNGEN
        e_field = calculate_e_field_with_pattern(
            erp_watts=antenna.erp_watts,
            distance_m=excel_distance,
            h_attenuation_db=excel_h_atten,
            v_attenuation_db=excel_v_atten,
            building_attenuation_db=omen.building_attenuation_db,
        )

        e_squared_sum += e_field ** 2

        deviation = e_field - excel_e_contrib if excel_e_contrib else 0
        deviation_pct = (deviation / excel_e_contrib * 100) if excel_e_contrib else 0

        print(f"  Ant {ant_idx} ({antenna.frequency_band:12s}): "
              f"Excel={excel_e_contrib:5.2f} V/m  "
              f"Python={e_field:5.2f} V/m  "
              f"Diff={deviation:+6.3f} ({deviation_pct:+6.2f}%)")

    # Gesamt-E-Feld
    python_total_e = np.sqrt(e_squared_sum)
    total_deviation = python_total_e - excel_total_e
    total_deviation_pct = (total_deviation / excel_total_e * 100)

    print()
    print(f"GESAMT: Excel={excel_total_e:.4f} V/m  "
          f"Python={python_total_e:.4f} V/m  "
          f"Diff={total_deviation:+.4f} ({total_deviation_pct:+.2f}%)")

    results.append({
        'omen_nr': f'O{omen_nr}',
        'excel_vm': excel_total_e,
        'python_vm': python_total_e,
        'deviation_vm': total_deviation,
        'deviation_pct': total_deviation_pct,
        'status': 'OK' if abs(total_deviation_pct) < 5 else 'DEVIATION'
    })

# Zusammenfassung
print("\n" + "=" * 80)
print("ZUSAMMENFASSUNG")
print("=" * 80)
print()
print(f"{'OMEN':<6} {'Excel [V/m]':>12} {'Python [V/m]':>12} {'Diff [V/m]':>12} {'Diff [%]':>10} {'Status':>10}")
print("-" * 80)
for r in results:
    print(f"{r['omen_nr']:<6} {r['excel_vm']:>12.4f} {r['python_vm']:>12.4f} "
          f"{r['deviation_vm']:>12.4f} {r['deviation_pct']:>10.2f} {r['status']:>10}")

ok_count = sum(1 for r in results if r['status'] == 'OK')
print()
print(f"Ergebnis: {ok_count}/{len(results)} OMEN-Punkte OK (<5% Abweichung)")
