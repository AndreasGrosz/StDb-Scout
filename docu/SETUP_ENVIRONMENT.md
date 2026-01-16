# Python Virtual Environment Setup

## Problem
Packages wurden möglicherweise global installiert und können mit anderen Projekten kollidieren.

## Lösung: Virtuelles Environment (venv)

---

## 1️⃣ Aktuellen Status prüfen

### Welche Packages sind global installiert?
```bash
pip list | grep -E "numpy|pandas|scipy|pyvista|matplotlib|lxml|openpyxl"
```

Oder prüfe welche in diesem Projekt verwendet werden:
```bash
python3 -c "import numpy; print('numpy:', numpy.__version__, numpy.__file__)"
python3 -c "import pandas; print('pandas:', pandas.__version__, pandas.__file__)"
python3 -c "import pyvista; print('pyvista:', pyvista.__version__)"
```

Falls `__file__` nicht `/usr/lib/` oder `/usr/local/` enthält, sind sie im user-space (`~/.local/`).

---

## 2️⃣ Virtuelles Environment erstellen

### Erstelle venv im Projekt-Root
```bash
cd /media/synology/files/projekte/kd0241-py/geo-plot

# Python 3 venv erstellen
python3 -m venv venv
```

Dies erstellt:
```
geo-plot/
├── venv/                  # Isoliertes Environment
│   ├── bin/              # python, pip Executables
│   ├── lib/              # Packages hier isoliert
│   └── pyvenv.cfg
├── requirements.txt
└── emf_hotspot/
```

---

## 3️⃣ Environment aktivieren

```bash
# Aktivieren
source venv/bin/activate

# Prompt ändert sich zu:
(venv) user@host:~/geo-plot$
```

**Wichtig:** Nach jedem Terminal-Neustart muss das venv aktiviert werden!

---

## 4️⃣ Dependencies installieren

### Im aktivierten venv:
```bash
# Upgrade pip zuerst
pip install --upgrade pip

# Installiere alle Dependencies
pip install -r requirements.txt
```

### Installation überprüfen:
```bash
pip list
```

Sollte zeigen:
```
Package         Version   Location
--------------- --------- ----------------------------------
numpy           1.26.3    /path/to/venv/lib/python3.10/...
pandas          2.1.4     /path/to/venv/lib/python3.10/...
pyvista         0.43.1    /path/to/venv/lib/python3.10/...
...
```

---

## 5️⃣ Projekt nutzen (mit venv)

### Immer venv aktivieren:
```bash
source venv/bin/activate
```

### Dann normales Arbeiten:
```bash
# Scripts ausführen
python3 -m emf_hotspot.main input/OMEN\ R37\ clean.xls -o output

# Oder direkt
python3 validate_omen.py

# Tests
python3 -m pytest tests/
```

### Environment deaktivieren:
```bash
deactivate
```

---

## 6️⃣ Globale Packages entfernen (optional)

**⚠️ NUR wenn keine anderen Projekte diese nutzen!**

### Prüfe zuerst andere Python-Projekte:
```bash
# Suche alle Python-Projekte
find /media/synology/files/projekte -name "*.py" -type f | head -20

# Prüfe deren Imports
grep -r "import numpy" /media/synology/files/projekte/kd0241-py/
```

### Falls sicher, dass nur dieses Projekt betroffen:
```bash
# OHNE aktiviertes venv (globaler pip):
pip uninstall numpy pandas scipy pyvista matplotlib lxml openpyxl xlrd

# Oder alle auf einmal:
pip uninstall -y numpy pandas scipy pyvista matplotlib lxml openpyxl xlrd
```

### User-installed packages entfernen:
```bash
# Falls in ~/.local/ installiert:
pip uninstall --user numpy pandas scipy pyvista matplotlib lxml openpyxl xlrd
```

---

## 7️⃣ IDE/Editor konfigurieren

### VS Code:
1. `Ctrl+Shift+P` → "Python: Select Interpreter"
2. Wähle: `./venv/bin/python`
3. VS Code nutzt automatisch venv

### PyCharm:
1. File → Settings → Project → Python Interpreter
2. Add Interpreter → Existing Environment
3. Wähle: `/path/to/geo-plot/venv/bin/python`

### Vim/Neovim:
```vim
" In .vimrc oder init.vim:
let g:python3_host_prog = '/path/to/geo-plot/venv/bin/python'
```

---

## 8️⃣ Git Integration

### venv NICHT committen:
```bash
# Falls noch nicht in .gitignore:
echo "venv/" >> .gitignore
echo "*.pyc" >> .gitignore
echo "__pycache__/" >> .gitignore
echo ".pytest_cache/" >> .gitignore
```

### Andere Developer:
```bash
# Klonen
git clone <repo>
cd geo-plot

# Eigenes venv erstellen
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 9️⃣ Automatisches venv-Aktivieren (optional)

### Mit direnv (empfohlen):
```bash
# Installiere direnv
sudo apt install direnv  # oder: brew install direnv

# In ~/.bashrc oder ~/.zshrc:
eval "$(direnv hook bash)"  # oder zsh

# Im Projekt-Root:
echo "source venv/bin/activate" > .envrc
direnv allow

# Jetzt automatisch aktiviert beim cd geo-plot/
```

### Mit Shell-Alias:
```bash
# In ~/.bashrc oder ~/.zshrc:
alias geo-plot='cd /media/synology/files/projekte/kd0241-py/geo-plot && source venv/bin/activate'
```

Dann einfach:
```bash
geo-plot
# → CD und venv aktiviert
```

---

## 🔟 Checkliste

- [ ] `python3 -m venv venv` ausgeführt
- [ ] `source venv/bin/activate` funktioniert
- [ ] `pip install -r requirements.txt` erfolgreich
- [ ] `pip list` zeigt Packages in `venv/lib/...`
- [ ] Test: `python3 -m emf_hotspot.main --help` funktioniert
- [ ] `.gitignore` enthält `venv/`
- [ ] IDE auf venv-Python konfiguriert
- [ ] (Optional) Globale packages entfernt
- [ ] (Optional) Auto-Aktivierung eingerichtet

---

## ❓ Troubleshooting

### "ModuleNotFoundError" nach venv-Aktivierung
→ venv ist aktiv, aber Package nicht installiert:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### "command not found: python3"
→ Nutze expliziten Pfad:
```bash
/usr/bin/python3 -m venv venv
```

### Permission denied beim Package-Entfernen
→ Nutze `--user` Flag oder `sudo` (vorsichtig!):
```bash
pip uninstall --user <package>
```

### Packages bleiben global sichtbar
→ PATH-Reihenfolge prüfen:
```bash
which python3
# Sollte zeigen: /path/to/venv/bin/python3

echo $PATH
# venv/bin sollte ZUERST kommen
```

### PyVista OpenGL-Fehler im venv
→ System-Bibliotheken installieren:
```bash
sudo apt install libgl1-mesa-glx libxrender1
```

---

## 📚 Weitere Ressourcen

- Python venv Doku: https://docs.python.org/3/library/venv.html
- pip Doku: https://pip.pypa.io/en/stable/
- direnv: https://direnv.net/
- Poetry (Alternative): https://python-poetry.org/

---

## 🎯 Empfohlener Workflow (nach Setup)

```bash
# Terminal öffnen
cd /media/synology/files/projekte/kd0241-py/geo-plot

# venv aktivieren
source venv/bin/activate

# Arbeiten
python3 -m emf_hotspot.main input/OMEN\ R37\ clean.xls -o output

# Fertig
deactivate
```

Oder mit auto-activate (direnv):
```bash
# Einfach:
cd /media/synology/files/projekte/kd0241-py/geo-plot
# → venv automatisch aktiv

python3 -m emf_hotspot.main input/OMEN\ R37\ clean.xls -o output

cd ~
# → venv automatisch deaktiviert
```
