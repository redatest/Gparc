"""Migrations de compatibilité pour les bases SQLite GPARC existantes."""

try:
    from .database_migration_repair_locations import migrate_repair_locations
except ImportError:
    from database_migration_repair_locations import migrate_repair_locations

try:
    from .database_migration_panne import migrate_panne
except ImportError:
    from database_migration_panne import migrate_panne

try:
    from .database_migration_affectations import migrate_affectations
except ImportError:
    from database_migration_affectations import migrate_affectations

try:
    from .database_migration_materiel import migrate_materiel
except ImportError:
    from database_migration_materiel import migrate_materiel


def run_migrations(cur):
    """Ajoute les colonnes manquantes et prépare les comptes d'accès."""
    migrate_materiel(cur)
    migrate_repair_locations(cur)
    migrate_panne(cur)
    migrate_affectations(cur)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id_admin INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL COLLATE NOCASE UNIQUE,
            full_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('super_admin', 'admin')),
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
