# Virtuelle Gebäude für Baugrundstücke

## Übersicht

**StDb-Scout** berechnet automatisch **virtuelle OMEN-Punkte** für unbebaute Parzellen im Umkreis der Antenne. Dies ist essentiell für die Beurteilung von Bauanträgen, da zukünftige Neubauten neue Hotspots erzeugen können.

## Funktionsweise

### 1. Katasterparzellen laden
```
geo.admin.ch API: ch.swisstopo-vd.amtliche-vermessung
```
- Lädt alle Parzellen im Untersuchungsradius (Standard: 200m)
- Extrahiert Polygon-Geometrie und EGRID

### 2. Leere Parzellen identifizieren
- Prüft ob Parzelle bebaut ist (Mittelpunkt eines Gebäudes liegt auf Parzelle)
- Unbebaute Parzellen werden markiert

### 3. Virtuelles Gebäude generieren

**Grundfläche:**
- Parzellenfläche minus **3m Grenzabstand** rundherum
- Verwendet Shapely `buffer(-3.0)` Operation
- Parzellen < 10m² werden verworfen

**Gebäudehöhe:**
- Übernimmt Höhe vom **höchsten Nachbargebäude** im Umkreis 100m
- Geschosszahl = Höhe / 3m (typische Stockwerkhöhe)
- Fallback: Mindestens 2 Stockwerke / 6m Höhe

**Terrain-Höhe:**
- Median aller Gebäude-Basishöhen in der Nähe
- Fallback: 400m ü.M.

### 4. Virtuelle OMEN-Punkte

**Fassaden-Sampling:**
- Pro Kante des Gebäudepolygons
- Auflösung: 1m Abstand entlang Kanten

**Höhen-Sampling:**
- Pro Stockwerk ein Messpunkt
- Bei 1.5m Fensterhöhe über Boden

**Beispiel:**
```
Gebäude: 4 Stockwerke, 20m × 15m
→ ~280 virtuelle Messpunkte
```

## Integration in Berechnung

Virtuelle Gebäude werden wie reale Gebäude behandelt:
- ✅ E-Feldstärke-Berechnung
- ✅ LOS-Analyse (können auch blockieren!)
- ✅ Hotspot-Identifikation
- ✅ CSV-Exports (EGID beginnt mit "VIRTUAL_")

## CSV-Kennzeichnung

```csv
building_id,egid,address,max_e_vm,is_virtual
GDB_EGID_12345,12345,"Hauptstrasse 1, Ort",5.2,false
VIRTUAL_CH123456789,VIRTUAL_1234,"",6.5,true
```

## Automatische Aktivierung

Das Feature ist **immer aktiv**. Bei jedem Lauf werden automatisch:
1. Parzellen im Radius geladen
2. Leere Parzellen identifiziert
3. Virtuelle Gebäude generiert
4. Virtuelle OMEN-Punkte berechnet

## Abhängigkeiten

```bash
pip install shapely
```

## Beispiel-Output

```
[3b/6] Lade Katasterparzellen und erstelle virtuelle Gebäude...
  Lade Parzellen im Radius 200.0m...
  → 87 Parzellen gefunden
  Analysiere leere Parzellen...
  → 12 leere Parzellen identifiziert
  → 12 virtuelle Gebäude erstellt

[4/6] Generiere Fassaden- und Dachpunkte (Auflösung: 1.0m)...
  Sample virtuelle Gebäude...
  → 3420 virtuelle Messpunkte hinzugefügt
  Fassadenpunkte: 31273 (3420 virtuell)
```

## Anwendungsfall: Bauanträge

### Problem
Ein Mobilfunkkritiker will einen Bauantrag anfechten:
- Neubau auf leerem Grundstück geplant
- Antenne in Nachbarschaft
- Frage: Wird der Neubau Hotspots haben?

### Lösung mit StDb-Scout
1. StDB des Mobilfunkbetreibers analysieren
2. Virtuelle Gebäude werden automatisch erstellt
3. Virtuelle OMEN-Punkte zeigen potenzielle Hotspots
4. Ergebnis in CSV + ParaView visualisieren

### Rechtliche Verwendung
- Zeigt worst-case Szenarien für Neubauten
- Begründung: "Zukünftige Bewohner werden exponiert"
- Kann in Einsprachen verwendet werden

## Technische Details

### Grenzabstand (Setback)
```python
setback_m = 3.0  # Gesetzlicher Mindestabstand zur Grenze
```

Kann in `main.py` Zeile 238 angepasst werden.

### Höhen-Lookup
```python
max_distance_m = 100.0  # Suchradius für höchstes Gebäude
```

Kann in `virtual_buildings.py` angepasst werden.

## Quellen

- **Kataster**: [geo.admin.ch Amtliche Vermessung](https://www.geo.admin.ch/de/amtliche-vermessung)
- **Gebäude**: [swissBUILDINGS3D 3.0](https://www.swisstopo.admin.ch/swissbuildings3d)
- **NISV**: [SR 814.710](https://www.admin.ch/opc/de/classified-compilation/19996141/index.html)
