"""
Excel-Export für NeuOmen-Berechnungsblätter

Erstellt für jeden Hotspot in hotspots_aggregated.csv ein OMEN-Berechnungsblatt
im Format des Standortdatenblatts (StDB).
"""

from pathlib import Path
from typing import List, Optional
import pandas as pd
from odf.table import TableRow, TableCell
from odf.text import P

# Optionale Excel-Module (xlrd + xlwt + xlutils für altes .xls Format mit Formatierung)
try:
    import xlrd
    import xlwt
    from xlutils.copy import copy as xl_copy
    EXCEL_SUPPORT = True
    XLUTILS_AVAILABLE = True
except ImportError:
    EXCEL_SUPPORT = False
    XLUTILS_AVAILABLE = False
    xlrd = None
    xlwt = None
    xl_copy = None

# Import Helper-Funktionen
try:
    from .omen_export_helpers import (
        add_sheet_from_existing,
        add_sheet_from_template,
        fill_omen_sheet_inputs_only,
        create_combined_neuomen_workbook_simple,
    )
except ImportError:
    # Fallback falls Helper-Modul fehlt
    add_sheet_from_existing = None
    add_sheet_from_template = None
    fill_omen_sheet_inputs_only = None
    create_combined_neuomen_workbook_simple = None


def set_cell_value(sheet, row_idx: int, col_idx: int, value):
    """
    Setzt den Wert einer Zelle in einem ODS-Sheet.

    Args:
        sheet: ODS Table-Objekt
        row_idx: Zeilenindex (0-basiert)
        col_idx: Spaltenindex (0-basiert)
        value: Wert (String, Float oder Int)
    """
    from odf.table import TableRow, TableCell
    from odf.text import P

    # Hole oder erstelle Zeile
    rows = sheet.getElementsByType(TableRow)

    # Stelle sicher, dass genug Zeilen vorhanden sind
    while len(rows) <= row_idx:
        sheet.addElement(TableRow())
        rows = sheet.getElementsByType(TableRow)

    row = rows[row_idx]

    # Hole Zellen in dieser Zeile
    cells = row.getElementsByType(TableCell)

    # Stelle sicher, dass genug Zellen vorhanden sind
    while len(cells) <= col_idx:
        row.addElement(TableCell())
        cells = row.getElementsByType(TableCell)

    cell = cells[col_idx]

    # WICHTIG: Lösche Formel, falls vorhanden (sonst bleibt Formel erhalten!)
    if cell.getAttribute('formula'):
        cell.removeAttribute('formula')

    # Lösche alten Text-Inhalt
    for p in cell.getElementsByType(P):
        cell.removeChild(p)

    # Setze neuen Wert
    if isinstance(value, (int, float)):
        # Numerischer Wert
        cell.setAttribute('valuetype', 'float')
        cell.setAttribute('value', str(value))
        p = P(text=str(value))
    else:
        # String-Wert
        cell.setAttribute('valuetype', 'string')
        p = P(text=str(value))

    cell.addElement(p)


def hide_row(sheet, row_idx: int):
    """
    Blendet eine Zeile in einem ODS-Sheet aus.

    Args:
        sheet: ODS Table-Objekt
        row_idx: Zeilenindex (0-basiert)
    """
    from odf.table import TableRow

    rows = sheet.getElementsByType(TableRow)
    if row_idx < len(rows):
        row = rows[row_idx]
        row.setAttribute('visibility', 'collapse')


def copy_sheets_via_xml(ods_file: Path, source_sheet_name: str, target_sheet_names: list):
    """
    Kopiert ein Sheet auf XML-Ebene (ODS ist ZIP mit content.xml).

    Dies ist der einzige zuverlässige Weg, Sheets mit Formeln/Formatierung zu kopieren,
    da odfpy keine clone()-Methode hat und deepcopy zu Rekursion führt.

    Args:
        ods_file: Pfad zur ODS-Datei
        source_sheet_name: Quell-Sheet (z.B. "O1")
        target_sheet_names: Liste der Ziel-Sheet-Namen (z.B. ["O14", "O15", "O16"])
    """
    import zipfile
    import tempfile
    import shutil
    import os
    from lxml import etree

    # ODS ist ein ZIP-Archiv
    temp_dir = tempfile.mkdtemp()

    try:
        # 1. Entpacke ODS
        with zipfile.ZipFile(ods_file, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        # 2. Lade content.xml
        content_xml_path = Path(temp_dir) / 'content.xml'
        tree = etree.parse(str(content_xml_path))
        root = tree.getroot()

        # Namespaces
        ns = {
            'office': 'urn:oasis:names:tc:opendocument:xmlns:office:1.0',
            'table': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
        }

        # 3. Finde Quell-Sheet (O1)
        source_table = None
        spreadsheet = root.find('.//office:spreadsheet', ns)

        for table in spreadsheet.findall('.//table:table', ns):
            name = table.get('{urn:oasis:names:tc:opendocument:xmlns:table:1.0}name')
            if name == source_sheet_name:
                source_table = table
                break

        if source_table is None:
            print(f"  FEHLER: Quell-Sheet {source_sheet_name} nicht gefunden")
            return False

        # 4. Für jedes Ziel-Sheet: Ersetze oder erstelle
        for target_name in target_sheet_names:
            # Suche ob Ziel-Sheet existiert
            target_table = None
            for table in spreadsheet.findall('.//table:table', ns):
                name = table.get('{urn:oasis:names:tc:opendocument:xmlns:table:1.0}name')
                if name == target_name:
                    target_table = table
                    break

            # Kopiere Quell-Sheet (deep copy im XML)
            new_table = etree.fromstring(etree.tostring(source_table))
            # Ändere Namen
            new_table.set('{urn:oasis:names:tc:opendocument:xmlns:table:1.0}name', target_name)

            if target_table is not None:
                # Ersetze existierendes Sheet
                parent = target_table.getparent()
                parent.replace(target_table, new_table)
            else:
                # Füge neues Sheet hinzu
                spreadsheet.append(new_table)

            print(f"    ✓ {source_sheet_name} → {target_name} kopiert")

        # 5. Speichere content.xml
        tree.write(str(content_xml_path), encoding='utf-8', xml_declaration=True)

        # 6. Packe ODS neu
        with zipfile.ZipFile(ods_file, 'w', zipfile.ZIP_DEFLATED) as zip_out:
            for root_dir, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = Path(root_dir) / file
                    arcname = file_path.relative_to(temp_dir)
                    zip_out.write(file_path, arcname)

        return True

    finally:
        # Aufräumen
        shutil.rmtree(temp_dir, ignore_errors=True)


def mark_formulas_dirty(sheet):
    """
    Markiert alle Formeln in einem Sheet als "dirty", damit sie neu berechnet werden.

    Entfernt die gecachten Werte (office:value, office:string-value etc.),
    damit LibreOffice die Formeln beim Öffnen neu berechnet.

    Args:
        sheet: ODS Table-Objekt
    """
    from odf.table import TableRow, TableCell

    rows = sheet.getElementsByType(TableRow)
    for row in rows:
        cells = row.getElementsByType(TableCell)
        for cell in cells:
            # Prüfe ob Zelle eine Formel hat
            formula = cell.getAttribute('formula')
            if formula:
                # Entferne gecachte Werte, damit Formel neu berechnet wird
                try:
                    # office:value für Zahlen
                    cell.removeAttribute('value')
                except:
                    pass
                try:
                    # office:string-value für Text
                    cell.removeAttribute('string-value')
                except:
                    pass
                try:
                    # office:date-value für Datum
                    cell.removeAttribute('date-value')
                except:
                    pass
                try:
                    # office:boolean-value für Boolean
                    cell.removeAttribute('boolean-value')
                except:
                    pass


def create_neuomen_workbooks(
    output_dir: Path,
    template_file: Path,
    input_omen_file: Path,
    hotspots_aggregated_csv: Path,
    results: Optional[List] = None,
    antenna_system = None,
) -> None:
    """
    Erstellt eine einzige Excel-Datei mit mehreren OMEN-Sheets für alle Hotspots.

    Args:
        output_dir: Ausgabeverzeichnis
        template_file: Template-Datei (OMEN R37 leer.xls)
        input_omen_file: Input-OMEN-Datei mit Global, Masten, Antenna Sheets
        hotspots_aggregated_csv: CSV mit aggregierten Hotspots
        results: HotspotResult-Objekte (optional, für detaillierte Daten)
        antenna_system: AntennaSystem-Objekt (für Antennen-Details)
    """

    if not EXCEL_SUPPORT:
        print(f"  INFO: NeuOmen-Excel-Export übersprungen (xlrd/xlwt nicht installiert)")
        print(f"        → Installation: pip install xlrd xlwt")
        return

    if not template_file.exists():
        print(f"  WARNUNG: Template nicht gefunden: {template_file}")
        return

    if not input_omen_file.exists():
        print(f"  WARNUNG: Input-OMEN nicht gefunden: {input_omen_file}")
        return

    if not hotspots_aggregated_csv.exists():
        print(f"  WARNUNG: hotspots_aggregated.csv nicht gefunden")
        return

    # Lade aggregierte Hotspots
    try:
        df_hotspots = pd.read_csv(hotspots_aggregated_csv)
    except Exception as e:
        print(f"  WARNUNG: Fehler beim Laden von hotspots_aggregated.csv: {e}")
        return

    if df_hotspots.empty:
        print(f"  INFO: Keine Hotspots zum Exportieren")
        return

    print(f"  NeuOmen-Export: {len(df_hotspots)} Hotspots")

    # Anzahl Antennen bestimmen
    num_antennas = len(antenna_system.antennas) if antenna_system else 9

    try:
        # Erstelle EINE Excel-Datei mit mehreren Sheets
        output_file = output_dir / "NeuOmen.xls"

        create_combined_neuomen_workbook(
            output_file=output_file,
            template_file=template_file,
            input_omen_file=input_omen_file,
            df_hotspots=df_hotspots,
            results=results,
            antenna_system=antenna_system,
            num_antennas=num_antennas,
        )

        print(f"  → NeuOmen-Datei: {output_file}")

    except Exception as e:
        print(f"  FEHLER bei NeuOmen-Export: {e}")
        import traceback
        traceback.print_exc()


def create_combined_neuomen_workbook(
    output_file: Path,
    template_file: Path,
    input_omen_file: Path,
    df_hotspots: pd.DataFrame,
    results: Optional[List],
    antenna_system,
    num_antennas: int,
) -> None:
    """
    Erstellt NeuOmen.ods als Kopie der Input-Datei mit überschriebenen Werten.

    Verwendet odfpy, um gezielt Werte in ODS-Zellen zu überschreiben,
    ohne Formeln oder Formatierung zu zerstören.

    Args:
        output_file: Zieldatei (NeuOmen.ods)
        template_file: Template-Datei (nicht verwendet)
        input_omen_file: Input-OMEN mit Global/Masten/Antenna
        df_hotspots: DataFrame mit allen Hotspots
        results: HotspotResult-Objekte
        antenna_system: AntennaSystem
        num_antennas: Anzahl Antennen
    """

    import shutil
    from odf import opendocument
    from odf.table import Table, TableRow, TableCell
    from odf.text import P

    # Ändere Dateiendung zu .ods
    output_file = output_file.with_suffix('.ods')

    # Prüfe ob Input-Datei ODS ist, sonst suche ODS-Version
    if not input_omen_file.suffix == '.ods':
        # Versuche ODS-Version zu finden
        ods_file = input_omen_file.with_suffix('.ods')
        if ods_file.exists():
            input_omen_file = ods_file
        else:
            print(f"  WARNUNG: Benötige ODS-Datei, gefunden: {input_omen_file.suffix}")
            print(f"  Bitte konvertieren Sie {input_omen_file.name} zu ODS")
            return

    # 1. Kopiere Input-Datei
    shutil.copy(str(input_omen_file), str(output_file))
    print(f"  → Kopie der Input-Datei erstellt: {output_file.name}")

    # 2. Finde höchste OMEN-Nummer aus omen_zuordnung.csv (für start_nr)
    max_omen_nr = 0
    omen_zuordnung_file = output_file.parent / "omen_zuordnung.csv"
    if omen_zuordnung_file.exists():
        try:
            df_omen = pd.read_csv(omen_zuordnung_file)
            for omen_nr_str in df_omen['omen_nr']:
                if isinstance(omen_nr_str, str) and omen_nr_str.startswith('O'):
                    num_str = omen_nr_str[1:]
                    if num_str.isdigit():
                        max_omen_nr = max(max_omen_nr, int(num_str))
        except Exception:
            pass

    start_nr = max_omen_nr + 1

    # 3. WICHTIG: Kopiere O1-Sheet auf O14, O15, O16 auf XML-Ebene
    # (muss VOR odfpy-Öffnung passieren, da odfpy kein clone() kann)
    import os
    target_sheet_names = [f"O{start_nr + i}" for i in range(len(df_hotspots))]
    if len(target_sheet_names) > 0:
        print(f"  → Kopiere O1-Template auf {', '.join(target_sheet_names)}...")
        if not copy_sheets_via_xml(output_file, "O1", target_sheet_names):
            print(f"  FEHLER: Sheet-Kopie fehlgeschlagen")
            return

    # 4. Öffne ODS und schreibe Werte
    try:
        doc = opendocument.load(str(output_file))
    except Exception as e:
        print(f"  FEHLER beim Laden der ODS: {e}")
        return

    # Basis-Position der Antenne
    base_pos = antenna_system.base_position if antenna_system else None

    # 5. Überschreibe Werte in den kopierten OMEN-Sheets
    for idx, row in df_hotspots.iterrows():
        neuomen_nr = start_nr + idx

        # Verwende die NÄCHSTEN freien Sheets nach der höchsten OMEN-Nr
        # z.B. wenn max_omen_nr = 13, dann O14, O15, O16, ...
        sheet_nr = neuomen_nr  # 14, 15, 16, ...

        if sheet_nr > 20:
            print(f"  WARNUNG: Sheet O{sheet_nr} überschreitet O20-Limit, überspringe Hotspot {neuomen_nr}")
            break

        old_sheet_name = f"O{sheet_nr}"  # O14, O15, O16, ...
        new_sheet_name = f"N{neuomen_nr}"  # N14, N15, N16, ...

        # Finde Ziel-Sheet
        sheet = None
        for table in doc.spreadsheet.getElementsByType(Table):
            if table.getAttribute('name') == old_sheet_name:
                sheet = table
                break

        if sheet is None:
            print(f"  WARNUNG: Sheet {old_sheet_name} nicht gefunden")
            continue

        # Ändere Sheet-Namen
        sheet.setAttribute('name', new_sheet_name)

        # Adresse
        address = row.get("address", "")
        if pd.isna(address) or address == "":
            address = f"Gebäude {row.get('building_id', 'Unbekannt')}"

        # Koordinaten RELATIV zur Antennenbasis
        x_abs = row.get("center_x", 0.0)
        y_abs = row.get("center_y", 0.0)
        z_abs = row.get("center_z", 0.0)

        if base_pos:
            x_rel = x_abs - base_pos.e
            y_rel = y_abs - base_pos.n
            z_rel = z_abs - base_pos.h
        else:
            x_rel = x_abs
            y_rel = y_abs
            z_rel = z_abs

        # Finde zugehöriges HotspotResult für Winkel und Dämpfungen
        # WICHTIG: Wir brauchen den PUNKT mit MAXIMALER E-Feldstärke (nicht den ersten!)
        # center_x/y/z sind bereits die Koordinaten des max_point
        building_id = row.get("building_id", "")
        hotspot_result = None
        if results:
            # Finde den result-Punkt, der zu den center-Koordinaten passt
            x_abs = row.get("center_x", 0.0)
            y_abs = row.get("center_y", 0.0)
            z_abs = row.get("center_z", 0.0)

            # Suche result mit gleichen Koordinaten (mit Toleranz)
            tolerance = 0.01
            for result in results:
                if result.building_id == building_id:
                    if (abs(result.x - x_abs) < tolerance and
                        abs(result.y - y_abs) < tolerance and
                        abs(result.z - z_abs) < tolerance):
                        hotspot_result = result
                        break

        # Überschreibe Zellen (Excel-Zeilen 31-34 = ODS-Zeilen 30-33)
        # Zeile 31, Spalte C (Index 2): OMEN-Nummer
        set_cell_value(sheet, 30, 2, str(neuomen_nr))

        # WICHTIG: Markiere B1 explizit als dirty, da sie auf C31 referenziert
        # B1 = Zeile 0, Spalte 1
        rows = sheet.getElementsByType(TableRow)
        if len(rows) > 0:
            cells = rows[0].getElementsByType(TableCell)
            if len(cells) > 1:
                b1_cell = cells[1]
                # Entferne gecachten Wert aus B1
                try:
                    b1_cell.removeAttribute('value')
                except:
                    pass
                try:
                    b1_cell.removeAttribute('string-value')
                except:
                    pass

        # Zeile 32, Spalte C: Adresse
        set_cell_value(sheet, 31, 2, address)

        # Zeile 33, Spalte C: Nutzung
        set_cell_value(sheet, 32, 2, "Arbeit")

        # Zeile 34, Spalten C, D, E: x, y, z
        set_cell_value(sheet, 33, 2, x_rel)
        set_cell_value(sheet, 33, 3, y_rel)
        set_cell_value(sheet, 33, 4, z_rel)

        # Winkel und Dämpfungen aus HotspotResult (falls vorhanden)
        if hotspot_result and hotspot_result.contributions:
            # Finde die Antenne mit der höchsten Feldstärke
            max_contribution = max(hotspot_result.contributions,
                                   key=lambda c: c.e_field_vm)

            # Berechne Azimut aus Koordinaten (relativ zur Antennenbasis)
            import math
            azimuth_deg = math.degrees(math.atan2(x_rel, y_rel))  # 0°=Nord

            # Berechne Elevation aus Koordinaten
            horiz_dist = math.sqrt(x_rel**2 + y_rel**2)
            elevation_deg = math.degrees(math.atan2(z_rel, horiz_dist))

            # DEBUG: Zeige eingetragene Werte
            print(f"      NO {neuomen_nr}: E_Python={hotspot_result.e_field_vm:.4f}, "
                  f"Az={azimuth_deg:.1f}°, El={elevation_deg:.1f}° (Winkel zum Punkt)")

            # Überschreibe FORMELN mit berechneten WERTEN
            # Zeile 48: Original aus StDB (ausblenden, nicht ändern)
            # Zeile 49 (Index 48): Überschreibe Formel mit Azimut-Wert (global zum OMEN-Punkt)
            set_cell_value(sheet, 48, 2, azimuth_deg)

            # Zeile 50: Original aus StDB (ausblenden, nicht ändern)
            # Zeile 51 (Index 50): Überschreibe Formel mit Elevation-Wert (global zum OMEN-Punkt)
            set_cell_value(sheet, 50, 2, elevation_deg)

            # WICHTIG: Schreibe für ALLE 9 Antennen die individuellen Werte!
            # Zeile 37 (Index 36): Horizontaler Abstand pro Antenne
            # Zeile 38 (Index 37): Höhenunterschied pro Antenne
            # Zeile 40 (Index 39): Azimut des OMEN relativ zu jeder Antenne
            # Zeile 51 (Index 50): Kritischer Tilt pro Antenne
            # Zeile 55 (Index 54): H-Dämpfung pro Antenne
            # Zeile 57 (Index 56): V-Dämpfung pro Antenne
            # Spalte C-K = Antennen 1-9
            if hotspot_result.contributions and antenna_system:
                # Berechne absolute Position des OMEN-Punkts
                # (x_rel, y_rel, z_rel sind relativ zur Basis)
                # LV95Coordinate hat .e (Easting/X), .n (Northing/Y), .h (Höhe/Z)
                omen_abs_x = antenna_system.base_position.e + x_rel
                omen_abs_y = antenna_system.base_position.n + y_rel
                omen_abs_z = antenna_system.base_position.h + z_rel

                for contrib in hotspot_result.contributions:
                    antenna_id = contrib.antenna_id
                    col_idx = 2 + (antenna_id - 1)  # Antenne 1→C(2), 2→D(3), ..., 9→K(10)

                    # Hole die Antenne aus dem System
                    antenna = None
                    for ant in antenna_system.antennas:
                        if ant.id == antenna_id:
                            antenna = ant
                            break

                    if antenna:
                        # Berechne relativen Vektor von Antenne zu OMEN
                        dx = omen_abs_x - antenna.position.e
                        dy = omen_abs_y - antenna.position.n
                        dz = omen_abs_z - antenna.position.h

                        # Horizontaler Abstand (Zeile 37)
                        horiz_dist_ant = math.sqrt(dx**2 + dy**2)
                        set_cell_value(sheet, 36, col_idx, horiz_dist_ant)

                        # Höhenunterschied (Zeile 38)
                        set_cell_value(sheet, 37, col_idx, dz)

                        # Azimut relativ zur Antenne (Zeile 40)
                        # Azimut der Antenne ist bereits in antenna.azimuth_deg gespeichert
                        # Relativer Azimut = Winkel von Antenne zu OMEN minus Antennen-Azimut
                        azimuth_to_omen = math.degrees(math.atan2(dx, dy))  # 0°=Nord
                        rel_azimuth = azimuth_to_omen - antenna.azimuth_deg
                        # Normalisiere auf [-180, 180]
                        while rel_azimuth > 180:
                            rel_azimuth -= 360
                        while rel_azimuth < -180:
                            rel_azimuth += 360
                        set_cell_value(sheet, 39, col_idx, rel_azimuth)

                    # Schreibe kritischen Tilt (Zeile 51)
                    set_cell_value(sheet, 50, col_idx, contrib.critical_tilt_deg)
                    # Schreibe H-Dämpfung (Zeile 55)
                    set_cell_value(sheet, 54, col_idx, contrib.h_attenuation_db)
                    # Schreibe V-Dämpfung (Zeile 57)
                    set_cell_value(sheet, 56, col_idx, contrib.v_attenuation_db)

                print(f"        → {len(hotspot_result.contributions)} Antennen-Werte geschrieben (Abstand, Azimut, Tilt, H-dB, V-dB)")
        else:
            print(f"      NO {neuomen_nr}: WARNUNG - Keine Contribution-Daten gefunden!")

        # Zeilen ausblenden: 41-45, 47, 48, 50, 54, 56
        # (Original-Werte aus StDB bleiben erhalten, aber ausgeblendet)
        # Wir schreiben die berechneten Werte in Zeilen 55 und 57!
        # Von unten nach oben (damit Indizes stimmen)
        rows_to_hide = [55, 53, 49, 47, 46, 44, 43, 42, 41, 40]  # 0-basiert: 56, 54, 50, 48, 47, 45, 44, 43, 42, 41
        for row_idx in rows_to_hide:
            hide_row(sheet, row_idx)

        # Markiere alle Formeln als dirty, damit sie neu berechnet werden
        mark_formulas_dirty(sheet)

        print(f"    {old_sheet_name} → {new_sheet_name} (NO {neuomen_nr})")

    # 4. Speichern
    try:
        doc.save(str(output_file))
        print(f"  → NeuOmen-Datei gespeichert: {output_file.name}")
        print(f"     (Start-Nr: NO {start_nr}, Koordinaten RELATIV zur Antennenbasis)")
    except Exception as e:
        print(f"  FEHLER beim Speichern: {e}")
        return

    # 5. Aktualisiere hotspots_aggregated.csv → hotspots_short.csv mit omen_nr
    try:
        # Lese die CSV (aus dem output_dir)
        hotspots_agg_file = output_file.parent / "hotspots_aggregated.csv"
        df_hotspots_update = pd.read_csv(hotspots_agg_file)

        # Füge omen_nr für die neuen NeuOmen hinzu
        for idx, row in df_hotspots.iterrows():
            neuomen_nr = start_nr + idx
            building_id = row.get("building_id", "")

            # Finde Zeile in df_hotspots_update
            mask = df_hotspots_update['building_id'] == building_id
            if mask.any():
                df_hotspots_update.loc[mask, 'omen_nr'] = f"O{neuomen_nr}"

        # Schreibe als hotspots_short.csv
        hotspots_short_csv = output_file.parent / "hotspots_short.csv"
        df_hotspots_update.to_csv(hotspots_short_csv, index=False)
        print(f"  → hotspots_short.csv erstellt mit NeuOmen-Nummern")

    except Exception as e:
        print(f"  WARNUNG: Fehler bei hotspots_short.csv: {e}")

    # 6. Hinweis zur manuellen Neuberechnung
    print(f"")
    print(f"  ⚠️  WICHTIG: Formeln müssen manuell neu berechnet werden!")
    print(f"     1. Öffnen Sie {output_file.name} in LibreOffice Calc")
    print(f"     2. Drücken Sie Strg+Shift+F9 (alle Formeln neu berechnen)")
    print(f"     3. Speichern Sie die Datei")

    return

    # ALTE METHODE (funktioniert nicht mit Formeln):
    if not XLUTILS_AVAILABLE:
        print(f"  INFO: Formatierung wird nicht erhalten (xlutils fehlt)")
        print(f"        → Installation: pip install xlutils")
        # Fallback auf alte Methode
        create_combined_neuomen_workbook_simple(
            output_file, template_file, input_omen_file, df_hotspots,
            results, antenna_system, num_antennas
        )
        return

    # 1. Input-Datei mit Formatierung öffnen und kopieren
    input_rb = xlrd.open_workbook(str(input_omen_file), formatting_info=True)
    wb = xl_copy(input_rb)

    # 2. Finde OMEN-Sheets (O1, O2, O3, etc.)
    input_omen_sheets = [name for name in input_rb.sheet_names()
                         if name.startswith('O') and len(name) <= 3 and name[1:].replace('b', '').isdigit()]

    # Sortiere numerisch (O1, O2, O3, ..., O10, O11, ..., O20)
    def omen_sort_key(name):
        # Extrahiere Nummer (O1 -> 1, O1b -> 1, O10 -> 10)
        num_str = name[1:].replace('b', '')
        return int(num_str) if num_str.isdigit() else 999

    input_omen_sheets.sort(key=omen_sort_key)

    if not input_omen_sheets:
        print(f"  WARNUNG: Keine OMEN-Sheets in Input gefunden")
        wb.save(str(output_file))
        return

    print(f"  → Überschreibe {min(len(df_hotspots), len(input_omen_sheets))} OMEN-Sheets mit NeuOmen-Daten")

    # 3. Für jeden Hotspot: Überschreibe entsprechendes OMEN-Sheet
    for idx, row in df_hotspots.iterrows():
        neuomen_nr = idx + 1  # 1-basiert

        if idx >= len(input_omen_sheets):
            print(f"  WARNUNG: Nicht genug OMEN-Sheets für Hotspot {neuomen_nr}")
            break

        # Verwende O1, O2, O3, etc.
        omen_sheet_name = input_omen_sheets[idx]

        # Finde Sheet-Index
        sheet_idx = None
        for i, sheet in enumerate(wb._Workbook__worksheets):
            if sheet.name == omen_sheet_name:
                sheet_idx = i
                break

        if sheet_idx is None:
            print(f"  WARNUNG: Sheet {omen_sheet_name} nicht gefunden")
            continue

        # Überschreibe NUR Input-Werte (Formatierung und Formeln bleiben erhalten)
        target_sheet = wb.get_sheet(sheet_idx)
        fill_omen_sheet_inputs_only(
            target_sheet=target_sheet,
            neuomen_nr=neuomen_nr,
            hotspot_row=row,
            antenna_system=antenna_system,
        )

        print(f"    {omen_sheet_name} → NO {neuomen_nr} Daten")

    # 4. Speichern
    wb.save(str(output_file))

