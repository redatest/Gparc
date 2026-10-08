"""
GPARC - Application Flask autonome de Gestion du Parc Informatique
Compatible avec le mode bureau (type green-dz) :
- Démarrage direct avec 'python app.py'
- Accès immédiat sur http://127.0.0.1:5000 sans configuration complexe
- Base de données SQLite automatique (gparc.db) avec données d'exemple complètes
- Interface web moderne intégrée (⚡ Interface Simple & Tableau de bord)
- Fiches d'interventions imprimables & gestion des photos d'équipements
"""

import webbrowser
from flask import Flask
from flask_cors import CORS
try:
    from .routes import (
        materiels_bp,
        pannes_bp,
        parametres_bp,
        utilisateurs_bp,
        types_materiel_bp,
        structures_bp,
        oracle_bp,
        system_bp,
        web_bp,
    )
except ImportError:  # Exécution directe de flask_app/app.py
    from routes import (
        materiels_bp,
        pannes_bp,
        parametres_bp,
        utilisateurs_bp,
        types_materiel_bp,
        structures_bp,
        oracle_bp,
        system_bp,
        web_bp,
    )

try:
    from .database import init_db
except ImportError:  # Exécution directe de flask_app/app.py
    from database import init_db

app = Flask(__name__)
CORS(app)

app.register_blueprint(materiels_bp)
app.register_blueprint(pannes_bp)
app.register_blueprint(parametres_bp)
app.register_blueprint(utilisateurs_bp)
app.register_blueprint(types_materiel_bp)
app.register_blueprint(structures_bp)
app.register_blueprint(oracle_bp)
app.register_blueprint(system_bp)
app.register_blueprint(web_bp)

# Initialiser la base dès le chargement du module
init_db()

# -----------------------------------------------------------------------------
# NAVIGATEUR
# -----------------------------------------------------------------------------

def open_browser():
    try:
        webbrowser.open_new('http://127.0.0.1:5000')
    except Exception:
        pass
