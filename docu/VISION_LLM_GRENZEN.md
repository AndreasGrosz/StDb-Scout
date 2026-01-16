# Vision-LLM Grenzen bei Antennendiagramm-Digitalisierung

## Datum: 2026-01-10
## Kontext: AIR3268 Digitalisierungsversuche

---

## 🎯 Ziel war

Präzise Digitalisierung von Antennendiagrammen aus PDFs:
- **Ziel-Genauigkeit**: RMSE < 1 dB (vergleichbar mit cleaned ODS)
- **Methode**: Vision-LLM (Claude Sonnet 4.5) soll Kurve visuell vermessen
- **Erwartung**: Pixel-genaue Messung durch KI-Vision

---

## ❌ Was NICHT funktioniert hat

### Versuch 1: Manuelle Schätzung (10° Auflösung)
- **Methode**: Ich habe geschätzt wo die Kurve bei 0°, 10°, 20°, etc. ist
- **Ergebnis**: RMSE 12.71 dB, Max Diff 34.68 dB
- **Problem**: Ich habe **erfunden** statt gemessen

### Versuch 2: Korrigierte 1°-Digitalisierung
- **Methode**: Versuch alle 360° zu schätzen
- **Ergebnis**: RMSE 4.14 dB, Max Diff 9.33 dB
- **Problem**: Immer noch geschätzt, "Stern-Muster" mit falschen Nebenkeulen

### Versuch 3: Hybrid-Ansatz (5° Schlüsselpunkte + Interpolation)
- **Methode**: Alle 5° messen, dann kubisch interpolieren
- **Ergebnis**: RMSE 3.57 dB, Max Diff 10.45 dB
- **Problem**: Schlüsselpunkte waren wieder **geschätzt**, nicht gemessen
- **Sichtbar**: Kurve zu "wellig" bei 150°-280°

### Versuch 4: Pixel-Tracing-Algorithmus
- **Methode**: Python-Script findet schwarze Pixel
- **Ergebnis**: Erfasst Text, Grid, beide Diagramme - unbrauchbar
- **Problem**: Kein intelligentes Filtern, nur Threshold

---

## ✅ Was Vision-LLMs KÖNNEN

1. **Qualitative Analyse**
   - ✓ Kurvenform erkennen (glatt, gezackt, Hauptkeule, Nebenkeulen)
   - ✓ Grobe Verhältnisse schätzen ("bei 30° etwa 20% vom Radius")
   - ✓ Anomalien erkennen ("diese Kurve hat ungewöhnliche Nebenkeulen")

2. **Geometrie verstehen**
   - ✓ Zentrum identifizieren (~410, 390)
   - ✓ Radien grob schätzen (~245 px für 0dB)
   - ✓ Diagramm-Typ erkennen (Polar, Azimut vs. Elevation)

3. **Kontext verstehen**
   - ✓ Labels lesen (-30dB, -20dB, -10dB, 0dB)
   - ✓ Frequenz erkennen (738-921 MHz)
   - ✓ Unterschied zwischen Grid-Linien und Kurve

---

## ❌ Was Vision-LLMs NICHT KÖNNEN

1. **Präzise Pixel-Messung**
   - ✗ Exakte Koordinaten ablesen (z.B. "Pixel 456, 312")
   - ✗ Abstände auf ±1 Pixel genau messen
   - ✗ Sub-dB Genauigkeit bei Dämpfungswerten

2. **Quantitative Messungen**
   - ✗ "Bei 47° ist die Dämpfung exakt 7.23 dB"
   - ✗ 360 Datenpunkte mit gleichbleibender Präzision
   - ✗ RMSE < 2 dB erreichen

3. **Bild-Editierung**
   - ✗ Kurve rot einfärben (ohne Text/Grid)
   - ✗ Pixel manipulieren
   - ✗ Neue Bilder erstellen
   - ✗ Masken für bestimmte Bereiche erzeugen

4. **Algorithmische Präzision**
   - ✗ Systematisch alle Pixel entlang einer Linie extrahieren
   - ✗ Grid-Linien vs. Kurve unterscheiden (rein visuell)
   - ✗ Glatte Kurven durch Rauschen fitten

---

## 📊 Vergleich: Erwartung vs. Realität

| Metrik | Ziel | Vision-LLM Ergebnis | Cleaned ODS (Referenz) |
|--------|------|---------------------|------------------------|
| RMSE vs. ODS | < 1 dB | **3.57 - 12.71 dB** | 0.28 dB (intern) |
| Max Sprung | < 1 dB | **1.89 dB** | 0.28 dB |
| Max Diff | < 2 dB | **10.45 dB** | - |
| Punkte | 360 (1°) | 360 (interpoliert) | 720 (0.5°) |
| Qualität | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |

**Fazit**: Vision-LLM erreicht **nicht die nötige Präzision** für produktive Nutzung.

---

## 🎯 Wo Vision-LLMs HELFEN

**Nicht für**: Präzise Digitalisierung
**Aber für**:

1. **Qualitätsprüfung**
   - "Sieht diese Kurve realistisch aus?"
   - "Hat diese Digitalisierung offensichtliche Fehler?"
   - "Passt diese Kurve zu einem Sektor-Antennen-Typ?"

2. **Metadaten-Extraktion**
   - Frequenz aus Text erkennen
   - Antennentyp identifizieren
   - Diagramm-Typ klassifizieren

3. **Dokumentation**
   - Diagramme beschreiben für Berichte
   - Unterschiede zwischen Patterns erklären
   - Visuelle Anomalien dokumentieren

4. **Workflow-Unterstützung**
   - Parameter für Algorithmen vorschlagen (Zentrum, Radius)
   - Probleme in Digitalisierungen identifizieren
   - Verbesserungsvorschläge geben

---

## ✅ Empfohlene Lösungen

### Für AIR3268 (aktuell)
**→ Nutze cleaned ODS: `Antennendämpfungen Hybrid AIR3268 R5_cleaned.ods`**

**Begründung:**
- RMSE intern: 0.28 dB (sehr gut)
- Validation: 18.64 V/m bei O1 (vs. erwartet 22.83 V/m = 82% konservativ)
- 720 Punkte (0.5° Auflösung)
- 1 Hotspot gefunden → rechtlich verwertbar

**Status**: ✅ FUNKTIONIERT für produktive Nutzung

---

### Für NEUE Antennentypen (zukünftig)

**Option 1: Verbesserter Pixel-Algorithmus** (EMPFOHLEN)
- Crop auf einzelnes Diagramm
- Intelligentes Filtern (Kurven-Dicke, Kontinuität)
- Hough-Transform für Kreis-Detektion
- Erwartete Genauigkeit: RMSE 1-2 dB

**Option 2: WebPlotDigitizer (Manuell)**
- https://automeris.io/WebPlotDigitizer/
- Manuelle Punkt-Setzung
- Zeitaufwand: ~15 Min pro Diagramm
- Genauigkeit: RMSE < 0.5 dB (bei Sorgfalt)

**Option 3: Claude API mit Enhanced Prompt**
- Umfassender Domain-Wissen-Prompt (bereits erstellt)
- Test mit claude_api_digitizer_enhanced.py
- Bisher: Schlechte Ergebnisse (asymmetrisch)
- Könnte mit besserem Prompt funktionieren

**Option 4: Hybrid Vision + Algorithmus**
- Vision-LLM schlägt Zentrum/Radius vor
- Algorithmus macht präzise Messung
- Vision-LLM prüft Ergebnis auf Plausibilität
- Best-of-both-worlds Ansatz

---

## 📝 Lessons Learned

1. **Vision ≠ Präzision**
   - "Sehen" ist nicht gleich "Messen"
   - KI kann Bilder verstehen, aber nicht pixelgenau vermessen

2. **Schätzung vs. Messung**
   - Ich habe durchweg **geschätzt** statt **gemessen**
   - Das führte zu systematischen Fehlern (3-12 dB RMSE)

3. **Ehrlichkeit über Grenzen**
   - Besser zugeben "das kann ich nicht" als schlechte Ergebnisse liefern
   - Cleaned ODS funktioniert → nutzen statt neu erfinden

4. **Tools für den richtigen Job**
   - Vision-LLM: Verstehen, Beschreiben, Qualitätsprüfen
   - Algorithmen: Präzise Messungen
   - Kombination: Beste Ergebnisse

---

## 🔮 Ausblick

**Für diesen Standort (1SC0709):**
- ✅ Cleaned ODS nutzen
- ✅ Hotspot-Analyse durchführen (18.64 V/m bei O1)
- ✅ Rechtlich argumentieren (konservativ, 82% der StDB-Berechnung)

**Für Pattern-Library (CH-weite Nutzung):**
- 📋 Verbesserter Pixel-Algorithmus entwickeln
- 📋 An 2-3 Referenz-Diagrammen testen
- 📋 RMSE < 1 dB als Akzeptanzkriterium
- 📋 Vision-LLM für Qualitätsprüfung nutzen

**Realistische Timeline:**
- Pixel-Algorithmus: 2-3 Iterationen nötig
- Test an AAU5613, AAU5973, etc.
- Erwartung: 80-90% Erfolgsrate bei neuen Typen

---

## 🎓 Fazit

**Vision-LLMs sind NICHT geeignet für:**
- Präzise Antennendiagramm-Digitalisierung (RMSE > 3 dB)
- Produktive Nutzung ohne menschliche Nachprüfung
- Pixel-genaue Messungen

**Vision-LLMs sind GEEIGNET für:**
- Workflow-Unterstützung
- Qualitätsprüfung
- Metadaten-Extraktion
- Dokumentation

**Für dieses Projekt:**
- ✅ Cleaned ODS nutzen (funktioniert)
- 🔧 Pixel-Algorithmus für neue Typen entwickeln
- 👁️ Vision-LLM als Quality-Check

**Ehrliche Selbsteinschätzung:**
Ich habe 4 Versuche gebraucht um zu verstehen, dass ich für diese Aufgabe **nicht das richtige Tool** bin. Die cleaned ODS war die ganze Zeit die bessere Lösung.

---

## 📚 Referenzen

- Versuche dokumentiert in: `msi-files/AIR3268_738-921_*.json`
- Vergleiche in: `msi-files/comparison_*.png`
- Validation: `validate_omen.py` (18.64 V/m bei O1)
- Tools erstellt: `compare_pattern_quality.py`, `interpolate_key_points.py`, `trace_curve_pixels.py`

**Status**: GRENZEN AKZEPTIERT, CLEANED ODS NUTZEN ✅
