"""
geo.admin.ch API-Client für EGID- und Adress-Lookups
"""

import json
from typing import Optional, Dict
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError


def lookup_address_by_egid(egid: str, building_e: Optional[float] = None, building_n: Optional[float] = None) -> Optional[Dict[str, str]]:
    """
    Schlägt Adresse eines Gebäudes via geo.admin.ch API nach.

    Args:
        egid: Eidgenössischer Gebäudeidentifikator
        building_e: Optionale LV95 E-Koordinate des Gebäudes für Validierung
        building_n: Optionale LV95 N-Koordinate des Gebäudes für Validierung

    Returns:
        Dict mit {
            'street': str,
            'house_number': str,
            'postal_code': str,
            'city': str,
            'full_address': str
        }
        oder None bei Fehler oder wenn Adresse nicht validiert werden kann
    """
    if not egid or egid == "":
        return None

    # API-Endpoint: GWR-Layer (Gebäude- und Wohnungsregister)
    base_url = "https://api3.geo.admin.ch/rest/services/api/MapServer/find"

    params = {
        'layer': 'ch.bfs.gebaeude_wohnungs_register',
        'searchField': 'egid',
        'searchText': egid,
        'returnGeometry': 'true',  # Brauchen Geometrie für Distanz-Validierung
    }

    url = f"{base_url}?{urlencode(params)}"

    try:
        req = Request(url, headers={'User-Agent': 'EMF-Hotspot-Finder/1.0'})
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        # Parse Antwort
        if 'results' in data and len(data['results']) > 0:
            results = data['results']

            # Wenn wir Koordinaten haben und mehrere Ergebnisse zurückkommen,
            # validiere welches Ergebnis am nächsten liegt
            if building_e is not None and building_n is not None and len(results) > 1:
                import math

                closest_result = None
                min_distance = float('inf')

                for res in results:
                    # Extrahiere Koordinaten aus Geometrie
                    geom = res.get('geometry', {})

                    # API kann verschiedene Geometrie-Formate zurückgeben
                    res_e = None
                    res_n = None

                    if 'x' in geom and 'y' in geom:
                        # Format: {x: ..., y: ..., spatialReference: {wkid: ...}}
                        res_e = geom['x']
                        res_n = geom['y']
                        # Prüfe Koordinatensystem
                        spatial_ref = geom.get('spatialReference', {})
                        wkid = spatial_ref.get('wkid', 2056)

                        # Konvertiere LV03 (EPSG:21781) zu LV95 (EPSG:2056)
                        if wkid == 21781:
                            res_e += 2000000
                            res_n += 1000000

                    elif geom.get('type') == 'Point' and 'coordinates' in geom:
                        # Format: {type: 'Point', coordinates: [e, n]}
                        coords = geom['coordinates']
                        if len(coords) >= 2:
                            res_e, res_n = coords[0], coords[1]
                            # Annahme: Bereits in LV95

                    if res_e is not None and res_n is not None:
                        distance = math.sqrt((res_e - building_e)**2 + (res_n - building_n)**2)

                        if distance < min_distance:
                            min_distance = distance
                            closest_result = res

                # Wenn die Distanz zu groß ist (>100m), ist etwas falsch
                if min_distance > 100:
                    print(f"  WARNUNG: EGID {egid} - nächstes Ergebnis ist {min_distance:.0f}m entfernt (erwartet <100m). Adresse verworfen.")
                    return None

                # Nutze das nächstgelegene Ergebnis
                result = closest_result if closest_result else results[0]
            else:
                # Nur ein Ergebnis oder keine Koordinaten zur Validierung
                result = results[0]

            attrs = result.get('attributes', {})

            # Hilfsfunktion um Werte zu string zu konvertieren
            def to_str(value):
                if value is None:
                    return ''
                if isinstance(value, (list, tuple)) and len(value) > 0:
                    return str(value[0])
                return str(value)

            # Extrahiere Adress-Felder (Namen können variieren)
            street = to_str(attrs.get('strname', attrs.get('deinr', '')))
            house_num = to_str(attrs.get('deinr', attrs.get('strname', '')))
            postal_code = to_str(attrs.get('plz4', attrs.get('plz', '')))
            city = to_str(attrs.get('plzname', attrs.get('dplzname', '')))

            # Baue vollständige Adresse
            address_parts = []
            if street:
                address_parts.append(street)
            if house_num and house_num != street:
                address_parts.append(house_num)

            street_full = ' '.join(address_parts)

            city_parts = []
            if postal_code:
                city_parts.append(postal_code)
            if city:
                city_parts.append(city)

            city_full = ' '.join(city_parts)

            full_address = f"{street_full}, {city_full}" if street_full and city_full else street_full or city_full

            return {
                'street': street,
                'house_number': house_num,
                'postal_code': postal_code,
                'city': city,
                'full_address': full_address,
            }

    except (HTTPError, URLError, json.JSONDecodeError) as e:
        print(f"  WARNUNG: Adress-Lookup für EGID {egid} fehlgeschlagen: {e}")
        return None

    return None


def lookup_address_by_coordinates(e: float, n: float) -> Optional[Dict[str, str]]:
    """
    Schlägt Adresse via Koordinaten nach (Fallback wenn EGID nicht funktioniert).

    Args:
        e: LV95 Ost-Koordinate
        n: LV95 Nord-Koordinate

    Returns:
        Dict mit Adress-Feldern oder None
    """
    # Identify API für Reverse-Geocoding
    base_url = "https://api3.geo.admin.ch/rest/services/api/MapServer/identify"

    params = {
        'geometryType': 'esriGeometryPoint',
        'geometry': f'{e},{n}',
        'geometryFormat': 'geojson',
        'mapExtent': f'{e-100},{n-100},{e+100},{n+100}',
        'imageDisplay': '500,600,96',
        'tolerance': 50,
        'layers': 'all:ch.bfs.gebaeude_wohnungs_register',
        'returnGeometry': 'false',
        'sr': '2056',  # EPSG:2056 (LV95)
    }

    url = f"{base_url}?{urlencode(params)}"

    try:
        req = Request(url, headers={'User-Agent': 'EMF-Hotspot-Finder/1.0'})
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        # Parse Antwort
        if 'results' in data and len(data['results']) > 0:
            result = data['results'][0]
            attrs = result.get('attributes', {})

            # Extrahiere Adress-Felder (wie in lookup_address_by_egid)
            street = attrs.get('strname', attrs.get('deinr', ''))
            house_num = attrs.get('deinr', attrs.get('strname', ''))
            postal_code = attrs.get('plz4', attrs.get('plz', ''))
            city = attrs.get('plzname', attrs.get('dplzname', ''))

            # Baue vollständige Adresse
            address_parts = []
            if street:
                address_parts.append(street)
            if house_num and house_num != street:
                address_parts.append(house_num)

            street_full = ' '.join(address_parts)

            city_parts = []
            if postal_code:
                city_parts.append(postal_code)
            if city:
                city_parts.append(city)

            city_full = ' '.join(city_parts)

            full_address = f"{street_full}, {city_full}" if street_full and city_full else street_full or city_full

            return {
                'street': street,
                'house_number': house_num,
                'postal_code': postal_code,
                'city': city,
                'full_address': full_address,
            }

    except HTTPError as http_err:
        print(f"  WARNUNG: Koordinaten-Lookup bei {e:.0f}/{n:.0f} fehlgeschlagen: HTTP {http_err.code}")
        return None
    except (URLError, json.JSONDecodeError) as err:
        print(f"  WARNUNG: Koordinaten-Lookup bei {e:.0f}/{n:.0f} fehlgeschlagen: {err}")
        return None

    return None
