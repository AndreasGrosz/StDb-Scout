"""
Laden von Katasterparzellen via geo.admin.ch API
"""

import json
from typing import List, Tuple, Optional
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from dataclasses import dataclass
import numpy as np


@dataclass
class Parcel:
    """Katasterparzelle (Liegenschaft/Grundstück)"""
    egrid: str  # Eidgenössischer Grundstücksidentifikator
    number: str  # Parzellennummer
    municipality_bfs: int  # BFS-Gemeindenummer
    canton: str  # Kanton (Kürzel)
    polygon: np.ndarray  # Shape (N, 2) - LV95 E, N Koordinaten
    bbox: Tuple[float, float, float, float]  # (min_e, min_n, max_e, max_n)


def load_parcels_in_radius(
    center_e: float,
    center_n: float,
    radius_m: float = 200.0
) -> List[Parcel]:
    """
    Lädt Katasterparzellen im Umkreis einer Position.

    Args:
        center_e: LV95 E-Koordinate des Zentrums
        center_n: LV95 N-Koordinate des Zentrums
        radius_m: Suchradius in Metern

    Returns:
        Liste von Parcel-Objekten
    """
    # API-Endpoint: geo.admin.ch Identify (Amtliche Vermessung)
    base_url = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify"

    # Bounding Box für Suche
    min_e = center_e - radius_m
    max_e = center_e + radius_m
    min_n = center_n - radius_m
    max_n = center_n + radius_m

    params = {
        'geometryType': 'esriGeometryEnvelope',
        'geometry': f'{min_e},{min_n},{max_e},{max_n}',
        'mapExtent': f'{min_e - 100},{min_n - 100},{max_e + 100},{max_n + 100}',
        'imageDisplay': '400,400,96',
        'tolerance': 10,
        'layers': 'all:ch.swisstopo-vd.amtliche-vermessung',
        'returnGeometry': 'true',
        'geometryFormat': 'geojson',
        'sr': '2056',  # EPSG:2056 (LV95)
    }

    url = f"{base_url}?{urlencode(params)}"

    try:
        req = Request(url, headers={'User-Agent': 'StDb-Scout/1.0'})
        with urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))

        parcels = []

        for feature in data.get('results', []):
            props = feature.get('properties', {})
            geom = feature.get('geometry', {})
            bbox_raw = feature.get('bbox', [])

            # Extrahiere Polygon-Koordinaten
            if geom.get('type') == 'Polygon':
                coords = geom.get('coordinates', [[]])[0]
            elif geom.get('type') == 'MultiPolygon':
                # Nimm den ersten Teil eines MultiPolygons
                coords = geom.get('coordinates', [[[]]])[0][0]
            else:
                continue

            if len(coords) < 3:
                continue

            # Konvertiere zu numpy array (N, 2) - nur E, N
            polygon = np.array([[c[0], c[1]] for c in coords])

            # Bounding Box
            if len(bbox_raw) >= 4:
                bbox = tuple(bbox_raw[:4])
            else:
                bbox = (
                    float(polygon[:, 0].min()),
                    float(polygon[:, 1].min()),
                    float(polygon[:, 0].max()),
                    float(polygon[:, 1].max())
                )

            # Erstelle Parcel-Objekt
            parcel = Parcel(
                egrid=props.get('egris_egrid', ''),
                number=props.get('number', props.get('name', '')),
                municipality_bfs=int(props.get('bfsnr', 0)),
                canton=props.get('ak', ''),
                polygon=polygon,
                bbox=bbox
            )

            parcels.append(parcel)

        return parcels

    except (HTTPError, URLError, json.JSONDecodeError) as e:
        print(f"  WARNUNG: Parzellen-Lookup fehlgeschlagen: {e}")
        return []


def get_parcel_center(parcel: Parcel) -> Tuple[float, float]:
    """Berechnet den Mittelpunkt einer Parzelle."""
    return (
        float(parcel.polygon[:, 0].mean()),
        float(parcel.polygon[:, 1].mean())
    )


def get_parcel_area(parcel: Parcel) -> float:
    """
    Berechnet die Fläche einer Parzelle in m².
    Verwendet Shoelace-Formel.
    """
    x = parcel.polygon[:, 0]
    y = parcel.polygon[:, 1]
    return 0.5 * abs(np.sum(x[:-1] * y[1:] - x[1:] * y[:-1]) + x[-1] * y[0] - x[0] * y[-1])
