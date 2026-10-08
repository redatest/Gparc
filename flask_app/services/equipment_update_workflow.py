"""Préparation métier des mises à jour d'équipements."""


from .equipment_references import validate_brand, resolve_model, validate_model
from .equipment_validation import (
    validate_equipment_type,
    validate_equipment_state,
    validate_equipment_status,
)
from .equipment_assignment import resolve_assignment
from .equipment_reform import prepare_reform, status_for_reform


def prepare_equipment_update(cur, data, existing, today):
    """Valide et normalise les données avant la persistance d'un équipement.

    Cette fonction ne fait ni commit ni fermeture de connexion.
    Elle conserve l'ordre métier du workflow historique de la route.
    """
    marque = (
        data.get("marque_mat")
        if "marque_mat" in data
        else existing["marque_mat"] or ""
    ).strip()
    validate_brand(cur, marque)

    id_typ = data.get("id_typ_mat") if "id_typ_mat" in data else existing["id_typ_mat"]
    id_model = (
        data.get("id_model_mat")
        if "id_model_mat" in data
        else existing["id_model_mat"]
    )
    model_name = (data.get("model_mat_name") or "").strip()
    id_model = resolve_model(cur, marque, id_model, model_name, id_typ)

    id_str, id_uti = resolve_assignment(cur, data, existing)
    validate_equipment_type(cur, id_typ)

    reform = prepare_reform(cur, data, existing, today)

    validate_model(cur, id_model, marque, id_typ)

    reforme_update = reform["reforme_update"]
    etat_reforme = reform["etat_reforme"]
    statut_mat = status_for_reform(
        etat_reforme,
        reforme_update,
        existing["statut_mat"],
        data.get("statut_mat") if "statut_mat" in data else None,
    )
    etat_mat = (
        data.get("etat_mat")
        if "etat_mat" in data
        else existing["etat_mat"]
    )

    validate_equipment_state(etat_mat)
    validate_equipment_status(statut_mat)

    return {
        "marque": marque,
        "id_model": id_model,
        "id_typ": id_typ,
        "id_str": id_str,
        "id_uti": id_uti,
        "etat_mat": etat_mat,
        "statut_mat": statut_mat,
        **reform,
    }
