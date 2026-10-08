"""Services de validation métier des équipements."""


VALID_EQUIPMENT_STATES = ("BON", "PANNE", "IRREPARABLE")
VALID_EQUIPMENT_STATUSES = ("ES", "PR", "RF")


def validate_equipment_type(cur, id_typ):
    """Vérifie qu'un type de matériel actif existe."""
    if id_typ is not None and not cur.execute(
        "SELECT 1 FROM type_mat WHERE id_typ_mat = ? AND archiv = 'N'", (id_typ,)
    ).fetchone():
        raise ValueError("Type d'équipement invalide.")


def validate_equipment_state(etat_mat):
    """Vérifie l'état physique du matériel."""
    if etat_mat not in VALID_EQUIPMENT_STATES:
        raise ValueError(
            "État de l'équipement invalide. Valeurs autorisées : Bon, En panne, Irréparable."
        )


def validate_equipment_status(statut_mat):
    """Vérifie le statut administratif du matériel."""
    if statut_mat not in VALID_EQUIPMENT_STATUSES:
        raise ValueError(
            "Statut de l'équipement invalide. Valeurs autorisées : En service, Proposé à la réforme, Réformé."
        )
