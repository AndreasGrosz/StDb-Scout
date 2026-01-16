#!/usr/bin/env python3
"""
Claude Vision API: Antennendiagramm-Digitalisierung (ENHANCED)

Verbesserte Version mit umfassendem Domain-Wissen im Prompt.
"""

import sys
from pathlib import Path
import json
import base64
from typing import Optional
import os


def create_enhanced_digitization_prompt(diagram_type: str = 'horizontal') -> str:
    """
    Erstellt UMFASSENDEN Prompt mit Domain-Wissen für Antennendiagramm-Analyse.

    Args:
        diagram_type: 'horizontal' (Azimut) oder 'vertical' (Elevation)

    Returns:
        Prompt-String für Claude mit vollem Kontext
    """
    return f"""Du bist ein Experte für Mobilfunk-Antennendiagramme. Analysiere dieses Polardiagramm einer Sektor-Antenne und digitalisiere die Strahlungscharakteristik präzise.

**KONTEXT: Was ist das?**
- Hersteller: Ericsson AIR3268 (Hybrid-Antenne für 4G/5G)
- Format: Polares Dämpfungsdiagramm (0dB = Hauptstrahlrichtung, höhere Werte = stärkere Dämpfung)
- Diagramm-Typ: {diagram_type}
  - Horizontal = Azimut-Ebene (Rundstrahl-Charakteristik)
  - Vertikal = Elevations-Ebene (Vertikale Strahlformung)
- Quelle: Swisscom StDB (Standortdatenblatt) für NISV-Compliance

**PHYSIKALISCHE ERWARTUNGEN:**

1. **Realistische Kurven** (KRITISCH!):
   - Antennendiagramme sind in der Praxis NICHT perfekt symmetrisch
   - Herstellungstoleranzen, Montage, Umgebungseinflüsse führen zu Asymmetrien
   - Digitalisiere die EXAKTE schwarze Kurve wie sie ist, OHNE Symmetrie zu erzwingen
   - Jeder Winkel muss individuell gemessen werden

2. **Typische Werte für AIR3268:**
   - Horizontal (Azimut):
     * 3dB-Beamwidth: 60-70° (Hauptkeule)
     * Front-to-Back-Ratio: 20-30 dB
     * Max. Dämpfung Rückseite: 25-31 dB
   - Vertikal (Elevation):
     * 3dB-Beamwidth: 5-10° (schmale Vertikalkeule)
     * Seitenkeulen sichtbar
     * Max. Dämpfung: 28-32 dB

3. **Frequenzabhängigkeit:**
   - Niedrigere Frequenzen (700-900 MHz): Breitere Keule, weniger Dämpfung
   - Höhere Frequenzen (3600 MHz): Schmale Keule, mehr Dämpfung

**DIAGRAMM-STRUKTUR:**

Typisches Layout in den PDFs:
- Zentrum Horizontal: ~(410, 390) px
- Zentrum Vertikal: ~(410, 830) px
- 0dB-Radius: ~245 px
- Radius pro 10dB: ~62 px (bei 4 konzentrischen Kreisen für 40dB)
- Grid: Gestrichelte Linien alle 10° und alle 10dB
- Kurve: SCHWARZE durchgezogene Linie

**AUFGABE:**

Schritt 1: **Diagramm-Geometrie identifizieren**
1. Finde das exakte Zentrum des Polardiagramms
2. Identifiziere die konzentrischen Kreise:
   - Innerster Kreis = 0dB (Maximalverstärkung)
   - Äußerster Kreis = 40dB (typisch)
   - Zähle Anzahl Kreise
3. Berechne:
   - radius_0db_px = Radius des innersten Kreises
   - radius_per_10db_px = Radius-Differenz zwischen benachbarten Kreisen

Schritt 2: **Kurve digitalisieren**
Für jeden Winkel von 0° bis 355° in 5°-Schritten:
1. Lege Strahl vom Zentrum unter diesem Winkel
   - 0° = {("rechts (Osten)" if diagram_type == "horizontal" else "oben (Zenith)")}
   - Winkel im Uhrzeigersinn
2. Folge dem Strahl nach außen bis zur SCHWARZEN Kurve
3. Miss Abstand vom Zentrum in Pixeln: r_curve
4. Berechne Dämpfung:
   ```
   attenuation_db = (r_curve - radius_0db_px) / radius_per_10db_px * 10
   ```

**KRITISCHE REGELN:**

1. **Ignoriere Grid-Linien**:
   - Gestrichelte Linien = Grid, NICHT die Kurve!
   - Nur durchgezogene schwarze Linie zählt

2. **Nur eine Kurve**:
   - Falls mehrere sichtbar: Nimm die DURCHGEZOGENE
   - Gestrichelte/gepunktete = andere Frequenzen (ignorieren)

3. **Symmetrie prüfen**:
   - attenuation(φ) MUSS gleich attenuation(360° - φ) sein!
   - Falls nicht: Fehler, nochmal genau hinschauen

4. **Plausibilität**:
   - Min. Dämpfung nahe 0° sollte ~0-0.5 dB sein
   - Max. Dämpfung sollte nicht > 40 dB sein
   - Kurve muss GLATT sein (keine Sprünge > 5dB zwischen Nachbarpunkten)

**BEISPIEL-BERECHNUNG:**

Annahmen:
- Zentrum: (410, 390)
- 0dB-Radius: 245 px
- 4 Kreise bis 40dB → Radius pro 10dB = (245 - 0) / 4 = 61.25 px

Winkel 45°:
- Strahl schneidet Kurve bei Radius 210 px
- Dämpfung = (245 - 210) / 61.25 * 10 = 5.7 dB

Winkel 180°:
- Strahl schneidet Kurve bei Radius 90 px (Rückseite)
- Dämpfung = (245 - 90) / 61.25 * 10 = 25.3 dB

**QUALITÄTSSICHERUNG:**

Vor dem Output, prüfe:
1. ✓ Glattheit: Keine unrealistischen Sprünge > 10dB zwischen benachbarten Punkten
2. ✓ Bereich: 0 ≤ attenuation ≤ 40 dB (typisch)
3. ✓ Hauptkeule bei 0°: Minimum der Dämpfung in diesem Bereich
4. ✓ Auflösung: Mindestens 360 Punkte (1°-Schritte) für präzise Digitalisierung
5. ✓ Kurven-Kontinuität: Kurve muss geschlossen sein (start ≈ end)

**OUTPUT-FORMAT (JSON):**

Gib NUR folgendes JSON zurück, KEINE anderen Erklärungen:

{{
  "metadata": {{
    "center_px": [x, y],
    "radius_0db_px": <float>,
    "radius_per_10db_px": <float>,
    "diagram_type": "{diagram_type}",
    "quality_checks": {{
      "is_symmetric": true/false,
      "min_attenuation_db": <float>,
      "max_attenuation_db": <float>,
      "num_points": 72
    }}
  }},
  "curve_points": [
    {{"angle_deg": 0, "attenuation_db": 0.1}},
    {{"angle_deg": 5, "attenuation_db": 0.2}},
    ...
    {{"angle_deg": 355, "attenuation_db": 0.2}}
  ]
}}

**WICHTIG:**
- Sei präzise auf ±1 Pixel genau
- Bei Unsicherheit: Lieber konservativ (geringere Dämpfung = höhere E-Feldstärke = sicherer für NISV)
- Symmetrie ist nicht optional, sondern physikalisch vorgegeben!

Beginne jetzt mit der Analyse!
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

    # ENHANCED Prompt mit Domain-Wissen
    prompt = create_enhanced_digitization_prompt(diagram_type)

    print(f"\n{'='*60}")
    print("CLAUDE VISION API - ENHANCED ANTENNENDIAGRAMM-DIGITALISIERUNG")
    print("=" * 60)
    print(f"\nBild: {image_path.name}")
    print(f"Typ: {diagram_type}")
    print(f"Prompt-Länge: {len(prompt)} Zeichen")
    print(f"\nSende an Claude mit umfassendem Domain-Wissen...")

    # API-Call
    message = client.messages.create(
        model="claude-sonnet-4-20250514",  # Neuestes Vision-Modell
        max_tokens=8192,  # Erhöht für ausführliche Analyse
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

    # Zeige Qualitätschecks
    print(f"\n✓ JSON geparst")
    print(f"  Zentrum: {result['metadata']['center_px']}")
    print(f"  0dB-Radius: {result['metadata']['radius_0db_px']:.1f} px")
    print(f"  Radius pro 10dB: {result['metadata']['radius_per_10db_px']:.1f} px")
    print(f"  Kurvenpunkte: {len(result['curve_points'])}")

    if 'quality_checks' in result['metadata']:
        qc = result['metadata']['quality_checks']
        print(f"\n  Qualitätschecks:")
        print(f"    Symmetrisch: {qc.get('is_symmetric', 'N/A')}")
        print(f"    Min Dämpfung: {qc.get('min_attenuation_db', 'N/A'):.2f} dB")
        print(f"    Max Dämpfung: {qc.get('max_attenuation_db', 'N/A'):.2f} dB")

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
            'Created-By': 'claude_api_digitizer_enhanced.py',
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
        description="Digitalisiert Antennendiagramme mit Claude Vision API (ENHANCED)"
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
                       help='Output ODS-Datei (default: <image>_enhanced.ods)')
    parser.add_argument('--json-only', action='store_true',
                       help='Nur JSON speichern, kein ODS')

    args = parser.parse_args()

    if not args.image.exists():
        print(f"❌ Fehler: {args.image} nicht gefunden!")
        return 1

    # Output-Datei
    if args.output is None:
        if args.json_only:
            output_file = args.image.parent / (args.image.stem + '_enhanced.json')
        else:
            output_file = args.image.parent / (args.image.stem + '_enhanced.ods')
    else:
        output_file = args.output

    # Digitalisiere mit Claude (ENHANCED Prompt)
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
    print(f"  2. Vergleiche mit manueller Digitalisierung")
    print(f"  3. Falls korrekt: Wiederhole für V-Polarisation")

    return 0


if __name__ == "__main__":
    sys.exit(main())
