#!/usr/bin/env python3
"""
Simpler Antennendiagramm-Digitalisierer mit OpenCV

Workflow:
1. Zeige Diagramme, User klickt Mittelpunkt + Randpunkt
2. Speichere Konfiguration
3. Digitalisiere alle Diagramme
4. Export nach ODS

Usage:
    python simple_pattern_digitizer.py <stdb.pdf> --output patterns.ods
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


class DiagramCalibration:
    """Gespeicherte Kalibrierung für ein Diagramm"""
    def __init__(self, page_nr: int, diagram_nr: int):
        self.page_nr = page_nr
        self.diagram_nr = diagram_nr
        self.center: Optional[Tuple[int, int]] = None
        self.radius: Optional[int] = None
        self.antenna_type: str = ""
        self.freq_band: str = ""
        self.h_or_v: str = ""

    def to_dict(self):
        return {
            'page_nr': self.page_nr,
            'diagram_nr': self.diagram_nr,
            'center': list(self.center) if self.center else None,
            'radius': self.radius,
            'antenna_type': self.antenna_type,
            'freq_band': self.freq_band,
            'h_or_v': self.h_or_v,
        }

    @classmethod
    def from_dict(cls, data):
        cal = cls(data['page_nr'], data['diagram_nr'])
        cal.center = tuple(data['center']) if data['center'] else None
        cal.radius = data['radius']
        cal.antenna_type = data['antenna_type']
        cal.freq_band = data['freq_band']
        cal.h_or_v = data['h_or_v']
        return cal


class SimpleCalibrator:
    """Einfache OpenCV-basierte Kalibrierung"""

    def __init__(self):
        self.clicks = []
        self.current_image = None
        self.window_name = "Diagram Calibrator - Klicke: Mittelpunkt, dann Randpunkt"

    def mouse_callback(self, event, x, y, flags, param):
        """Mouse-Event Handler"""
        if event == cv2.EVENT_LBUTTONDOWN:
            self.clicks.append((x, y))
            print(f"  Klick {len(self.clicks)}: ({x}, {y})")

            # Zeichne Klick auf Bild
            if len(self.clicks) == 1:
                # Mittelpunkt
                cv2.drawMarker(self.current_image, (x, y),
                              (0, 0, 255), cv2.MARKER_CROSS, 30, 3)
            elif len(self.clicks) == 2:
                # Randpunkt + Kreis
                cv2.drawMarker(self.current_image, (x, y),
                              (255, 0, 0), cv2.MARKER_TILTED_CROSS, 20, 2)

                # Berechne und zeichne Radius
                center = self.clicks[0]
                radius = int(np.sqrt((x - center[0])**2 + (y - center[1])**2))
                cv2.circle(self.current_image, center, radius, (0, 255, 0), 2)

                print(f"  → Radius: {radius} px")

            cv2.imshow(self.window_name, self.current_image)

    def calibrate_diagram(self, image: np.ndarray) -> Tuple[Tuple[int, int], int]:
        """
        Zeigt Bild und wartet auf 2 Klicks (Mittelpunkt, Randpunkt).

        Returns:
            (center, radius)
        """
        self.clicks = []
        self.current_image = image.copy()

        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(self.window_name, 1200, 900)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

        cv2.imshow(self.window_name, self.current_image)

        print("Warte auf 2 Klicks: Mittelpunkt, dann Randpunkt des äußeren Kreises")
        print("Drücke 'r' zum Reset, 'q' zum Überspringen")

        while True:
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):  # Überspringen
                print("Übersprungen")
                return None, None

            if key == ord('r'):  # Reset
                print("Reset")
                self.clicks = []
                self.current_image = image.copy()
                cv2.imshow(self.window_name, self.current_image)

            if len(self.clicks) >= 2:
                # Beide Klicks vorhanden
                center = self.clicks[0]
                outer = self.clicks[1]
                radius = int(np.sqrt((outer[0] - center[0])**2 + (outer[1] - center[1])**2))

                # Warte auf Bestätigung
                print("Drücke ENTER zum Bestätigen, 'r' zum Reset")
                key = cv2.waitKey(0) & 0xFF

                if key == 13:  # ENTER
                    return center, radius
                elif key == ord('r'):
                    print("Reset")
                    self.clicks = []
                    self.current_image = image.copy()
                    cv2.imshow(self.window_name, self.current_image)

        cv2.destroyAllWindows()


def pdf_to_images(pdf_file: Path, output_dir: Path, dpi: int = 300) -> List[Path]:
    """Konvertiert PDF zu PNG"""
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = ['pdftoppm', '-png', '-r', str(dpi), str(pdf_file), str(output_dir / 'page')]
    subprocess.run(cmd, check=True, capture_output=True)

    pages = sorted(output_dir.glob('page-*.png'))
    print(f"PDF → {len(pages)} Bilder konvertiert")

    return pages


def run_calibration(
    pdf_file: Path,
    start_page: Optional[int] = None
) -> List[DiagramCalibration]:
    """Führt Kalibrierung aller Diagramme durch"""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        pages = pdf_to_images(pdf_file, tmpdir_path)

        # Finde Start-Seite
        if start_page is None:
            start_page = 1  # Default: Seite 1
            print(f"Starte bei Seite {start_page} (verwende --start-page zum Anpassen)")

        calibrations = []
        calibrator = SimpleCalibrator()

        # Pro Seite: 2 Diagramme (H und V)
        for page_idx in range(start_page - 1, len(pages)):
            page_nr = page_idx + 1
            page_file = pages[page_idx]

            img = cv2.imread(str(page_file))

            print(f"\n{'='*60}")
            print(f"Seite {page_nr}")
            print(f"{'='*60}")

            for diagram_nr in [1, 2]:
                print(f"\nDiagramm {diagram_nr}/2:")

                # Kalibriere
                center, radius = calibrator.calibrate_diagram(img)

                if center is None:
                    print("Übersprungen")
                    continue

                # Metadaten abfragen
                print(f"\nMetadaten für Diagramm {diagram_nr}:")
                antenna_type = input("  Antennentyp (z.B. AIR3268): ").strip()
                freq_band = input("  Frequenzband (z.B. 738-921): ").strip()
                h_or_v = input("  H oder V [h/v]: ").strip().lower()

                # Speichere Kalibrierung
                cal = DiagramCalibration(page_nr, diagram_nr)
                cal.center = center
                cal.radius = radius
                cal.antenna_type = antenna_type
                cal.freq_band = freq_band
                cal.h_or_v = h_or_v

                calibrations.append(cal)

                print(f"✓ Kalibrierung gespeichert")

            # Frage ob weiter
            print(f"\nNächste Seite? [j/n]: ", end='')
            if input().lower() != 'j':
                break

        cv2.destroyAllWindows()

        return calibrations


def digitize_diagram(
    image_gray: np.ndarray,
    center: Tuple[int, int],
    radius: int
) -> Tuple[np.ndarray, np.ndarray]:
    """Digitalisiert Polardiagramm"""

    cx, cy = center
    r_outer = radius

    # Sample entlang Radien
    angles = np.arange(0, 360, 0.5)
    curve_radii = []

    # Binärisierung
    _, binary = cv2.threshold(image_gray, 128, 255, cv2.THRESH_BINARY_INV)

    for angle_deg in angles:
        angle_rad = np.deg2rad(angle_deg)

        # Finde äußersten schwarzen Pixel
        max_r = 0
        for r in range(50, r_outer + 100):
            x = int(cx + r * np.sin(angle_rad))
            y = int(cy - r * np.cos(angle_rad))

            if 0 <= x < binary.shape[1] and 0 <= y < binary.shape[0]:
                if binary[y, x] > 0:
                    max_r = r

        curve_radii.append(max_r if max_r > 0 else 50)

    curve_radii = np.array(curve_radii)

    # Konvertiere zu Dämpfung [dB]
    r_max = curve_radii.max()
    attenuation_db = 30.0 * (1.0 - curve_radii / r_max)

    return angles, attenuation_db


def digitize_all(
    pdf_file: Path,
    calibrations: List[DiagramCalibration],
    stdb_id: str
) -> pd.DataFrame:
    """Digitalisiert alle kalibrierten Diagramme"""

    print(f"\n{'='*60}")
    print("DIGITALISIERUNG")
    print(f"{'='*60}")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        pages = pdf_to_images(pdf_file, tmpdir_path)

        all_data = []

        for cal in calibrations:
            print(f"\nDigitalisiere: Seite {cal.page_nr}, Diagramm {cal.diagram_nr}")
            print(f"  {cal.antenna_type} {cal.freq_band} {cal.h_or_v.upper()}")

            # Lade Bild
            page_file = pages[cal.page_nr - 1]
            img = cv2.imread(str(page_file))
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Digitalisiere
            angles, attenuation = digitize_diagram(gray, cal.center, cal.radius)

            # Zu DataFrame
            for phi, db in zip(angles, attenuation):
                all_data.append({
                    'StDb-ID': stdb_id,
                    'Antennen-Typ': cal.antenna_type,
                    'Frequenz-band': cal.freq_band,
                    'vertical or horizontal': cal.h_or_v,
                    'Phi': phi,
                    'dB': db,
                })

            print(f"  → {len(angles)} Punkte, Dämpfung {attenuation.min():.1f}-{attenuation.max():.1f} dB")

    df = pd.DataFrame(all_data)
    return df


def update_source_registry(
    stdb_id: str,
    pdf_path: Path,
    calibrations: List[DiagramCalibration],
    registry_file: Path = Path("antenna_pattern_sources.csv")
):
    """
    Aktualisiert die Quellen-Tabelle mit neuer Digitalisierung.

    Format: StDb-ID, PDF-Pfad, Datum, Anzahl-Diagramme, Antennentypen, Frequenzbänder
    """
    import datetime

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
        df_registry = pd.read_csv(registry_file)

        # Prüfe ob StDb-ID bereits existiert
        existing_idx = df_registry[df_registry['StDb-ID'] == stdb_id].index

        if len(existing_idx) > 0:
            # Aktualisiere existierenden Eintrag
            for key, value in new_entry.items():
                df_registry.loc[existing_idx[0], key] = value
            print(f"\n✓ Quellen-Registry aktualisiert: {stdb_id}")
        else:
            # Füge neuen Eintrag hinzu
            df_registry = pd.concat([df_registry, pd.DataFrame([new_entry])], ignore_index=True)
            print(f"\n✓ Quellen-Registry: Neuer Eintrag für {stdb_id}")
    else:
        # Erstelle neue Registry
        df_registry = pd.DataFrame([new_entry])
        print(f"\n✓ Quellen-Registry erstellt: {registry_file}")

    # Speichere
    df_registry.to_csv(registry_file, index=False)
    print(f"  → {len(df_registry)} Einträge in Registry")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Simpler Antennendiagramm-Digitalisierer"
    )
    parser.add_argument('pdf_file', type=Path, help='Pfad zum StDB-PDF')
    parser.add_argument('-o', '--output', type=Path, required=True,
                       help='Output ODS-Datei')
    parser.add_argument('--start-page', type=int,
                       help='Start-Seite (nach "Antenna Diagrams")')
    parser.add_argument('--stdb-id', type=str, default='',
                       help='StDB-ID (default: Dateiname)')
    parser.add_argument('--config', type=Path,
                       help='Lade gespeicherte Kalibrierung (überspringt GUI)')
    parser.add_argument('--registry', type=Path,
                       default=Path('antenna_pattern_sources.csv'),
                       help='Quellen-Registry CSV (default: antenna_pattern_sources.csv)')

    args = parser.parse_args()

    if not args.pdf_file.exists():
        print(f"Fehler: Datei nicht gefunden: {args.pdf_file}")
        sys.exit(1)

    stdb_id = args.stdb_id if args.stdb_id else args.pdf_file.stem

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
        calibrations = run_calibration(args.pdf_file, args.start_page)

        # Speichere Konfiguration
        config_file = args.output.with_suffix('.json')
        with open(config_file, 'w') as f:
            json.dump([c.to_dict() for c in calibrations], f, indent=2)
        print(f"\n✓ Kalibrierung gespeichert: {config_file}")

    # Phase 2: Digitalisierung
    print("\n" + "="*60)
    print("PHASE 2: DIGITALISIERUNG")
    print("="*60)

    df = digitize_all(args.pdf_file, calibrations, stdb_id)

    # Phase 3: Export
    print("\n" + "="*60)
    print("PHASE 3: EXPORT")
    print("="*60)

    print(f"Exportiere {len(df)} Datenpunkte → {args.output}")

    with pd.ExcelWriter(args.output, engine='odf') as writer:
        df.to_excel(writer, sheet_name='dB', index=False)

    # Phase 4: Aktualisiere Quellen-Registry
    print("\n" + "="*60)
    print("PHASE 4: QUELLEN-REGISTRY")
    print("="*60)

    update_source_registry(stdb_id, args.pdf_file, calibrations, args.registry)

    print("\n✓ FERTIG!")
    print(f"  Diagramme: {len(calibrations)}")
    print(f"  Datenpunkte: {len(df)}")
    print(f"  Output: {args.output}")
    print(f"  Registry: {args.registry}")


if __name__ == "__main__":
    main()
