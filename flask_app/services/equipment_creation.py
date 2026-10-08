"""Services métier pour la création des équipements."""


from datetime import datetime

from .equipment_assignment import record_assignment_changes
from .equipment_references import resolve_model, validate_brand


REFORM_CREATION_ERROR = (
    "La réforme d'un équipement se déclare depuis la rubrique « Réforme »."
)


def create_materiel(cur, data):
    """Crée un équipement et retourne son identifiant."""
    marque = (data.get("marque_mat") or "").strip()
    try:
        validate_brand(cur, marque)
    except ValueError:
        raise

    id_model = data.get("id_model_mat") or None
    model_name = (data.get("model_mat_name") or "").strip()
    id_typ = data.get("id_typ_mat") or None

    requested_reforme = data.get("etat_reforme") or "AUCUNE"
    if requested_reforme != "AUCUNE":
        raise ValueError(REFORM_CREATION_ERROR)

    id_model = resolve_model(cur, marque, id_model, model_name, id_typ)

    cur.execute(
        """
        INSERT INTO materiel (
            id_str, id_typ_mat, id_model_mat, marque_mat, num_inv, num_ser, etat_mat, obs_mat,
            ram, disk, cpu, se, ordi, ip, id_uti, image_url, etat_reforme, motif_reforme,
            date_proposition_reforme, date_validation_reforme, date_reforme, decision_reforme, pv_reforme
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data.get("id_str") or None,
            id_typ,
            id_model,
            marque or None,
            data.get("num_inv", f"INV-{datetime.now().strftime('%y%m%d%H%M')}"),
            data.get("num_ser", f"SN-{datetime.now().strftime('%y%m%d%H%M')}"),
            "BON",
            data.get("obs_mat", ""),
            data.get("ram", 16),
            data.get("disk", 512),
            data.get("cpu", "Intel Core i5/i7"),
            data.get("se", "Windows 11 Pro"),
            data.get("ordi", ""),
            data.get("ip", ""),
            data.get("id_uti") or None,
            data.get("image_url", ""),
            "AUCUNE",
            None,
            None,
            None,
            None,
            None,
            None,
        ),
    )
    last_id = cur.lastrowid

    if data.get("id_str") or data.get("id_uti"):
        record_assignment_changes(
            cur,
            last_id,
            None,
            None,
            data.get("id_str") or None,
            data.get("id_uti") or None,
        )

    return last_id
