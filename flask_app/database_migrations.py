"""Migrations de compatibilité pour les bases SQLite GPARC existantes."""

try:
    from .database_migration_repair_locations import migrate_repair_locations
except ImportError:  # Exécution directe depuis flask_app/
    from database_migration_repair_locations import migrate_repair_locations

try:
    from .database_migration_panne import migrate_panne
except ImportError:  # Exécution directe depuis flask_app/
    from database_migration_panne import migrate_panne

try:
    from .database_migration_materiel import migrate_materiel
except ImportError:  # Exécution directe depuis flask_app/
    from database_migration_materiel import migrate_materiel


def run_migrations(cur):
    """Ajoute les colonnes manquantes et harmonise les anciens codes."""
    migrate_materiel(cur)

    migrate_repair_locations(cur)

    migrate_panne(cur)

    # Migration légère de l'historique d'affectation.
    affect_columns = {row[1] for row in cur.execute("PRAGMA table_info(affect_mat)").fetchall()}
    if 'action_aff' not in affect_columns:
        cur.execute("ALTER TABLE affect_mat ADD COLUMN action_aff TEXT DEFAULT 'NOUVELLE_AFFECTATION'")
    if 'ancien_id_str' not in affect_columns:
        cur.execute("ALTER TABLE affect_mat ADD COLUMN ancien_id_str INTEGER")
    if 'ancien_id_uti' not in affect_columns:
        cur.execute("ALTER TABLE affect_mat ADD COLUMN ancien_id_uti INTEGER")

