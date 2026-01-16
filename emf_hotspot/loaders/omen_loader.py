"""
OMEN XLS-Loader

Parst die OMEN-Standortdatenblatt-Excel-Datei und extrahiert Antennendaten.
"""

from pathlib import Path
from typing import Optional
import pandas as pd

from ..models import LV95Coordinate, Antenna, AntennaSystem, OMENLocation


# Zeilen-Indizes im Antenna-Sheet (0-basiert)
class AntennaSheetRows:
    STRAHL = 0  # Strahl A/B/C
    LAUFNUMMER = 1  # Laufnummer n (40)
    MAST_NR = 2  # Antennenmast (42)
    ANTENNA_NR = 3  # Nr. der Antenne (50)
    FREQUENZBAND = 4  # Frequenzband [MHz] (60)
    NETZBETREIBER = 5  # Netzbetreiber (70)
    ANTENNENTYP = 6  # Antennen-Typ (80)
    ADAPTIV = 7  # Adaptiver Betrieb (90)
    SUB_ARRAYS = 8  # Anzahl Sub-Arrays (100)
    KAA = 9  # Korrekturfaktor (101)
    X_OFFSET = 10  # X-Offset Mast (111)
    Y_OFFSET = 11  # Y-Offset Mast (112)
    Z_HOEHE = 12  # Z-Höhe Mast (113)
    ERP = 13  # ERP in Watt (120)
    # Zeile 14 (130) ist leer
    AZIMUT = 15  # Azimut (140)
    TILT = 16  # Tilt (150) - nur Referenz
    # Zeile 17-19 sind mechanisch/elektrisch einzeln
    TILT_FROM = 20  # Gesamter Neigungswinkel von (175)
    TILT_TO = 21  # Gesamter Neigungswinkel bis (180)


def load_omen_data(filepath: Path) -> AntennaSystem:
    """
    Lädt Antennendaten aus einer OMEN XLS-Datei.

    Args:
        filepath: Pfad zur XLS-Datei

    Returns:
        AntennaSystem mit allen Antennen
    """
    xls = pd.ExcelFile(filepath)

    # Global-Sheet für Basiskoordinaten
    df_global = pd.read_excel(xls, sheet_name="Global", header=None)
    base_position = _parse_global_coordinates(df_global)
    stdb_name = _get_cell_value(df_global, 1, 2, "")  # Zeile 1, Spalte C
    stdb_date = _get_cell_value(df_global, 0, 12, "")  # Zeile 0, Spalte M (StDb-Datum)
    address = _get_cell_value(df_global, 3, 2, "")  # Zeile 3, Spalte C

    # Antenna-Sheet für Antennendaten
    df_antenna = pd.read_excel(xls, sheet_name="Antenna", header=None)
    antennas = _parse_antennas(df_antenna, base_position)

    # OMEN-Sheets (O1-O20) für kritische Punkte
    omen_locations = _parse_omen_sheets(xls, base_position)

    return AntennaSystem(
        name=stdb_name,
        base_position=base_position,
        antennas=antennas,
        stdb_date=str(stdb_date),
        address=str(address),
        omen_locations=omen_locations,
    )


def _parse_global_coordinates(df: pd.DataFrame) -> LV95Coordinate:
    """
    Extrahiert LV95-Koordinaten aus Global-Sheet.

    Neu: Zeile 6 (Excel-Zeile 7), Spalten C/D/E (Index 2/3/4)
    """
    # Zeile 6 (Index 6), Spalten C/D/E enthalten E/N/H
    try:
        e = df.iloc[6, 2]  # Spalte C
        n = df.iloc[6, 3]  # Spalte D
        h = df.iloc[6, 4]  # Spalte E

        # Prüfe ob Werte gültig sind (nicht NaN)
        if pd.notna(e) and pd.notna(n) and pd.notna(h):
            return LV95Coordinate(e=float(e), n=float(n), h=float(h))
    except (ValueError, TypeError, IndexError):
        pass

    # Fallback: Versuche alte Methode (String-Parsing aus Spalte B)
    coord_str = None
    for idx in range(len(df)):
        cell_a = df.iloc[idx, 0]
        if isinstance(cell_a, str) and cell_a.lower() == "geo":
            coord_str = str(df.iloc[idx, 1])
            break

    if coord_str is None:
        coord_str = str(df.iloc[4, 1])

    return LV95Coordinate.from_string(coord_str)


def _parse_antennas(df: pd.DataFrame, base_position: LV95Coordinate) -> list[Antenna]:
    """Extrahiert alle Antennen aus dem Antenna-Sheet."""
    antennas = []

    # Spalten 2-10 enthalten die Antennendaten (Spalte 0 = Zeilennummer, Spalte 1 = 0)
    num_cols = len(df.columns)

    for col_idx in range(2, num_cols):
        # Prüfe ob diese Spalte gültige Daten enthält
        laufnummer = _get_cell_value(df, AntennaSheetRows.LAUFNUMMER, col_idx, None)
        if laufnummer is None or pd.isna(laufnummer):
            continue

        try:
            laufnummer = int(laufnummer)
        except (ValueError, TypeError):
            continue

        # ERP prüfen - wenn 0 oder leer, überspringen
        erp = _get_cell_value(df, AntennaSheetRows.ERP, col_idx, 0)
        if erp is None or pd.isna(erp) or float(erp) <= 0:
            continue

        # Extrahiere Antennendaten
        mast_nr = int(_get_cell_value(df, AntennaSheetRows.MAST_NR, col_idx, 1))
        freq_band = str(_get_cell_value(df, AntennaSheetRows.FREQUENZBAND, col_idx, ""))
        antenna_type = str(_get_cell_value(df, AntennaSheetRows.ANTENNENTYP, col_idx, ""))
        adaptiv = _get_cell_value(df, AntennaSheetRows.ADAPTIV, col_idx, "nein")
        is_adaptive = str(adaptiv).lower() in ("ja", "yes", "1", "true")

        # Sub-Arrays: Robust parsen (kann "-" oder leer sein)
        sub_arrays_raw = _get_cell_value(df, AntennaSheetRows.SUB_ARRAYS, col_idx, 1)
        try:
            sub_arrays = int(sub_arrays_raw)
        except (ValueError, TypeError):
            sub_arrays = 1  # Default

        # Position (Offsets relativ zur Basis)
        x_offset = float(_get_cell_value(df, AntennaSheetRows.X_OFFSET, col_idx, 0))
        y_offset = float(_get_cell_value(df, AntennaSheetRows.Y_OFFSET, col_idx, 0))
        z_height = float(_get_cell_value(df, AntennaSheetRows.Z_HOEHE, col_idx, 0))

        position = base_position.offset(x_offset, y_offset, z_height)

        # Azimut und Tilt
        azimut = float(_get_cell_value(df, AntennaSheetRows.AZIMUT, col_idx, 0))
        tilt = float(_get_cell_value(df, AntennaSheetRows.TILT, col_idx, 0))
        tilt_from = float(_get_cell_value(df, AntennaSheetRows.TILT_FROM, col_idx, tilt))
        tilt_to = float(_get_cell_value(df, AntennaSheetRows.TILT_TO, col_idx, tilt))

        antenna = Antenna(
            id=laufnummer,
            mast_nr=mast_nr,
            position=position,
            azimuth_deg=azimut,
            tilt_deg=tilt,
            tilt_from_deg=tilt_from,
            tilt_to_deg=tilt_to,
            erp_watts=float(erp),
            frequency_band=freq_band,
            antenna_type=antenna_type,
            is_adaptive=is_adaptive,
            sub_arrays=sub_arrays,
        )
        antennas.append(antenna)

    return antennas


def _get_cell_value(df: pd.DataFrame, row: int, col: int, default=None):
    """Sichere Zellenabfrage mit Default-Wert."""
    try:
        value = df.iloc[row, col]
        if pd.isna(value):
            return default
        return value
    except (IndexError, KeyError):
        return default


def _get_row_by_identifier(df: pd.DataFrame, row_id: int) -> Optional[int]:
    """
    Findet die DataFrame-Zeile (Index), die in Spalte A den Wert row_id hat.

    Args:
        df: DataFrame
        row_id: Zeilennummer in Spalte A (z.B. 111, 370)

    Returns:
        Index der Zeile (0-basiert) oder None
    """
    for idx in range(len(df)):
        cell_a = df.iloc[idx, 0]
        try:
            if int(cell_a) == row_id:
                return idx
        except (ValueError, TypeError):
            continue
    return None


def _parse_omen_sheets(xls: pd.ExcelFile, base_position: LV95Coordinate) -> list[OMENLocation]:
    """
    Extrahiert OMEN-Daten aus den O1-O20 Sheets.

    Zeilennr 111: X-Offset (Easting) relativ zu base_position
    Zeilennr 112: Y-Offset (Northing) relativ zu base_position
    Zeilennr 113: Z-Höhe
    Zeilennr 370: Gebäudedämpfung [dB]
    """
    omen_locations = []

    for sheet_name in xls.sheet_names:
        # Prüfe ob OMEN-Sheet (O1, O2, ..., O20)
        if not sheet_name.startswith("O") or len(sheet_name) > 3:
            continue

        try:
            omen_nr = int(sheet_name[1:])
        except ValueError:
            continue

        # Sheet laden
        df = pd.read_excel(xls, sheet_name=sheet_name, header=None)

        # Finde Zeilen nach Identifier
        # OMEN-Offsets stehen in Zeile 216 (nicht 111-113!)
        row_216 = _get_row_by_identifier(df, 216)  # OMEN X/Y/Z Offsets
        row_370 = _get_row_by_identifier(df, 370)  # Dämpfung

        if row_216 is None:
            continue

        # Offsets extrahieren aus Zeile 216
        # Spalte C (Index 2): X-Offset
        # Spalte D (Index 3): Y-Offset
        # Spalte E (Index 4): Z-Offset (Höhe über Basispunkt)
        x_offset = _get_cell_value(df, row_216, 2, None)
        y_offset = _get_cell_value(df, row_216, 3, None)
        z_offset = _get_cell_value(df, row_216, 4, None)

        if x_offset is None or y_offset is None or z_offset is None:
            continue

        # Absolute Position berechnen
        position = base_position.offset(
            float(x_offset),
            float(y_offset),
            float(z_offset),
        )

        # Dämpfung (optional)
        attenuation = 0.0
        if row_370 is not None:
            att_value = _get_cell_value(df, row_370, 2, 0.0)
            if att_value is not None and not pd.isna(att_value):
                attenuation = float(att_value)

        # E-Feld Referenzwert (Zeile 410, Spalte D)
        e_field_expected = None
        row_410 = _get_row_by_identifier(df, 410)
        if row_410 is not None:
            e_value = _get_cell_value(df, row_410, 3, None)  # Spalte D = Index 3
            if e_value is not None and not pd.isna(e_value):
                e_field_expected = float(e_value)

        omen_locations.append(OMENLocation(
            nr=omen_nr,
            position=position,
            building_attenuation_db=attenuation,
            e_field_expected=e_field_expected,
        ))

    return omen_locations
