"""Accès et initialisation de la base SQLite de GPARC."""

import os
import sqlite3

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

try:
    from .database_schema import SCHEMA_SQL
except ImportError:  # Exécution directe depuis flask_app/
    from database_schema import SCHEMA_SQL

try:
    from .database_migrations import run_migrations
except ImportError:  # Exécution directe depuis flask_app/
    from database_migrations import run_migrations

try:
    from .database_seed import seed_default_parameters
except ImportError:  # Exécution directe depuis flask_app/
    from database_seed import seed_default_parameters

try:
    from .database_demo_seed import seed_demo_data
except ImportError:  # Exécution directe depuis flask_app/
    from database_demo_seed import seed_demo_data

try:
    from .database_reference_sync import sync_reference_data
except ImportError:  # Exécution directe depuis flask_app/
    from database_reference_sync import sync_reference_data

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

def init_db():
    """Initialise le schéma SQLite et les données de démonstration si la base est neuve."""
    conn = get_db()
    try:
        cur = conn.cursor()

        cur.executescript(SCHEMA_SQL)
        run_migrations(cur)
        seed_default_parameters(cur)
        seed_demo_data(cur)
        sync_reference_data(cur)

        conn.commit()
    finally:
        conn.close()
