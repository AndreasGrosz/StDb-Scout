# Roadmap: EMF-Hotspot-Finder Verbesserungen

## Status: 2026-01-13

### ✅ IMPLEMENTIERT (Version 2.2)

#### 1. Mehr Gebäudeinfos in CSV ✓
- **Was:** EGID und Adressen für ALLE Gebäude, nicht nur OMEN
- **Implementierung:**
  - `hotspots_detailliert.csv` enthält jetzt `egid` und `address` Spalten
  - Automatischer Lookup via geo.admin.ch API
- **Dateien:** `output/csv_export.py`, `main.py`

#### 2. Geschosshöhen-Validierung ✓
- **Was:** Erkennung von hohen Räumen (Altbauten, Industriehallen)
- **Problem:** NISV-Formel nutzt fix 2.90m/Geschoss
- **Lösung:** Reale Geschosshöhen aus swissBUILDINGS3D berechnen
- **Implementierung:**
  - Neue `analysis/building_validation.py`
  - Berechnet: `real_floor_height = height_m / estimated_floors`
  - Warnung wenn > 3.2m pro Geschoss
- **Output:** `gebaeude_validierung.csv`
- **Dateien:** `analysis/building_validation.py`, `main.py`

#### 3. OMEN-Geschosse prüfen ✓
- **Was:** Vergleich reale Gebäudehöhe vs OMEN-Annahmen
- **Implementierung:**
  - Rückrechnung OMEN-Geschosszahl aus Z-Position
  - Vergleich mit tatsächlicher Gebäudehöhe
  - Erkennung fehlender Geschosse
- **Output:** `gebaeude_validierung.csv` (Spalten: `missing_floors`, `z_deviation_m`)
- **Dateien:** `analysis/building_validation.py`

#### 4. NISV-Formel vs Realität ✓
- **Was:** Prüfung ob NISV-Formel die Höhe unterschätzt
- **Formel:** `z = Geschosszahl × 2.90m + 1.50m + 1.00m`
- **Implementierung:**
  - Berechnung NISV-Z (`omen_z_nisv`)
  - Berechnung Real-Z aus Geodaten (`omen_z_real`)
  - Differenz dokumentiert in `z_deviation_m`
- **Warnung:** Bei > 1m Abweichung
- **Output:** `gebaeude_validierung.csv`, Terminal-Zusammenfassung

---

## 🚧 IN ARBEIT / GEPLANT

### 1. MSI-Dateien Kalibrierung (-4% Abweichung)

**Status:** Analyse läuft

**Problem:**
- `omen_validierung.csv` zeigt systematisch -4% Unterschätzung
- MSI-Dämpfungswerte sind zu großzügig
- Führt zu konservativen (zu niedrigen) E-Feld-Berechnungen

**Mögliche Ursachen:**
- Digitalisierung der PDF-Diagramme ungenau
- Interpolation zwischen Messpunkten
- Winkelauflösung zu grob

**Lösungsansätze:**

**A) Globaler Korrekturfaktor (schnell)**
```python
# Aus omen_validierung.csv:
mean_ratio = mean(e_calculated / e_expected)  # z.B. 0.96
correction_factor = 1 / mean_ratio  # 1.042

# Anwendung:
e_field_corrected = e_field_raw * correction_factor
```

**B) Frequenzabhängige Korrektur (genauer)**
```python
corrections = {
    "700-900": 1.05,
    "1805": 1.04,
    "2100": 1.03,
    "2600": 1.04,
}
```

**C) Winkel- und frequenzabhängig (am genauesten)**
- Analyse pro Frequenzband UND Winkelbereich
- Neue Spalte in ODS: `correction_factor`
- Aufwändig, aber präziseste Lösung

**Nächste Schritte:**
1. Detaillierte Analyse der Abweichungen pro Frequenzband
2. Entscheidung: Global vs Frequenzabhängig
3. MSI-ODS aktualisieren ODER Runtime-Korrektur implementieren
4. Erneute Validierung gegen OMEN-Referenzwerte

**Dateien:** `msi-files/Antennendämpfungen Hybrid AIR3268 R5.ods`

---

### 2. Virtuelle OMEN auf Bauplätzen

**Status:** Konzept, nicht implementiert

**Ziel:**
- Leere Parzellen erkennen
- Virtuelle Gebäude konstruieren (mit Grenzabständen)
- Virtuelle OMEN-Punkte platzieren
- AGW-Konformität für potenzielle Neubauten prüfen

**Benötigte Daten:**
- Katasterparzellen von geo.admin.ch
- WFS-Service: `ch.swisstopo-vd.amtliche-vermessung`
- Format: GeoJSON/WFS

**Algorithmus:**
```python
1. Lade Katasterparzellen (WFS)
2. Für jede Parzelle:
   - Prüfe ob Gebäude vorhanden (swissBUILDINGS3D)
   - Wenn leer:
     a) Virtuelles Gebäude konstruieren:
        - Grenzabstand: 3m
        - Höhe: Max. Höhe der Nachbargebäude
        - Grundfläche: Parzelle minus Grenzabstand
     b) Virtuelle Fassaden generieren
     c) Virtuelle OMEN-Punkte platzieren:
        - Pro Geschoss: Mitte Fassade + 1.5m
     d) E-Feld berechnen
     e) In separater CSV dokumentieren
```

**Technische Umsetzung:**

**Phase 1: WFS-Integration**
```python
def load_cadastral_parcels(bbox: Tuple[float, float, float, float]) -> List[Polygon]:
    """
    Lädt Katasterparzellen via WFS.

    Args:
        bbox: (min_e, min_n, max_e, max_n) in LV95

    Returns:
        Liste von Shapely Polygons (Parzellengrenzen)
    """
    wfs_url = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify"
    # ...
```

**Phase 2: Leere Parzellen identifizieren**
```python
def find_empty_parcels(parcels: List[Polygon], buildings: List[Building]) -> List[Polygon]:
    """
    Findet Parzellen ohne Gebäude.
    """
    empty = []
    for parcel in parcels:
        has_building = any(
            parcel.intersects(building_polygon)
            for building in buildings
        )
        if not has_building:
            empty.append(parcel)
    return empty
```

**Phase 3: Virtuelles Gebäude konstruieren**
```python
def create_virtual_building(
    parcel: Polygon,
    neighboring_buildings: List[Building],
    border_distance_m: float = 3.0
) -> Building:
    """
    Konstruiert virtuelles Gebäude auf leerer Parzelle.
    """
    # Grenzabstand anwenden (Shapely buffer)
    buildable_area = parcel.buffer(-border_distance_m)

    # Höhe aus Nachbargebäuden
    max_neighbor_height = max(
        get_building_height(b) for b in neighboring_buildings
    )

    # Erzeuge Fassaden
    walls = []
    for i, (p1, p2) in enumerate(zip(buildable_area.exterior.coords[:-1],
                                       buildable_area.exterior.coords[1:])):
        wall = create_vertical_wall(p1, p2, height=max_neighbor_height)
        walls.append(wall)

    return Building(
        id=f"VIRTUAL_{parcel.id}",
        egid="VIRTUAL",
        wall_surfaces=walls,
    )
```

**Phase 4: Export**
- Separate CSV: `virtuelle_omen.csv`
- Spalten: `parcel_id`, `x`, `y`, `z`, `e_field_vm`, `exceeds_limit`, `virtual_building_height`, `neighbor_max_height`
- Visualisierung: Eigene Farbe in Heatmap (z.B. Orange)

**Abhängigkeiten:**
```bash
pip install shapely
```

**Geschätzter Aufwand:** 2-3 Tage
- 1 Tag: WFS-Integration + Parzellen-Download
- 1 Tag: Virtuelle Gebäude-Konstruktion
- 0.5 Tag: OMEN-Platzierung + E-Feld-Berechnung
- 0.5 Tag: CSV-Export + Tests

**Priorität:** MITTEL (Nice-to-have für vollständige Compliance-Prüfung)

---

## 📊 Neue Output-Dateien (Version 2.2)

### `gebaeude_validierung.csv`

**Zweck:** Erkennung von Problemen mit NISV-Standardformel

**Spalten:**
- `building_id`: Gebäude-ID aus swissBUILDINGS3D
- `egid`: Eidgenössischer Gebäudeidentifikator
- `height_m`: Gebäudehöhe (max_z - min_z)
- `estimated_floors`: Geschätzte Geschosszahl (height / 3m)
- `real_floor_height_m`: Reale Geschosshöhe
- `has_high_ceilings`: Ja/Nein (> 3.2m)
- `ceiling_warning`: Warntext bei hohen Räumen
- `omen_nr`: OMEN-Nummer (falls zugeordnet)
- `omen_floors`: Geschosszahl aus OMEN-Z zurückgerechnet
- `omen_z_nisv`: Z-Position nach NISV-Formel
- `omen_z_real`: Z-Position oberster Messpunkt real
- `missing_floors`: Fehlende Geschosse in OMEN
- `z_deviation_m`: Abweichung NISV vs Real in Metern
- `recommendation`: Handlungsempfehlung

**Beispiel-Ausgabe:**
```csv
building_id,egid,height_m,estimated_floors,real_floor_height_m,has_high_ceilings,ceiling_warning,omen_nr,omen_floors,omen_z_nisv,omen_z_real,missing_floors,z_deviation_m,recommendation
UUID_123,123456,15.50,5,3.10,Nein,,O1,5,478.00,479.20,0,1.20,"⚠️ Oberste Geschoss 1.2m höher als NISV-Formel! "
UUID_456,789012,18.20,6,3.03,Nein,,,,,,,,"✓ OK"
UUID_789,345678,22.80,7,3.26,Ja,"Hohe Räume: 3.26m/Geschoss (NISV: 2.90m). NISV-Formel unterschätzt Höhe um 2.5m!",O3,6,481.50,484.00,1,2.50,"⚠️ Hohe Decken: NISV-Formel prüfen! ⚠️ 1 Geschoss(e) fehlen in OMEN! ⚠️ Oberste Geschoss 2.5m höher als NISV-Formel! "
```

**Verwendung:**
1. Gebäude mit `⚠️` in `recommendation` prüfen
2. Bei hohen Decken: NISV-Formel im Gutachten anpassen
3. Bei fehlenden Geschossen: Zusätzliche OMEN-Punkte berechnen
4. Bei Z-Abweichung: Höhere E-Feldstärken zu erwarten

---

## 🎯 Prioritäten

### HOCH (sofort)
1. **MSI-Kalibrierung** - Systematische -4% Abweichung korrigieren

### MITTEL (nächste Wochen)
2. **Virtuelle OMEN** - Bauplätze abdecken

### NIEDRIG (zukünftig)
3. **Multi-Typ MSI-Datenbank** - Zentrale DB für alle Antennentypen
4. **Automatische Pattern-Digitalisierung** - PDF → ODS via OCR/AI

---

## 📈 Erfolgskennzahlen

### Vor Optimierung (Version 2.1)
- OMEN-Abweichung: -4% (zu niedrig)
- Fehlende Geschosse: Unbekannt
- NISV-Formel-Probleme: Unbekannt

### Nach Optimierung (Version 2.2)
- OMEN-Abweichung: -4% (**bekannt**, Kalibrierung folgt)
- Fehlende Geschosse: **Dokumentiert** in `gebaeude_validierung.csv`
- NISV-Formel-Probleme: **Erkannt** und dokumentiert
- Gebäudeinfos: **Vollständig** (EGID/Adresse für alle)

### Ziel Version 2.3
- OMEN-Abweichung: < 2% (nach MSI-Kalibrierung)
- Virtuelle OMEN: **Implementiert**
- Compliance-Rate: > 99% (inkl. Bauplätze)

---

## 📝 Nächste Schritte

1. **MSI-Kalibrierung durchführen** (diese Woche)
   - Analyse der Abweichungen pro Frequenzband
   - Korrekturfaktoren ermitteln
   - MSI-ODS aktualisieren

2. **Validierung testen** (nach Kalibrierung)
   - Erneute OMEN-Validierung
   - Soll: < 2% Abweichung

3. **Virtuelle OMEN planen** (nächste Woche)
   - WFS-API testen
   - Prototyp für eine Parzelle

4. **Dokumentation erweitern**
   - Anleitung zur Interpretation von `gebaeude_validierung.csv`
   - Empfehlungen für Gutachter

---

**Letzte Aktualisierung:** 2026-01-13
**Version:** 2.2
**Autor:** Claude + User Collaboration
