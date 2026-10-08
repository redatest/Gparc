"""Services métier pour l'affectation des équipements."""

from .equipment_history import log_affectation


ASSIGNMENT_ERRORS = {
    "structure": "Structure invalide.",
    "user": "Utilisateur assigné invalide.",
}


def resolve_assignment(cur, data, existing):
    """Résout et valide la structure et l'utilisateur assignés."""
    id_str = data.get("id_str") if "id_str" in data else existing["id_str"]
    id_uti = data.get("id_uti") if "id_uti" in data else existing["id_uti"]

    if id_str is not None and not cur.execute(
        "SELECT 1 FROM structures WHERE id_str = ? AND archiv = 'N'", (id_str,)
    ).fetchone():
        raise ValueError(ASSIGNMENT_ERRORS["structure"])

    if id_uti is not None and not cur.execute(
        "SELECT 1 FROM utilisateurs WHERE id_uti = ? AND archiv = 'N'", (id_uti,)
    ).fetchone():
        raise ValueError(ASSIGNMENT_ERRORS["user"])

    return id_str, id_uti


def record_assignment_changes(cur, mat_id, old_str, old_uti, id_str, id_uti):
    """Enregistre les changements d'affectation dans l'historique."""
    if (old_str is None and old_uti is None) and (id_str is not None or id_uti is not None):
        log_affectation(
            cur,
            mat_id,
            "NOUVELLE_AFFECTATION",
            id_str,
            id_uti,
            ancien_id_str=old_str,
            ancien_id_uti=old_uti,
            obs="Nouvelle affectation de l’équipement",
        )
        return

    if old_str != id_str:
        log_affectation(
            cur,
            mat_id,
            "CHANGEMENT_STRUCTURE",
            id_str,
            id_uti,
            ancien_id_str=old_str,
            ancien_id_uti=old_uti,
            obs="Changement de structure / direction",
        )

    if old_uti != id_uti:
        log_affectation(
            cur,
            mat_id,
            "CHANGEMENT_UTILISATEUR",
            id_str,
            id_uti,
            ancien_id_str=old_str,
            ancien_id_uti=old_uti,
            obs="Changement d’utilisateur assigné",
        )
