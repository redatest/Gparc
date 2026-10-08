"""Services métier du workflow de réforme des équipements."""


VALID_REFORM_STATES = ("AUCUNE", "PROPOSEE", "REFORME")


def prepare_reform(cur, data, existing, today):
    """Valide et normalise les données de réforme sans modifier la base."""
    reforme_update = "etat_reforme" in data
    etat_reforme = (
        data.get("etat_reforme")
        if reforme_update
        else (existing["etat_reforme"] or "AUCUNE")
    )
    motif_reforme = (
        data.get("motif_reforme")
        if reforme_update
        else existing["motif_reforme"]
    )
    date_reforme = (
        data.get("date_reforme")
        if reforme_update
        else existing["date_reforme"]
    )
    annee_reforme = (
        data.get("annee_reforme")
        if reforme_update
        else existing["annee_reforme"]
    )
    lot_reforme = (
        data.get("lot_reforme")
        if reforme_update
        else existing["lot_reforme"]
    )

    if etat_reforme not in VALID_REFORM_STATES:
        raise ValueError("État de réforme invalide.")

    if etat_reforme == "REFORME":
        if not date_reforme:
            raise ValueError("La date de réforme est obligatoire.")
        if not annee_reforme:
            raise ValueError("L'année de réforme est obligatoire.")
        try:
            annee_reforme = int(annee_reforme)
        except (TypeError, ValueError):
            raise ValueError("L'année de réforme doit être un nombre valide.")
        if annee_reforme < 2000 or annee_reforme > 2100:
            raise ValueError(
                "L'année de réforme doit être comprise entre 2000 et 2100."
            )
        if not lot_reforme or not str(lot_reforme).strip():
            raise ValueError("Le N° de lot de réforme est obligatoire.")
        if not motif_reforme or not str(motif_reforme).strip():
            raise ValueError("Le motif de réforme est obligatoire.")

        lot_reforme = str(lot_reforme).strip()
        lot_ref = cur.execute(
            """SELECT id_param
               FROM parametres_materiel
               WHERE categorie = 'lot_reforme'
                 AND archiv = 'N'
                 AND LOWER(TRIM(valeur)) = LOWER(TRIM(?))
               LIMIT 1""",
            (lot_reforme,),
        ).fetchone()
        if not lot_ref:
            raise ValueError(
                "Le N° de lot sélectionné n'existe pas dans le référentiel des lots de réforme."
            )

        date_proposition = existing["date_proposition_reforme"] or today

    elif etat_reforme == "PROPOSEE":
        date_proposition = today
        date_reforme = None
        annee_reforme = None
        lot_reforme = None
        motif_reforme = None

    else:
        date_proposition = None
        date_reforme = None
        annee_reforme = None
        lot_reforme = None
        motif_reforme = None

    return {
        "reforme_update": reforme_update,
        "etat_reforme": etat_reforme,
        "motif_reforme": motif_reforme,
        "date_reforme": date_reforme,
        "annee_reforme": annee_reforme,
        "lot_reforme": lot_reforme,
        "date_proposition": date_proposition,
        "date_validation": None,
        "decision": None,
        "pv_reforme": None,
    }


def status_for_reform(etat_reforme, reforme_update, existing_status, requested_status):
    """Détermine le statut matériel associé au workflow de réforme."""
    if reforme_update:
        return {
            "AUCUNE": "ES",
            "PROPOSEE": "PR",
            "REFORME": "RF",
        }.get(etat_reforme, "ES")

    return requested_status if requested_status is not None else (existing_status or "ES")
