"""
Helper-Funktionen für NeuOmen-Excel-Export mit Formatierung
"""

from typing import Optional
import xlrd
import xlwt


def add_sheet_from_existing(wb, source_wb: xlrd.Book, source_sheet_name: str, new_sheet_name: str, num_cols: int) -> Optional[int]:
    """
    Fügt ein neues Sheet hinzu basierend auf einem existierenden Sheet (mit Spaltenreduktion).

    Args:
        wb: xlwt Workbook (von xlutils.copy)
        source_wb: xlrd Workbook
        source_sheet_name: Name des Quell-Sheets
        new_sheet_name: Name des neuen Sheets
        num_cols: Anzahl Spalten (A, B + num_antennas)

    Returns:
        Index des neuen Sheets oder None bei Fehler
    """

    if source_sheet_name not in source_wb.sheet_names():
        return None

    source_sheet = source_wb.sheet_by_name(source_sheet_name)

    # Finde nächsten freien Sheet-Index
    next_idx = len(wb._Workbook__worksheets)

    # Erstelle neues Sheet
    target_sheet = wb.add_sheet(new_sheet_name, cell_overwrite_ok=True)

    # Kopiere Daten (nur bis num_cols Spalten)
    max_cols = 2 + num_cols  # A, B + Antennen-Spalten
    max_cols = min(max_cols, source_sheet.ncols)

    for row_idx in range(source_sheet.nrows):
        for col_idx in range(max_cols):
            cell = source_sheet.cell(row_idx, col_idx)

            try:
                # Kopiere Wert (Formatierung wird von xlutils.copy erhalten)
                target_sheet.write(row_idx, col_idx, cell.value)
            except Exception:
                pass

    return next_idx


def add_sheet_from_template(wb, template_sheet: xlrd.sheet.Sheet, new_sheet_name: str, num_cols: int) -> Optional[int]:
    """
    Fügt ein neues Sheet hinzu basierend auf einem Template-Sheet.

    Args:
        wb: xlwt Workbook
        template_sheet: xlrd Sheet (Template)
        new_sheet_name: Name des neuen Sheets
        num_cols: Anzahl Spalten

    Returns:
        Index des neuen Sheets
    """

    next_idx = len(wb._Workbook__worksheets)
    target_sheet = wb.add_sheet(new_sheet_name, cell_overwrite_ok=True)

    max_cols = 2 + num_cols
    max_cols = min(max_cols, template_sheet.ncols)

    for row_idx in range(template_sheet.nrows):
        for col_idx in range(max_cols):
            cell = template_sheet.cell(row_idx, col_idx)
            try:
                target_sheet.write(row_idx, col_idx, cell.value)
            except Exception:
                pass

    return next_idx


def fill_omen_sheet_inputs_only(
    target_sheet,
    neuomen_nr: int,
    hotspot_row,
    antenna_system,
) -> None:
    """
    Füllt NUR die Input-Felder im OMEN-Sheet (nicht berechnete Werte).

    Excel-Formeln bleiben erhalten und berechnen selbst.

    Input-Felder:
    - Zeile 1, Spalte B: Titel
    - Zeile 31, Spalte C: OMEN-Nummer
    - Zeile 32, Spalte C: Adresse
    - Zeile 33, Spalte C: Nutzung
    - Zeile 34, Spalten C, D, E: x, y, z Koordinaten

    NICHT überschreiben:
    - Zeile 57, Spalte C: E-Feldstärke (wird von Excel berechnet)
    - Alle anderen berechneten Felder

    Args:
        target_sheet: xlwt Worksheet
        neuomen_nr: Nummer des NeuOmen
        hotspot_row: DataFrame-Zeile mit Hotspot-Daten
        antenna_system: AntennaSystem
    """

    import pandas as pd

    # Titel (Zeile 0, Spalte B) - Excel Zeile 1
    target_sheet.write(0, 1, f"Berechnung der kritischen Feldstärke beim NO {neuomen_nr}")

    # OMEN Nummer (Zeile 30, Spalte C) - Excel Zeile 31
    target_sheet.write(30, 2, neuomen_nr)

    # Adresse (Zeile 31, Spalte C) - Excel Zeile 32
    address = hotspot_row.get("address", "")
    if pd.isna(address) or address == "":
        address = f"Gebäude ID: {hotspot_row.get('building_id', 'Unbekannt')}"
    target_sheet.write(31, 2, address)

    # Nutzung (Zeile 32, Spalte C) - Excel Zeile 33
    target_sheet.write(32, 2, "Arbeit")

    # Koordinaten (Zeile 33, Spalten C, D, E) - Excel Zeile 34
    x = hotspot_row.get("center_x", 0.0)
    y = hotspot_row.get("center_y", 0.0)
    z = hotspot_row.get("center_z", 0.0)

    target_sheet.write(33, 2, float(x))
    target_sheet.write(33, 3, float(y))
    target_sheet.write(33, 4, float(z))

    # NICHT überschreiben: E-Feldstärke (Zeile 56, Spalte C)
    # Diese wird von Excel-Formeln berechnet!


def create_combined_neuomen_workbook_simple(
    output_file,
    template_file,
    input_omen_file,
    df_hotspots,
    results,
    antenna_system,
    num_antennas,
) -> None:
    """
    Fallback-Methode ohne xlutils (ohne Formatierung).
    """

    import xlrd
    import xlwt

    wb = xlwt.Workbook()

    # Input-Datei öffnen
    input_rb = xlrd.open_workbook(str(input_omen_file), formatting_info=False)

    # Kopiere Global, Masten, Antenna
    sheets_to_copy = ["Global", "Masten", "Antenna"]
    for sheet_name in sheets_to_copy:
        if sheet_name in input_rb.sheet_names():
            source_sheet = input_rb.sheet_by_name(sheet_name)
            target_sheet = wb.add_sheet(sheet_name)

            # Kopiere alle Daten
            for row_idx in range(source_sheet.nrows):
                for col_idx in range(source_sheet.ncols):
                    cell = source_sheet.cell(row_idx, col_idx)
                    try:
                        target_sheet.write(row_idx, col_idx, cell.value)
                    except Exception:
                        pass

    # Template öffnen
    template_rb = xlrd.open_workbook(str(template_file), formatting_info=False)

    if "Omen" not in template_rb.sheet_names():
        wb.save(str(output_file))
        return

    template_omen = template_rb.sheet_by_name("Omen")

    # Für jeden Hotspot ein Sheet
    for idx, row in df_hotspots.iterrows():
        neuomen_nr = idx + 1
        sheet_name = f"NO {neuomen_nr}"

        target_sheet = wb.add_sheet(sheet_name, cell_overwrite_ok=True)

        # Kopiere Template
        max_cols = 2 + num_antennas
        max_cols = min(max_cols, template_omen.ncols)

        for row_idx in range(template_omen.nrows):
            for col_idx in range(max_cols):
                cell = template_omen.cell(row_idx, col_idx)
                try:
                    target_sheet.write(row_idx, col_idx, cell.value)
                except Exception:
                    pass

        # Fülle Input-Werte
        fill_omen_sheet_inputs_only(
            target_sheet=target_sheet,
            neuomen_nr=neuomen_nr,
            hotspot_row=row,
            antenna_system=antenna_system,
        )

    wb.save(str(output_file))
