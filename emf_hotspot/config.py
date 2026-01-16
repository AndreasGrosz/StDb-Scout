"""
EMF-Hotspot-Finder: Konfiguration und Konstanten
"""

# NISV Anlagegrenzwert (AGW) für Mobilfunk
AGW_LIMIT_VM = 5.0  # V/m

# Physikalische Konstanten
SPEED_OF_LIGHT = 299792458  # m/s
FREE_SPACE_IMPEDANCE = 376.73  # Ohm

# E-Feld-Berechnung: E = sqrt(K * ERP) / distance
# Schweizer NISV-Praxis verwendet K=49 (validiert mit offiziellen StdB)
# International Standard wäre K=30
E_FIELD_CONSTANT = 49.0  # Schweizer NISV-Standard

# Standard-Parameter
DEFAULT_RESOLUTION_M = 1.0  # Fassaden-Raster in Metern (von 0.5m erhöht für bessere Performance)
DEFAULT_RADIUS_M = 200.0  # Suchradius um Antenne (von 100m erhöht für mehr Gebäude)
MIN_DISTANCE_M = 0.1  # Minimaler Abstand (verhindert Division durch 0)


# swissBUILDINGS3D API
SWISSTOPO_WFS_URL = "https://wms.geo.admin.ch/"
SWISSTOPO_BUILDINGS_LAYER = "ch.swisstopo.swissbuildings3d_3_0"

# Frequenzband-Mapping für Antennendiagramm-Dateien
FREQUENCY_BAND_MAPPING = {
    "700-900": "738-921",
    "738-921": "738-921",
    "1400-2600": "1427-2570",
    "1427-2570": "1427-2570",
    "1800-2600": "1427-2570",
    "3600": "3600",
}
