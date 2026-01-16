#!/usr/bin/env python3
"""
Sucht Antennendiagramme in internationalen Datenbanken.

Quellen:
- ANFR (Frankreich): data.anfr.fr
- FCC (USA): fccid.io

Usage:
    python search_antenna_patterns.py AIR3268
    python search_antenna_patterns.py "Ericsson AIR" --source anfr
    python search_antenna_patterns.py RRU --source fcc
"""

import sys
import requests
from pathlib import Path
from typing import List, Dict, Optional
import json
import argparse


class ANFRSearcher:
    """Sucht in ANFR (Frankreich) Datenbank."""

    BASE_URL = "https://data.anfr.fr/api/explore/v2.1"

    def search_antenna_patterns(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Sucht nach Antennendiagrammen in ANFR.

        Args:
            query: Suchbegriff (z.B. "AIR3268", "Ericsson")
            limit: Max. Anzahl Ergebnisse

        Returns:
            Liste von Treffern mit Metadaten
        """
        results = []

        # Dataset 1: Supports (Antenna Supports)
        print(f"\n[ANFR] Suche in 'Supports d'antennes'...")
        supports = self._search_dataset(
            "donnees-sur-les-installations-radioelectriques-de-plus-de-5-watts-1",
            query,
            limit
        )
        results.extend(supports)

        # Dataset 2: Stations
        print(f"\n[ANFR] Suche in 'Stations radioélectriques'...")
        stations = self._search_dataset(
            "stations-radioelectriques",
            query,
            limit
        )
        results.extend(stations)

        return results

    def _search_dataset(self, dataset_id: str, query: str, limit: int) -> List[Dict]:
        """Sucht in einem spezifischen ANFR-Dataset."""
        url = f"{self.BASE_URL}/catalog/datasets/{dataset_id}/records"

        params = {
            "where": f'search(emetteur, "{query}")',  # Suche in Emitter-Feld
            "limit": limit,
            "timezone": "UTC"
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            records = data.get("results", [])

            print(f"  → {len(records)} Treffer gefunden")

            parsed = []
            for record in records:
                fields = record.get("record", {}).get("fields", {})
                parsed.append({
                    "source": "ANFR",
                    "dataset": dataset_id,
                    "emetteur": fields.get("emetteur", ""),
                    "site": fields.get("nom_site", ""),
                    "commune": fields.get("nom_com", ""),
                    "exploitant": fields.get("nom_op", ""),
                    "frequence": fields.get("frequence", ""),
                    "raw_data": fields
                })

            return parsed

        except requests.RequestException as e:
            print(f"  ❌ Fehler: {e}")
            return []


class FCCSearcher:
    """Sucht in FCC (USA) Datenbank via fccid.io."""

    BASE_URL = "https://fccid.io"

    def search_antenna_patterns(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Sucht nach FCC IDs für Antennen.

        Hinweis: fccid.io hat keine offizielle API. Wir suchen via Google/DuckDuckGo
        nach "site:fccid.io {query}" und extrahieren Links.

        Alternative: Direkter Zugriff auf FCC.gov Equipment Authorization Database.
        """
        print(f"\n[FCC] Suche nach '{query}'...")

        # Option 1: FCC Equipment Authorization System (direkt)
        results = self._search_fcc_direct(query, limit)

        return results

    def _search_fcc_direct(self, query: str, limit: int) -> List[Dict]:
        """
        Sucht direkt in FCC Equipment Authorization Database.

        API: https://api.fcc.gov/license-view/basicSearch/getLicenses
        """
        # FCC API für Equipment Authorization
        url = "https://publicapi.fcc.gov/equipment/search"

        params = {
            "query": query,
            "format": "json",
            "limit": limit
        }

        try:
            response = requests.get(url, params=params, timeout=10)

            # FCC API kann 404 zurückgeben wenn kein Public API aktiv
            # Fallback: Web-Scraping oder manuelle Links
            if response.status_code == 404:
                print("  ℹ️  FCC Public API nicht verfügbar")
                print(f"  → Manuelle Suche: https://fccid.io/search.php?q={query.replace(' ', '+')}")
                return [{
                    "source": "FCC",
                    "message": "Manuelle Suche erforderlich",
                    "url": f"https://fccid.io/search.php?q={query.replace(' ', '+')}"
                }]

            response.raise_for_status()
            data = response.json()

            # Parse Ergebnisse (FCC-spezifisches Format)
            results = []
            for item in data.get("results", [])[:limit]:
                results.append({
                    "source": "FCC",
                    "fcc_id": item.get("fcc_id", ""),
                    "applicant": item.get("applicant", ""),
                    "product": item.get("product_description", ""),
                    "grant_date": item.get("grant_date", ""),
                    "url": f"https://fccid.io/{item.get('fcc_id', '')}"
                })

            print(f"  → {len(results)} Treffer gefunden")
            return results

        except requests.RequestException as e:
            print(f"  ❌ Fehler: {e}")
            print(f"  → Manuelle Suche: https://fccid.io/search.php?q={query.replace(' ', '+')}")
            return []


def main():
    parser = argparse.ArgumentParser(
        description="Sucht Antennendiagramme in internationalen Datenbanken"
    )
    parser.add_argument('query', type=str, help='Suchbegriff (z.B. AIR3268, Ericsson)')
    parser.add_argument('--source', type=str, choices=['anfr', 'fcc', 'all'],
                       default='all', help='Datenquelle')
    parser.add_argument('--limit', type=int, default=20,
                       help='Max. Anzahl Ergebnisse pro Quelle')
    parser.add_argument('-o', '--output', type=Path,
                       help='Output JSON-Datei')

    args = parser.parse_args()

    all_results = []

    # ANFR (Frankreich)
    if args.source in ['anfr', 'all']:
        anfr = ANFRSearcher()
        anfr_results = anfr.search_antenna_patterns(args.query, args.limit)
        all_results.extend(anfr_results)

    # FCC (USA)
    if args.source in ['fcc', 'all']:
        fcc = FCCSearcher()
        fcc_results = fcc.search_antenna_patterns(args.query, args.limit)
        all_results.extend(fcc_results)

    # Ausgabe
    print(f"\n{'='*60}")
    print(f"ERGEBNISSE ({len(all_results)} Treffer)")
    print(f"{'='*60}")

    for i, result in enumerate(all_results, 1):
        print(f"\n{i}. [{result['source']}]")
        for key, value in result.items():
            if key != 'raw_data' and key != 'source':
                print(f"   {key}: {value}")

    # Speichere JSON
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Ergebnisse gespeichert: {args.output}")

    # Hilfreiche Links
    print(f"\n{'='*60}")
    print("WEITERFÜHRENDE LINKS")
    print(f"{'='*60}")
    print(f"ANFR (Frankreich):")
    print(f"  - Cartoradio: https://www.cartoradio.fr/")
    print(f"  - Open Data: https://data.anfr.fr/explore/")
    print(f"\nFCC (USA):")
    print(f"  - Equipment Search: https://fccid.io/search.php?q={args.query.replace(' ', '+')}")
    print(f"  - OET Equipment Authorization: https://www.fcc.gov/oet/ea/fccid")
    print(f"\nEricsson Product Catalog:")
    print(f"  - https://www.ericsson.com/en/portfolio/networks/ericsson-radio-system")

    if len(all_results) == 0:
        print(f"\n⚠️  Keine automatischen Treffer gefunden.")
        print(f"    Versuche manuelle Suche in den oben genannten Links.")
        sys.exit(1)


if __name__ == "__main__":
    main()
