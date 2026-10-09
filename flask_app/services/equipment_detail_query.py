"""Requêtes de consultation détaillée d'un équipement."""


def get_materiel_by_id(cur, mat_id):
    """Retourne un équipement par son identifiant, ou None s'il n'existe pas."""
    return cur.execute(
        "SELECT * FROM materiel WHERE id_mat = ?",
        (mat_id,)
    ).fetchone()
