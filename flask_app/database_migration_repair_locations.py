"""Migration de compatibilité des lieux de réparation."""


def migrate_repair_locations(cur):
    """Ajoute et renseigne la catégorie des lieux de réparation."""
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
