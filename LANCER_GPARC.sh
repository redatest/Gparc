#!/usr/bin/env bash
set -e

echo "======================================================================"
echo "         GPARC - APPLICATION DE GESTION DU PARC INFORMATIQUE"
echo "======================================================================"

python3 -c "import flask, flask_cors" >/dev/null 2>&1 || {
    echo "[ERREUR] Dependances manquantes. Executez : python3 -m pip install -r requirements.txt"
    exit 1
}

python3 app.py
