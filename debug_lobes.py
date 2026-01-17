"""Debug-Skript für Antenna Lobe Rotation"""

import numpy as np

# Test: Wo landet ein Punkt bei Elevation=0°, Azimut=0° nach Rotation?

# Lokale Koordinaten (vor Rotation)
el = 0  # Horizontal
az = 0  # Hauptstrahlrichtung (lokal)
radius = 100

el_rad = np.radians(el)
az_rad = np.radians(az)

x_local = radius * np.cos(el_rad) * np.cos(az_rad)
y_local = radius * np.cos(el_rad) * np.sin(az_rad)
z_local = radius * np.sin(el_rad)

print("=== LOKAL (vor Rotation) ===")
print(f"Elevation: {el}°, Azimut: {az}°")
print(f"Punkt: [{x_local:.1f}, {y_local:.1f}, {z_local:.1f}]")
print(f"→ Zeigt in +X Richtung (lokal)")

# Jetzt rotieren auf echten Azimut 30°
azimuth_deg = 30.0
tilt_deg = 0.0

# Aktuelle Formel
azimuth_rad = np.radians(90.0 - azimuth_deg)

rotation_z = np.array([
    [np.cos(azimuth_rad), -np.sin(azimuth_rad), 0],
    [np.sin(azimuth_rad),  np.cos(azimuth_rad), 0],
    [0, 0, 1]
])

tilt_rad = np.radians(tilt_deg)
rotation_tilt = np.array([
    [np.cos(-tilt_rad), 0, np.sin(-tilt_rad)],
    [0, 1, 0],
    [-np.sin(-tilt_rad), 0, np.cos(-tilt_rad)]
])

point = np.array([x_local, y_local, z_local])
point_rotated = point @ rotation_tilt.T @ rotation_z.T

print("\n=== NACH ROTATION ===")
print(f"Antenne Azimut: {azimuth_deg}°, Tilt: {tilt_deg}°")
print(f"Punkt: [{point_rotated[0]:.1f}, {point_rotated[1]:.1f}, {point_rotated[2]:.1f}]")
print(f"Länge (X,Y): {np.linalg.norm(point_rotated[:2]):.1f}")
print(f"Länge Z: {abs(point_rotated[2]):.1f}")

# Erwarteter Richtungsvektor für Azimut 30° (0° = Nord = +Y)
expected_direction = np.array([np.sin(np.radians(azimuth_deg)), np.cos(np.radians(azimuth_deg)), 0])
actual_direction = point_rotated / np.linalg.norm(point_rotated)

print(f"\nErwartet: {expected_direction}")
print(f"Tatsächlich: {actual_direction}")
print(f"Abweichung: {np.linalg.norm(expected_direction - actual_direction):.4f}")

# Jetzt teste was passiert bei Elevation +90° (nach oben)
el_up = 90
az_up = 0

el_rad_up = np.radians(el_up)
az_rad_up = np.radians(az_up)

x_local_up = radius * np.cos(el_rad_up) * np.cos(az_rad_up)
y_local_up = radius * np.cos(el_rad_up) * np.sin(az_rad_up)
z_local_up = radius * np.sin(el_rad_up)

print("\n=== ELEVATION +90° (nach oben) ===")
print(f"Lokal: [{x_local_up:.1f}, {y_local_up:.1f}, {z_local_up:.1f}]")

point_up = np.array([x_local_up, y_local_up, z_local_up])
point_up_rotated = point_up @ rotation_tilt.T @ rotation_z.T

print(f"Nach Rotation: [{point_up_rotated[0]:.1f}, {point_up_rotated[1]:.1f}, {point_up_rotated[2]:.1f}]")
print(f"→ Z-Komponente: {point_up_rotated[2]:.1f} (sollte ~100 sein)")
