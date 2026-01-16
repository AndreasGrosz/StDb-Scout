#!/bin/bash
# Automatisches Setup für Python Virtual Environment
# EMF-Hotspot-Finder Projekt

set -e  # Exit bei Fehler

PROJECT_DIR="/media/synology/files/projekte/kd0241-py/geo-plot"
VENV_DIR="$PROJECT_DIR/venv"

echo "============================================"
echo "EMF-Hotspot-Finder: Environment Setup"
echo "============================================"
echo ""

# 1. Prüfe Python-Version
echo "[1/6] Prüfe Python-Version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.10"

if [[ $(echo -e "$PYTHON_VERSION\n$REQUIRED_VERSION" | sort -V | head -n1) != "$REQUIRED_VERSION" ]]; then
    echo "❌ Python $REQUIRED_VERSION oder höher erforderlich (gefunden: $PYTHON_VERSION)"
    exit 1
fi
echo "✅ Python $PYTHON_VERSION"

# 2. Prüfe ob venv bereits existiert
if [ -d "$VENV_DIR" ]; then
    echo ""
    echo "⚠️  Virtual Environment existiert bereits: $VENV_DIR"
    read -p "Neu erstellen? (löscht bestehendes venv) [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "[2/6] Lösche bestehendes venv..."
        rm -rf "$VENV_DIR"
    else
        echo "Abbruch. Nutze bestehendes venv."
        exit 0
    fi
fi

# 3. Erstelle venv
echo "[2/6] Erstelle Virtual Environment..."
python3 -m venv "$VENV_DIR"
echo "✅ venv erstellt: $VENV_DIR"

# 4. Aktiviere venv
echo "[3/6] Aktiviere Virtual Environment..."
source "$VENV_DIR/bin/activate"
echo "✅ venv aktiviert"

# 5. Upgrade pip
echo "[4/6] Upgrade pip..."
pip install --upgrade pip setuptools wheel -q
echo "✅ pip upgraded"

# 6. Installiere Dependencies
echo "[5/6] Installiere Dependencies..."
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    pip install -r "$PROJECT_DIR/requirements.txt" -q
    echo "✅ Dependencies installiert"
else
    echo "❌ requirements.txt nicht gefunden!"
    exit 1
fi

# 7. Test Installation
echo "[6/6] Teste Installation..."
python3 -c "import numpy; import pandas; import matplotlib; print('✅ Core packages OK')"
python3 -c "import pyvista; print('✅ PyVista OK')" 2>/dev/null || echo "⚠️  PyVista fehlt (optional)"
python3 -c "import lxml; print('✅ lxml OK')" 2>/dev/null || echo "⚠️  lxml fehlt (optional)"

echo ""
echo "============================================"
echo "✅ Setup abgeschlossen!"
echo "============================================"
echo ""
echo "Aktiviere venv mit:"
echo "  source venv/bin/activate"
echo ""
echo "Oder füge zu ~/.bashrc hinzu:"
echo "  alias geo-plot='cd $PROJECT_DIR && source venv/bin/activate'"
echo ""
echo "Dann einfach: geo-plot"
echo "============================================"

# Deaktiviere venv
deactivate
