"""Services métier pour les référentiels utilisés par les équipements."""


BRAND_NOT_FOUND = "La marque sélectionnée n'existe pas dans le référentiel des marques."


def validate_brand(cur, marque):
    """Vérifie qu'une marque active existe dans le référentiel."""
    if not marque:
        return

    brand_ref = cur.execute(
        "SELECT id_param FROM parametres_materiel "
        "WHERE categorie = 'marque' AND archiv = 'N' "
        "AND LOWER(TRIM(valeur)) = LOWER(?)",
        (marque,),
    ).fetchone()
    if not brand_ref:
        raise ValueError(BRAND_NOT_FOUND)


def resolve_model(cur, marque, id_model, model_name, id_typ):
    """Résout un modèle existant ou crée le modèle saisi s'il n'existe pas."""
    if not model_name or not marque:
        return id_model

    model_row = cur.execute(
        "SELECT id_model_mat FROM model_mat "
        "WHERE archiv = 'N' "
        "AND LOWER(TRIM(model_mat)) = LOWER(?) "
        "AND LOWER(TRIM(marque_mat)) = LOWER(?) "
        "AND (id_typ_mat = ? OR id_typ_mat IS NULL)",
        (model_name, marque, id_typ),
    ).fetchone()

    if model_row:
        return model_row["id_model_mat"]

    cur.execute(
        "INSERT INTO model_mat (marque_mat, model_mat, id_typ_mat) VALUES (?, ?, ?)",
        (marque, model_name, id_typ),
    )
    return cur.lastrowid


def validate_model(cur, id_model, marque, id_typ):
    """Vérifie qu'un modèle actif correspond à la marque et au type demandés."""
    if id_model is None:
        return

    model = cur.execute(
        "SELECT marque_mat, id_typ_mat FROM model_mat "
        "WHERE id_model_mat = ? AND archiv = 'N'",
        (id_model,),
    ).fetchone()
    if not model:
        raise ValueError("Modèle invalide.")

    if marque and (model["marque_mat"] or "").strip().lower() != marque.lower():
        raise ValueError("Le modèle sélectionné ne correspond pas à la marque.")

    if (
        id_typ is not None
        and model["id_typ_mat"] is not None
        and int(model["id_typ_mat"]) != int(id_typ)
    ):
        raise ValueError("Le modèle sélectionné ne correspond pas au type.")
