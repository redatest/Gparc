"""Migration de compatibilité des colonnes et statuts du matériel."""


def migrate_materiel(cur):
    """Ajoute les colonnes matérielles manquantes et harmonise leurs statuts."""
    mat_columns = {row[1] for row in cur.execute("PRAGMA table_info(materiel)").fetchall()}
    additions = {
        'marque_mat': "TEXT",
        'dat_mod': "DATETIME",
        'etat_reforme': "TEXT DEFAULT 'AUCUNE'",
        'motif_reforme': "TEXT",
        'date_proposition_reforme': "DATE",
        'date_validation_reforme': "DATE",
        'date_reforme': "DATE",
        'annee_reforme': "INTEGER",
        'lot_reforme': "TEXT",
        'decision_reforme': "TEXT",
        'pv_reforme': "TEXT",
        'statut_mat': "TEXT DEFAULT 'ES'",
        # Legacy Oracle retirement fields are kept as first-class fields as well as in the raw archive.
        'dat_sortie': "DATE",
        'motif_sortie': "TEXT",
    }
    for name, declaration in additions.items():
        if name not in mat_columns:
            cur.execute("ALTER TABLE materiel ADD COLUMN " + name + " " + declaration)

    cur.execute("UPDATE materiel SET dat_mod = COALESCE(dat_mod, dat_cre, CURRENT_TIMESTAMP) WHERE dat_mod IS NULL")
    cur.execute("UPDATE materiel SET etat_reforme = 'AUCUNE' WHERE etat_reforme IS NULL")
    cur.execute("""
        UPDATE materiel
        SET statut_mat = CASE
            WHEN etat_reforme = 'PROPOSEE' THEN 'PR'
            WHEN etat_reforme = 'REFORME' THEN 'RF'
            ELSE COALESCE(NULLIF(statut_mat, ''), 'ES')
        END
        WHERE statut_mat IS NULL OR statut_mat = '' OR etat_reforme IN ('PROPOSEE','REFORME')
    """)
    cur.execute("""
        UPDATE materiel
        SET etat_mat = CASE
            WHEN etat_mat = 'OP' THEN 'BON'
            WHEN etat_mat IN ('PA','RE') THEN 'PANNE'
            WHEN etat_mat = 'SO' THEN 'BON'
            WHEN etat_mat IS NULL OR etat_mat = '' THEN 'BON'
            ELSE etat_mat
        END
    """)
