# Schnellreferenz - StDb-Scout

Häufig genutzte Commands für den täglichen Workflow.

---

## Python Virtual Environment

```bash
# Venv aktivieren (Linux/Mac)
source venv/bin/activate

# Venv aktivieren (falls noch nicht erstellt)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Venv deaktivieren
deactivate
```

---

## EMF-Analyse starten

```bash
# Standard-Analyse
python -m emf_hotspot input/OMEN\ R37\ clean.xls

# Mit Zeiterfassung
time python -m emf_hotspot input/OMEN\ R37\ clean.xls

# Output umleiten
python -m emf_hotspot input/OMEN\ R37\ clean.xls 2>&1 | tee log.txt

# Environment-Check
python tools/check_environment.py
```

---

## ParaView Visualisierung

```bash
# ParaView mit Preset öffnen (empfohlen)
paraview --state=output/Wehntalerstrasse_464_8046_Zurich/paraview_preset.pvsm

# ParaView mit VTM-Datei
paraview output/Wehntalerstrasse_464_8046_Zurich/paraview-*.vtm

# Alle ParaView-Dateien finden
find output/ -name "*.pvsm"
find output/ -name "*.vtm"
```

---

## Git-Workflow

```bash
# Status prüfen
git status

# Log anzeigen
git log --oneline
git log --oneline --graph

# Änderungen ansehen
git diff
git diff HEAD~1  # Vergleich mit vorherigem Commit

# Pushen
git push

# Zu bestimmter Version zurück (nur ansehen)
git checkout <commit-hash>
git checkout main  # zurück zu main

# Zu bestimmter Version zurück (permanent)
git reset --hard <commit-hash>

# Tags anzeigen
git tag -l
git tag -l -n9  # mit Beschreibung
```

---

## Datei-Suche & Navigation

```bash
# Wichtige Dateien finden
find . -name "*.xls" -o -name "*.ods" | grep -v output

# Output-Ordner anzeigen
ls -lh output/*/

# Letzte Änderungen
ls -lt output/*/ | head -20

# Festplattenbelegung
du -sh output/
du -sh swisstopo/
```

---

## Projekt-Struktur

```
StDb-Scout/
├── README.md              # GitHub-Hauptdokumentation
├── QUICKREF.md           # Diese Datei
├── requirements.txt      # Python-Dependencies
├── setup_venv.sh         # Venv-Setup-Script
│
├── emf_hotspot/          # Haupt-Package
│   ├── main.py           # CLI-Einstiegspunkt
│   ├── models.py         # Datenmodelle
│   ├── config.py         # Konstanten
│   ├── loaders/          # Daten laden (OMEN, Gebäude, Patterns)
│   ├── geometry/         # Koordinaten, Winkel, Fassaden
│   ├── physics/          # E-Feld-Berechnung
│   ├── analysis/         # Validierung, Virtuelle Gebäude
│   └── output/           # Export (CSV, GeoJSON, ParaView)
│
├── docu/                 # Dokumentation
│   ├── BENUTZERHANDBUCH.md
│   ├── PFLICHTENHEFT.md
│   └── ...
│
├── tools/                # Helper-Scripts
│   ├── validate_omen.py
│   └── ...
│
├── input/                # Test-Input-Dateien
│   └── OMEN R37 clean.xls
│
└── output/               # Analyse-Ergebnisse (nicht in Git)
    └── Wehntalerstrasse_464_8046_Zurich/
        ├── ergebnisse.geojson
        ├── hotspots.csv
        ├── heatmap.png
        ├── paraview_preset.pvsm
        └── paraview-*.vtm
```

---

## Debugging & Validierung

```bash
# OMEN-Validierung
python tools/validate_omen.py

# Python-Fehler mit Traceback
python -m emf_hotspot input/OMEN*.xls 2>&1 | less

# Prozesse anzeigen (falls hängt)
ps aux | grep python
top

# Speicher prüfen
free -h
```

---

## Nützliche Aliases (optional)

In `~/.bashrc` oder `~/.bash_aliases` einfügen:

```bash
# StDb-Scout
alias stdb='cd /media/synology/files/projekte/kd0241-py/stdb-scout'
alias venv-stdb='source /media/synology/files/projekte/kd0241-py/stdb-scout/venv/bin/activate'
alias emf='python -m emf_hotspot'
alias pv='paraview --state=output/*/paraview_preset.pvsm'
```

Dann reicht:
```bash
stdb           # ins Projekt
venv-stdb      # Venv aktivieren
emf input/*.xls  # Analyse starten
```

---

## Tipps

1. **Tab-Completion**: Nutzen Sie die Tab-Taste für Pfade und Commands
2. **History**: Pfeiltaste hoch für letzte Commands, oder `history | grep paraview`
3. **Screen/Tmux**: Für lange Läufe, die nicht unterbrochen werden sollen
4. **Git-Tags**: `git tag v1.1` für wichtige Meilensteine

---

## Hilfe

```bash
# Projekt-Hilfe
python -m emf_hotspot --help

# Git-Hilfe
git help <command>

# Dieses Dokument öffnen
cat QUICKREF.md
```

---

**Zuletzt aktualisiert:** 2026-01-16
