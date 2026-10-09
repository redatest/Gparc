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
    cur = conn.cursor()

    cur.executescript(SCHEMA_SQL)

    run_migrations(cur)

    seed_default_parameters(cur)

    seed_demo_data(conn, cur)

    # Synchroniser les marques du référentiel avec les modèles existants.
    brands = [r[0] for r in cur.execute("SELECT DISTINCT TRIM(marque_mat) FROM model_mat WHERE archiv = 'N' AND TRIM(marque_mat) <> ''").fetchall()]
    for brand in brands:
        exists = cur.execute("SELECT 1 FROM parametres_materiel WHERE categorie = 'marque' AND LOWER(TRIM(valeur)) = LOWER(?) AND archiv = 'N'", (brand,)).fetchone()
        if not exists:
            cur.execute("INSERT INTO parametres_materiel (categorie, valeur, description, ordre) VALUES ('marque', ?, 'Marque issue du référentiel des modèles', 0)", (brand,))

    cur.execute("""
        UPDATE materiel
        SET marque_mat = (SELECT mm.marque_mat FROM model_mat mm WHERE mm.id_model_mat = materiel.id_model_mat)
        WHERE (marque_mat IS NULL OR TRIM(marque_mat) = '') AND id_model_mat IS NOT NULL
    """)

    # Synchroniser le référentiel des modèles avec les paramètres.
    model_rows = cur.execute(
        "SELECT DISTINCT TRIM(model_mat) AS model_name FROM model_mat WHERE archiv = 'N' AND TRIM(model_mat) <> ''"
    ).fetchall()
    for row in model_rows:
        exists = cur.execute(
            "SELECT 1 FROM parametres_materiel WHERE categorie = 'modele' AND LOWER(TRIM(valeur)) = LOWER(?) AND archiv = 'N'",
            (row['model_name'],)
        ).fetchone()
        if not exists:
            cur.execute(
                "INSERT INTO parametres_materiel (categorie, valeur, description, ordre) VALUES ('modele', ?, 'Modèle issu du référentiel des équipements', 0)",
                (row['model_name'],)
            )

    conn.commit()
    conn.close()
