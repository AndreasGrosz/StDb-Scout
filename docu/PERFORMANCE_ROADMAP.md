# Performance-Optimierung Roadmap

## Aktueller Stand (v1.0)

### Performance-Metriken
- **Laufzeit**: ~2-3 Minuten (Standard-Analyse)
- **Messpunkte**: ~2000-5000 Fassadenpunkte
- **CPU-Auslastung**: 1 Kern (seriell)
- **Speicher**: ~100 MB

### Berechnungsschritte (seriell)
1. OMEN-Daten laden (XLS-Parsing)
2. Antennendiagramme laden (CSV-Interpolation)
3. swissBUILDINGS3D laden (CityGML)
4. Fassaden-Sampling (pro Gebäude)
5. E-Feld-Berechnung (pro Punkt)
6. Line-of-Sight (Ray-Casting pro Punkt)
7. Hotspot-Identifikation
8. CSV-Export
9. VTK-Export
10. Heatmap-Generierung

---

## Optimierungspotenzial (basierend auf Feedback)

### Zitat Kollege
> "20.000 Punkte in 1:40 mit 1 Kern → mit Optimierung Faktor 10 → mit 8 Kernen 1.6 Mio Punkte in 1:40"

### Übertragen auf StDb-Scout (15 CPU-Kerne)
- **Aktuell**: 2000 Punkte in 120s = 16.7 Punkte/s
- **Mit Optimierung (Faktor 10)**: 167 Punkte/s
- **Mit 15 Kernen parallel**: 2500 Punkte/s
- **Damit in 2 Minuten**: 300.000 Punkte

---

## Roadmap zur Parallelisierung

### Phase 1: Low-Hanging Fruit (Aufwand: 1-2 Tage)

#### 1.1 Paralleles Fassaden-Sampling
```python
# Statt:
for building in buildings:
    points = sample_all_facades(building, resolution)

# Verwende:
from multiprocessing import Pool
with Pool(processes=15) as pool:
    results = pool.starmap(sample_all_facades, building_args)
```

**Gewinn**: 10-15x schneller beim Sampling

#### 1.2 Parallele E-Feld-Berechnung
```python
# Teile Messpunkte in Chunks auf
chunks = np.array_split(all_points, 15)  # 15 Kerne

with Pool(processes=15) as pool:
    results = pool.starmap(calculate_e_field_batch, chunks)
```

**Gewinn**: 10-15x schneller bei E-Feld-Berechnung

#### 1.3 Numpy-Vektorisierung
Statt Loops über Punkte:
```python
# Vorher:
for point in points:
    distance = np.linalg.norm(point - antenna_pos)
    e_field = sqrt(30 * erp) / distance

# Nachher (vektorisiert):
distances = np.linalg.norm(points - antenna_pos, axis=1)
e_fields = np.sqrt(30 * erp) / distances
```

**Gewinn**: 5-10x schneller

---

### Phase 2: Strukturiertes 3D-Grid (Aufwand: 3-5 Tage)

#### 2.1 Umstellung auf Volumen-Grid
Statt nur Fassadenpunkte → **gesamtes 3D-Volumen** berechnen

```python
# Definiere Grid
x = np.arange(center_e - 100, center_e + 100, 1.0)  # 200m, 1m Auflösung
y = np.arange(center_n - 100, center_n + 100, 1.0)  # 200m
z = np.arange(ground_h, ground_h + 30, 1.0)        # 30m Höhe

# Erstelle Mesh-Grid
X, Y, Z = np.meshgrid(x, y, z)  # 200×200×30 = 1.2 Mio Punkte
points = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])

# Berechne E-Feld für alle Punkte (parallel)
e_fields = calculate_e_field_vectorized(points, antenna_system)

# PyVista StructuredGrid
grid = pv.StructuredGrid(X, Y, Z)
grid["E_Field_Vm"] = e_fields.reshape(X.shape)
```

**Vorteile**:
- Vollständige 3D-Visualisierung (nicht nur Gebäudefassaden)
- Iso-Flächen (z.B. 5 V/m Grenzfläche)
- Schnitte in beliebigen Ebenen
- Volumen-Rendering in ParaView

**Gewinn**: 100x mehr Datenpunkte bei gleicher Laufzeit

#### 2.2 Adaptive Verfeinerung
```python
# Grob-Grid: 200x200x30 @ 5m = 4800 Punkte (sehr schnell)
coarse_grid = calculate_coarse(resolution=5.0)

# Finde Hotspot-Regionen (E > 4 V/m)
hotspot_regions = find_regions(coarse_grid, threshold=4.0)

# Verfeinere nur Hotspot-Regionen auf 0.5m
for region in hotspot_regions:
    fine_grid = calculate_fine(region, resolution=0.5)
```

**Gewinn**: Fokus auf relevante Bereiche, 10x weniger Gesamt-Punkte

---

### Phase 3: GPU-Beschleunigung (Aufwand: 1-2 Wochen)

Für **massive** Performance-Steigerung (wenn relevant):

```python
import cupy as cp  # CUDA-beschleunigtes NumPy

# E-Feld-Berechnung auf GPU
points_gpu = cp.asarray(points)
antenna_pos_gpu = cp.asarray(antenna_pos)

distances_gpu = cp.linalg.norm(points_gpu - antenna_pos_gpu, axis=1)
e_fields_gpu = cp.sqrt(30 * erp) / distances_gpu

e_fields = e_fields_gpu.get()  # Zurück auf CPU
```

**Gewinn**: 100-1000x schneller als CPU (abhängig von GPU)

---

## Empfohlene Umsetzung

### Sofort umsetzen (heute/morgen)
1. ✅ **Paralleles Fassaden-Sampling** (multiprocessing)
2. ✅ **Parallele E-Feld-Berechnung** (multiprocessing)
3. ✅ **Numpy-Vektorisierung** (wo noch Loops existieren)

**Erwarteter Gewinn**: 5-10x schneller → Laufzeit <30 Sekunden

### Mittelfristig (nächste Woche)
4. **Strukturiertes 3D-Grid** implementieren
5. **Adaptive Verfeinerung** für Hotspots
6. **CLI-Parameter** für Grid-Auflösung

**Erwarteter Gewinn**: Vollständige 3D-Visualisierung, Iso-Flächen

### Langfristig (bei Bedarf)
7. GPU-Beschleunigung mit CuPy
8. Distributed Computing (mehrere Maschinen)

---

## Technische Details

### Multiprocessing mit Ray-Casting
**Problem**: Ray-Casting (Line-of-Sight) ist nicht trivial zu parallelisieren wegen shared memory.

**Lösung**: Jeder Worker bekommt eigene Kopie der Gebäude-Dreiecke:
```python
def calculate_point_batch(points_batch, buildings_triangles, antenna_system):
    """Worker-Funktion für multiprocessing."""
    results = []
    for point in points_batch:
        e_field = calculate_e_field(point, antenna_system)
        los = check_line_of_sight(point, antenna_system.base_position, buildings_triangles)
        results.append((point, e_field, los))
    return results

# Hauptprozess
with Pool(processes=15) as pool:
    triangles = extract_all_triangles(buildings)  # Einmalig
    chunks = np.array_split(all_points, 15)

    args = [(chunk, triangles, antenna_system) for chunk in chunks]
    results = pool.starmap(calculate_point_batch, args)
```

### PyVista StructuredGrid vs. PolyData
```python
# Aktuell: PolyData (unstrukturiert)
points = pv.PolyData(all_points)
points["E_Field_Vm"] = e_field_values

# Besser: StructuredGrid (strukturiert)
grid = pv.StructuredGrid(X, Y, Z)  # Regelmäßiges Gitter
grid["E_Field_Vm"] = e_field_values.reshape(X.shape)

# Vorteile StructuredGrid:
# - Schnelleres Rendering in ParaView
# - Iso-Flächen (Contour-Filter)
# - Volumen-Rendering möglich
# - Slicing in beliebigen Ebenen
```

---

## Benchmark-Ziele

| Konfiguration | Punkte | Laufzeit | Punkte/s |
|---------------|--------|----------|----------|
| **Aktuell (seriell)** | 2.000 | 120s | 17 |
| **Phase 1 (parallel)** | 20.000 | 120s | 167 |
| **Phase 2 (Grid)** | 1.200.000 | 120s | 10.000 |
| **Phase 3 (GPU)** | 10.000.000 | 120s | 83.333 |

---

## Nächste Schritte

1. **Heute**: Implementiere paralleles E-Feld-Berechnung (multiprocessing)
2. **Diese Woche**: Teste Performance-Gewinn, verfeinere Parallelisierung
3. **Nächste Woche**: Strukturiertes Grid als optionales Feature

**Frage an Sie**: Sollen wir mit Phase 1 (Parallelisierung) sofort anfangen?
