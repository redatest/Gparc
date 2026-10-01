"""
GPARC - Lanceur Racine pour le Bureau (Identique à green-dz)
Permet de lancer l'application directement depuis la racine avec :
    python app.py
"""

import sys
import os

# Ajouter flask_app au chemin d'importation
root_dir = os.path.dirname(os.path.abspath(__file__))
flask_dir = os.path.join(root_dir, 'flask_app')
if flask_dir not in sys.path:
    sys.path.insert(0, flask_dir)

try:
    import importlib.util
    flask_app_file = os.path.join(flask_dir, 'app.py')
    spec = importlib.util.spec_from_file_location("gparc_flask_module", flask_app_file)
    flask_module = importlib.util.module_from_spec(spec)
    sys.modules["gparc_flask_module"] = flask_module
    spec.loader.exec_module(flask_module)

    app = flask_module.app
    init_db = flask_module.init_db
    open_browser = flask_module.open_browser
    from threading import Timer

    if __name__ == '__main__':
        init_db()
        port = int(os.environ.get('PORT', 5000))
        print("=" * 65)
        print("  GPARC - Gestion du Parc Informatique & Pannes")
        print(f"  Serveur accessible sur : http://127.0.0.1:{port}")
        print("  Base SQLite locale : data/gparc.db")
        print("=" * 65)
        # Ouvre automatiquement le navigateur web comme green-dz
        

except ImportError as e:
    print("\n[ERREUR] Les dépendances Python ne sont pas installées.")
    print("Veuillez exécuter la commande suivante :")
    print("    pip install flask flask-cors\n")
    print(f"Détail de l'erreur : {e}")
    sys.exit(1)
