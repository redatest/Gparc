"""Migrations de compatibilité pour les bases SQLite GPARC existantes."""


def run_migrations(cur):
    """Ajoute les colonnes manquantes et harmonise les anciens codes."""
    # Migrations légères pour les bases GPARC déjà existantes.
    # CREATE TABLE IF NOT EXISTS ne modifie pas une table déjà présente :
    # on complète donc explicitement les colonnes ajoutées dans les versions
    # récentes de l'application.
    mat_columns = {row[1] for row in cur.execute("PRAGMA table_info(materiel)").fetchall()}
    if 'marque_mat' not in mat_columns:
        cur.execute("ALTER TABLE materiel ADD COLUMN marque_mat TEXT")
    if 'dat_mod' not in mat_columns:
        # Nullable volontairement : SQLite n'autorise pas toujours
        # l'ajout d'un DEFAULT CURRENT_TIMESTAMP via ALTER TABLE.
        cur.execute("ALTER TABLE materiel ADD COLUMN dat_mod DATETIME")
        cur.execute("UPDATE materiel SET dat_mod = COALESCE(dat_cre, CURRENT_TIMESTAMP) WHERE dat_mod IS NULL")
    if 'etat_reforme' not in mat_columns:
        cur.execute("ALTER TABLE materiel ADD COLUMN etat_reforme TEXT DEFAULT 'AUCUNE'")
        cur.execute("UPDATE materiel SET etat_reforme = 'AUCUNE' WHERE etat_reforme IS NULL")
    if 'motif_reforme' not in mat_columns:
        cur.execute("ALTER TABLE materiel ADD COLUMN motif_reforme TEXT")
    if 'date_proposition_reforme' not in mat_columns:
        cur.execute("ALTER TABLE materiel ADD COLUMN date_proposition_reforme DATE")
    if 'date_validation_reforme' not in mat_columns:
        cur.execute("ALTER TABLE materiel ADD COLUMN date_validation_reforme DATE")
    if 'date_reforme' not in mat_columns:
        cur.execute("ALTER TABLE materiel ADD COLUMN date_reforme DATE")
    if 'annee_reforme' not in mat_columns:
        cur.execute("ALTER TABLE materiel ADD COLUMN annee_reforme INTEGER")
    if 'lot_reforme' not in mat_columns:
        cur.execute("ALTER TABLE materiel ADD COLUMN lot_reforme TEXT")
    if 'decision_reforme' not in mat_columns:
        cur.execute("ALTER TABLE materiel ADD COLUMN decision_reforme TEXT")
    if 'pv_reforme' not in mat_columns:
        cur.execute("ALTER TABLE materiel ADD COLUMN pv_reforme TEXT")
    if 'statut_mat' not in mat_columns:
        cur.execute("ALTER TABLE materiel ADD COLUMN statut_mat TEXT DEFAULT 'ES'")
    # Séparation stricte entre le statut de cycle de vie et l'état physique.
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

