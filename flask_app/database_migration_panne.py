"""Migration de compatibilité pour les enregistrements de panne."""


def migrate_panne(cur):
    """Ajoute les colonnes de réparation manquantes et harmonise les anciens codes."""
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
