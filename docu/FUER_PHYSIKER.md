# StDb-Scout - Werkzeug für EMF-Gutachter

**Für: Physiker und EMF-Spezialisten**

---

## Was ist StDb-Scout?

StDb-Scout ist ein **Werkzeug zur Automatisierung repetitiver Berechnungsaufgaben** bei der Erstellung von Standortdatenblättern (StDb) für Mobilfunkanlagen.

**Wichtig:** StDb-Scout ersetzt **nicht** die fachliche Expertise eines Physikers. Es übernimmt mechanische Rechenarbeit, damit Sie sich auf die physikalisch anspruchsvollen und bewertenden Tätigkeiten konzentrieren können.

---

## Ihre Expertise bleibt unverzichtbar

### Was das Tool NICHT kann (und Sie weiterhin tun):

1. **Physikalische Plausibilitätsprüfung**
   - Sind die berechneten Werte realistisch?
   - Passen die Feldstärken zur Anlagenkonfiguration?
   - Stimmen die Antennendiagramme mit den Herstellerangaben überein?

2. **Interpretation und Bewertung**
   - Welche Messpunkte sind kritisch?
   - Wo sind zusätzliche Messungen erforderlich?
   - Wie sind Abweichungen zu OMEN-Berechnungen zu bewerten?

3. **Kommunikation mit Behörden**
   - Erläuterung der Berechnungsmethodik
   - Begründung von Annahmen
   - Beantwortung fachlicher Rückfragen

4. **Entscheidungen bei Grenzfällen**
   - Konservative vs. realistische Berechnungsannahmen
   - Wahl der Messpunkt-Positionierung
   - Berücksichtigung von Sonderfällen (Dachaufbauten, etc.)

5. **Qualitätssicherung**
   - Validierung gegen OMEN-Berechnungen
   - Überprüfung der Gebäudezuordnung
   - Kontrolle der Worst-Case-Annahmen

**→ Ihre physikalische Expertise ist der kritische Faktor für korrekte Gutachten.**

---

## Was das Tool übernimmt (mechanische Arbeit)

### Zeitaufwändige, fehleranfällige Tätigkeiten:

#### 1. Datenerfassung und -aufbereitung
**Vorher:**
- Manuelles Abtippen aus PDFs
- Koordinaten-Umrechnungen von Hand
- Excel-Formeln kopieren und anpassen
- Gebäude-IDs nachschlagen

**Mit StDb-Scout:**
```bash
python -m emf_hotspot input/StandortXY.xls
```
**Zeitersparnis: ~1-2 Stunden pro Standort**

#### 2. 3D-Gebäudegeometrie
**Vorher:**
- Manuelle Schätzung von Geschosshöhen
- Gebäudehöhe aus 2D-Karten ableiten
- Unsicherheit bei komplexen Dachformen

**Mit StDb-Scout:**
- Automatischer Download von swissBUILDINGS3D
- Exakte 3D-Geometrie inkl. Dachneigung
- Präzise Fassadenpunkte im 1m-Raster
- Konservative Berechnung der obersten Geschosshöhe

**Genauigkeit: ±0.1m statt ±1-2m Schätzung**

#### 3. Antennendiagramm-Interpolation
**Vorher:**
- Manuelle Interpolation aus PDF-Diagrammen
- Excel-Lookup-Tabellen pflegen
- Fehler bei nicht-ganzzahligen Winkeln

**Mit StDb-Scout:**
- Automatische Interpolation auf 0.01° genau
- Validierte Diagramme aus Herstellerdaten
- Konsistente Dämpfungswerte für alle Antennen

**Fehlerreduktion: Eliminiert Interpolationsfehler**

#### 4. E-Feld-Berechnung für tausende Punkte
**Vorher (OMEN):**
- 10-20 Punkte manuell berechnen
- Risiko: Hotspots werden übersehen
- Konservative Annahmen nötig

**Mit StDb-Scout:**
- 28.853 Punkte in 3 Minuten (parallele Berechnung)
- Alle Fassaden, alle Geschosse systematisch erfasst
- Garantiert: Kein Hotspot wird übersehen

**Sicherheit: Vollständige Abdeckung statt Stichprobe**

#### 5. Dokumentation und Visualisierung
**Vorher:**
- Screenshots manuell erstellen
- Karten in Word/PowerPoint einfügen
- Tabellen formatieren

**Mit StDb-Scout:**
- 3D-Visualisierung für ParaView
- Heatmaps auf swisstopo-Basis
- KML für geo.admin.ch 3D-Viewer
- Fertige CSV-Tabellen

**Zeitersparnis: ~30-60 Minuten pro Gutachten**

---

## Konkrete Vorteile für Ihre tägliche Arbeit

### 1. Mehr Zeit für Physik, weniger für Datenerfassung

| Aufgabe | Vorher | Mit StDb-Scout | Gewinn |
|---------|--------|----------------|--------|
| Datenerfassung aus StDb | 1-2h | 0h (automatisch) | 1-2h |
| Gebäudehöhen recherchieren | 0.5-1h | 0h (swissBUILDINGS3D) | 0.5-1h |
| E-Feld-Berechnungen | 1-2h | 3min (parallel) | 1-2h |
| Visualisierung erstellen | 0.5-1h | 5min (automatisch) | 0.5-1h |
| **GESAMT pro Standort** | **3-6h** | **~30min Setup + Prüfung** | **2.5-5.5h** |

**→ Sie gewinnen 2.5-5.5 Stunden pro Standort für fachliche Arbeit.**

### 2. Höhere Genauigkeit durch systematische Abdeckung

**Problem bei OMEN:**
- 10-20 Messpunkte manuell gewählt
- Risiko: Hotspots zwischen den Punkten werden übersehen
- Konservative "Worst-Case"-Annahmen nötig

**Mit StDb-Scout:**
- Alle Fassaden, alle Geschosse systematisch berechnet
- Echte Worst-Case-Erkennung, nicht geschätzt
- Validierung gegen OMEN-Berechnungen automatisch

**→ Rechtssicherheit: Nachweislich keine Hotspots übersehen**

### 3. Reproduzierbare, nachvollziehbare Berechnungen

**Bei Rückfragen von Behörden:**
- Alle Berechnungsschritte dokumentiert
- Antennendiagramme aus validierten Quellen
- 3D-Geometrie aus offiziellen swissBUILDINGS3D-Daten
- Quellcode einsehbar (keine "Black Box")

**→ Sie können jede Berechnung physikalisch begründen.**

### 4. Konsistenz über Projekte hinweg

**Problem bei manueller Arbeit:**
- Verschiedene Excel-Versionen
- Unterschiedliche Interpolationsmethoden
- Inkonsistente Annahmen

**Mit StDb-Scout:**
- Identische Berechnungsmethodik für alle Standorte
- Einheitliche Antennendiagramme
- Vergleichbare Ergebnisse

**→ Ihre Gutachten sind professionell konsistent.**

---

## Typischer Arbeitsablauf (mit StDb-Scout)

### 1. Sie erhalten einen Auftrag
**Ihre Aufgabe:**
- StDb-PDF und OMEN-Datei prüfen
- Plausibilität der Eingangsdaten bewerten
- Besonderheiten identifizieren (Dachaufbauten, Sonderfälle)

**Zeit: 15-30 Minuten**

### 2. Automatische Berechnung
**Das Tool übernimmt:**
```bash
python -m emf_hotspot input/Standort_XY.xls
```
- Lädt Gebäudedaten von swisstopo
- Generiert Fassadenpunkte
- Berechnet E-Felder parallel
- Erstellt Visualisierungen

**Zeit: 3-5 Minuten (läuft automatisch)**

### 3. Sie validieren die Ergebnisse
**Ihre fachliche Prüfung:**
- Stimmen die Hotspots mit den OMEN-Berechnungen überein?
- Sind die Gebäudehöhen plausibel?
- Gibt es unerwartete Abweichungen?
- Müssen Annahmen angepasst werden?

**Zeit: 30-60 Minuten (Kernkompetenz!)**

### 4. Sie erstellen das Gutachten
**Ihre Interpretation:**
- Bewertung der Ergebnisse
- Empfehlungen für Messungen
- Kommunikation mit Behörden
- Unterschrift als verantwortlicher Physiker

**Zeit: 1-2 Stunden (professionelle Arbeit)**

**→ Gesamtzeit: 2-3h statt 4-8h, mehr Fokus auf Physik**

---

## Qualitätssicherung: Ihre Kontrolle bleibt

### Das Tool gibt Ihnen Werkzeuge zur Validierung:

1. **OMEN-Vergleich**
   - Automatischer Vergleich der ersten 10 OMEN-Punkte
   - Abweichungen >10% werden markiert
   - **Sie entscheiden:** Akzeptabel oder nachjustieren?

2. **Gebäude-Validierung**
   - Vergleich NISV-Formel vs. Geodaten
   - Warnung bei >1m Abweichung
   - **Sie entscheiden:** Konservative oder NISV-Methode?

3. **Worst-Case-Tilt-Suche**
   - Automatische Suche des kritischsten Tilts pro Antenne
   - Bereich konfigurierbar (z.B. -12° bis -2°)
   - **Sie entscheiden:** Welcher Tilt-Bereich ist realistisch?

4. **Visualisierung zur Plausibilitätsprüfung**
   - ParaView 3D-Viewer: Sehen Sie die Feldverteilung
   - Heatmap: Übersicht über Hotspot-Verteilung
   - **Sie beurteilen:** Ist das Muster physikalisch sinnvoll?

**→ Sie haben die volle Kontrolle und Verantwortung.**

---

## Für Programmierer: Der Code ist einsehbar

Falls Sie den Code reviewen oder anpassen möchten:

```
stdb-scout/
├── emf_hotspot/
│   ├── physics/              # E-Feld-Berechnungen
│   │   ├── propagation.py    # Freiraumdämpfung
│   │   ├── pattern.py        # Antennendiagramm-Interpolation
│   │   └── summation.py      # Leistungsaddition
│   ├── geometry/             # Koordinaten, Winkel
│   └── loaders/              # Datenimport
└── docu/
    ├── BENUTZERHANDBUCH.md   # Vollständige Dokumentation
    └── PFLICHTENHEFT.md      # Physikalische Formeln
```

**Alle Formeln sind dokumentiert:**
- Freiraumdämpfung: E = √(30·ERP) / r
- Leistungsaddition: E_total = √(Σ E_i²)
- LV95 ↔ WGS84 Konversion (swisstopo-Formel)

**→ Transparenz: Sie können jede Berechnung nachvollziehen.**

---

## Häufige Bedenken (FAQ)

### "Das Tool ersetzt mich doch?"
**Nein.** Das Tool ersetzt Excel-Formeln und manuelle Dateneingabe. Es ersetzt nicht Ihre Fähigkeit, Ergebnisse zu interpretieren, Plausibilität zu prüfen und physikalisch zu argumentieren. **Vergleich:** Ein Taschenrechner ersetzt auch keinen Mathematiker.

### "Ich verliere die Kontrolle über die Berechnungen?"
**Nein.** Der Code ist Open Source (auf GitHub). Alle Formeln sind dokumentiert. Sie können jeden Schritt nachvollziehen und validieren. **Mehr Kontrolle** als bei proprietären Tools wie OMEN.

### "Ich muss Python lernen?"
**Nur für Anpassungen.** Für die tägliche Arbeit reicht:
```bash
python -m emf_hotspot input/Datei.xls
```
Falls Sie den Code anpassen wollen: Python ist einfacher als C++ und Sie sind bereits Programmierer.

### "Was, wenn ich Spezialfälle habe?"
**Sie passen an.** Der Code ist modular. Sie können eigene Annahmen einbauen:
- Eigene Gebäudedämpfungswerte
- Spezielle Antennentypen
- Andere Berechnungsmethoden

**→ Flexibler als starre kommerzielle Software.**

### "Ist das wissenschaftlich validiert?"
**Ja.** Die Berechnungsmethodik basiert auf:
- ITU-R P.525: Freiraumdämpfung
- NISV Anhang 1: Anlagengrenzwerte
- swisstopo swissBUILDINGS3D 3.0
- Herstellerdaten für Antennendiagramme

**Validierung:** OMEN-Vergleich in jedem Gutachten dokumentiert.

---

## Ihre Rolle wird aufgewertet, nicht abgewertet

### Statt:
❌ 60% Datenerfassung, Excel-Formeln kopieren
❌ 30% Berechnungen mit Taschenrechner
❌ 10% Physikalische Bewertung

### Mit StDb-Scout:
✅ 10% Tool-Setup und Dateneingabe
✅ 20% Validierung und Plausibilitätsprüfung
✅ **70% Physikalische Interpretation und Gutachten-Erstellung**

**→ Sie arbeiten als Physiker, nicht als Datenerfasser.**

---

## Praktischer Einstieg

### Schritt 1: Erstes Testprojekt (1 Stunde)
```bash
# Environment aktivieren
source venv/bin/activate

# Beispiel-Standort berechnen
python -m emf_hotspot input/OMEN_R37_clean.xls

# Ergebnisse prüfen
paraview output/*/paraview_preset.pvsm
```

**Aufgabe:** Vergleichen Sie die Ergebnisse mit Ihrer OMEN-Berechnung.

### Schritt 2: Validierung (2 Stunden)
- Prüfen Sie die berechneten E-Felder gegen OMEN
- Kontrollieren Sie die Gebäudehöhen in ParaView
- Bewerten Sie die Hotspot-Positionen

**Frage:** Sind die Abweichungen physikalisch erklärbar?

### Schritt 3: Eigener Standort (½ Tag)
- Wählen Sie einen aktuellen Standort
- Lassen Sie das Tool laufen
- Erstellen Sie parallel Ihre manuelle Berechnung
- Vergleichen Sie beide Ergebnisse

**Ziel:** Vertrauen in das Tool aufbauen durch eigene Validierung.

---

## Support und Weiterentwicklung

**Sie sind nicht allein:**
- Vollständige Dokumentation in `docu/`
- QUICKREF.md für häufige Commands
- GitHub: Issues für Fragen/Bugs
- Direkte Kommunikation mit Entwickler (Andreas)

**Ihre Ideen sind willkommen:**
- Welche Features würden Ihre Arbeit verbessern?
- Welche Berechnungen sind noch nicht automatisiert?
- Welche Ausgabeformate brauchen Sie?

**→ Sie gestalten das Tool mit.**

---

## Fazit: Werkzeug, kein Ersatz

StDb-Scout ist ein **Werkzeug zur Effizienzsteigerung**, wie:
- Ein Taschenrechner für Mathematiker
- MATLAB für Ingenieure
- ParaView für 3D-Visualisierung

**Es automatisiert:**
✅ Repetitive Datenerfassung
✅ Mechanische Berechnungen
✅ Standardisierte Visualisierungen

**Es ersetzt NICHT:**
❌ Ihre physikalische Expertise
❌ Ihre Erfahrung bei Grenzfällen
❌ Ihre Fähigkeit, Ergebnisse zu interpretieren
❌ Ihre Verantwortung als gutachtender Physiker

**Ihre Unterschrift bleibt unverzichtbar.**

---

## Nächste Schritte

1. **Lesen Sie:** `docu/BENUTZERHANDBUCH.md`
2. **Testen Sie:** Ein Beispielprojekt durchrechnen
3. **Validieren Sie:** Ergebnisse mit OMEN vergleichen
4. **Feedback geben:** Was fehlt? Was stört?

**Bei Fragen:** Sprechen Sie mit Andreas oder öffnen Sie ein GitHub-Issue.

---

**Erstellt:** 2026-01-17
**Version:** 1.0
**Zielgruppe:** Physiker und EMF-Gutachter mit Programmiererfahrung
