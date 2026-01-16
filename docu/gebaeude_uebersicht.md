# Dokumentation: gebaeude_uebersicht.csv

## Übersicht

Die Datei `gebaeude_uebersicht.csv` enthält eine umfassende Zusammenstellung aller Gebäudeinformationen, Hotspot-Statistiken und NISV-Validierungsergebnisse.

**Anzahl Spalten**: 26
**Format**: UTF-8, Komma-separiert
**Erzeugt von**: `export_buildings_overview_csv()` in `emf_hotspot/output/csv_export.py`

---

## Spalten-Definitionen

### 1. Identifikation

#### `building_id`
- **Typ**: String (UUID)
- **Quelle**: swissBUILDINGS3D CityGML (`gml:id`)
- **Beschreibung**: Eindeutiger Identifier des Gebäudes aus der swissBUILDINGS3D-Datenbank
- **Beispiel**: `ID_20A451C2-3ACF-462A-92BD-9631EE7BAE36`
- **Verwendung**: Technische Referenz, wird für interne Zuordnungen verwendet

#### `egid`
- **Typ**: Integer
- **Quelle**: swissBUILDINGS3D CityGML (`gen:intAttribute name="EGID"`)
- **Beschreibung**: Eidgenössischer Gebäudeidentifikator - offizieller Schweizer Gebäudeschlüssel
- **Beispiel**: `502153548`
- **Verwendung**: Offizielle Referenz, ermöglicht Verknüpfung mit anderen Schweizer Geodaten
- **Besonderheit**: Leer bei Gebäuden ohne EGID (z.B. Nebengebäude, Garagen)

#### `address`
- **Typ**: String
- **Quelle**: geo.admin.ch API (via EGID oder Koordinaten)
- **Beschreibung**: Vollständige Gebäudeadresse
- **Format**: `"Strassenname Hausnummer, PLZ Ort"`
- **Beispiel**: `"Burgerrietstrasse 19, Uznach"`
- **Lookup-Strategie**:
  1. Primär: EGID-basierter Lookup über `ch.bfs.gebaeude_wohnungs_register`
  2. Fallback: Koordinaten-basierter Lookup über MapServer identify API
- **Besonderheit**: Leer wenn weder EGID noch Koordinaten-Lookup erfolgreich

#### `omen_nr`
- **Typ**: String
- **Format**: `"O1"`, `"O2"`, ... oder leer
- **Quelle**: OMEN-Excel-Datei, zugeordnet über räumliche Nähe
- **Beschreibung**: OMEN-Nummer (Ort mit empfindlicher Nutzung) falls dieses Gebäude ein OMEN-Gebäude ist
- **Zuordnungskriterium**: Gebäude mit geringstem Abstand zum OMEN-Punkt (< 50m)
- **Verwendung**: Identifikation von Gebäuden mit bekannten Messpunkten aus dem Standortdatenblatt
- **Besonderheit**: Leer für alle Nicht-OMEN-Gebäude

---

### 2. Geometrie

#### `min_z`
- **Typ**: Float
- **Einheit**: Meter über Meer [m ü.M.]
- **Quelle**: Berechnet aus allen Fassadenpunkten des Gebäudes
- **Beschreibung**: Niedrigster Z-Wert (Höhe) aller berechneten Punkte
- **Interpretation**: Ungefähre Geländehöhe / Sockelhöhe des Gebäudes
- **Beispiel**: `405.00`
- **Genauigkeit**: ±0.5m (Auflösung der Fassaden-Sampling)

#### `max_z`
- **Typ**: Float
- **Einheit**: Meter über Meer [m ü.M.]
- **Quelle**: Berechnet aus allen Fassadenpunkten des Gebäudes
- **Beschreibung**: Höchster Z-Wert (Höhe) aller berechneten Punkte
- **Interpretation**: Oberkante der höchsten Fassade / Dachansatz
- **Beispiel**: `413.71`
- **Besonderheit**: Entspricht **nicht** der Firsthöhe, sondern der Traufhöhe (Dachunterkante)

#### `height_m`
- **Typ**: Float
- **Einheit**: Meter [m]
- **Formel**: `height_m = max_z - min_z`
- **Beschreibung**: Gebäudehöhe vom niedrigsten bis zum höchsten Punkt
- **Beispiel**: `8.71`
- **Verwendung**: Basis für Geschosszahl-Schätzung
- **Interpretation**:
  - 6-9m: 2-3 Geschosse (typisches Einfamilienhaus)
  - 9-12m: 3-4 Geschosse (kleines Mehrfamilienhaus)
  - >12m: 4+ Geschosse (größeres Mehrfamilienhaus)

#### `num_floors`
- **Typ**: Integer
- **Formel**: `num_floors = max(1, int(height_m / 3.0))`
- **Beschreibung**: Geschätzte Geschosszahl basierend auf Gebäudehöhe
- **Annahme**: 3.0m pro Geschoss (grobe Schätzung)
- **Beispiel**: `2` (bei 8.71m Höhe)
- **Verwendung**: Schnelle Übersicht über Gebäudegröße
- **Limitation**: Berücksichtigt keine Variationen in Geschosshöhen

#### `estimated_floors`
- **Typ**: Integer
- **Quelle**: `building_validation.py`
- **Formel**: `estimated_floors = max(1, round(height_m / 3.0))`
- **Beschreibung**: Geschätzte Geschosszahl für NISV-Formel (präziser als `num_floors`)
- **Beispiel**: `3`
- **Besonderheit**: Leer bei Gebäuden ohne BuildingAnalysis-Daten

#### `real_floor_height_m`
- **Typ**: Float
- **Einheit**: Meter [m]
- **Formel**: `real_floor_height_m = height_m / estimated_floors`
- **Beschreibung**: Tatsächliche durchschnittliche Geschosshöhe basierend auf Geodaten
- **Beispiel**: `3.01`
- **Interpretation**:
  - 2.5-3.0m: Normale Raumhöhe (Neubau)
  - 3.0-3.5m: Hohe Räume (Altbau, gehobener Wohnungsbau)
  - >3.5m: Sehr hohe Räume (Industriehalle, Gewerbe, Altbau)
- **Verwendung**: Prüfung ob NISV-Standardformel (2.90m) anwendbar ist

---

### 3. Hotspot-Statistik

#### `num_points`
- **Typ**: Integer
- **Beschreibung**: Anzahl berechneter Punkte auf allen Fassaden dieses Gebäudes
- **Auflösung**: 0.5m Raster (default)
- **Beispiel**: `2839`
- **Interpretation**:
  - Je mehr Punkte, desto größer die Fassadenfläche
  - Dichte Bebauung → viele Gebäude mit wenigen Punkten
  - Freistehendes Gebäude → mehr exponierte Fassadenfläche

#### `num_hotspots`
- **Typ**: Integer
- **Beschreibung**: Anzahl Punkte mit E-Feldstärke ≥ AGW (5.0 V/m)
- **Beispiel**: `0` (kein Hotspot) oder `469` (viele Hotspots)
- **Interpretation**:
  - 0: AGW eingehalten, keine Maßnahmen nötig
  - 1-10: Lokale Überschreitungen, ggf. Einzelmaßnahmen
  - >10: Flächige Überschreitungen, strukturelle Maßnahmen empfohlen
- **Verwendung**: Schnelle Identifikation problematischer Gebäude

#### `max_e_vm`
- **Typ**: Float
- **Einheit**: Volt pro Meter [V/m]
- **Beschreibung**: Maximale E-Feldstärke aller Punkte auf diesem Gebäude
- **Beispiel**: `4.7948` (unter AGW) oder `5.2419` (über AGW)
- **Grenzwert**: 5.0 V/m (AGW für Orte mit empfindlicher Nutzung, NISV Anhang 1 Ziff. 13)
- **Interpretation**:
  - <3 V/m: Unbedenklich
  - 3-5 V/m: Nahe am Grenzwert, Monitoring empfohlen
  - 5-6 V/m: Leichte Überschreitung
  - >6 V/m: Deutliche Überschreitung, Maßnahmen erforderlich

#### `avg_e_vm`
- **Typ**: Float
- **Einheit**: Volt pro Meter [V/m]
- **Beschreibung**: Durchschnittliche E-Feldstärke aller Punkte auf diesem Gebäude
- **Beispiel**: `2.6939`
- **Verwendung**:
  - Indikator für generelle Exposition
  - Unterscheidung zwischen lokalen Hotspots vs. flächiger Belastung
  - Niedrige avg_e bei hoher max_e → punktueller Hotspot
  - Hohe avg_e → flächige Exposition

---

### 4. NISV-Validierung

#### `z_top_floor_nisv`
- **Typ**: Float
- **Einheit**: Meter über Meer [m ü.M.]
- **Quelle**: `building_validation.py`
- **Formel**: `z_nisv = min_z + 1.0m + (estimated_floors - 1) × 2.90m + 1.50m`
- **Beschreibung**: Z-Position des obersten Messpunkts nach NISV-Standardformel (von unten nach oben)
- **Komponenten**:
  - `min_z`: Geländehöhe
  - `1.0m`: Erdgeschoss über Gelände
  - `(floors-1) × 2.90m`: Stockwerke (2.90m pro Geschoss)
  - `1.50m`: Messhöhe (Bauchhöhe)
- **Beispiel**: `413.05`
- **Verwendung**: Vergleich mit OMEN-Sheets und realen Geodaten
- **Limitation**: Unterschätzt Höhe bei Gebäuden mit >2.90m Geschosshöhe

#### `z_top_floor_conservative`
- **Typ**: Float
- **Einheit**: Meter über Meer [m ü.M.]
- **Quelle**: `building_validation.py`
- **Formel**: `z_conservative = max_z - (2.90m - 1.80m) = max_z - 1.10m`
- **Beschreibung**: Z-Position des obersten Messpunkts nach konservativer Methode (von oben nach unten)
- **Komponenten**:
  - `max_z`: Dachunterkante aus Geodaten
  - `1.10m`: Abstand von Decke zu Kopfhöhe (2.90m - 1.80m)
  - `1.80m`: Messhöhe für 1.90m große Person (Kopfhöhe statt Bauchhöhe)
- **Beispiel**: `412.69`
- **Vorteile**:
  - Nutzt reale Gebäudehöhe aus Geodaten
  - Berücksichtigt variable Geschosshöhen
  - Konservativer (Kopfhöhe statt Bauchhöhe)
  - Unabhängig von Geschosszahl-Schätzung
- **Empfehlung**: Bei Altbauten und hohen Räumen bevorzugen

---

### 5. OMEN-Vergleich

**Diese Felder sind nur bei OMEN-Gebäuden gefüllt** (wo `omen_nr` nicht leer ist).

#### `omen_floors`
- **Typ**: Integer
- **Quelle**: Rückgerechnet aus OMEN-Z-Position
- **Formel**: `omen_floors = round((omen_z_given - min_z - 1.0 - 1.50) / 2.90) + 1`
- **Beschreibung**: Geschosszahl wie sie im OMEN-Sheet implizit angenommen wurde
- **Beispiel**: `5`
- **Verwendung**: Prüfung ob OMEN-Sheet alle Geschosse berücksichtigt hat
- **Besonderheit**: Kann von realer Geschosszahl abweichen → `missing_floors`

#### `omen_z_given`
- **Typ**: Float
- **Einheit**: Meter über Meer [m ü.M.]
- **Quelle**: OMEN-Excel-Datei
- **Beschreibung**: Im Standortdatenblatt angegebene Z-Position des OMEN-Messpunkts
- **Beispiel**: `409.58`
- **Verwendung**: Referenzwert für Validierung der Berechnungsmethoden
- **Besonderheit**: Vom Gutachter festgelegt, kann Fehler enthalten

#### `omen_z_nisv`
- **Typ**: Float
- **Einheit**: Meter über Meer [m ü.M.]
- **Beschreibung**: Was die NISV-Formel für diesen OMEN-Punkt berechnen würde
- **Beispiel**: `408.45`
- **Verwendung**: Zeigt Abweichung zwischen OMEN-Sheet und NISV-Standardformel

#### `omen_z_conservative`
- **Typ**: Float
- **Einheit**: Meter über Meer [m ü.M.]
- **Beschreibung**: Was die konservative Methode für diesen OMEN-Punkt berechnen würde
- **Beispiel**: `415.46`
- **Verwendung**: Zeigt wie viel höher ein konservativer Ansatz rechnet

#### `missing_floors`
- **Typ**: Integer
- **Formel**: `missing_floors = estimated_floors - omen_floors`
- **Beschreibung**: Anzahl Geschosse die im OMEN-Sheet nicht berücksichtigt wurden
- **Beispiel**: `0` (alle erfasst) oder `1` (ein Geschoss fehlt)
- **Interpretation**:
  - `0`: OMEN-Sheet hat alle Geschosse berücksichtigt ✓
  - `>0`: Geschosse fehlen → höhere Messpunkte wurden nicht geprüft ⚠️
  - `<0`: OMEN rechnet mit mehr Geschossen als geodätisch sichtbar (selten)
- **Konsequenz bei >0**: Zusätzliche Messungen auf fehlendem Geschoss empfohlen

#### `z_deviation_nisv`
- **Typ**: Float
- **Einheit**: Meter [m]
- **Formel**: `z_deviation_nisv = omen_z_nisv - omen_z_given`
- **Beschreibung**: Abweichung zwischen NISV-Formel und OMEN-Sheet-Angabe
- **Beispiel**: `1.20` (NISV rechnet 1.2m höher) oder `-0.50` (NISV rechnet 0.5m tiefer)
- **Interpretation**:
  - `< 0.5m`: Gute Übereinstimmung ✓
  - `0.5-1.0m`: Moderate Abweichung
  - `> 1.0m`: Signifikante Abweichung, Ursache prüfen ⚠️
- **Verwendung**: Qualitätskontrolle der OMEN-Sheet-Berechnungen

#### `z_deviation_conservative`
- **Typ**: Float
- **Einheit**: Meter [m]
- **Formel**: `z_deviation_conservative = z_top_floor_conservative - omen_z_given`
- **Beschreibung**: Abweichung zwischen konservativer Methode und OMEN-Sheet
- **Beispiel**: `5.9` (konservativ rechnet 5.9m höher!)
- **Interpretation**:
  - `< 1.0m`: OMEN-Sheet ist ausreichend konservativ ✓
  - `1.0-3.0m`: Moderate Unterschätzung, höhere E-Felder möglich
  - `> 3.0m`: OMEN-Sheet unterschätzt Höhe deutlich, kritisch! ⚠️
- **Konsequenz bei >3m**: Nachmessung auf tatsächlich oberstem Geschoss dringend empfohlen
- **Ursachen**:
  - Hohe Geschosshöhen (Altbau)
  - Fehlende Geschosse im OMEN-Sheet
  - Dachgeschoss nicht berücksichtigt

---

### 6. Warnungen

#### `has_high_ceilings`
- **Typ**: Boolean (`True`/`False` oder `Ja`/`Nein`)
- **Kriterium**: `real_floor_height_m > 3.2m`
- **Beschreibung**: Kennzeichnung von Gebäuden mit überdurchschnittlich hohen Räumen
- **Beispiel**: `False` (normale Höhe) oder `True` (hohe Räume)
- **Schwellwert**: 3.2m (10% über NISV-Standard von 2.90m)
- **Ursachen**:
  - Altbau mit hohen Stuckdecken
  - Industriehalle / Gewerbebau
  - Loft-Wohnungen
  - Repräsentative Bauten
- **Konsequenz**: NISV-Standardformel unterschätzt Höhe → oberste Messpunkte zu tief

#### `ceiling_warning`
- **Typ**: String (leer oder Warntext)
- **Beschreibung**: Detaillierte Warnung wenn `has_high_ceilings = True`
- **Format**: `"Hohe Räume: X.XXm/Geschoss (NISV: 2.90m). NISV-Formel unterschätzt Höhe um Y.Ym!"`
- **Beispiel**: `"Hohe Räume: 3.26m/Geschoss (NISV: 2.90m). NISV-Formel unterschätzt Höhe um 2.5m!"`
- **Komponenten**:
  - Tatsächliche Geschosshöhe
  - NISV-Referenz (2.90m)
  - Totale Höhendifferenz über alle Geschosse
- **Verwendung**: Gutachter-Hinweis für Anpassung der Formel

#### `recommendation`
- **Typ**: String
- **Beschreibung**: Zusammenfassende Handlungsempfehlung basierend auf allen Validierungsergebnissen
- **Mögliche Werte**:
  - `"✓ OK"`: Keine Auffälligkeiten
  - `"⚠️ Hohe Decken: NISV-Formel prüfen! "`: Geschosshöhen überprüfen
  - `"⚠️ X Geschoss(e) fehlen in OMEN! "`: Zusätzliche Geschosse nachprüfen
  - `"⚠️ Konservativ X.Xm höher als OMEN-Z! "`: OMEN-Höhe unterschätzt
  - `"(NISV weicht X.Xm ab) "`: NISV-Formel weicht ab
- **Kombination möglich**: Mehrere Warnungen können kombiniert auftreten
- **Beispiel**: `"⚠️ Hohe Decken: NISV-Formel prüfen! ⚠️ 1 Geschoss(e) fehlen in OMEN! ⚠️ Konservativ 2.5m höher als OMEN-Z!"`
- **Schwellwerte**:
  - Hohe Decken: `real_floor_height_m > 3.2m`
  - Fehlende Geschosse: `missing_floors > 0`
  - Z-Abweichung: `|z_deviation_conservative| > 1.0m`

---

## Verwendungsbeispiele

### Beispiel 1: Unbedenkliches Gebäude

```csv
building_id,egid,address,omen_nr,min_z,max_z,height_m,num_floors,estimated_floors,real_floor_height_m,num_points,num_hotspots,max_e_vm,avg_e_vm,z_top_floor_nisv,z_top_floor_conservative,omen_floors,omen_z_given,omen_z_nisv,omen_z_conservative,missing_floors,z_deviation_nisv,z_deviation_conservative,has_high_ceilings,ceiling_warning,recommendation
ID_20A451C2...,502153548,"Burgerrietstrasse 19, Uznach",,405.00,413.71,8.71,2,3,3.01,2839,0,4.7948,2.6939,413.05,412.69,,,,,0,0.00,0.00,False,,✓ OK
```

**Interpretation**:
- Normales Gebäude, 3 Geschosse, 8.71m hoch
- Keine Hotspots (max_e_vm = 4.79 < 5.0 V/m)
- Normale Geschosshöhe (3.01m)
- Keine Warnungen

### Beispiel 2: OMEN-Gebäude mit Problemen

```csv
ID_C4E421F8...,190541368,"Hauptstrasse 5, Stadt",O10,404.50,415.80,11.30,3,4,3.26,5421,15,5.82,4.21,412.90,414.70,3,409.58,412.45,415.46,1,2.87,5.88,True,"Hohe Räume: 3.26m/Geschoss (NISV: 2.90m). NISV-Formel unterschätzt Höhe um 1.4m!","⚠️ Hohe Decken: NISV-Formel prüfen! ⚠️ 1 Geschoss(e) fehlen in OMEN! ⚠️ Konservativ 5.9m höher als OMEN-Z!"
```

**Interpretation**:
- OMEN O10 mit kritischen Befunden
- 15 Hotspots, max E-Feld 5.82 V/m (über AGW!)
- Hohe Räume: 3.26m pro Geschoss (Altbau)
- 1 fehlendes Geschoss im OMEN-Sheet
- Konservative Methode zeigt 5.9m höheren Messpunkt
- **Handlung erforderlich**: Nachmessung auf oberstem Geschoss!

### Beispiel 3: Gebäude ohne EGID

```csv
ID_7A3B9E12...,,"",3,408.20,412.50,4.30,1,1,4.30,842,0,3.21,2.15,411.60,411.40,,,,,0,0.00,0.00,False,,✓ OK
```

**Interpretation**:
- Kein EGID → wahrscheinlich Nebengebäude, Garage
- Keine Adresse verfügbar
- Kleine Struktur, 1 Geschoss, 4.30m hoch
- Keine Hotspots, unbedenklich

---

## Datenqualität und Einschränkungen

### Datenquellen

| Datenfeld | Quelle | Qualität | Update-Zyklus |
|-----------|--------|----------|---------------|
| `building_id`, `egid` | swissBUILDINGS3D 3.0 | ⭐⭐⭐⭐⭐ Sehr gut | Jährlich |
| `address` | geo.admin.ch GWR | ⭐⭐⭐⭐ Gut | Kontinuierlich |
| Geometrie (`min_z`, `max_z`, `height_m`) | swissBUILDINGS3D + Berechnung | ⭐⭐⭐⭐ Gut | Jährlich |
| Hotspot-Statistik | EMF-Berechnung | ⭐⭐⭐⭐⭐ Sehr gut | Pro Analyse |
| OMEN-Daten | OMEN-Excel-Sheet | ⭐⭐⭐ Mittel | Manuell |

### Bekannte Limitationen

1. **Geschosszahl-Schätzung**:
   - Basiert auf Höhe / 3m
   - Keine Berücksichtigung von Untergeschossen
   - Dachgeschosse können fehlen wenn nicht als Fassade sichtbar

2. **EGID-Abdeckung**:
   - Nicht alle Gebäude haben EGID
   - Nebengebäude, Garagen oft ohne EGID
   - Ältere Gebäude teilweise unvollständig

3. **Adress-Lookup**:
   - Abhängig von geo.admin.ch API-Verfügbarkeit
   - Koordinaten-basierter Fallback weniger präzise
   - Neue Gebäude ggf. noch nicht im Register

4. **Höhengenauigkeit**:
   - swissBUILDINGS3D: ±0.5m typisch
   - Sampling-Auflösung: 0.5m
   - Gelände-Neigung kann `min_z` beeinflussen

5. **OMEN-Vergleich**:
   - Nur für OMEN-Gebäude verfügbar
   - Abhängig von Qualität der OMEN-Sheet-Daten
   - Manuelle OMEN-Zuordnung zu Gebäuden

---

## Interpretation und Best Practices

### Priorisierung von Gebäuden

**Hohe Priorität** (sofortige Überprüfung):
```
num_hotspots > 10 UND max_e_vm > 5.5 UND recommendation enthält "⚠️"
```

**Mittlere Priorität** (genauere Analyse):
```
num_hotspots > 0 ODER (has_high_ceilings = True UND omen_nr != "")
```

**Niedrige Priorität** (Monitoring):
```
max_e_vm > 4.5 UND num_hotspots = 0
```

### Auswahl der Berechnungsmethode

**Verwende `z_top_floor_nisv` wenn**:
- Neubau mit Standardgeschosshöhen
- `real_floor_height_m` < 3.2m
- Konsistenz mit bestehenden NISV-Gutachten erforderlich

**Verwende `z_top_floor_conservative` wenn**:
- Altbau oder unbekannte Bauweise
- `has_high_ceilings = True`
- `missing_floors > 0`
- Konservativer Ansatz gewünscht (Worst-Case)
- Gutachten für kritische Standorte

**Empfehlung**: Bei Zweifel immer `z_top_floor_conservative` verwenden!

### Typische Arbeitsabläufe

#### Workflow 1: Hotspot-Identifikation
```python
1. Sortiere nach num_hotspots (absteigend)
2. Filtere Gebäude mit num_hotspots > 0
3. Prüfe max_e_vm für Schwere der Überschreitung
4. Prüfe recommendation für zusätzliche Risiken
5. Erstelle Maßnahmenplan pro Gebäude
```

#### Workflow 2: OMEN-Validierung
```python
1. Filtere Gebäude mit omen_nr != ""
2. Sortiere nach |z_deviation_conservative| (absteigend)
3. Prüfe missing_floors > 0
4. Prüfe has_high_ceilings
5. Für kritische Fälle: Nachmessung empfehlen
```

#### Workflow 3: Gebäudeanalyse
```python
1. Suche Gebäude nach Adresse oder EGID
2. Prüfe Geometrie (height_m, real_floor_height_m)
3. Prüfe Hotspot-Statistik (num_hotspots, max_e_vm)
4. Lies recommendation für Zusammenfassung
5. Bei Bedarf: detaillierte CSV (hotspots_detailliert.csv) konsultieren
```

---

## Technische Details

### Berechnungsformeln

**NISV-Messpunkthöhe** (traditionell):
```
z_nisv = min_z + ground_offset + (floors - 1) × floor_height + measurement_height
       = min_z + 1.0m + (floors - 1) × 2.90m + 1.50m

wobei:
  min_z             = niedrigste Geländehöhe am Gebäude [m ü.M.]
  ground_offset     = Erdgeschoss über Gelände = 1.0m
  floors            = estimated_floors
  floor_height      = NISV-Standard = 2.90m
  measurement_height = Bauchhöhe = 1.50m
```

**Konservative Messpunkthöhe** (empfohlen):
```
z_conservative = max_z - (floor_height - head_height)
                = max_z - (2.90m - 1.80m)
                = max_z - 1.10m

wobei:
  max_z        = höchste Gebäudekante (Dachunterkante) [m ü.M.]
  floor_height = NISV-Standard = 2.90m
  head_height  = Kopfhöhe bei 1.90m Person = 1.80m
```

### CSV-Export-Trigger

Die Datei wird erstellt durch:
```python
from emf_hotspot.output.csv_export import export_buildings_overview_csv

export_buildings_overview_csv(
    results=all_facade_points,
    output_path=output_dir / "gebaeude_uebersicht.csv",
    building_analyses=building_analyses,  # aus building_validation.py
    antenna_system=antenna_system,
    buildings=buildings,
)
```

---

## Verwandte Dateien

| Datei | Inhalt | Verhältnis zu gebaeude_uebersicht.csv |
|-------|--------|---------------------------------------|
| `hotspots_detailliert.csv` | Alle Einzelpunkte mit Antennenbeiträgen | Detail-Daten zu den Hotspots |
| `hotspots_aggregated.csv` | Hotspots pro Gebäude×Geschoss | Aggregierte Hotspot-Daten |
| `omen_validierung.csv` | Vergleich Berechnung vs OMEN-Erwartung | OMEN-spezifische Validierung |
| `alle_punkte.csv` | Alle berechneten Fassadenpunkte | Rohdaten (sehr groß) |
| `zusammenfassung.csv` | Standort-Gesamtstatistik | Übersicht über alle Gebäude |

---

## Änderungshistorie

| Version | Datum | Änderung |
|---------|-------|----------|
| 1.0 | 2026-01-13 | Initiale Erstellung, vereint pro_gebaeude.csv und gebaeude_validierung.csv |

---

## Support und Feedback

**Fragen zur Interpretation?**
- Siehe: `documentation/BENUTZERHANDBUCH.md`
- Oder: `documentation/DATEI_UEBERSICHT.md`

**Technische Details zur Berechnung?**
- Code: `emf_hotspot/output/csv_export.py` → Funktion `export_buildings_overview_csv()`
- Validierung: `emf_hotspot/analysis/building_validation.py`

**Bug-Reports:**
- GitHub Issues: https://github.com/anthropics/claude-code/issues
