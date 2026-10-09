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
    from .database_migration_affectations import migrate_affectations
except ImportError:  # Exécution directe depuis flask_app/
    from database_migration_affectations import migrate_affectations

try:
    from .database_migration_materiel import migrate_materiel
except ImportError:  # Exécution directe depuis flask_app/
    from database_migration_materiel import migrate_materiel


def run_migrations(cur):
    """Ajoute les colonnes manquantes et harmonise les anciens codes."""
    migrate_materiel(cur)

    migrate_repair_locations(cur)

    migrate_panne(cur)

    migrate_affectations(cur)

