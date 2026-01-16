"""
Automatischer Antennendiagramm-Extraktor aus PDF

Extrahiert H- und V-Dämpfungskurven aus Antennendiagramm-PDFs und
exportiert sie im ODS-Format.

Annahmen (typisches Layout):
- Polardiagramme mit konzentrischenKreisen
- Skalierung: Mittelpunkt=30dB, Außenkreis=0dB, linear
- 2 Hauptdiagramme pro Seite (H und V) oder mehrere Frequenzen

Usage:
    python pdf_pattern_extractor.py <pdf_file> <output_ods>
"""

import sys
from pathlib import Path
import numpy as np
import cv2
import pandas as pd
from typing import List, Tuple, Dict
import tempfile
import subprocess


class PolarDiagramExtractor:
    """Extrahiert Dämpfungskurven aus Polardiagrammen"""

    def __init__(self, center_x: int, center_y: int, radius: int):
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius

    def extract_curve(self, image_gray: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extrahiert Dämpfungskurve aus Polardiagramm.

        Returns:
            angles: Winkel in Grad [0-360]
            attenuation_db: Dämpfung in dB [0-30]
        """
        # ROI extrahieren
        y1 = max(0, self.center_y - self.radius)
        y2 = min(image_gray.shape[0], self.center_y + self.radius)
        x1 = max(0, self.center_x - self.radius)
        x2 = min(image_gray.shape[1], self.center_x + self.radius)

        roi = image_gray[y1:y2, x1:x2]

        # Binärisierung
        _, roi_binary = cv2.threshold(roi, 128, 255, cv2.THRESH_BINARY_INV)

        # Morphologie: Dicke Linien verstärken
        kernel = np.ones((3, 3), np.uint8)
        roi_thick = cv2.morphologyEx(roi_binary, cv2.MORPH_CLOSE, kernel)

        # Sample entlang Radien
        angles = np.arange(0, 360, 0.5)  # 720 Punkte
        curve_radii = []

        for angle_deg in angles:
            angle_rad = np.deg2rad(angle_deg)
            max_r = 0

            # Sample vom Zentrum nach außen
            for r in range(50, self.radius):
                x = int(self.radius + r * np.sin(angle_rad))
                y = int(self.radius - r * np.cos(angle_rad))

                if 0 <= x < roi_thick.shape[1] and 0 <= y < roi_thick.shape[0]:
                    if roi_thick[y, x] > 0:  # Schwarzer Pixel
                        max_r = r

            curve_radii.append(max_r if max_r > 0 else 50)

        curve_radii = np.array(curve_radii)

        # Konvertiere Radius → Dämpfung [dB]
        # Mittelpunkt=30dB, Außenkreis=0dB, linear
        radius_max = curve_radii.max()
        if radius_max > 0:
            attenuation_db = 30.0 * (1.0 - curve_radii / radius_max)
        else:
            attenuation_db = np.zeros_like(curve_radii)

        return angles, attenuation_db


def pdf_to_images(pdf_file: Path, output_dir: Path, dpi: int = 300) -> List[Path]:
    """Konvertiert PDF zu PNG-Bildern"""
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        'pdftoppm',
        '-png',
        '-r', str(dpi),
        str(pdf_file),
        str(output_dir / 'page')
    ]

    subprocess.run(cmd, check=True)

    # Finde generierte Dateien
    pages = sorted(output_dir.glob('page-*.png'))
    print(f"  PDF → {len(pages)} Bilder konvertiert")

    return pages


def find_main_diagrams(image_gray: np.ndarray, min_radius: int = 300) -> List[Tuple[int, int, int]]:
    """
    Findet Haupt-Polardiagramme in einem Bild.

    Returns:
        Liste von (center_x, center_y, radius)
    """
    # Binärisierung
    _, binary = cv2.threshold(image_gray, 200, 255, cv2.THRESH_BINARY_INV)

    # Hough Circle Detection
    circles = cv2.HoughCircles(
        binary,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=500,
        param1=30,
        param2=20,
        minRadius=min_radius,
        maxRadius=600
    )

    diagrams = []
    if circles is not None:
        circles = np.uint16(np.around(circles))

        # Filtere überlappende Kreise (behalte größten pro Cluster)
        for x, y, r in circles[0]:
            # Prüfe ob dieser Kreis anderen zu nahe ist
            too_close = False
            for dx, dy, dr in diagrams:
                dist = np.sqrt((x - dx)**2 + (y - dy)**2)
                if dist < 200:  # Zu nah
                    if r > dr:  # Dieser ist größer, ersetze
                        diagrams.remove((dx, dy, dr))
                    else:
                        too_close = True
                        break

            if not too_close:
                diagrams.append((int(x), int(y), int(r)))

    return diagrams


def extract_all_diagrams(
    pdf_file: Path,
    antenna_type: str,
    freq_configs: Dict[int, Tuple[str, str]]  # page_nr -> (freq_band, h_or_v)
) -> pd.DataFrame:
    """
    Extrahiert alle Diagramme aus PDF.

    Args:
        pdf_file: Pfad zum PDF
        antenna_type: Antennentyp (z.B. "AIR3268")
        freq_configs: Mapping Seite → (Frequenzband, "h" oder "v")

    Returns:
        DataFrame mit Spalten: StDb-ID, Antennen-Typ, Frequenz-band,
                               vertical or horizontal, Radius, Phi, dB
    """
    print(f"Verarbeite PDF: {pdf_file}")

    # PDF → Bilder
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        pages = pdf_to_images(pdf_file, tmpdir_path)

        all_data = []

        for page_idx, page_file in enumerate(pages, start=1):
            if page_idx not in freq_configs:
                print(f"  Seite {page_idx}: übersprungen (keine Konfiguration)")
                continue

            freq_band, h_or_v = freq_configs[page_idx]
            print(f"  Seite {page_idx}: {freq_band} MHz, {h_or_v.upper()}-Diagramm")

            # Lade Bild
            img = cv2.imread(str(page_file))
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Finde Diagramme
            diagrams = find_main_diagrams(gray)
            print(f"    Gefunden: {len(diagrams)} Diagramme")

            if len(diagrams) == 0:
                print(f"    WARNUNG: Keine Diagramme gefunden!")
                continue

            # Extrahiere erstes/größtes Diagramm
            diagram = max(diagrams, key=lambda d: d[2])  # Größter Radius
            center_x, center_y, radius = diagram
            print(f"    Verwende: Zentrum=({center_x}, {center_y}), Radius={radius}px")

            # Extrahiere Kurve
            extractor = PolarDiagramExtractor(center_x, center_y, radius + 50)
            angles, attenuation = extractor.extract_curve(gray)

            # Zu DataFrame
            for phi, db in zip(angles, attenuation):
                all_data.append({
                    'StDb-ID': '',  # Leer
                    'Antennen-Typ': antenna_type,
                    'Frequenz-band': freq_band,
                    'vertical or horizontal': h_or_v,
                    'Radius': 30 - db,  # Für ODS-Format
                    'Phi': phi,
                    'dB': db,
                })

            print(f"    Extrahiert: {len(angles)} Punkte, Dämpfung {attenuation.min():.1f}-{attenuation.max():.1f} dB")

    df = pd.DataFrame(all_data)
    return df


def main():
    if len(sys.argv) < 3:
        print("Usage: python pdf_pattern_extractor.py <pdf_file> <output_ods>")
        print()
        print("Beispiel:")
        print("  python pdf_pattern_extractor.py antenna.pdf patterns.ods")
        sys.exit(1)

    pdf_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])

    if not pdf_file.exists():
        print(f"Fehler: Datei nicht gefunden: {pdf_file}")
        sys.exit(1)

    # TODO: Frequenz-Konfiguration aus User-Input oder OCR
    # Beispiel für AIR3268:
    freq_configs = {
        2: ("738-921", "h"),      # Seite 2: 700-900 MHz H
        3: ("1427-2570", "h"),    # Seite 3: 1400-2600 MHz H
        4: ("3600", "h"),         # Seite 4: 3600 MHz H
        5: ("738-921", "v"),      # Seite 5: 700-900 MHz V
        6: ("1427-2570", "v"),    # Seite 6: 1400-2600 MHz V
        7: ("3600", "v"),         # Seite 7: 3600 MHz V
    }

    # Extrahiere
    df = extract_all_diagrams(pdf_file, "AIR3268", freq_configs)

    # Exportiere als ODS
    print(f"\nExportiere nach: {output_file}")

    with pd.ExcelWriter(output_file, engine='odf') as writer:
        df.to_excel(writer, sheet_name='dB', index=False)

    print(f"Fertig! {len(df)} Datenpunkte exportiert.")
    print(f"  Frequenzbänder: {df['Frequenz-band'].unique().tolist()}")
    print(f"  H/V: {df['vertical or horizontal'].unique().tolist()}")


if __name__ == "__main__":
    main()
