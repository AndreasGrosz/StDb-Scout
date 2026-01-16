"""
Utility-Funktionen für EMF-Hotspot-Finder
"""

import sys

# Terminal Colors
YELLOW = "\033[93m"
RED = "\033[91m"
GREEN = "\033[92m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"


def ask_yes_no(question: str, details: str = None, default: bool = False) -> bool:
    """
    Stellt eine farblich hervorgehobene Ja/Nein-Frage.

    Args:
        question: Die Hauptfrage
        details: Optional - Zusätzliche Details/Erklärung
        default: Standard-Antwort bei ENTER (True=Ja, False=Nein)

    Returns:
        True für Ja, False für Nein
    """
    print()
    print(f"{YELLOW}{BOLD}{'=' * 70}{RESET}")
    print(f"{YELLOW}{BOLD}⚠️  BENUTZER-EINGABE ERFORDERLICH{RESET}")
    print(f"{YELLOW}{BOLD}{'=' * 70}{RESET}")
    print()
    print(f"{BOLD}{question}{RESET}")

    if details:
        print()
        print(details)

    print()

    # Prompt mit Standard-Antwort
    if default:
        prompt = f"{GREEN}Fortfahren? [J/n]:{RESET} "
        valid_yes = ['j', 'y', 'ja', 'yes', '']
        valid_no = ['n', 'nein', 'no']
    else:
        prompt = f"{RED}Fortfahren? [j/N]:{RESET} "
        valid_yes = ['j', 'y', 'ja', 'yes']
        valid_no = ['n', 'nein', 'no', '']

    while True:
        try:
            response = input(prompt).strip().lower()

            if response in valid_yes:
                print(f"{GREEN}✓ Fortfahren{RESET}")
                print()
                return True
            elif response in valid_no:
                print(f"{RED}✗ Abgebrochen{RESET}")
                print()
                return False
            else:
                print(f"{RED}Bitte 'j' für Ja oder 'n' für Nein eingeben.{RESET}")
        except (EOFError, KeyboardInterrupt):
            # Bei Ctrl+C oder EOF: Abbrechen
            print()
            print(f"{RED}✗ Abgebrochen durch Benutzer{RESET}")
            print()
            return False


def warn_fallback(title: str, message: str, recommendation: str = None):
    """
    Zeigt eine farbige Fallback-Warnung an (ohne Frage).

    Args:
        title: Titel der Warnung
        message: Hauptnachricht
        recommendation: Optional - Empfehlung für den Benutzer
    """
    print()
    print(f"{YELLOW}{'=' * 70}{RESET}")
    print(f"{YELLOW}{BOLD}⚠️  {title}{RESET}")
    print(f"{YELLOW}{'=' * 70}{RESET}")
    print()
    print(message)

    if recommendation:
        print()
        print(f"{BLUE}💡 Empfehlung:{RESET}")
        print(recommendation)

    print(f"{YELLOW}{'=' * 70}{RESET}")
    print()


def error_and_exit(message: str, exit_code: int = 1):
    """
    Zeigt eine Fehlermeldung und beendet das Programm.

    Args:
        message: Fehlermeldung
        exit_code: Exit-Code (default: 1)
    """
    print()
    print(f"{RED}{BOLD}{'=' * 70}{RESET}")
    print(f"{RED}{BOLD}❌ FEHLER{RESET}")
    print(f"{RED}{BOLD}{'=' * 70}{RESET}")
    print()
    print(message)
    print()
    print(f"{RED}{BOLD}{'=' * 70}{RESET}")
    print()
    sys.exit(exit_code)
