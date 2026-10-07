"""Lanceur principal de GPARC.

Usage:
    python app.py
"""
import os
from threading import Timer

try:
    from flask_app.app import app, init_db, open_browser
except ImportError as exc:
    print("\n[ERREUR] Les dépendances Python ne sont pas installées.")
    print("Installez-les avec :")
    print("    pip install -r requirements.txt")
    print(f"Détail de l'erreur : {exc}")
    raise SystemExit(1)


if __name__ == "__main__":
    init_db()

    port = int(os.environ.get("PORT", 5000))
    print("=" * 65)
    print("  GPARC - Gestion du Parc Informatique & Pannes")
    print(f"  Serveur accessible sur : http://127.0.0.1:{port}")
    print("  Base SQLite locale : data/gparc.db")
    print("=" * 65)

    Timer(1.2, open_browser).start()
    app.run(host="0.0.0.0", port=port, debug=True)
