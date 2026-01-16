# Milestone: Präzise Antennendiagramm-Digitalisierung

## Problem
Die aktuellen CSV-Dateien (msi-files) zeigen deutliche Abweichungen zu Excel-Werten:
- **3600 MHz**: H-Dämpfung Python=31.46 dB vs Excel=29.70 dB (Differenz: 1.76 dB)
- **3600 MHz**: V-Dämpfung Python=1.66 dB vs Excel=0.40 dB (Differenz: 1.26 dB)

Diese Ungenauigkeiten führen zu Abweichungen bei der E-Feld-Berechnung.

## Ursachen
1. **CSV-Interpolation**: Wenige Stützstellen, lineare Interpolation
2. **Digitalisierungs-Fehler**: Manuelle Extraktion aus PDFs/Bildern
3. **Format-Probleme**: Semikolon/Komma-Trenner, Encoding

## Ziele
1. **Höhere Auflösung**: Mehr Stützstellen (0.1° statt 1°)
2. **Bessere Interpolation**: Spline statt linear
3. **Validierung**: Vergleich mit Hersteller-Daten (Kathrein, Huawei, etc.)
4. **Automatisierung**: Python-Script zum Extrahieren aus PDF-Diagrammen

## Implementierung

### Phase 1: Datenqualität prüfen
- [ ] Vergleiche MSI-CSV mit Original-PDF (Hybrid AIR3268)
- [ ] Identifiziere Bereiche mit größten Abweichungen
- [ ] Dokumentiere Ist-Zustand

### Phase 2: Manuelle Verbesserung
- [ ] Re-Digitalisierung kritischer Bereiche (z.B. -10° bis +10° Elevation)
- [ ] Erhöhung der Stützstellen-Dichte auf 0.5° oder 0.1°
- [ ] Validierung gegen Excel-Referenzwerte

### Phase 3: Automatisierung
- [ ] Python-Script mit `matplotlib` + `numpy`:
  - PDF → Bild (pdfplumber/pdf2image)
  - Bild → Koordinaten (cv2 Kantenerkennung)
  - Koordinaten → CSV
- [ ] Spline-Interpolation für glatte Kurven
- [ ] Qualitäts-Check: Vergleich Eingabe-PDF vs. Ausgabe-CSV

### Phase 4: Format-Standardisierung
- [ ] Wechsel zu ODS (wie `Antennendämpfungen Hybrid AIR3268 R5.ods`)
- [ ] Ein File pro Antennentyp statt viele CSVs
- [ ] Metadaten: Hersteller, Typ, Frequenz, Quelle, Datum

## Alternative: Hersteller-Daten verwenden
Falls verfügbar:
- Kathrein/Ericsson bieten `.msi` oder `.xml` Dateien an
- Konverter schreiben: MSI → Python AntennaPattern

## Erfolgskriterien
- Dämpfungswerte weichen <0.5 dB von Excel ab
- OMEN-Validierung: Alle Punkte <5% Abweichung
- Automatisierte Pipeline für neue Antennentypen

## Priorität
**Mittel** - Erst nach Fertigstellung der Kern-Features (Fassadenberechnung, Hotspot-Export)

## Geschätzter Aufwand
- Manuelle Verbesserung: 4-8h (je nach Anzahl Antennentypen)
- Automatisierung: 8-16h (PDF-Parsing, CV, Testing)
