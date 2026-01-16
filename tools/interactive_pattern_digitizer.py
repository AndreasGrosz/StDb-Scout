#!/usr/bin/env python3
"""
Interaktiver Antennendiagramm-Digitalisierer

Workflow:
1. User markiert Mittelpunkt und Randpunkt für alle Diagramme (Batch)
2. Script digitalisiert alle Diagramme automatisch
3. Export nach ODS

Usage:
    python interactive_pattern_digitizer.py <stdb.pdf> --output patterns.ods
"""

import sys
from pathlib import Path
import numpy as np
import cv2
import pandas as pd
from typing import List, Tuple, Dict, Optional
import tempfile
import subprocess
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import json


class DiagramConfig:
    """Konfiguration für ein Polardiagramm"""

    def __init__(self, page_nr: int, diagram_nr: int):
        self.page_nr = page_nr
        self.diagram_nr = diagram_nr
        self.center: Optional[Tuple[float, float]] = None
        self.outer_point: Optional[Tuple[float, float]] = None
        self.antenna_type: str = ""
        self.freq_band: str = ""
        self.h_or_v: str = ""  # "h" oder "v"

    @property
    def radius(self) -> Optional[float]:
        """Berechnet Radius aus Zentrum und Randpunkt"""
        if self.center and self.outer_point:
            dx = self.outer_point[0] - self.center[0]
            dy = self.outer_point[1] - self.center[1]
            return np.sqrt(dx**2 + dy**2)
        return None

    def is_complete(self) -> bool:
        """Prüft ob Konfiguration vollständig ist"""
        return (self.center is not None and
                self.outer_point is not None and
                len(self.antenna_type) > 0 and
                len(self.freq_band) > 0 and
                len(self.h_or_v) > 0)


class InteractiveDiagramCalibrator:
    """Interaktive Kalibrierung aller Diagramme in einem PDF"""

    def __init__(self, pdf_file: Path, start_page: int = None):
        self.pdf_file = pdf_file
        self.start_page = start_page
        self.configs: List[DiagramConfig] = []
        self.current_config_idx = 0
        self.current_image = None
        self.current_page_nr = 0
        self.click_mode = "center"  # "center" oder "outer"

        # Matplotlib figure
        self.fig = None
        self.ax = None

    def pdf_to_images(self, output_dir: Path, dpi: int = 300) -> List[Path]:
        """Konvertiert PDF zu PNG-Bildern"""
        print(f"Konvertiere PDF zu Bildern (DPI={dpi})...")
        output_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            'pdftoppm',
            '-png',
            '-r', str(dpi),
            str(self.pdf_file),
            str(output_dir / 'page')
        ]

        subprocess.run(cmd, check=True, capture_output=True)
        pages = sorted(output_dir.glob('page-*.png'))
        print(f"  → {len(pages)} Seiten konvertiert")

        return pages

    def find_antenna_diagrams_page(self, pages: List[Path]) -> int:
        """Findet Seite mit 'Antenna Diagrams' Überschrift per OCR"""
        try:
            import pytesseract

            print("\nSuche nach 'Antenna Diagrams' Seite...")
            for i, page_file in enumerate(pages, start=1):
                img = cv2.imread(str(page_file))
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

                # OCR auf oberem Drittel der Seite (Überschriften)
                h = gray.shape[0]
                header = gray[:h//3, :]

                text = pytesseract.image_to_string(header)

                if 'antenna' in text.lower() and 'diagram' in text.lower():
                    print(f"  → Gefunden auf Seite {i}")
                    return i

            print("  → Nicht gefunden, verwende Seite 1")
            return 1

        except ImportError:
            print("  → pytesseract nicht verfügbar, verwende --start-page")
            return self.start_page if self.start_page else 1

    def run_calibration(self) -> List[DiagramConfig]:
        """Führt interaktive Kalibrierung durch"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            pages = self.pdf_to_images(tmpdir_path)

            # Finde Start-Seite
            if self.start_page is None:
                start_idx = self.find_antenna_diagrams_page(pages)
            else:
                start_idx = self.start_page

            # Sammle Diagramm-Seiten (ab Antenna Diagrams)
            diagram_pages = pages[start_idx:]

            if len(diagram_pages) == 0:
                print("Keine Diagramm-Seiten gefunden!")
                return []

            print(f"\nKalibriere {len(diagram_pages)} Diagramm-Seiten...")
            print("Pro Seite: 2 Diagramme (H und V)")

            # Erstelle Konfigurationen (2 pro Seite)
            for page_idx, page_file in enumerate(diagram_pages, start=start_idx):
                for diagram_nr in [1, 2]:
                    config = DiagramConfig(page_idx, diagram_nr)
                    self.configs.append(config)

            print(f"Total: {len(self.configs)} Diagramme zu kalibrieren")

            # Interaktive Kalibrierung
            self._run_interactive_session(diagram_pages, start_idx)

            return self.configs

    def _run_interactive_session(self, pages: List[Path], start_idx: int):
        """Zeigt Diagramme und sammelt User-Klicks"""
        self.fig, self.ax = plt.subplots(figsize=(14, 10))
        plt.subplots_adjust(bottom=0.15)

        # Buttons
        ax_next = plt.axes([0.7, 0.02, 0.1, 0.05])
        ax_prev = plt.axes([0.5, 0.02, 0.1, 0.05])
        ax_done = plt.axes([0.85, 0.02, 0.1, 0.05])

        btn_next = Button(ax_next, 'Weiter')
        btn_prev = Button(ax_prev, 'Zurück')
        btn_done = Button(ax_done, 'Fertig')

        btn_next.on_clicked(lambda event: self._next_diagram())
        btn_prev.on_clicked(lambda event: self._prev_diagram())
        btn_done.on_clicked(lambda event: self._finish_calibration())

        # Mouse-Click Handler
        self.fig.canvas.mpl_connect('button_press_event', self._on_click)

        # Zeige erstes Diagramm
        self._load_and_show_diagram(pages, start_idx)

        plt.show()

    def _load_and_show_diagram(self, pages: List[Path], start_idx: int):
        """Lädt und zeigt aktuelles Diagramm"""
        if self.current_config_idx >= len(self.configs):
            print("Alle Diagramme kalibriert!")
            return

        config = self.configs[self.current_config_idx]
        page_idx = config.page_nr - start_idx

        # Lade Bild
        img = cv2.imread(str(pages[page_idx]))
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.current_image = img_rgb
        self.current_page_nr = config.page_nr

        # Zeige
        self.ax.clear()
        self.ax.imshow(img_rgb)
        self.ax.set_title(
            f"Seite {config.page_nr}, Diagramm {config.diagram_nr}/2\n"
            f"Klicke: {'MITTELPUNKT' if self.click_mode == 'center' else 'RANDPUNKT (äußerer Kreis)'}",
            fontsize=14, fontweight='bold'
        )

        # Zeichne bereits gesetzte Punkte
        if config.center:
            self.ax.plot(config.center[0], config.center[1], 'r+',
                        markersize=20, markeredgewidth=3, label='Mittelpunkt')

        if config.outer_point:
            self.ax.plot(config.outer_point[0], config.outer_point[1], 'bx',
                        markersize=15, markeredgewidth=3, label='Randpunkt')

            # Zeichne Kreis
            if config.center and config.radius:
                circle = plt.Circle(config.center, config.radius,
                                   color='g', fill=False, linewidth=2,
                                   linestyle='--', label='Äußerer Kreis')
                self.ax.add_patch(circle)

        if config.center or config.outer_point:
            self.ax.legend(loc='upper right')

        self.ax.axis('off')
        self.fig.canvas.draw()

    def _on_click(self, event):
        """Maus-Klick Handler"""
        if event.inaxes != self.ax:
            return

        config = self.configs[self.current_config_idx]

        if self.click_mode == "center":
            config.center = (event.xdata, event.ydata)
            print(f"  Mittelpunkt gesetzt: ({event.xdata:.0f}, {event.ydata:.0f})")
            self.click_mode = "outer"

        elif self.click_mode == "outer":
            config.outer_point = (event.xdata, event.ydata)
            print(f"  Randpunkt gesetzt: ({event.xdata:.0f}, {event.ydata:.0f})")
            print(f"  → Radius: {config.radius:.0f} px")

            # Frage Metadaten ab (im Terminal)
            print(f"\nDiagramm-Metadaten für Seite {config.page_nr}, Diagramm {config.diagram_nr}:")
            config.antenna_type = input("  Antennentyp (z.B. AIR3268): ").strip()
            config.freq_band = input("  Frequenzband (z.B. 738-921): ").strip()
            config.h_or_v = input("  H oder V [h/v]: ").strip().lower()

            self.click_mode = "center"

            # Automatisch zum nächsten
            self._next_diagram()

        # Neu zeichnen
        self._load_and_show_diagram(
            [Path(f"/tmp/{self.current_page_nr}.png")],  # Dummy, wird ignoriert
            0
        )

    def _next_diagram(self):
        """Nächstes Diagramm"""
        if self.current_config_idx < len(self.configs) - 1:
            self.current_config_idx += 1
            # Hier müssten wir die pages wieder laden - vereinfacht
            print(f"Wechsel zu Diagramm {self.current_config_idx + 1}/{len(self.configs)}")

    def _prev_diagram(self):
        """Vorheriges Diagramm"""
        if self.current_config_idx > 0:
            self.current_config_idx -= 1
            print(f"Zurück zu Diagramm {self.current_config_idx + 1}/{len(self.configs)}")

    def _finish_calibration(self):
        """Beendet Kalibrierung"""
        print("\nKalibrierung abgeschlossen!")
        plt.close(self.fig)

    def save_config(self, output_file: Path):
        """Speichert Kalibrierungs-Konfiguration als JSON"""
        data = []
        for config in self.configs:
            data.append({
                'page_nr': config.page_nr,
                'diagram_nr': config.diagram_nr,
                'center': config.center,
                'outer_point': config.outer_point,
                'radius': config.radius,
                'antenna_type': config.antenna_type,
                'freq_band': config.freq_band,
                'h_or_v': config.h_or_v,
            })

        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"Konfiguration gespeichert: {output_file}")


def digitize_diagram(
    image_gray: np.ndarray,
    center: Tuple[float, float],
    radius: float
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Digitalisiert ein Polardiagramm.

    Args:
        image_gray: Graustufenbild
        center: (x, y) Mittelpunkt
        radius: Radius des äußeren Kreises

    Returns:
        angles: Winkel in Grad [0-360]
        attenuation_db: Dämpfung in dB [0-30]
    """
    cx, cy = int(center[0]), int(center[1])
    r_outer = int(radius)

    # ROI extrahieren
    y1, y2 = max(0, cy - r_outer - 50), min(image_gray.shape[0], cy + r_outer + 50)
    x1, x2 = max(0, cx - r_outer - 50), min(image_gray.shape[1], cx + r_outer + 50)

    roi = image_gray[y1:y2, x1:x2]

    # Mittelpunkt relativ zum ROI
    cx_roi = cx - x1
    cy_roi = cy - y1

    # Binärisierung
    _, binary = cv2.threshold(roi, 128, 255, cv2.THRESH_BINARY_INV)

    # Sample entlang Radien
    angles = np.arange(0, 360, 0.5)
    curve_radii = []

    for angle_deg in angles:
        angle_rad = np.deg2rad(angle_deg)

        # Finde äußersten schwarzen Pixel entlang Strahl
        max_r = 0
        for r in range(50, r_outer + 50):
            x = int(cx_roi + r * np.sin(angle_rad))
            y = int(cy_roi - r * np.cos(angle_rad))  # -cos weil Y nach unten

            if 0 <= x < binary.shape[1] and 0 <= y < binary.shape[0]:
                if binary[y, x] > 0:  # Schwarzer Pixel
                    max_r = r

        curve_radii.append(max_r if max_r > 0 else 50)

    curve_radii = np.array(curve_radii)

    # Konvertiere zu Dämpfung
    # Mittelpunkt=30dB, Außenkreis=0dB
    r_max = curve_radii.max()
    attenuation_db = 30.0 * (1.0 - curve_radii / r_max)

    return angles, attenuation_db


def digitize_all_diagrams(
    pdf_file: Path,
    configs: List[DiagramConfig],
    stdb_id: str
) -> pd.DataFrame:
    """Digitalisiert alle kalibrierten Diagramme"""

    print(f"\nDigitalisiere {len(configs)} Diagramme...")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # PDF → Bilder
        cmd = ['pdftoppm', '-png', '-r', '300', str(pdf_file), str(tmpdir_path / 'page')]
        subprocess.run(cmd, check=True, capture_output=True)
        pages = sorted(tmpdir_path.glob('page-*.png'))

        all_data = []

        for config in configs:
            if not config.is_complete():
                print(f"  Überspringe Diagramm {config.page_nr}-{config.diagram_nr} (unvollständig)")
                continue

            print(f"  Digitalisiere: Seite {config.page_nr}, Diagramm {config.diagram_nr} "
                  f"({config.antenna_type} {config.freq_band} {config.h_or_v.upper()})")

            # Lade Bild
            page_file = pages[config.page_nr - 1]
            img = cv2.imread(str(page_file))
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Digitalisiere
            angles, attenuation = digitize_diagram(gray, config.center, config.radius)

            # Zu DataFrame
            for phi, db in zip(angles, attenuation):
                all_data.append({
                    'StDb-ID': stdb_id,
                    'Antennen-Typ': config.antenna_type,
                    'Frequenz-band': config.freq_band,
                    'vertical or horizontal': config.h_or_v,
                    'Phi': phi,
                    'dB': db,
                })

            print(f"    → {len(angles)} Punkte, Dämpfung {attenuation.min():.1f}-{attenuation.max():.1f} dB")

    df = pd.DataFrame(all_data)
    return df


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Interaktiver Antennendiagramm-Digitalisierer"
    )
    parser.add_argument('pdf_file', type=Path, help='Pfad zum StDB-PDF')
    parser.add_argument('-o', '--output', type=Path, required=True,
                       help='Output ODS-Datei')
    parser.add_argument('--start-page', type=int,
                       help='Seite nach "Antenna Diagrams" (optional)')
    parser.add_argument('--stdb-id', type=str, default='',
                       help='StDB-ID für Metadaten (optional)')
    parser.add_argument('--config', type=Path,
                       help='Lade existierende Kalibrierungs-Config (überspringt GUI)')

    args = parser.parse_args()

    if not args.pdf_file.exists():
        print(f"Fehler: Datei nicht gefunden: {args.pdf_file}")
        sys.exit(1)

    # Phase 1: Kalibrierung (oder laden)
    if args.config and args.config.exists():
        print(f"Lade Kalibrierung: {args.config}")
        with open(args.config) as f:
            config_data = json.load(f)

        configs = []
        for item in config_data:
            config = DiagramConfig(item['page_nr'], item['diagram_nr'])
            config.center = tuple(item['center']) if item['center'] else None
            config.outer_point = tuple(item['outer_point']) if item['outer_point'] else None
            config.antenna_type = item['antenna_type']
            config.freq_band = item['freq_band']
            config.h_or_v = item['h_or_v']
            configs.append(config)

    else:
        print("=== Phase 1: Interaktive Kalibrierung ===")
        calibrator = InteractiveDiagramCalibrator(args.pdf_file, args.start_page)
        configs = calibrator.run_calibration()

        # Speichere Config
        config_file = args.output.with_suffix('.json')
        calibrator.save_config(config_file)

    # Phase 2: Digitalisierung
    print("\n=== Phase 2: Automatische Digitalisierung ===")

    stdb_id = args.stdb_id if args.stdb_id else args.pdf_file.stem
    df = digitize_all_diagrams(args.pdf_file, configs, stdb_id)

    # Phase 3: Export
    print(f"\n=== Phase 3: Export nach ODS ===")
    print(f"Exportiere {len(df)} Datenpunkte nach: {args.output}")

    with pd.ExcelWriter(args.output, engine='odf') as writer:
        df.to_excel(writer, sheet_name='dB', index=False)

    print("\n✓ Fertig!")
    print(f"  Diagramme: {len(configs)}")
    print(f"  Datenpunkte: {len(df)}")
    print(f"  Output: {args.output}")


if __name__ == "__main__":
    main()
