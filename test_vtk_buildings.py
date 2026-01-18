"""Test: Prüfe ob Buildings im VTK vorhanden sind"""

import pyvista as pv
from pathlib import Path

vtm_file = Path("output/Wehntalerstrasse_464_8046_Zurich/paraview-250917_StDB_Zürich_.vtm")

print(f"Lade VTM: {vtm_file}")
mb = pv.read(vtm_file)

print(f"\nMultiBlock hat {mb.n_blocks} Blocks:")
for i in range(mb.n_blocks):
    block_name = mb.get_block_name(i)
    block = mb[i]
    if block:
        print(f"  Block {i}: {block_name}")
        print(f"    Typ: {type(block)}")
        print(f"    Punkte: {block.n_points if hasattr(block, 'n_points') else 'N/A'}")
        print(f"    Zellen: {block.n_cells if hasattr(block, 'n_cells') else 'N/A'}")
    else:
        print(f"  Block {i}: {block_name} - LEER")
