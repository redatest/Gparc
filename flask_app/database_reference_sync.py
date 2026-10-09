"""Synchronisation des référentiels de modèles, marques et matériels."""


def sync_reference_data(cur):
    """Synchronise les paramètres avec le référentiel des modèles existants."""
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
