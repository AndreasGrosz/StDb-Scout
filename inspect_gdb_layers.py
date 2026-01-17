"""Inspiziere alle Layer in der GDB-Datei"""

from pathlib import Path
import tempfile
import zipfile
from osgeo import ogr

gdb_path = Path.home() / ".cache" / "emf_hotspot" / "swissbuildings3d_2681_1252.gdb.zip"

print(f"Inspiziere GDB: {gdb_path.name}")

with tempfile.TemporaryDirectory() as tmpdir:
    tmppath = Path(tmpdir)

    # Entpacke
    with zipfile.ZipFile(gdb_path, 'r') as zip_ref:
        zip_ref.extractall(tmppath)

    # Finde .gdb
    gdb_dirs = list(tmppath.glob("*.gdb"))
    gdb_dir = gdb_dirs[0]

    # Öffne mit GDAL
    datasource = ogr.Open(str(gdb_dir))

    print(f"\nAnzahl Layer: {datasource.GetLayerCount()}")
    print("\n" + "="*60)

    for i in range(datasource.GetLayerCount()):
        layer = datasource.GetLayerByIndex(i)
        layer_name = layer.GetName()
        feature_count = layer.GetFeatureCount()

        print(f"\nLayer {i+1}: {layer_name}")
        print(f"  Features: {feature_count}")

        # Prüfe Geometrie-Typ des ersten Features
        if feature_count > 0:
            layer.ResetReading()
            feature = layer.GetNextFeature()
            if feature:
                geom = feature.GetGeometryRef()
                if geom:
                    print(f"  Geometrie: {geom.GetGeometryName()}")

                # Zeige erste paar Felder
                fields = []
                for j in range(min(5, feature.GetFieldCount())):
                    field_def = feature.GetFieldDefnRef(j)
                    fields.append(field_def.GetName())
                print(f"  Felder (erste 5): {', '.join(fields)}")

    datasource = None
