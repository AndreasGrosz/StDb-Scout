# TODO: Virtuelle Gebäude auf leeren Parzellen

## Ziel
Potenzielle zukünftige AGW-Überschreitungen voraussagen, wenn auf aktuell leeren Parzellen gebaut wird.

## Kontext
- Aus dem Plan-File: "Katasterparzellen + Virtuelle OMEN"
- User-Anforderung: "was ist mit den 'virtuellen Gebäuden' auf nahen bauplätzen, die noch kommen könnten. das sind auch omen."

## Anforderungen

### 1. Datenquellen
- **Katasterparzellen**: WMS Layer `ch.swisstopo-vd.amtliche-vermessung`
- **Bestehende Gebäude**: swissBUILDINGS3D
- **Leere Parzellen**: Geometrischer Vergleich (Parzellen ohne Gebäude)

### 2. Identifikation leerer Parzellen
```python
# Algorithmus:
1. Lade Katasterparzellen im Umkreis (z.B. 100m)
2. Lade bestehende Gebäude (swissBUILDINGS3D)
3. Für jede Parzelle:
   - Prüfe ob Gebäude-Polygon innerhalb liegt
   - Falls NEIN → Parzelle ist leer
```

### 3. Virtuelle Gebäude erstellen

**Parameter:**
- **Grenzabstand**: 3m von Parzellengrenze (gemäß Bauordnung)
- **Grundfläche**: Parzellenfläche minus Grenzabstand
- **Geschosszahl**: Gleich wie höchstes Gebäude im Umkreis (z.B. 50m)
- **Geschosshöhe**: 3m (Standard)

**Beispiel:**
```python
def create_virtual_building(parcel_polygon, neighboring_buildings):
    # Grenzabstand anwenden
    footprint = parcel_polygon.buffer(-3.0)  # 3m innen

    # Höchstes Nachbargebäude finden
    max_floors = max(b.num_floors for b in neighboring_buildings)

    # Virtuelle Höhe
    ground_z = get_terrain_height(parcel_polygon.centroid)
    building_height = max_floors * 3.0

    # OMEN-Punkte auf Fassaden generieren
    virtual_omen = sample_facades(footprint, ground_z, building_height)

    return VirtualBuilding(footprint, max_floors, virtual_omen)
```

### 4. OMEN-Nummerierung
- Bestehende OMEN: O1-O20
- Virtuelle OMEN: **V1, V2, V3, ...** (mit "V" prefix)
- In CSV-Outputs: Spalte `is_virtual=True`

### 5. Integration in Workflow

**Neue CLI-Option:**
```bash
python -m emf_hotspot.main ... --include-virtual-buildings
```

**Neue Exports:**
- `hotspots_virtual.csv` - Nur virtuelle OMEN-Punkte
- `hotspots_combined.csv` - Real + Virtuell
- `heatmap_virtual.png` - Markiere virtuelle Gebäude anders (gestrichelte Umrisse)

### 6. Visualisierung

**Heatmap:**
- Virtuelle Gebäude: Gestrichelte Umrandung
- Virtuelle OMEN: Dreieck-Marker (△) statt Box (□)
- Farbe: Orange (statt gelb für real)

**ParaView:**
- Virtuelle Gebäude: Transparenter (opacity=0.3)
- Attribut `is_virtual` für Filterung

## Implementierungsreihenfolge

### Phase 1: Kataster-Integration
1. WMS-Layer für Parzellen implementieren
2. Parser für Parzellen-Geometrien
3. Vergleichsalgorithmus (Parzelle ↔ Gebäude)

### Phase 2: Virtuelle Gebäude
4. Grenzabstand-Berechnung (buffer)
5. Geschosszahl-Heuristik (Nachbargebäude)
6. Virtuelle OMEN-Generierung (Fassaden-Sampling)

### Phase 3: E-Feld-Berechnung
7. Bestehende `calculate_all_points()` verwenden
8. Virtuelle Punkte mit Flag markieren
9. Separate CSV-Exports

### Phase 4: Visualisierung
10. Heatmap mit virtuellen Gebäuden
11. ParaView mit Virtual-Attribut
12. Dokumentation & Tests

## Abhängigkeiten

**Python-Packages:**
```python
shapely  # Geometrie-Operationen (buffer, contains)
owslib   # WMS-Zugriff für Kataster
```

**Daten:**
- geo.admin.ch WMS für Katasterparzellen
- swissBUILDINGS3D für Gebäude
- DHM25 für Terrain-Höhen (optional)

## Offene Fragen

1. **Welche Bauzone-Typen berücksichtigen?**
   - Nur Wohnzonen?
   - Auch Gewerbezonen?

2. **Maximale Geschosszahl?**
   - Aus Bauordnung ableiten?
   - Oder fix 6 Stockwerke als Worst-Case?

3. **Welcher Umkreis für Nachbargebäude?**
   - 50m? 100m?

4. **Welche Parzellen sind relevant?**
   - Nur leere Parzellen?
   - Auch unterbebaute (Parzelle größer als Gebäude)?

## Zeitschätzung

**Konservativ:**
- Phase 1: Kataster-Integration → Implementiert, getestet
- Phase 2: Virtuelle Gebäude → Implementiert, getestet
- Phase 3: E-Feld-Berechnung → Minimal (nutzt bestehende Funktion)
- Phase 4: Visualisierung → Anpassung bestehender Funktionen

**Total:** Implementierung wenn benötigt

## Priorität
**NIEDRIG** - Erst nach Hauptfunktionen und Validierung.

Aktueller Fokus:
1. ✅ Hotspot-Analyse mit echten Gebäuden
2. ✅ Gutachten-Visualisierungen
3. ✅ OMEN-Validierung
4. 🔜 Antennentypen-Tabelle mit Tilt/Pmax
5. 🔜 Heatmaps auf Tilt/Pmax-Basis
6. 📋 Virtuelle Gebäude (später)

## Status
**GEPLANT** - Bereit für Implementierung bei Bedarf.

---

## Referenzen
- Ursprünglicher Plan: `/home/res/.claude/plans/drifting-questing-rivest.md`
- User-Anforderung: Chat vom 2026-01-11
- geo.admin.ch Kataster: `ch.swisstopo-vd.amtliche-vermessung`
