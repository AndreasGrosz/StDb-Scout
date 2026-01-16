#!/usr/bin/env python3
"""
Claude Vision API: Antennendiagramm-Digitalisierung

Nutzt Claude's Vision-Fähigkeiten um Antennendiagramme zu analysieren
und automatisch zu digitalisieren.

Workflow:
1. Lade Diagramm-Bild
2. Sende an Claude API mit spezifischem Prompt
3. Claude gibt JSON mit Kurvenpunkten zurück
4. Konvertiere zu ODS-Format

Vorteil:
- Keine manuelle Eingabe
- Keine fehleranfälligen Algorithmen
- Einmalige Digitalisierung aller CH-Antennentypen
"""

import sys
from pathlib import Path
import json
import base64
from typing import Optional
import os


def create_digitization_prompt(diagram_type: str = 'horizontal') -> str:
    """
    Erstellt spezialisierten Prompt für Antennendiagramm-Analyse.

    Args:
        diagram_type: 'horizontal' (Azimut) oder 'vertical' (Elevation)

    Returns:
        Prompt-String für Claude
    """
    return f"""Analysiere dieses Antennendiagramm und digitalisiere die schwarze Kurve.

**Aufgabe:**
1. Identifiziere das Zentrum des Polardiagramms (Pixel-Koordinaten)
2. Bestimme den Radius der 0dB-Linie (in Pixeln)
3. Bestimme den Radius-Abstand pro 10dB (in Pixeln)
4. Extrahiere die schwarze Kurve: Für jeden Winkel 0-360° (alle 5°):
   - Folge dem Strahl vom Zentrum nach außen
   - Finde wo die schwarze Kurve den Strahl kreuzt
   - Berechne die Dämpfung in dB

**Diagramm-Typ:** {diagram_type}
- Horizontal: 0° = rechts (Osten), im Uhrzeigersinn
- Vertikal: 0° = oben (Zenith), im Uhrzeigersinn

**Wichtig:**
- Ignoriere gestrichelte Grid-Linien
- Ignoriere Text/Labels
- Nur die schwarze durchgezogene Kurve zählt
- Bei mehreren Kurven: Nutze die äußerste (Hauptkeule)

**Output-Format (JSON):**
{{
  "metadata": {{
    "center_px": [x, y],
    "radius_0db_px": <float>,
    "radius_per_10db_px": <float>,
    "diagram_type": "{diagram_type}"
  }},
  "curve_points": [
    {{"angle_deg": 0, "attenuation_db": 0.5}},
    {{"angle_deg": 5, "attenuation_db": 0.7}},
    ...
    {{"angle_deg": 355, "attenuation_db": 0.6}}
  ]
}}

**Beispiel-Berechnung:**
- Zentrum bei (400, 400)
- 0dB-Radius: 200px
- Pro 10dB: 50px Radius-Reduktion
- Kurve bei 45° schneidet Radius 180px
- Dämpfung = (200 - 180) / 50 * 10 = 4.0 dB

Gib NUR das JSON zurück, keine anderen Erklärungen.
"""


def digitize_with_claude_api(
    image_path: Path,
    diagram_type: str = 'horizontal',
    api_key: Optional[str] = None
) -> dict:
    """
    Digitalisiert Antennendiagramm via Claude Vision API.

    Args:
        image_path: Pfad zum Bild
        diagram_type: 'horizontal' oder 'vertical'
        api_key: Anthropic API-Key (oder via ANTHROPIC_API_KEY env)

    Returns:
        Dictionary mit Metadata + Kurvenpunkten
    """
    try:
        from anthropic import Anthropic
    except ImportError:
        print("❌ Fehler: anthropic-Paket nicht installiert!")
        print("   Installiere mit: pip install anthropic")
        sys.exit(1)

    # API-Key
    if api_key is None:
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            print("❌ Fehler: ANTHROPIC_API_KEY nicht gesetzt!")
            print("   Export mit: export ANTHROPIC_API_KEY='sk-...'")
            sys.exit(1)

    # Lade Bild als base64
    with open(image_path, 'rb') as f:
        image_data = base64.standard_b64encode(f.read()).decode('utf-8')

    # Bestimme MIME-Type
    suffix = image_path.suffix.lower()
    mime_type = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
    }.get(suffix, 'image/png')

    # Erstelle Client
    client = Anthropic(api_key=api_key)

    # Prompt
    prompt = create_digitization_prompt(diagram_type)

    print(f"\n{'='*60}")
    print("CLAUDE VISION API - ANTENNENDIAGRAMM-DIGITALISIERUNG")
    print("=" * 60)
    print(f"\nBild: {image_path.name}")
    print(f"Typ: {diagram_type}")
    print(f"\nSende an Claude...")

    # API-Call
    message = client.messages.create(
        model="claude-sonnet-4-20250514",  # Neuestes Vision-Modell
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ],
            }
        ],
    )

    # Parse Response
    response_text = message.content[0].text
    print(f"\n✓ Claude Response erhalten ({len(response_text)} chars)")

    # Extrahiere JSON (falls Claude zusätzlichen Text gibt)
    try:
        # Versuche direktes JSON-Parsing
        result = json.loads(response_text)
    except json.JSONDecodeError:
        # Suche JSON-Block in Response
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            print(f"\n❌ Fehler: Kein gültiges JSON in Response!")
            print(f"Response: {response_text[:500]}...")
            sys.exit(1)

    print(f"✓ JSON geparst")
    print(f"  Zentrum: {result['metadata']['center_px']}")
    print(f"  0dB-Radius: {result['metadata']['radius_0db_px']:.1f} px")
    print(f"  Kurvenpunkte: {len(result['curve_points'])}")

    return result


def convert_to_ods_format(
    data: dict,
    antenna_type: str,
    freq_band: str,
    output_file: Path
):
    """
    Konvertiert Claude-Output zu ODS-Format (kompatibel mit clean_msi_patterns.py).

    Args:
        data: Claude API Response
        antenna_type: Antennentyp (z.B. "AIR3268")
        freq_band: Frequenzband (z.B. "738-921")
        output_file: Output ODS-Datei
    """
    import pandas as pd

    # Erstelle DataFrame
    rows = []
    h_or_v = 'h' if data['metadata']['diagram_type'] == 'horizontal' else 'v'

    for point in data['curve_points']:
        rows.append({
            'StDb-ID': '',
            'Antennen-Typ': antenna_type,
            'Frequenz-band': freq_band,
            'vertical or horizontal': h_or_v,
            'Phi': point['angle_deg'],
            'dB': point['attenuation_db'],
            'MSI-Filename': '',
            'Frequency-Range': freq_band,
            'Created-By': 'claude_api_digitizer.py',
            'PDF-Path': '',
            'PDF-Filename': '',
        })

    df = pd.DataFrame(rows)

    # Speichere als ODS
    with pd.ExcelWriter(output_file, engine='odf') as writer:
        df.to_excel(writer, sheet_name='dB', index=False)

    print(f"\n✓ ODS gespeichert: {output_file}")
    print(f"  {len(rows)} Punkte")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Digitalisiert Antennendiagramme mit Claude Vision API"
    )
    parser.add_argument('image', type=Path, help='Antennendiagramm-Bild')
    parser.add_argument('--type', choices=['horizontal', 'vertical'],
                       default='horizontal',
                       help='Diagramm-Typ (default: horizontal)')
    parser.add_argument('--antenna', type=str, default='AIR3268',
                       help='Antennentyp (default: AIR3268)')
    parser.add_argument('--freq', type=str, default='738-921',
                       help='Frequenzband (default: 738-921)')
    parser.add_argument('-o', '--output', type=Path,
                       help='Output ODS-Datei (default: <image>_digitized.ods)')
    parser.add_argument('--json-only', action='store_true',
                       help='Nur JSON speichern, kein ODS')

    args = parser.parse_args()

    if not args.image.exists():
        print(f"❌ Fehler: {args.image} nicht gefunden!")
        return 1

    # Output-Datei
    if args.output is None:
        if args.json_only:
            output_file = args.image.with_suffix('.json')
        else:
            output_file = args.image.parent / (args.image.stem + '_digitized.ods')
    else:
        output_file = args.output

    # Digitalisiere mit Claude
    result = digitize_with_claude_api(
        image_path=args.image,
        diagram_type=args.type
    )

    # Speichere
    if args.json_only:
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n✓ JSON gespeichert: {output_file}")
    else:
        convert_to_ods_format(
            data=result,
            antenna_type=args.antenna,
            freq_band=args.freq,
            output_file=output_file
        )

    print(f"\n{'='*60}")
    print("ABGESCHLOSSEN")
    print("=" * 60)
    print(f"\nNächste Schritte:")
    print(f"  1. Prüfe Ergebnis: {output_file}")
    print(f"  2. Falls korrekt: Wiederhole für V-Polarisation")
    print(f"  3. Kombiniere H+V in einer ODS-Datei")
    print(f"  4. Bereinige mit: clean_msi_patterns.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())
