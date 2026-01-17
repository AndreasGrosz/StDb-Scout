"""Prüfe V-Pattern Winkel-Bereich"""

from emf_hotspot.loaders.omen_loader import load_omen_data
from emf_hotspot.loaders.pattern_loader_ods import load_patterns_from_ods
from pathlib import Path

# Lade Antennensystem
antenna_system = load_omen_data(Path('input/OMEN R37 clean.xls'))

# Lade Patterns
patterns = load_patterns_from_ods(
    Path('msi-files/Antennendämpfungen Hybrid AIR3268 R5.ods'),
    antenna_system
)

for key, pattern in patterns.items():
    print(f'\n{key}:')
    print(f'  V-Pattern Winkel: min={pattern.v_angles.min():.1f}°, max={pattern.v_angles.max():.1f}°')
    print(f'  V-Pattern Länge: {len(pattern.v_angles)} Werte')
    print(f'  V-Gains bei min Winkel ({pattern.v_angles[0]:.1f}°): {pattern.v_gains[0]:.2f} dB')
    print(f'  V-Gains bei max Winkel ({pattern.v_angles[-1]:.1f}°): {pattern.v_gains[-1]:.2f} dB')
    print(f'  V-Gains Bereich: {pattern.v_gains.min():.2f} bis {pattern.v_gains.max():.2f} dB')

    # Finde Winkel mit geringster Dämpfung (stärkste Energie)
    min_idx = pattern.v_gains.argmin()
    print(f'  Stärkste Energie bei: {pattern.v_angles[min_idx]:.1f}° (Dämpfung: {pattern.v_gains[min_idx]:.2f} dB)')
    break
