"""
GPARC - Application Flask autonome de Gestion du Parc Informatique
Compatible avec le mode bureau (type green-dz) :
- Démarrage direct avec 'python app.py'
- Accès immédiat sur http://127.0.0.1:5000 sans configuration complexe
- Base de données SQLite automatique (gparc.db) avec données d'exemple complètes
- Interface web moderne intégrée (⚡ Interface Simple & Tableau de bord)
- Fiches d'interventions imprimables & gestion des photos d'équipements
"""

import os
import webbrowser
import socket
import json
import time
from threading import Timer
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Définition du chemin de la base de données SQLite
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Si on est dans le dossier flask_app, remonter d'un cran si ../data existe, sinon créer localement
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, '../data'))
if not os.path.exists(DATA_DIR):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except Exception:
        DATA_DIR = os.path.join(BASE_DIR, 'data')
        os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, 'gparc.db')

def get_db():
    # timeout : si la base est momentanément verrouillée par une autre écriture,
    # SQLite patiente jusqu'à 15s au lieu d'échouer immédiatement avec "database is locked".
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL : autorise les lectures concurrentes pendant une écriture (au lieu de verrouiller
    # tout le fichier). Essentiel dès que plusieurs postes utilisent l'app en même temps.
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn

def log_affectation(cur, id_mat, action, id_str, id_uti, ancien_id_str=None, ancien_id_uti=None, obs=''):
    """Enregistre un événement dans l'historique d'affectation."""
    mat = cur.execute(
        "SELECT id_model_mat, id_typ_mat, num_inv, num_ser FROM materiel WHERE id_mat = ?",
        (id_mat,)
    ).fetchone()
    if not mat:
        return
