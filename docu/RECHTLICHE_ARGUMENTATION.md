# Rechtliche Argumentation: Standard-Antennendiagramme

## Zusammenfassung

**Bei fehlenden herstellerspezifischen MSI-Files können ITU-R/3GPP Standard-Antennendiagramme für EMF-Berechnungen verwendet werden. Dies ist wissenschaftlich anerkannt und verschiebt die Beweislast auf Behörde/Betreiber.**

---

## 1. Rechtliche Grundlage

### 1.1 Öffentlichkeitsgesetz (BGÖ)

**Art. 6 Abs. 1 BGÖ**: Jede Person hat Anspruch auf Zugang zu amtlichen Dokumenten.

**Problem**: Kantonale Umweltämter verweigern MSI-Files mit Verweis auf "Betriebsgeheimnis" (Art. 7 BGÖ).

**Gegenargument**:
- Öffentliches Interesse an EMF-Transparenz überwiegt (Art. 7 Abs. 2 BGÖ)
- Technische Parameter (dB-Werte) sind keine Geschäftsgeheimnisse
- Präzedenz: Frankreich (ANFR), Deutschland (BNetzA) publizieren diese Daten

### 1.2 NISV (SR 814.710)

**Art. 4 NISV**: Anlagegrenzwerte (AGW) für Orte mit empfindlicher Nutzung (OMEN).

**Anhang 1 Nr. 64**: AGW = **5.0 V/m** (900 MHz)

**Problem**: OMEN-Berechnungen verwenden nicht-öffentliche Antennendiagramme.

**→ Fehlende Nachvollziehbarkeit behördlicher Berechnungen**

---

## 2. Wissenschaftliche Grundlage

### 2.1 Verwendete Standards (FINAL KORRIGIERT)

**WICHTIG**: 3GPP ist die primäre Quelle für Mobilfunk-Antennenmodelle. ITU übernimmt von 3GPP.

#### 3GPP TR 36.814 V9.2.0 (2017) - PRIMÄR
- **Titel**: "Further advancements for E-UTRA physical layer aspects"
- **Status**: Technischer Report der 3GPP (globales Standardisierungsgremium für Mobilfunk)
- **Inhalt**: **Section A.2.1.1: "3-sector cell antenna model"**
  - Exakte Formeln für Azimut und Elevation
  - A(φ) = -min[12(φ/φ₃dB)², Am]
  - A(θ) = -min[12((θ-θtilt)/θ₃dB)², SLAv]
- **Anwendung**: LTE/4G Basisstationen weltweit
- **Link**: https://portal.3gpp.org/desktopmodules/Specifications/SpecificationDetails.aspx?specificationId=2493

#### 3GPP TR 38.901 V17.0.0 (2022) - PRIMÄR
- **Titel**: "Study on channel model for frequencies from 0.5 to 100 GHz"
- **Status**: 5G NR Channel Model (Technical Report)
- **Inhalt**: **Table 7.3-1: "Antenna patterns"**
  - Detaillierte 5G Antennenmodelle
  - Inkl. Massive MIMO und Beamforming
- **Anwendung**: 5G NR Netze
- **Link**: https://portal.3gpp.org/desktopmodules/Specifications/SpecificationDetails.aspx?specificationId=3173

#### ITU-R M.2412-0 (2017) - SEKUNDÄR
- **Titel**: "Guidelines for evaluation of radio interface technologies for IMT-2020"
- **Status**: ITU-Empfehlung (verweist auf 3GPP!)
- **Inhalt**: Evaluation Guidelines (nutzt 3GPP TR 38.901 als Basis)
- **Link**: https://www.itu.int/rec/R-REC-M.2412/en
- **Hinweis**: ITU ist NICHT die primäre Quelle, sondern übernimmt von 3GPP

### 2.2 Anerkennung durch Regulierer

Diese Standards werden verwendet von:
- **ETSI** (Europa): Übernahme von 3GPP-Standards
- **FCC** (USA): Equipment Authorization basiert auf ITU-R
- **BAKOM** (Schweiz): Verweist auf ETSI-Standards (SR 784.101.1 Art. 4)

**→ Implizite Anerkennung durch CH-Regulierung**

### 2.3 Besonderheit: 5G-Antennen und Beamforming

#### Das 5G-Problem: Variable Abstrahldiagramme

Anders als 4G/LTE-Antennen haben **5G-Antennen KEIN festes Pattern**:

| Eigenschaft | 4G/LTE | 5G NR (Massive MIMO) |
|-------------|--------|----------------------|
| Antennenelemente | 2-8 | 64-256 |
| Abstrahlcharakteristik | Fest (3-Sektor) | Dynamisch (Beamforming) |
| Pattern | Konstant | Ändert sich in Echtzeit |
| Vorhersagbarkeit | ✓ Hoch | ✗ Gering |

#### 5G Beamforming erklärt:

**Massive MIMO** (Multiple Input Multiple Output):
- 64-256 Antennenelemente pro Sektor
- Jedes Element kann Phasen- und Amplituden-gesteuert werden
- **Resultat**: "Beam" (Strahlenbündel) kann elektronisch gelenkt werden

**Dynamisches Verhalten**:
```
Beispiel: Ericsson AIR 3268 im 5G-Modus
- 09:00 Uhr: 3 aktive Beams → Richtung A, B, C
- 09:01 Uhr: 8 aktive Beams → Richtung A, D, E, F, G, H, I, J
- 09:02 Uhr: 1 aktiver Beam → Richtung K (eng fokussiert)

→ Pattern ändert sich JEDE SEKUNDE abhängig von:
  - Anzahl aktiver Nutzer
  - Position der Nutzer
  - Netzauslastung
  - Scheduling-Algorithmus (Betriebsgeheimnis!)
```

#### Rechtliche Implikation:

**Problem für OMEN-Berechnungen**:
- OMEN werden mit **einem** festen Pattern berechnet
- 5G hat aber **unendlich viele** mögliche Patterns
- Welches Pattern wurde für OMEN verwendet?
  - Best-Case? (Beam zeigt weg vom OMEN)
  - Worst-Case? (Beam zeigt direkt auf OMEN)
  - Average-Case? (Statistische Mittelung über alle Beam-Konfigurationen?)

**→ OMEN-Berechnungen für 5G sind per Definition unvollständig!**

#### Rechtliche Strategie: Worst-Case-Nachweis

**Deine Position**:
1. Berechne mit **3GPP TR 36.814** (4G-Standard-Pattern, breit)
2. Alternativ: Mit **3GPP TR 38.901** (5G Narrow Beam, fokussiert)
3. Falls AGW-Überschreitung nachgewiesen → **gilt für mindestens eine Beam-Konfiguration**

**Gegenargument Behörde** (vorhersehbar):
> "In der Praxis wird der Beam nicht dauerhaft auf diesen Punkt zeigen."

**Deine Erwiderung**:
> "Nach NISV Art. 4 gilt der AGW für **OMEN** (Orte mit empfindlicher Nutzung).
> Diese müssen **jederzeit** geschützt sein, nicht nur 'im Durchschnitt'.
>
> Falls der Beam auch nur **temporär** (z.B. 10 Sekunden pro Stunde) auf das
> OMEN zeigt und dabei AGW überschreitet → NISV-Verletzung.
>
> **Beweislast**: Behörde/Betreiber muss nachweisen, dass **ALLE möglichen
> Beam-Konfigurationen** den AGW einhalten. Dazu erforderlich:
> - Vorlage aller MSI-Files (alle Beam-Steering-Winkel)
> - Statistische Nutzungsdaten (Beam-Aktivierungswahrscheinlichkeit)
> - Worst-Case-Analyse über alle Konfigurationen
>
> Ohne diese Nachweise gilt meine Berechnung als Beweis der Möglichkeit
> einer AGW-Überschreitung."

#### 3GPP TR 38.901 - 5G Narrow Beam (optional)

Falls du technisch präziser argumentieren willst:

**5G Narrow Beam Charakteristik** (3GPP TR 38.901 Table 7.3-1):
- Azimut: 33° Beamwidth (vs. 65° bei 4G)
- Elevation: 5° Beamwidth (vs. 7° bei 4G)
- **Beamforming-Gewinn**: +3 bis +10 dB (je nach Antennen-Array)

**Konsequenz**:
- **Engerer Beam** = höhere Leistungsdichte im Beam
- Falls Beam auf OMEN zeigt → **HÖHERE Immissionen als mit 4G-Pattern!**

**Formulierung im Gutachten**:
```markdown
Für 5G-Antennen wurden zwei Szenarien berechnet:

**Szenario A (konservativ)**: 3GPP TR 36.814 (4G-Pattern, breit)
→ E-Feld am OMEN: 6.2 V/m (AGW-Überschreitung)

**Szenario B (5G Narrow Beam)**: 3GPP TR 38.901 (33°/5° Beam)
→ E-Feld am OMEN: 8.5 V/m (höhere Überschreitung!)

Beide Szenarien zeigen AGW-Überschreitung. Die tatsächliche Immission
hängt von der Beam-Konfiguration ab, die sich dynamisch ändert.

Beweislast: Behörde muss nachweisen, dass keine Beam-Konfiguration
existiert, die AGW überschreitet.
```

#### Präzedenzfall-Argumentation

**Vergleich mit anderen Umwelt-Grenzwerten**:

**Lärmschutz** (LSV):
- Grenzwerte gelten für **Maximalpegel**, nicht Durchschnitt
- Auch kurzzeitige Überschreitungen sind relevant

**Luftreinhaltung** (LRV):
- Immissionsgrenzwerte gelten **jederzeit**
- Nicht nur im Jahresmittel

**NISV** (Analogie):
- AGW gilt für OMEN **jederzeit**
- Nicht nur "im Durchschnitt über alle Beam-Konfigurationen"
- **Jede mögliche Beam-Konfiguration muss AGW einhalten**

#### Zusammenfassung: 5G-Strategie

**Für dein Gutachten (EMPFOHLEN)**:
1. Nutze 3GPP TR 36.814 (4G-Pattern) auch für 5G
2. Argumentiere: "Konservativer Worst-Case"
3. Falls Behörde bestreitet: Beweislast für **ALLE** Beam-Konfigurationen

**Vorteil**:
- Einfach zu argumentieren
- Rechtlich robust
- Beweislast klar beim Betreiber
- Betreiber kann sich nicht mit "durchschnittlicher Nutzung" rausreden

**Alternativ (technisch präziser)**:
1. Berechne beide Szenarien (4G-Pattern UND 5G Narrow Beam)
2. Zeige dass BEIDE AGW überschreiten
3. Argumentiere: "Unabhängig vom Szenario problematisch"

**Was du NICHT tun solltest**:
- ✗ Auf Betreiber-Aussagen "Beam zeigt meist nicht auf OMEN" eingehen
- ✗ Statistische Durchschnittsbetrachtungen akzeptieren
- ✗ Ohne MSI-Files für alle Beam-Winkel auf Betreiber-Berechnungen vertrauen

---

## 3. Konservativität der Standard-Patterns

### 3.1 Vergleich: Standard vs. Herstellerdaten

Typisches 3-Sektor-Antennen-Pattern (65° Beamwidth):

| Winkel | ITU-R Standard | Typisches reales Pattern | Konservativität |
|--------|----------------|---------------------------|-----------------|
| 0°     | 0 dB           | 0 dB                      | Gleich          |
| 30°    | 2.6 dB         | 1-3 dB                    | Ähnlich         |
| 60°    | 10.2 dB        | 6-12 dB                   | Konservativ     |
| 90°    | 23.0 dB        | 14-25 dB                  | Konservativ     |
| 180°   | 25.0 dB        | 20-30 dB                  | Konservativ     |

**Konservativ bedeutet**: Standard-Pattern hat **WENIGER** Dämpfung als reale Antennen.

**Konsequenz**:
- Berechnete E-Felder mit Standard-Patterns sind tendenziell **HÖHER**
- Falls mit Standard-Pattern **keine** AGW-Überschreitung → sicher
- Falls mit Standard-Pattern **AGW-Überschreitung** → mit realen Patterns **wahrscheinlich auch** (oder höher)

### 3.2 Adaptive Antennen (AIR3268, AAU)

**Problem**: Adaptive Antennen haben **kein festes Pattern**.

**Worst-Case-Annahme**:
- Nutze Standard-Pattern für 3-Sektor-Antenne
- **Ignoriere** Beamforming-Gewinn (konservativ)
- **Falls** Beamforming genutzt wird → höhere Leistungsdichte im Beam

**Rechtliche Implikation**:
- Betreiber kann nicht argumentieren "adaptive Antenne hat besseres Pattern"
- Beweislast: Betreiber muss nachweisen, dass **alle** möglichen Beam-Konfigurationen unter AGW bleiben

---

## 4. Beweislastverteilung

### 4.1 Ausgangslage

**Normale Beweislast**:
- Beschwerdeführer muss NISV-Verletzung nachweisen (Art. 8 ZGB)

**Problem**:
- MSI-Files sind nicht öffentlich
- Ohne MSI-Files keine präzise Berechnung möglich

### 4.2 Beweislastumkehr via Standard-Patterns

**Schritt 1**: Beschwerdeführer berechnet mit ITU-R/3GPP Standard-Patterns

**Ergebnis**: AGW-Überschreitung nachgewiesen (z.B. 6.2 V/m an Position XY)

**Schritt 2**: Betreiber/Behörde bestreitet

**Argumentation Behörde**: "Echtes Pattern hat mehr Dämpfung, kein AGW-Überschreitung"

**Schritt 3**: Beweislastumkehr

**Beschwerdeführer**:
> "Ich habe mit international anerkannten Standards (3GPP TR 36.814, 3GPP TR 38.901)
> eine AGW-Überschreitung nachgewiesen. Diese Standards sind wissenschaftlich peer-reviewed
> und werden von ETSI/BAKOM anerkannt.
>
> Falls die Behörde/Betreiber behauptet, das echte Pattern weiche ab:
> **Obliegenheit zur Vorlage der MSI-Files** (Art. 8 ZGB analog).
>
> Andernfalls: Meine Berechnung gilt als Beweis."

### 4.3 Präzedenzfälle (analog)

**Umweltrecht - Beweislastumkehr**:
- BGE 119 Ib 480: Bei Umweltgefährdung genügt Glaubhaftmachung
- Behörde muss widerlegen (Vorsorgeprinzip)

**Baurecht - Fachgutachten**:
- Anerkannte Standards = Prima-facie-Beweis
- Behörde muss mit gleichwertigem Gegengutachten widerlegen

---

## 5. Formulierung im Gutachten

### 5.1 Methodenteil

```markdown
## Methodik - Antennendiagramme

Für die Berechnung der EMF-Immissionen wurden Antennendiagramme benötigt.

### MSI-Files (herstellerspezifisch)
Eine BGÖ-Anfrage beim Kantonalen Umweltamt [Datum] wurde mit Verweis auf
"Betriebsgeheimnis" abgelehnt (Schreiben vom [Datum], Beilage X).

### Standard-Antennendiagramme (3GPP)
In Ermangelung herstellerspezifischer Daten wurden international anerkannte
Standard-Antennendiagramme verwendet:

- **3GPP TR 36.814 V9.2.0 (2017)**: "Further advancements for E-UTRA physical layer aspects"
  - Section A.2.1.1: "3-sector cell antenna model"
  - Definiert exakte Formeln für 3-Sektor-Antennen (LTE/4G)
  - Beamwidth: 65° horizontal (Azimut), 7° vertikal (Elevation)
  - Von ETSI übernommen und weltweit für LTE-Netze verwendet

Diese Standards sind:
1. Wissenschaftlich peer-reviewed
2. Von Telekom-Regulierern weltweit akzeptiert
3. Tendenziell konservativ (weniger Dämpfung als reale Antennen)

### Rechtliche Qualifizierung
Die Verwendung dieser Standards ist zulässig und wissenschaftlich anerkannt.
Falls die Behörde/Betreiber abweichende (bessere) Patterns geltend macht,
obliegt ihr die Beweislast durch Vorlage der MSI-Files.
```

### 5.2 Ergebnisteil

```markdown
## Ergebnisse

### Hotspot-Analyse
Mit den ITU-R/3GPP Standard-Antennendiagrammen wurden folgende potenzielle
AGW-Überschreitungen identifiziert:

| Position | LV95 Koordinaten | E-Feld [V/m] | AGW [V/m] | Überschreitung |
|----------|------------------|--------------|-----------|----------------|
| Fassade Gebäude A | 2681050 / 1252270 | **6.2** | 5.0 | +24% |
| Dach Gebäude B    | 2681045 / 1252265 | **5.8** | 5.0 | +16% |

**Wichtig**: Diese Berechnungen verwenden **konservative** Standard-Patterns.
Reale Antennendiagramme könnten abweichen.

Falls Behörde/Betreiber bestreitet:
→ Vorlage der echten MSI-Files erforderlich zum Nachweis niedrigerer Immissionen.
```

### 5.3 Schlussfolgerungen

```markdown
## Schlussfolgerungen

1. **AGW-Überschreitungen nachgewiesen**:
   Mit international anerkannten Standard-Antennendiagrammen (3GPP TR 36.814, 3GPP TR 38.901)
   wurden an 2 Positionen AGW-Überschreitungen berechnet.

2. **Beweislast bei Behörde/Betreiber**:
   Falls die berechneten Werte bestritten werden, obliegt es der Behörde/Betreiber,
   mittels herstellerspezifischer MSI-Files niedrigere Immissionen nachzuweisen.

3. **BGÖ-Verweigerung rechtswidrig**:
   Die Verweigerung der MSI-Files verhindert die Nachvollziehbarkeit behördlicher
   OMEN-Berechnungen und verletzt Art. 6 BGÖ. Das öffentliche Interesse an EMF-
   Transparenz überwiegt allfällige Betriebsgeheimnisse (Art. 7 Abs. 2 BGÖ).

4. **Empfehlung**:
   - Verwaltungsbeschwerde gegen BGÖ-Verweigerung (an EDÖB)
   - Forderung nach Offenlegung der MSI-Files im Baubewilligungsverfahren
   - Verwaltungsgerichtliche Überprüfung der OMEN-Berechnungen
```

---

## 6. Verfahrensstrategie

### 6.1 Reihenfolge

1. **BGÖ-Anfrage** (BAKOM, kantonales Umweltamt)
   - Dokumentiere Verweigerung

2. **Hotspot-Berechnung** mit Standard-Patterns
   - Technisches Gutachten erstellen

3. **Einsprache/Beschwerde** im Baubewilligungsverfahren
   - "AGW-Überschreitungen nachgewiesen (mit ITU-R Standards)"
   - "Behörde muss widerlegen → MSI-Files vorlegen"

4. **Verwaltungsbeschwerde** (parallel)
   - Gegen BGÖ-Verweigerung (an EDÖB)

5. **Verwaltungsgericht**
   - Falls Behörde weiterhin MSI-Files verweigert
   - Beweiserhebung: Gericht kann MSI-Files anfordern

### 6.2 Risiken

**Risiko 1**: Gericht akzeptiert "Betriebsgeheimnis"
- **Gegenargument**: Öffentliches Interesse überwiegt (BGÖ Art. 7 Abs. 2)

**Risiko 2**: Behörde liefert MSI-Files → zeigen geringere Immissionen
- **Vorteil**: Du hast die Daten bekommen! (Ziel erreicht)
- **Folge**: Neu berechnen mit echten Patterns

**Risiko 3**: Gericht verlangt "Gegengutachten"
- **Lösung**: ITU-R/3GPP Standards **sind** das Gegengutachten (international anerkannt)

---

## 7. Checkliste für Gutachten

- [ ] BGÖ-Anfrage dokumentiert (mit Ablehnungsschreiben)
- [ ] 3GPP Standards korrekt zitiert (TR 36.814, TR 38.901)
- [ ] Konservativität der Standards erklärt
- [ ] Berechnungsmethodik transparent (Python-Code als Anhang)
- [ ] Hotspots mit Koordinaten dokumentiert
- [ ] Beweislastumkehr argumentiert
- [ ] Alternative Szenarien berechnet (worst-case, typical)
- [ ] Visualisierung (Heatmap, 3D-Plot)

---

## 8. Formulierungsbeispiele

### Defensiv (für Behörde):
> "Mangels Zugang zu herstellerspezifischen MSI-Files wurden wissenschaftlich anerkannte
> Standard-Antennendiagramme (3GPP TR 36.814) verwendet. Diese sind tendenziell konservativ."

### Offensiv (für Beschwerde):
> "Die Verweigerung der MSI-Files durch das Umweltamt verletzt Art. 6 BGÖ und verhindert
> die Nachvollziehbarkeit der OMEN-Berechnungen. Mit international anerkannten Standards
> wurden AGW-Überschreitungen nachgewiesen. Die Beweislast für abweichende (bessere)
> Patterns liegt bei der Behörde."

### Kompromiss (für Verhandlung):
> "Zur Klärung der tatsächlichen EMF-Immissionen schlagen wir vor: Das Umweltamt gibt
> die MSI-Files unter Geheimhaltungsvereinbarung an einen neutralen Gutachter heraus.
> Dieser berechnet die E-Felder und gibt nur die Ergebnisse (ohne MSI-Details) bekannt."

---

**Fazit**: Mit ITU-R/3GPP Standard-Patterns hast du ein **gerichtsfestes Werkzeug**,
um AGW-Überschreitungen nachzuweisen und die Beweislast umzukehren.
