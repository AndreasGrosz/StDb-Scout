#!/usr/bin/env python3
"""
Prüft Python-Environment und installierte Packages.
Zeigt ob Packages global oder im venv installiert sind.
"""

import sys
import os
from pathlib import Path

# Terminal colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def check_package(package_name, optional=False):
    """Prüft ob Package installiert ist und wo."""
    try:
        module = __import__(package_name)
        location = Path(module.__file__).parent
        version = getattr(module, "__version__", "unknown")

        # Prüfe ob in venv
        in_venv = "venv" in str(location) or "virtual" in str(location)

        if in_venv:
            print(f"  {GREEN}✓{RESET} {package_name:20s} {version:10s} (venv: {location})")
        else:
            print(f"  {YELLOW}⚠{RESET} {package_name:20s} {version:10s} (global: {location})")

        return True
    except ImportError:
        if optional:
            print(f"  {BLUE}○{RESET} {package_name:20s} {'---':10s} (optional, nicht installiert)")
        else:
            print(f"  {RED}✗{RESET} {package_name:20s} {'---':10s} (FEHLT!)")
        return False


def main():
    print("=" * 80)
    print("EMF-Hotspot-Finder: Environment Check")
    print("=" * 80)
    print()

    # Shell Detection (check for Fish via FISH_VERSION env var)
    if os.environ.get('FISH_VERSION'):
        shell = 'fish'
    else:
        shell = os.environ.get('SHELL', '').split('/')[-1]

    # Python Info
    print(f"Python Version: {sys.version.split()[0]}")
    print(f"Python Path:    {sys.executable}")
    print(f"Shell:          {shell}")

    # Virtual Environment Check
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )

    if in_venv:
        print(f"Environment:    {GREEN}Virtual Environment (venv){RESET}")
        print(f"venv Location:  {sys.prefix}")
    else:
        print(f"Environment:    {YELLOW}Global (KEIN venv aktiv!){RESET}")
        print()
        print(f"{YELLOW}⚠️  WARNUNG: Kein Virtual Environment aktiv!{RESET}")

        # Shell-spezifische Anweisungen
        if shell == "fish":
            print(f"{YELLOW}   Aktiviere mit: source venv/bin/activate.fish{RESET}")
        else:
            print(f"{YELLOW}   Aktiviere mit: source venv/bin/activate{RESET}")

    print()
    print("-" * 80)
    print("REQUIRED PACKAGES:")
    print("-" * 80)

    # Core packages
    all_ok = True
    all_ok &= check_package("numpy")
    all_ok &= check_package("pandas")
    all_ok &= check_package("scipy")
    all_ok &= check_package("matplotlib")
    all_ok &= check_package("openpyxl")
    all_ok &= check_package("xlrd")

    print()
    print("-" * 80)
    print("OPTIONAL PACKAGES:")
    print("-" * 80)

    check_package("pyvista", optional=True)
    check_package("lxml", optional=True)

    print()
    print("=" * 80)

    if not in_venv:
        print(f"{YELLOW}EMPFEHLUNG: Nutze Virtual Environment!{RESET}")
        print()

        if shell == "fish":
            print("Setup:")
            print("  fish setup_venv.fish")
            print()
            print("Oder manuell:")
            print("  python3 -m venv venv")
            print("  source venv/bin/activate.fish")
            print("  pip install -r requirements.txt")
        else:
            print("Setup:")
            print("  bash setup_venv.sh")
            print()
            print("Oder manuell:")
            print("  python3 -m venv venv")
            print("  source venv/bin/activate")
            print("  pip install -r requirements.txt")
        print()
    elif all_ok:
        print(f"{GREEN}✅ Alle erforderlichen Packages installiert!{RESET}")
        print()
    else:
        print(f"{RED}❌ Fehlende Packages!{RESET}")
        print()
        print("Installiere mit:")
        print("  pip install -r requirements.txt")
        print()

    print("=" * 80)

    # Return exit code
    return 0 if (in_venv and all_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
