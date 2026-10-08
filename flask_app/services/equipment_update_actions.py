"""Orchestration de la mise à jour d'un équipement."""

from .equipment_assignment import record_assignment_changes
from .equipment_history import log_reforme
from .equipment_update import update_materiel


def apply_equipment_update(cur, mat_id, data, existing, prepared, today):
    """Persiste la mise à jour et enregistre les changements associés."""
    update_materiel(
        cur,
        mat_id,
        data,
        prepared["marque"],
        prepared["id_model"],
        prepared["id_typ"],
        prepared["id_str"],
        prepared["id_uti"],
        prepared["etat_mat"],
        prepared["statut_mat"],
        prepared["etat_reforme"],
        prepared["motif_reforme"],
        prepared["date_proposition"],
        prepared["date_validation"],
        prepared["date_reforme"],
        prepared["annee_reforme"],
        prepared["lot_reforme"],
        prepared["decision"],
        prepared["pv_reforme"],
    )

    record_assignment_changes(
        cur,
        mat_id,
        existing["id_str"],
        existing["id_uti"],
        prepared["id_str"],
        prepared["id_uti"],
    )

    if prepared["reforme_update"] and prepared["etat_reforme"] != (existing["etat_reforme"] or "AUCUNE"):
        log_reforme(
            cur,
            mat_id,
            prepared["etat_reforme"],
            prepared["date_reforme"]
            if prepared["etat_reforme"] == "REFORME" and prepared["date_reforme"]
            else today,
            prepared["motif_reforme"],
            existing["etat_reforme"] or "AUCUNE",
        )
