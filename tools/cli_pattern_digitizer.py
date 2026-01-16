#!/usr/bin/env python3
"""
CLI Antennendiagramm-Digitalisierer (ohne GUI)

Workflow:
1. Konvertiert PDF zu PNGs
2. Öffnet Bilder in Standard-Bildbetrachter (oder zeigt Pfad)
3. User gibt Koordinaten manuell ein (aus Bildbetrachter abgelesen)
4. Digitalisiert automatisch alle Diagramme

Usage:
    python cli_pattern_digitizer.py input/Stdb.pdf -o patterns.ods --start-page 32
"""

import sys
from pathlib import Path
import numpy as np
import cv2
import pandas as pd
from typing import List, Tuple, Optional
import tempfile
import subprocess
import json
import datetime


class DiagramCalibration:
    """Gespeicherte Kalibrierung für ein Diagramm"""
    def __init__(self, page_nr: int, diagram_nr: int):
        self.page_nr = page_nr
        self.diagram_nr = diagram_nr
        self.center: Optional[Tuple[int, int]] = None
        self.radius: Optional[int] = None
        self.curve_points: List[Tuple[int, int]] = []  # User-geklickte Punkte AUF der Kurve

        # Basis-Metadaten
        self.antenna_type: str = ""
        self.freq_band: str = ""
        self.h_or_v: str = ""

        # Erweiterte Metadaten aus OCR (4 Kopfzeilen von oben)
        self.stdb_id: str = ""
        self.msi_filename: str = ""
        self.frequency_range: str = ""
        self.created_by: str = ""

        # PDF-Quelle
        self.pdf_path: str = ""
        self.pdf_filename: str = ""

    def to_dict(self):
        return {
            'page_nr': self.page_nr,
            'diagram_nr': self.diagram_nr,
            'center': list(self.center) if self.center else None,
            'radius': self.radius,
            'curve_points': [list(p) for p in self.curve_points],
            'antenna_type': self.antenna_type,
            'freq_band': self.freq_band,
            'h_or_v': self.h_or_v,
            'stdb_id': self.stdb_id,
            'msi_filename': self.msi_filename,
            'frequency_range': self.frequency_range,
            'created_by': self.created_by,
            'pdf_path': self.pdf_path,
            'pdf_filename': self.pdf_filename,
        }

    @classmethod
    def from_dict(cls, data):
        cal = cls(data['page_nr'], data['diagram_nr'])
        cal.center = tuple(data['center']) if data['center'] else None
        cal.radius = data['radius']
        cal.curve_points = [tuple(p) for p in data.get('curve_points', [])]
        cal.antenna_type = data['antenna_type']
        cal.freq_band = data['freq_band']
        cal.h_or_v = data['h_or_v']
        cal.stdb_id = data.get('stdb_id', '')
        cal.msi_filename = data.get('msi_filename', '')
        cal.frequency_range = data.get('frequency_range', '')
        cal.created_by = data.get('created_by', '')
        cal.pdf_path = data.get('pdf_path', '')
        cal.pdf_filename = data.get('pdf_filename', '')
        return cal


def pdf_to_images(pdf_file: Path, output_dir: Path, dpi: int = 300) -> List[Path]:
    """Konvertiert PDF zu PNG"""
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Konvertiere PDF zu Bildern (DPI={dpi})...")
    cmd = ['pdftoppm', '-png', '-r', str(dpi), str(pdf_file), str(output_dir / 'page')]
    subprocess.run(cmd, check=True, capture_output=True)

    pages = sorted(output_dir.glob('page-*.png'))
    print(f"  → {len(pages)} Bilder erstellt in: {output_dir}")

    return pages


def open_image_viewer(image_path: Path):
    """Öffnet Bild in GIMP"""
    try:
        # GIMP starten
        subprocess.Popen(['gimp', str(image_path)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)
    except Exception:
        print(f"  (Konnte GIMP nicht automatisch öffnen)")
        print(f"  Öffne manuell: gimp {image_path}")


def get_coordinates_visual(
    page_nr: int,
    diagram_nr: int,
    image_path: Path
) -> Tuple[Optional[Tuple[int, int]], Optional[int], List[Tuple[int, int]]]:
    """
    Interaktive Koordinaten-Auswahl mit matplotlib ginput().

    User klickt:
    1. Mittelpunkt
    2. Randpunkt (äußerer Kreis)
    3-5. Kurve (2-3 Punkte AUF der schwarzen Kurve)

    Returns:
        (center, radius, curve_points) oder (None, None, [])
    """
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    from PIL import Image

    while True:  # Retry-Loop
        try:
            img = Image.open(image_path)
            img_array = np.array(img)

            fig, ax = plt.subplots(figsize=(16, 10))
            ax.imshow(img_array, extent=[0, img_array.shape[1], img_array.shape[0], 0])
            ax.set_xlim(0, img_array.shape[1])
            ax.set_ylim(img_array.shape[0], 0)
            ax.set_title(
                f"Seite {page_nr}, Diagramm {diagram_nr}\n"
                f"WICHTIG: Nach Zoom mit Home-Button (🏠) zurücksetzen BEVOR du klickst!\n"
                f"Klicke 5 Punkte: 1=Mitte, 2=Rand, 3-5=Kurve | Mittlere Maustaste wenn <5 Punkte genügen",
                fontsize=14, fontweight='bold'
            )
            ax.axis('on')  # Zeige Achsen für Koordinaten-Check

            print(f"\n{'─'*60}")
            print(f"SEITE {page_nr}, DIAGRAMM {diagram_nr}")
            print(f"{'─'*60}")
            print("Matplotlib-Fenster öffnet sich...")
            print()
            print("⚠️  WICHTIG:")
            print("  - Du kannst mit den Zoom-Tools (🔍) heranzoomen")
            print("  - ABER: Drücke Home (🏠) um Zoom zurückzusetzen VOR dem Klicken!")
            print("  - Sonst sind die Koordinaten falsch!")
            print()
            print("Klicke 5 Punkte:")
            print("  1. Mittelpunkt des Diagramms")
            print("  2. Punkt auf dem äußeren Kreis")
            print("  3-5. Punkte AUF der schwarzen Kurve")
            print()
            print("  - Mittlere Maustaste oder 'n' = Fertig (wenn <5 Punkte)")
            print("  - Rechtsklick = Letzten Punkt löschen")
            print("  - Fenster schließen = Überspringen")
            print()

            # Sammle Punkte (max 5)
            # timeout=0 = unbegrenzt, mouse_add=1 (linke Maustaste), mouse_pop=3 (rechte), mouse_stop=2 (mittlere)
            points = plt.ginput(n=5, timeout=0, show_clicks=True, mouse_add=1, mouse_pop=3, mouse_stop=2)

            if len(points) == 0:
                print("Übersprungen (Fenster geschlossen)")
                plt.close()
                return None, None, []

            if len(points) < 2:
                print(f"❌ Nur {len(points)} Punkt(e) - mindestens 2 erforderlich!")
                plt.close()
                continue

            # Parse Punkte
            center = (int(points[0][0]), int(points[0][1]))
            outer = (int(points[1][0]), int(points[1][1]))
            curve_points = [(int(p[0]), int(p[1])) for p in points[2:]]

            radius = int(np.sqrt((outer[0] - center[0])**2 + (outer[1] - center[1])**2))

            # Visualisiere Auswahl
            ax.clear()
            ax.imshow(img)
            ax.set_title(f"Auswahl überprüfen", fontsize=14, fontweight='bold')
            ax.axis('off')

            # Zeichne Mittelpunkt
            ax.plot(center[0], center[1], 'ro', markersize=12, label='Mittelpunkt', zorder=10)

            # Zeichne Randpunkt
            ax.plot(outer[0], outer[1], 'bs', markersize=12, label='Randpunkt', zorder=10)

            # Zeichne Kreis
            circle = Circle(center, radius, fill=False, color='yellow', linewidth=2, label='Erkannter Kreis')
            ax.add_patch(circle)

            # Zeichne Kurvenpunkte
            for i, (px, py) in enumerate(curve_points):
                label = 'Kurvenpunkte' if i == 0 else ''
                ax.plot(px, py, 'g^', markersize=12, label=label, zorder=10)

            ax.legend(loc='upper right', fontsize=11)
            plt.draw()
            plt.pause(0.1)

            # Zeige Zusammenfassung
            print(f"\n✓ {len(points)} Punkte erfasst:")
            print(f"  Mittelpunkt: {center}")
            print(f"  Randpunkt: {outer}")
            print(f"  Radius: {radius} px")
            print(f"  Kurvenpunkte: {len(curve_points)}")

            if len(curve_points) < 2:
                print(f"  ⚠️  Nur {len(curve_points)} Kurvenpunkte - empfohlen sind 2-3")

            # Frage Bestätigung
            confirm = input("\nKorrekt? [j/n/skip]: ").strip().lower()
            plt.close()

            if confirm in ['skip', 's', 'q']:
                return None, None, []

            if confirm == 'j':
                return center, radius, curve_points

            # 'n' → Wiederholen
            print("Wiederhole Auswahl...\n")
            continue

        except Exception as e:
            print(f"❌ Fehler: {e}")
            plt.close()
            retry = input("Erneut versuchen? [j/n]: ").strip().lower()
            if retry != 'j':
                return None, None, []
            continue


def get_user_coordinates_old(
    page_nr: int,
    diagram_nr: int,
    image_path: Path,
    open_gimp: bool = True
) -> Tuple[Optional[Tuple[int, int]], Optional[int], List[Tuple[int, int]]]:
    """
    ALTE METHODE: Fragt User nach Koordinaten für ein Diagramm (CLI).

    Args:
        open_gimp: Wenn False, GIMP nicht neu öffnen (für 2. Diagramm auf gleicher Seite)

    Returns:
        (center, radius) oder (None, None) wenn übersprungen
    """
    print(f"\n{'─'*60}")
    print(f"SEITE {page_nr}, DIAGRAMM {diagram_nr}")
    print(f"{'─'*60}")

    if open_gimp:
        print(f"Bild: {image_path}")
        print("\nÖffne GIMP...")
        open_image_viewer(image_path)
        print("In GIMP: Koordinaten mit Maus ablesen (unten links in Statusleiste)")
        print()

    print("Koordinaten für dieses Diagramm:")
    print("  1. Mittelpunkt des Diagramms (x, y)")
    print("  2. Einen Punkt auf dem äußeren Kreis (x, y)")
    print("  3-5. [NEU] 2-3 Punkte AUF der Kurve (für Kurven-Tracking)")
    print()

    # Frage Koordinaten ab (mit Retry)
    while True:
        try:
            center_input = input("Mittelpunkt (x,y) oder 'skip' zum Überspringen: ").strip()

            if center_input.lower() in ['skip', 's', 'q']:
                return None, None, []

            # Parse robust: "1234,5678" oder "1234, 5678" oder "1234 5678"
            # Erlaube auch "." als Trenner (häufiger Fehler)
            center_str = center_input.replace('.', ',').replace(' ', '').replace(',', ' ')
            coords = center_str.split()
            if len(coords) != 2:
                print(f"  ❌ Fehler: Erwarte 2 Koordinaten (x,y), bekam: {center_input}")
                print(f"  → Beispiel: '1234,2579' oder '1234 2579'")
                continue
            cx, cy = int(coords[0]), int(coords[1])
            print(f"  → Mittelpunkt: ({cx}, {cy})")
            break  # Erfolg

        except ValueError as e:
            print(f"  ❌ Fehler: {e}")
            print(f"  → Bitte erneut eingeben")
            continue

    # Frage Randpunkt (mit Retry)
    while True:
        try:
            outer_input = input("Randpunkt (x,y): ").strip()
            outer_str = outer_input.replace('.', ',').replace(' ', '').replace(',', ' ')
            coords_outer = outer_str.split()
            if len(coords_outer) != 2:
                print(f"  ❌ Fehler: Erwarte 2 Koordinaten (x,y), bekam: {outer_input}")
                print(f"  → Beispiel: '1390,2579' oder '1390 2579'")
                continue
            ox, oy = int(coords_outer[0]), int(coords_outer[1])
            print(f"  → Randpunkt: ({ox}, {oy})")

            # Berechne Radius
            radius = int(np.sqrt((ox - cx)**2 + (oy - cy)**2))
            print(f"  → Radius: {radius} px")
            break  # Erfolg

        except ValueError as e:
            print(f"  ❌ Fehler: {e}")
            print(f"  → Bitte erneut eingeben")
            continue

    # NEU: Frage nach Kurven-Punkten (für Option B: Curve Tracking)
    print()
    print("Kurven-Punkte (für bessere Digitalisierung):")
    print("  Klicke 2-3 Punkte DIREKT AUF die schwarze Kurve")
    print("  (z.B. bei 0°, 90°, 180° - wichtig für Kurven-Erkennung)")
    print("  Drücke ENTER ohne Eingabe wenn fertig")
    print()

    curve_points = []
    for i in range(1, 4):  # Max 3 Punkte
        try:
            curve_input = input(f"Kurvenpunkt {i} (x,y) [ENTER=fertig]: ").strip()

            if not curve_input:  # Leer = fertig
                break

            curve_str = curve_input.replace('.', ',').replace(' ', '').replace(',', ' ')
            coords_curve = curve_str.split()
            if len(coords_curve) != 2:
                print(f"  ❌ Überspringe ungültige Eingabe: {curve_input}")
                continue

            px, py = int(coords_curve[0]), int(coords_curve[1])
            curve_points.append((px, py))
            print(f"  → Kurvenpunkt {i}: ({px}, {py})")

        except (ValueError, KeyboardInterrupt):
            print(f"  ❌ Überspringe ungültige Eingabe")
            continue

    if len(curve_points) < 2:
        print(f"  ⚠️  Nur {len(curve_points)} Kurvenpunkte - empfohlen sind 2-3")
        print(f"  Digitalisierung wird weniger genau sein!")

    return (cx, cy), radius, curve_points


def extract_metadata_from_ocr(image_path: Path) -> dict:
    """
    Erweiterte OCR-Extraktion von Metadaten aus StDB-Seiten.

    Returns:
        dict mit allen extrahierten Feldern
    """
    try:
        import pytesseract
        import re

        img = cv2.imread(str(image_path))
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # OCR auf gesamte Seite
        text = pytesseract.image_to_string(gray)

        # Debug: Zeige OCR-Text (optional)
        # print(f"OCR-Text:\n{text[:500]}\n")

        # Initialisiere Ergebnis
        result = {
            'stdb_id': '',
            'msi_filename': '',
            'frequency_range': '',
            'created_by': '',
            'location': '',
            'revision': '',
            'antenna_type': '',
            'freq_band': '',
            'h_or_v': ''
        }

        # 1. StDB-ID (z.B. "1SC0709")
        stdb_match = re.search(r'\b(\d[A-Z]{2}\d{4})\b', text)
        if stdb_match:
            result['stdb_id'] = stdb_match.group(1)

        # 2. MSI-Filename (z.B. "HybridAIR3268.070809.ADI01.msi")
        msi_match = re.search(r'(Hybrid[A-Z0-9]+\.\d+\.[A-Z0-9]+\.msi)', text, re.IGNORECASE)
        if msi_match:
            result['msi_filename'] = msi_match.group(1)

        # 3. Frequency Range (z.B. "FREQUENCY 738 791 921")
        freq_range_match = re.search(r'FREQUENCY\s+([\d\s]+)', text, re.IGNORECASE)
        if freq_range_match:
            result['frequency_range'] = freq_range_match.group(1).strip()

        # 4. Created By (z.B. "created by: taamuer4, date: 2022.03.14")
        created_match = re.search(r'created by:\s*([^,]+),\s*date:\s*([\d.]+)', text, re.IGNORECASE)
        if created_match:
            result['created_by'] = f"{created_match.group(1)}, {created_match.group(2)}"

        # 5. Location (z.B. "für ZAFE")
        location_match = re.search(r'für\s+([A-Z][A-Za-z0-9_-]+),', text)
        if location_match:
            result['location'] = location_match.group(1)

        # 6. Revision (z.B. "Revision: 1.8")
        revision_match = re.search(r'Revision:\s*([\d.]+)', text, re.IGNORECASE)
        if revision_match:
            result['revision'] = revision_match.group(1)

        # 7. Antenna Type (z.B. "AIR3268")
        antenna_match = re.search(r'(AIR|SC)\d{4}', text, re.IGNORECASE)
        if antenna_match:
            result['antenna_type'] = antenna_match.group(0).upper()

        # 8. Frequency Band (aus "FREQUENCY 738 791 921" oder Filename)
        if result['frequency_range']:
            # Parse "738 791 921" → "738-921" (erstes bis letztes)
            freq_numbers = re.findall(r'\d+', result['frequency_range'])
            if len(freq_numbers) >= 2:
                result['freq_band'] = f"{freq_numbers[0]}-{freq_numbers[-1]}"
            elif len(freq_numbers) == 1:
                result['freq_band'] = freq_numbers[0]

        # Fallback: Aus MSI-Filename (z.B. "070809")
        if not result['freq_band'] and result['msi_filename']:
            freq_band_match = re.search(r'\.(\d{6})\.', result['msi_filename'])
            if freq_band_match:
                result['freq_band'] = freq_band_match.group(1)

        # 9. H/V (aus "(horizontal)" oder "(vertical)")
        # Dies wird später pro Diagramm spezifisch erkannt
        if '(horizontal)' in text.lower():
            result['h_or_v'] = 'h'
        elif '(vertical)' in text.lower():
            result['h_or_v'] = 'v'

        return result

    except ImportError:
        # pytesseract nicht verfügbar
        return {
            'stdb_id': '', 'msi_filename': '', 'frequency_range': '',
            'created_by': '', 'location': '', 'revision': '',
            'antenna_type': '', 'freq_band': '', 'h_or_v': ''
        }
    except Exception as e:
        print(f"  OCR-Fehler: {e}")
        return {
            'stdb_id': '', 'msi_filename': '', 'frequency_range': '',
            'created_by': '', 'location': '', 'revision': '',
            'antenna_type': '', 'freq_band': '', 'h_or_v': ''
        }


def extract_hv_from_diagram_area(image_path: Path, cy: int) -> str:
    """
    Erkennt H/V aus dem Bereich um ein spezifisches Diagramm.

    Args:
        image_path: Pfad zum Bild
        cy: Y-Koordinate des Diagramm-Zentrums

    Returns:
        'h' oder 'v' oder ''
    """
    try:
        import pytesseract
        import re

        img = cv2.imread(str(image_path))
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # OCR nur um das Diagramm herum (±200px vertikal)
        y1 = max(0, cy - 200)
        y2 = min(gray.shape[0], cy + 200)
        diagram_area = gray[y1:y2, :]

        text = pytesseract.image_to_string(diagram_area)

        if 'horizontal' in text.lower():
            return 'h'
        elif 'vertical' in text.lower():
            return 'v'

        return ''

    except:
        return ''


def extract_metadata_from_ocr_old(image_path: Path) -> dict:
    """
    Alte einfache OCR-Funktion (Fallback).

    Returns:
        dict mit 'antenna_type', 'freq_band', oder leere Strings
    """
    try:
        import pytesseract

        img = cv2.imread(str(image_path))
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # OCR auf oberen Teil (Titel)
        h = gray.shape[0]
        header = gray[:h//5, :]

        text = pytesseract.image_to_string(header)

        # Einfache Pattern-Erkennung
        antenna_type = ""
        freq_band = ""

        # Suche nach Antennentyp (z.B. "AIR3268", "SC3636")
        import re
        antenna_match = re.search(r'(AIR|SC)\d{4}', text, re.IGNORECASE)
        if antenna_match:
            antenna_type = antenna_match.group(0).upper()

        # Suche nach Frequenz (z.B. "2600", "738-921")
        freq_match = re.search(r'(\d{3,4}(?:-\d{3,4})?)', text)
        if freq_match:
            freq_band = freq_match.group(0)

        return {'antenna_type': antenna_type, 'freq_band': freq_band}

    except ImportError:
        return {'antenna_type': '', 'freq_band': ''}
    except Exception:
        return {'antenna_type': '', 'freq_band': ''}


def find_diagram_start_page(pages: List[Path]) -> int:
    """
    Findet automatisch die erste Seite mit Antennendiagrammen per OCR.

    Sucht nach: "Antenna Diagram", "radiation pattern", "Pattern", usw.

    Returns:
        Seitennummer (1-basiert) oder 1 als Fallback
    """
    try:
        import pytesseract
        import re

        print("\nAuto-Detect: Suche erste Diagramm-Seite...")

        for idx, page_file in enumerate(pages, start=1):
            # Nur erste 50 Seiten durchsuchen (Performance)
            if idx > 50:
                break

            try:
                img = cv2.imread(str(page_file))
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

                # OCR
                text = pytesseract.image_to_string(gray).lower()

                # Suche nach typischen Begriffen
                if any(keyword in text for keyword in [
                    'antenna diagram',
                    'radiation pattern',
                    'azimuth pattern',
                    'elevation pattern',
                    'horizontal pattern',
                    'vertical pattern',
                    'antenna pattern',
                ]):
                    print(f"  → Diagramme gefunden ab Seite {idx}")
                    return idx

            except Exception:
                continue

        print(f"  → Keine Diagramme erkannt, starte bei Seite 1")
        return 1

    except ImportError:
        print("  → pytesseract nicht verfügbar, starte bei Seite 1")
        return 1


def run_calibration_cli(
    pdf_file: Path,
    start_page: Optional[int],
    temp_dir: Path
) -> List[DiagramCalibration]:
    """Führt CLI-basierte Kalibrierung durch"""

    pages = pdf_to_images(pdf_file, temp_dir)

    # Auto-detect start page wenn nicht angegeben
    if start_page is None:
        start_page = find_diagram_start_page(pages)

    calibrations = []
    last_antenna_type = ""
    last_freq_band = ""

    print(f"\n{'='*60}")
    print("KALIBRIERUNG")
    print(f"{'='*60}")
    print(f"Starte bei Seite {start_page}")
    print("Pro Seite gibt es typischerweise 2 Diagramme (H und V)")
    print()

    # Schleife über Seiten
    current_page = start_page

    while current_page <= len(pages):
        page_file = pages[current_page - 1]

        print(f"\n{'='*60}")
        print(f"SEITE {current_page}")
        print(f"{'='*60}")
        print(f"Bild: {page_file}")
        print()

        # Frage Anzahl Diagramme (oder skip)
        num_diagrams_str = input(f"Wie viele Diagramme auf Seite {current_page}? [2/skip/fertig]: ").strip().lower()

        if num_diagrams_str in ['skip', 's', 'n', 'nein']:
            current_page += 1
            continue

        if num_diagrams_str in ['fertig', 'f', 'done', 'd']:
            break

        num_diagrams = int(num_diagrams_str) if num_diagrams_str and num_diagrams_str.isdigit() else 2

        # OCR-Versuch für Metadaten (erweitert)
        print("\nOCR-Extraktion läuft...")
        ocr_data = extract_metadata_from_ocr(page_file)

        if ocr_data['antenna_type']:
            print(f"  OCR: Antennentyp={ocr_data['antenna_type']}, Freq={ocr_data['freq_band']}")
            print(f"  OCR: StDB-ID={ocr_data['stdb_id']}, Location={ocr_data['location']}")

        # Kalibriere jedes Diagramm (VISUELL mit matplotlib)
        for diagram_nr in range(1, num_diagrams + 1):
            center, radius, curve_points = get_coordinates_visual(current_page, diagram_nr, page_file)

            if center is None:
                print("Übersprungen")
                continue

            # Diagramm-spezifische H/V-Erkennung
            hv_ocr = extract_hv_from_diagram_area(page_file, center[1]) if center else ''

            # Metadaten mit intelligenten Defaults
            print(f"\nMetadaten für Seite {current_page}, Diagramm {diagram_nr}:")

            # Antenna Type
            default_ant_type = ocr_data['antenna_type'] or last_antenna_type or "AIR3268"
            ant_input = input(f"  Antennentyp [{default_ant_type}]: ").strip()
            antenna_type = ant_input if ant_input else default_ant_type

            # Frequency Band
            default_freq = ocr_data['freq_band'] or last_freq_band or ""
            freq_input = input(f"  Frequenzband [{default_freq}]: ").strip()
            freq_band = freq_input if freq_input else default_freq

            # H oder V (mit OCR-Unterstützung)
            if hv_ocr:
                default_hv = hv_ocr
            elif diagram_nr == 2 and num_diagrams == 2:
                # 2. Diagramm ist oft das andere (H→V oder V→H)
                prev_hv = calibrations[-1].h_or_v if calibrations else 'h'
                default_hv = 'v' if prev_hv == 'h' else 'h'
            else:
                default_hv = ocr_data.get('h_or_v', 'h') or 'h'

            hv_input = input(f"  H oder V [{default_hv}]: ").strip().lower()
            h_or_v = hv_input if hv_input else default_hv

            # Speichere für nächstes Diagramm
            last_antenna_type = antenna_type
            last_freq_band = freq_band

            # Speichere Kalibrierung (erweitert)
            cal = DiagramCalibration(current_page, diagram_nr)
            cal.center = center
            cal.radius = radius
            cal.curve_points = curve_points

            # Basis-Metadaten
            cal.antenna_type = antenna_type
            cal.freq_band = freq_band
            cal.h_or_v = h_or_v

            # Erweiterte OCR-Metadaten (nur 4 Kopfzeilen von oben)
            cal.stdb_id = ocr_data.get('stdb_id', '')
            cal.msi_filename = ocr_data.get('msi_filename', '')
            cal.frequency_range = ocr_data.get('frequency_range', '')
            cal.created_by = ocr_data.get('created_by', '')

            # PDF-Quelle
            cal.pdf_path = str(pdf_file.resolve())
            cal.pdf_filename = pdf_file.name

            calibrations.append(cal)
            print(f"✓ Kalibrierung gespeichert ({len(curve_points)} Kurvenpunkte)")

        current_page += 1

    return calibrations


def is_near_grid_circle(radius: float, outer_radius: int, tolerance: int = 5) -> bool:
    """
    Prüft ob Radius nahe an einem Grid-Kreis liegt.

    Grid-Kreise bei: 3dB, 10dB, 20dB
    Skalierung: 0dB am Rand, 30dB am Mittelpunkt
    """
    # Berechne Grid-Radien
    grid_db_values = [3, 10, 20]
    grid_radii = [outer_radius * (1 - db/30) for db in grid_db_values]

    # Prüfe Nähe zu einem Grid-Kreis
    for grid_r in grid_radii:
        if abs(radius - grid_r) < tolerance:
            return True

    return False


def is_near_sector_line(angle_deg: float, tolerance: float = 2.0) -> bool:
    """
    Prüft ob Winkel nahe an einer 30°-Sektorlinie liegt.

    Sektorlinien bei: 0°, 30°, 60°, ..., 330°
    """
    sector_angles = np.arange(0, 360, 30)

    for sector_angle in sector_angles:
        # Minimaler Abstand (berücksichtigt 360°=0° wrap)
        diff = abs(angle_deg - sector_angle)
        diff = min(diff, 360 - diff)

        if diff < tolerance:
            return True

    return False


def remove_grid_lines(
    image_gray: np.ndarray,
    center: Tuple[int, int],
    radius: int
) -> np.ndarray:
    """
    Entfernt Grid-Linien aus Polardiagramm (Option C).

    Strategie:
    1. Aggressives Thresholding - nur sehr schwarze Pixel (<100)
    2. Maskiere bekannte Grid-Kreis-Positionen (3dB, 10dB, 20dB)
    3. Maskiere 30°-Radiallinien
    4. Morphologie - entferne dünne Linien

    Returns:
        Binärbild mit Grid-Linien entfernt
    """
    cx, cy = center

    # Stufe 1: Nur sehr schwarze Pixel (Kurve ist schwarz, Grid oft grau)
    _, very_black = cv2.threshold(image_gray, 100, 255, cv2.THRESH_BINARY_INV)

    # Stufe 2: Erstelle Maske für Grid-Kreise
    mask = np.ones_like(very_black)
    grid_db_values = [3, 10, 20]

    for db_value in grid_db_values:
        # Radius des Grid-Kreises
        grid_r = int(radius * (1 - db_value / 30))

        # Zeichne Ring (Grid-Kreis ± 3px) als 0 (maskiert)
        cv2.circle(mask, center, grid_r, 0, thickness=6)

    # Stufe 3: Maskiere 30°-Radiallinien
    for sector_deg in range(0, 360, 30):
        angle_rad = np.deg2rad(sector_deg)

        # Zeichne Linie vom Zentrum nach außen (Antennendiagramm: 0°=Ost)
        x_end = int(cx + (radius + 50) * np.cos(angle_rad))
        y_end = int(cy - (radius + 50) * np.sin(angle_rad))

        cv2.line(mask, center, (x_end, y_end), 0, thickness=6)

    # Wende Maske an
    filtered = cv2.bitwise_and(very_black, mask)

    # Stufe 4: Morphologie - entferne dünne Reste
    kernel = np.ones((3, 3), np.uint8)
    # Erosion entfernt dünne Linien, Dilation stellt dicke Linien wieder her
    eroded = cv2.erode(filtered, kernel, iterations=1)
    cleaned = cv2.dilate(eroded, kernel, iterations=1)

    return cleaned


def find_thick_curve_radius(
    binary: np.ndarray,
    cx: int,
    cy: int,
    angle_rad: float,
    r_outer: int
) -> int:
    """
    Findet Radius der dicken Kurve (nicht dünne Grid-Linien).

    Unterscheidet:
    - Dicke Linie (Kurve): ≥3 von 5 aufeinanderfolgenden Pixeln schwarz
    - Dünne Linie (Grid): <3 schwarze Pixel

    Returns:
        Radius der Kurve, oder 50 wenn nichts gefunden
    """
    for r in range(50, r_outer + 100):
        x = int(cx + r * np.sin(angle_rad))
        y = int(cy - r * np.cos(angle_rad))

        if not (0 <= x < binary.shape[1] and 0 <= y < binary.shape[0]):
            continue

        if binary[y, x] > 0:  # Schwarzer Pixel gefunden
            # Prüfe ob das eine dicke Linie ist (Kurve) oder dünne (Grid)
            # Teste ±2 Pixel entlang des Radius
            thick_count = 0

            for dr in [-2, -1, 0, 1, 2]:
                r_test = r + dr
                if r_test < 0:
                    continue

                x_test = int(cx + r_test * np.sin(angle_rad))
                y_test = int(cy - r_test * np.cos(angle_rad))

                if 0 <= x_test < binary.shape[1] and 0 <= y_test < binary.shape[0]:
                    if binary[y_test, x_test] > 0:
                        thick_count += 1

            # Kurve = mindestens 3 von 5 Pixeln schwarz
            if thick_count >= 3:
                return r

    return 50  # Fallback


def snap_to_black(
    image_gray: np.ndarray,
    point: Tuple[int, int],
    search_radius: int = 15,
    black_threshold: int = 100
) -> Tuple[int, int]:
    """
    Findet den NÄCHSTEN schwarzen Pixel zum geklickten Punkt (radiale Suche).

    Args:
        image_gray: Graustufenbild
        point: Geklickter Punkt (x, y)
        search_radius: Suchradius in Pixeln
        black_threshold: Intensität-Schwelle für "schwarz"

    Returns:
        (x, y) des nächstgelegenen schwarzen Pixels
    """
    px, py = point

    # Radiale Suche: In alle Richtungen vom geklickten Punkt
    best_dist = float('inf')
    best_pos = (px, py)

    # Suche in 360° Richtungen, in jedem Radius von 1 bis search_radius
    for angle_deg in range(0, 360, 5):  # Alle 5° (72 Richtungen)
        angle_rad = np.deg2rad(angle_deg)

        for dist in range(1, search_radius + 1):
            # Position in dieser Richtung/Distanz
            x = int(px + dist * np.cos(angle_rad))
            y = int(py + dist * np.sin(angle_rad))

            # Prüfe Bounds
            if not (0 <= x < image_gray.shape[1] and 0 <= y < image_gray.shape[0]):
                break

            # Ist das ein schwarzer Pixel?
            if image_gray[y, x] < black_threshold:
                # Erster schwarzer Pixel in dieser Richtung gefunden
                if dist < best_dist:
                    best_dist = dist
                    best_pos = (x, y)
                break  # Nicht weiter in dieser Richtung suchen

    return best_pos


def learn_curve_properties(
    image_gray: np.ndarray,
    curve_points: List[Tuple[int, int]]
) -> dict:
    """
    Lernt Eigenschaften der Kurve aus User-geklickten Punkten (Option B).

    WICHTIG:Snappt jeden Punkt zuerst auf den nächsten schwarzen Pixel!

    Returns:
        dict mit 'intensity_mean', 'intensity_std', 'thickness'
    """
    if len(curve_points) == 0:
        # Fallback: Standard-Annahmen
        return {
            'intensity_mean': 50,  # Sehr schwarz
            'intensity_std': 30,
            'thickness': 3
        }

    intensities = []
    thicknesses = []
    snapped_points = []

    for px, py in curve_points:
        # SNAP TO BLACK: Finde dunkelsten Pixel in Nähe
        black_x, black_y = snap_to_black(image_gray, (px, py), search_radius=15)
        snapped_points.append((black_x, black_y))

        # Lese Intensität am schwarzen Pixel
        if 0 <= black_y < image_gray.shape[0] and 0 <= black_x < image_gray.shape[1]:
            intensity = image_gray[black_y, black_x]
            intensities.append(intensity)

            # Schätze Dicke: Wie viele schwarze Pixel in 5x5 Nachbarschaft?
            y1, y2 = max(0, black_y-2), min(image_gray.shape[0], black_y+3)
            x1, x2 = max(0, black_x-2), min(image_gray.shape[1], black_x+3)
            patch = image_gray[y1:y2, x1:x2]
            black_count = np.sum(patch < 128)
            thicknesses.append(black_count)

    if len(intensities) == 0:
        return {
            'intensity_mean': 50,
            'intensity_std': 30,
            'thickness': 3
        }

    return {
        'intensity_mean': np.mean(intensities),
        'intensity_std': np.std(intensities) + 20,  # +20 für Toleranz
        'thickness': np.mean(thicknesses)
    }


def track_curve_radius(
    image_gray: np.ndarray,
    cx: int,
    cy: int,
    angle_rad: float,
    r_outer: int,
    last_radius: Optional[int],
    curve_props: dict
) -> int:
    """
    Tracked Kurve basierend auf gelernten Eigenschaften (Option B).

    Args:
        image_gray: Graustufenbild
        cx, cy: Zentrum
        angle_rad: Aktueller Winkel (Radiant, 0°=Ost, 90°=Nord)
        r_outer: Äußerer Radius
        last_radius: Radius beim letzten Winkel (für Kontinuität)
        curve_props: Gelernte Kurven-Eigenschaften

    Returns:
        Radius der Kurve
    """
    target_intensity = curve_props['intensity_mean']
    intensity_tolerance = curve_props['intensity_std']

    # Suchbereich: ±50px von letztem Radius (wenn vorhanden)
    if last_radius is not None:
        r_min = max(50, last_radius - 50)
        r_max = min(r_outer + 100, last_radius + 50)
    else:
        r_min = 50
        r_max = r_outer + 100

    best_r = None
    best_score = -1

    for r in range(r_min, r_max):
        # Antennendiagramm-Konvention: 0°=Ost (rechts), 90°=Nord (oben)
        x = int(cx + r * np.cos(angle_rad))
        y = int(cy - r * np.sin(angle_rad))

        if not (0 <= x < image_gray.shape[1] and 0 <= y < image_gray.shape[0]):
            continue

        intensity = image_gray[y, x]

        # Score: Wie gut passt Intensität zur Kurve?
        intensity_diff = abs(intensity - target_intensity)

        if intensity_diff < intensity_tolerance:
            # Bonus: Näher an letztem Radius = besser (Kontinuität)
            continuity_bonus = 0
            if last_radius is not None:
                continuity_bonus = 50 - abs(r - last_radius)

            score = (intensity_tolerance - intensity_diff) + continuity_bonus

            if score > best_score:
                best_score = score
                best_r = r

    # Fallback: Nutze letzten Radius oder 50
    if best_r is None:
        best_r = last_radius if last_radius is not None else 50

    return best_r


def digitize_diagram(
    image_gray: np.ndarray,
    center: Tuple[int, int],
    radius: int,
    curve_points: List[Tuple[int, int]] = None
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Digitalisiert Polardiagramm mit bidirektionalem Kurven-Tracking.

    Args:
        image_gray: Graustufenbild
        center: Zentrum (x, y)
        radius: Äußerer Radius
        curve_points: User-geklickte Punkte AUF der Kurve (für Tracking)

    Workflow:
    1. Lerne Kurven-Eigenschaften aus geklickten Punkten
    2. Finde besten Startpunkt (einer der geklickten Punkte)
    3. Tracke VORWÄRTS von Start → 360°
    4. Tracke RÜCKWÄRTS von Start → 0°
    5. Kombiniere beide Richtungen
    6. Median-Filter für Glättung
    """

    cx, cy = center
    r_outer = radius

    if curve_points is None:
        curve_points = []

    # Lerne Kurven-Eigenschaften
    print(f"    Kurven-Tracking ({len(curve_points)} Referenzpunkte)...")
    curve_props = learn_curve_properties(image_gray, curve_points)
    print(f"    Kurvenfarbe: {curve_props['intensity_mean']:.0f} ± {curve_props['intensity_std']:.0f}")

    # Finde Startpunkt: Wähle einen der geklickten Punkte
    # Snap to black wurde schon gemacht, berechne nur den Winkel
    if len(curve_points) > 0:
        # Wähle ersten Kurvenpunkt als Start
        start_px, start_py = curve_points[0]
        # Snap to black für exakte Position
        start_px, start_py = snap_to_black(image_gray, (start_px, start_py), search_radius=15)

        # Berechne Winkel dieses Punkts
        dx = start_px - cx
        dy = cy - start_py  # cy - start_py wegen y-Achse nach unten
        start_angle_deg = np.rad2deg(np.arctan2(dy, dx)) % 360

        # Berechne Radius am Startpunkt
        start_radius = int(np.sqrt(dx**2 + dy**2))

        print(f"    Startpunkt: {start_angle_deg:.1f}°, r={start_radius}px")
    else:
        # Fallback: Starte bei 0°
        start_angle_deg = 0
        start_radius = None

    # Erstelle Winkel-Array (0.5° Schritte)
    angles_all = np.arange(0, 360, 0.5)
    curve_radii = np.zeros(len(angles_all))

    # Digitalisiere im UHRZEIGERSINN (wie Antennendiagramme konventionell gezeichnet werden)
    # 0° → 350° → 340° → ... → 10° → 0° (kompletter Kreis)
    print(f"    Tracking im Uhrzeigersinn ab {start_angle_deg:.1f}°...")
    last_r = start_radius

    for i in range(len(angles_all)):
        # Gehe im Uhrzeigersinn: subtrahiere Winkel
        # i=0: start_angle, i=1: start_angle-0.5, i=2: start_angle-1.0, ...
        current_angle = (start_angle_deg - i * 0.5) % 360
        angle_rad = np.deg2rad(current_angle)

        r = track_curve_radius(image_gray, cx, cy, angle_rad, r_outer, last_r, curve_props)

        # Finde Index für diesen Winkel im Output-Array
        out_idx = int(current_angle / 0.5) % len(angles_all)
        curve_radii[out_idx] = r
        last_r = r

    # Glättung: Median-Filter um Ausreißer zu entfernen
    from scipy.ndimage import median_filter
    curve_radii_smooth = median_filter(curve_radii, size=11)

    # Konvertiere zu Dämpfung [dB]
    # WICHTIG: r_outer ist die 0dB-Referenz (äußerer Rand), NICHT max(curve_radii)!
    attenuation_db = 30.0 * (1.0 - curve_radii_smooth / r_outer)

    return angles_all, attenuation_db


def digitize_all(
    pdf_file: Path,
    calibrations: List[DiagramCalibration],
    stdb_id: str,
    temp_dir: Path
) -> pd.DataFrame:
    """Digitalisiert alle kalibrierten Diagramme"""

    print(f"\n{'='*60}")
    print("DIGITALISIERUNG")
    print(f"{'='*60}")

    pages = pdf_to_images(pdf_file, temp_dir)

    all_data = []

    for cal in calibrations:
        print(f"\nDigitalisiere: Seite {cal.page_nr}, Diagramm {cal.diagram_nr}")
        print(f"  {cal.antenna_type} {cal.freq_band} {cal.h_or_v.upper()}")

        # Lade Bild
        page_file = pages[cal.page_nr - 1]
        img = cv2.imread(str(page_file))
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Digitalisiere mit Kurven-Tracking
        angles, attenuation = digitize_diagram(
            gray,
            cal.center,
            cal.radius,
            curve_points=cal.curve_points
        )

        # Zu DataFrame (mit erweiterten Metadaten)
        for phi, db in zip(angles, attenuation):
            all_data.append({
                # Basis
                'StDb-ID': cal.stdb_id or stdb_id,  # Priorisiere OCR-StDB-ID
                'Antennen-Typ': cal.antenna_type,
                'Frequenz-band': cal.freq_band,
                'vertical or horizontal': cal.h_or_v,
                'Phi': phi,
                'dB': db,

                # 4 Kopfzeilen (von oben)
                'MSI-Filename': cal.msi_filename,
                'Frequency-Range': cal.frequency_range,
                'Created-By': cal.created_by,

                # PDF-Quelle
                'PDF-Path': cal.pdf_path,
                'PDF-Filename': cal.pdf_filename,
            })

        print(f"  → {len(angles)} Punkte, Dämpfung {attenuation.min():.1f}-{attenuation.max():.1f} dB")

    df = pd.DataFrame(all_data)
    return df


def update_source_registry(
    stdb_id: str,
    pdf_path: Path,
    calibrations: List[DiagramCalibration],
    registry_file: Path
):
    """Aktualisiert die Quellen-Tabelle"""

    # Sammle Metadaten
    antenna_types = list(set(c.antenna_type for c in calibrations))
    freq_bands = list(set(c.freq_band for c in calibrations))

    new_entry = {
        'StDb-ID': stdb_id,
        'PDF-Pfad': str(pdf_path.resolve()),
        'Digitalisierungs-Datum': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'Anzahl-Diagramme': len(calibrations),
        'Antennentypen': '; '.join(sorted(antenna_types)),
        'Frequenzbänder': '; '.join(sorted(freq_bands)),
    }

    # Lade existierende Registry
    if registry_file.exists():
        df_registry = pd.read_csv(registry_file, dtype=str)  # Alle Spalten als string

        # Prüfe ob StDb-ID bereits existiert
        existing_idx = df_registry[df_registry['StDb-ID'] == stdb_id].index

        if len(existing_idx) > 0:
            # Aktualisiere existierenden Eintrag (komplette Zeile ersetzen)
            for key, value in new_entry.items():
                df_registry.at[existing_idx[0], key] = str(value)
            print(f"\n✓ Quellen-Registry aktualisiert: {stdb_id}")
        else:
            # Füge hinzu
            df_registry = pd.concat([df_registry, pd.DataFrame([new_entry])], ignore_index=True)
            print(f"\n✓ Quellen-Registry: Neuer Eintrag für {stdb_id}")
    else:
        # Erstelle neue
        df_registry = pd.DataFrame([new_entry])
        print(f"\n✓ Quellen-Registry erstellt: {registry_file}")

    # Speichere
    df_registry.to_csv(registry_file, index=False)
    print(f"  → {len(df_registry)} Einträge in Registry")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="CLI Antennendiagramm-Digitalisierer"
    )
    parser.add_argument('pdf_file', type=Path, help='Pfad zum StDB-PDF')
    parser.add_argument('-o', '--output', type=Path, required=True,
                       help='Output ODS-Datei')
    parser.add_argument('--start-page', type=int, default=None,
                       help='Start-Seite (erste Seite mit Diagrammen). Auto-detect per OCR wenn nicht angegeben.')
    parser.add_argument('--stdb-id', type=str, default='',
                       help='StDB-ID (default: Dateiname)')
    parser.add_argument('--config', type=Path,
                       help='Lade gespeicherte Kalibrierung (überspringt Eingabe)')
    parser.add_argument('--registry', type=Path,
                       default=Path('antenna_pattern_sources.csv'),
                       help='Quellen-Registry CSV')

    args = parser.parse_args()

    if not args.pdf_file.exists():
        print(f"Fehler: Datei nicht gefunden: {args.pdf_file}")
        sys.exit(1)

    stdb_id = args.stdb_id if args.stdb_id else args.pdf_file.stem

    # Temp-Verzeichnis für PNGs (im Projektverzeichnis)
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)

    try:
        # Phase 1: Kalibrierung
        if args.config and args.config.exists():
            print(f"Lade Kalibrierung: {args.config}")
            with open(args.config) as f:
                data = json.load(f)
            calibrations = [DiagramCalibration.from_dict(d) for d in data]

        else:
            print("\n" + "="*60)
            print("PHASE 1: KALIBRIERUNG")
            print("="*60)
            calibrations = run_calibration_cli(args.pdf_file, args.start_page, temp_dir)

            # Speichere Konfiguration
            config_file = args.output.with_suffix('.json')
            with open(config_file, 'w') as f:
                json.dump([c.to_dict() for c in calibrations], f, indent=2)
            print(f"\n✓ Kalibrierung gespeichert: {config_file}")

        # Phase 2: Digitalisierung
        print("\n" + "="*60)
        print("PHASE 2: DIGITALISIERUNG")
        print("="*60)

        df = digitize_all(args.pdf_file, calibrations, stdb_id, temp_dir)

        # Phase 3: Export (mit Append-Mode)
        print("\n" + "="*60)
        print("PHASE 3: EXPORT")
        print("="*60)

        # Prüfe ob Output bereits existiert
        if args.output.exists():
            print(f"Existierende Datei gefunden: {args.output}")
            print("  → Lade existierende Daten...")

            try:
                df_existing = pd.read_excel(args.output, sheet_name='dB', engine='odf')
                print(f"  → {len(df_existing)} existierende Datenpunkte")

                # Entferne alte Einträge für diese StDB-ID (falls vorhanden)
                df_existing = df_existing[df_existing['StDb-ID'] != stdb_id]
                print(f"  → {len(df_existing)} nach Entfernung alter {stdb_id}-Einträge")

                # Hänge neue Daten an
                df_combined = pd.concat([df_existing, df], ignore_index=True)
                print(f"  → {len(df_combined)} total nach Hinzufügen neuer Daten")

                df = df_combined

            except Exception as e:
                print(f"  ⚠️  Fehler beim Laden: {e}")
                print(f"  → Überschreibe Datei mit neuen Daten")

        print(f"Exportiere {len(df)} Datenpunkte → {args.output}")

        with pd.ExcelWriter(args.output, engine='odf') as writer:
            df.to_excel(writer, sheet_name='dB', index=False)

        # Phase 4: Registry
        print("\n" + "="*60)
        print("PHASE 4: QUELLEN-REGISTRY")
        print("="*60)

        update_source_registry(stdb_id, args.pdf_file, calibrations, args.registry)

        print("\n✓ FERTIG!")
        print(f"  Diagramme: {len(calibrations)}")
        print(f"  Datenpunkte: {len(df)}")
        print(f"  Output: {args.output}")
        print(f"  Registry: {args.registry}")
        print(f"  Temp-Bilder: {temp_dir}")

    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
