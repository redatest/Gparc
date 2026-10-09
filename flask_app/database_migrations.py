"""Migrations de compatibilité pour les bases SQLite GPARC existantes."""

try:
    from .database_migration_materiel import migrate_materiel
except ImportError:  # Exécution directe depuis flask_app/
    from database_migration_materiel import migrate_materiel


def run_migrations(cur):
    """Ajoute les colonnes manquantes et harmonise les anciens codes."""
    migrate_materiel(cur)

    # Migration légère des lieux de réparation.
    lieu_columns = {row[1] for row in cur.execute("PRAGMA table_info(lieu_rep)").fetchall()}
    if 'categorie_lieu' not in lieu_columns:
        cur.execute("ALTER TABLE lieu_rep ADD COLUMN categorie_lieu TEXT DEFAULT 'EXTERIEUR'")
        cur.execute("""
            UPDATE lieu_rep
            SET categorie_lieu = CASE
                WHEN LOWER(nom_lieu_rep) LIKE '%atelier%' OR LOWER(nom_lieu_rep) LIKE '%interne%' THEN 'LOCAL'
                ELSE 'EXTERIEUR'
            END
        """)

    # Migration légère de la procédure de panne.
    # Les anciennes bases peuvent ne pas contenir les colonnes ajoutées
    # pour documenter complètement une réparation.
    panne_columns = {row[1] for row in cur.execute("PRAGMA table_info(panne)").fetchall()}
    if 'pieces_remplacees' not in panne_columns:
        cur.execute("ALTER TABLE panne ADD COLUMN pieces_remplacees TEXT")
    if 'recommandations' not in panne_columns:
        cur.execute("ALTER TABLE panne ADD COLUMN recommandations TEXT")
    if 'cout_rep' not in panne_columns:
        cur.execute("ALTER TABLE panne ADD COLUMN cout_rep REAL DEFAULT 0")
    # Harmonisation des anciens codes de traitement de panne.
    cur.execute("""
        UPDATE panne
        SET eta_pan = CASE
            WHEN eta_pan = 'EC' THEN 'EP'
            WHEN eta_pan = 'AT' THEN 'ER'
            WHEN eta_pan = 'NR' THEN 'IR'
            ELSE eta_pan
        END
        WHERE eta_pan IN ('EC','AT','NR')
    """)

    # Migration légère de l'historique d'affectation.
    affect_columns = {row[1] for row in cur.execute("PRAGMA table_info(affect_mat)").fetchall()}
    if 'action_aff' not in affect_columns:
        cur.execute("ALTER TABLE affect_mat ADD COLUMN action_aff TEXT DEFAULT 'NOUVELLE_AFFECTATION'")
    if 'ancien_id_str' not in affect_columns:
        cur.execute("ALTER TABLE affect_mat ADD COLUMN ancien_id_str INTEGER")
    if 'ancien_id_uti' not in affect_columns:
        cur.execute("ALTER TABLE affect_mat ADD COLUMN ancien_id_uti INTEGER")

