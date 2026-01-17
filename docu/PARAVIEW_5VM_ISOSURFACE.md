# ParaView: 5V/m Isosurfaces visualisieren

**Für: Valentin**

## Was sind Isosurfaces?

Isosurfaces zeigen alle Punkte im 3D-Raum mit **exakt demselben E-Feld-Wert** (z.B. 5.0 V/m). Sie erscheinen als "Keulen" oder "Blasen" um die Antennen.

## Schnellanleitung: 5V/m Keulen anzeigen

### 1. ParaView öffnen

```bash
paraview output/*/paraview_preset.pvsm
```

### 2. Contour-Filter erstellen

1. **Pipeline Browser** (links): Klick auf "Results"
2. **Menü**: Filters → Common → **Contour**
3. Im **Properties Panel** (links):
   - **Contour By**: `E_field_Vm` (sollte schon gesetzt sein)
   - **Isosurfaces**: Trage **5.0** ein (AGW-Grenzwert)
   - Optional: Weitere Werte: 4.0, 6.0, 7.0 (für mehrere Keulen)
4. Klick **Apply** ✅

### 3. Färbung einstellen

Die Isosurface ist jetzt sichtbar, aber grau:

1. **Color by** (Toolbar oben): Wähle `E_field_Vm`
2. **Edit Color Map** (Zahnrad-Icon):
   - **Rescale to Custom Range**: Min=0, Max=6
   - **Color Map**: "Cool to Warm" (Blau → Rot)

### 4. Transparenz für bessere Sicht

Die Isosurface verdeckt möglicherweise die Gebäude:

1. **Properties Panel** (Contour ausgewählt):
   - **Opacity**: 0.5 (halbtransparent)

### 5. Gebäude transparent machen

Um die Isosurface besser zu sehen:

1. **Pipeline Browser**: Klick auf "Buildings"
2. **Properties Panel**:
   - **Opacity**: 0.3
   - **Color**: Lightgray

### 6. Mehrere Grenzwerte gleichzeitig

Für verschiedene Werte (z.B. 4, 5, 6, 7 V/m):

1. **Contour Properties**:
   - **Isosurfaces**: Klick auf "+"-Symbol
   - Füge Werte hinzu: 4.0, 5.0, 6.0, 7.0
2. **Apply**

Jetzt siehst du mehrere "Schalen" um die Antennen.

---

## Alternative: Threshold-Filter (für Hotspot-Bereiche)

Wenn du **alle Punkte E ≥ 5 V/m** sehen willst (nicht nur die Oberfläche):

### 1. Threshold erstellen

1. **Pipeline Browser**: Klick auf "Results"
2. **Menü**: Filters → Common → **Threshold**
3. **Properties Panel**:
   - **Scalars**: `E_field_Vm`
   - **Minimum**: 5.0
   - **Maximum**: 100.0 (oder leer lassen)
4. **Apply**

### 2. Färbung

Wie bei Contour: **Color by** → `E_field_Vm`

---

## Tipps für Gutachten-Screenshots

### Kamera-Einstellungen

1. **View** → **Camera**:
   - **Parallel Projection**: ✅ (orthogonale Ansicht, keine Perspektive)
   - **View Direction**: +Z (Draufsicht) oder anpassen

2. **Rotation**:
   - Linke Maustaste: Rotieren
   - Mittlere Maustaste: Zoom
   - Rechte Maustaste: Verschieben

### Screenshot exportieren

1. **File** → **Save Screenshot**
2. **Optionen**:
   - **Resolution**: 1920×1080 oder höher (2560×1440 für Gutachten)
   - **Format**: PNG (verlustfrei) oder JPG

---

## Was du jetzt siehst

- **Terrain/Relief**: Geländeoberfläche mit Höhenlinien
- **Gebäude**: 3D-Modelle (transparent)
- **5V/m Keulen**: Isosurfaces zeigen, wo genau der Grenzwert erreicht wird
- **Antennen**: Hellblaue Würfel mit Pfeilen (Hauptstrahlrichtungen)
- **Hotspots**: Wo Keulen Gebäude schneiden → Potenzielle OMEN-Punkte!

---

## Häufige Fragen

### "Ich sehe keine Isosurface?"

- **Prüfe**: Gibt es überhaupt Punkte mit E ≥ 5 V/m?
- **Lösung**: Contour-Wert niedriger setzen (z.B. 3.0 V/m zum Testen)

### "Die Keulen sind zu klein/groß?"

- **Ursache**: Antennen-ERP zu niedrig/hoch oder Tilt falsch
- **Lösung**: Prüfe OMEN-Datei auf korrekte ERP-Werte

### "Terrain fehlt?"

- **Ursache**: SwissALTI3D-Download fehlgeschlagen
- **Lösung**: Prüfe Internet-Verbindung, Cache löschen

---

**Erstellt**: 2026-01-17
**Für**: Valentin (Dr. phys.)
**Ziel**: Schnelles Erkennen potenzieller OMEN-Punkte
