"""Debug: Prüfe ob TIN-Faces korrekt erstellt werden"""

from pathlib import Path
from emf_hotspot.loaders.omen_loader import load_omen_data
from emf_hotspot.loaders.building_loader import download_buildings_for_location

# Lade Zürich-Daten
antenna_system = load_omen_data(Path('input/OMEN R37 clean.xls'))

print(f"Antennensystem: {antenna_system.name}")
print(f"Position: E={antenna_system.base_position.e}, N={antenna_system.base_position.n}")

# Lade Gebäude
buildings = download_buildings_for_location(
    position=antenna_system.base_position,
    radius=200.0
)

print(f"\nAnzahl Gebäude: {len(buildings)}")

# Prüfe erste 3 Gebäude
for i, building in enumerate(buildings[:3]):
    print(f"\n=== Gebäude {i+1} (EGID: {building.egid}) ===")
    print(f"  Wände: {len(building.wall_surfaces)}")

    for j, wall in enumerate(building.wall_surfaces[:2]):
        print(f"\n  Wand {j+1}:")
        print(f"    Vertices: {len(wall.vertices)}")
        print(f"    Faces: {wall.faces is not None and len(wall.faces) if wall.faces is not None else 'None'}")
        if wall.faces is not None:
            print(f"    Face-Array Shape: {wall.faces.shape}")
            print(f"    Face-Array Sample: {wall.faces[:20]}")  # Erste 20 Einträge
        print(f"    Vertex-Shape: {wall.vertices.shape}")
