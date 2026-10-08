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
from threading import Timer
from flask import Flask
from flask_cors import CORS
try:
    from .routes.utilisateurs import utilisateurs_bp
except ImportError:
    from routes.utilisateurs import utilisateurs_bp
try:
    from .routes.types_materiel import types_materiel_bp
except ImportError:
    from routes.types_materiel import types_materiel_bp
try:
    from .routes.structures import structures_bp
except ImportError:
    from routes.structures import structures_bp
try:
    from .routes.parametres import parametres_bp
except ImportError:
    from routes.parametres import parametres_bp
try:
    from .routes.pannes import pannes_bp
except ImportError:
    from routes.pannes import pannes_bp
try:
    from .routes.oracle import oracle_bp
except ImportError:
    from routes.oracle import oracle_bp
try:
    from .routes.materiels import materiels_bp
except ImportError:  # Exécution directe de flask_app/app.py
    from routes.materiels import materiels_bp
try:
    from .routes.system import system_bp
except ImportError:
    from routes.system import system_bp
try:
    from .routes.web import web_bp
except ImportError:
    from routes.web import web_bp

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
