"""Lecture et construction de l'historique d'un équipement."""


PANNE_STATUS = {
    "EP": "En panne",
    "ER": "En réparation",
    "RP": "Réparé",
    "IR": "Irréparable",
    "EC": "En panne",
    "AT": "En réparation",
    "NR": "Irréparable",
}

REFORME_LABELS = {
    "AUCUNE": "Remise en service",
    "PROPOSEE": "Proposé à la réforme",
    "REFORME": "Réformé",
}


def build_equipment_history(cur, mat_id):
    """Construit l'historique complet d'un équipement sans gérer la connexion."""
    events = []

    events.extend(_get_assignment_events(cur, mat_id))
    events.extend(_get_breakdown_events(cur, mat_id))
    events.extend(_get_reform_events(cur, mat_id))

    events.sort(
        key=lambda event: (
            event.get("date_evenement") or "",
            event.get("type_evenement") or "",
        ),
        reverse=True,
    )
    return events


def _get_assignment_events(cur, mat_id):
    rows = cur.execute(
        """
        SELECT a.id_aff_mat, a.dat_aff, a.action_aff, a.obs_aff,
               a.id_str, a.ancien_id_str, a.id_uti, a.ancien_id_uti,
               s.lib_str AS structure_nom, os.lib_str AS ancienne_structure_nom,
               u.nom_uti, u.pnom_uti, ou.nom_uti AS ancien_nom_uti,
               ou.pnom_uti AS ancien_pnom_uti
        FROM affect_mat a
        LEFT JOIN structures s ON a.id_str = s.id_str
        LEFT JOIN structures os ON a.ancien_id_str = os.id_str
        LEFT JOIN utilisateurs u ON a.id_uti = u.id_uti
        LEFT JOIN utilisateurs ou ON a.ancien_id_uti = ou.id_uti
        WHERE a.id_mat = ? AND a.archiv = 'N'
        ORDER BY a.dat_aff DESC, a.id_aff_mat DESC
        """,
        (mat_id,),
    ).fetchall()

    events = []
    for row in rows:
        data = dict(row)
        if data["action_aff"] == "NOUVELLE_AFFECTATION":
            libelle = "Nouvelle affectation"
            detail = data["structure_nom"] or "Structure non précisée"
            if data["nom_uti"]:
                detail += " — " + (
                    (data["pnom_uti"] or "") + " " + (data["nom_uti"] or "")
                ).strip()
        elif data["action_aff"] == "CHANGEMENT_STRUCTURE":
            libelle = "Changement de structure"
            detail = (
                f"{data['ancienne_structure_nom'] or 'Aucune structure'} → "
                f"{data['structure_nom'] or 'Aucune structure'}"
            )
        else:
            libelle = "Changement d’utilisateur"
            old_name = (
                (data["ancien_pnom_uti"] or "")
                + " "
                + (data["ancien_nom_uti"] or "")
            ).strip() or "Aucun utilisateur"
            new_name = (
                (data["pnom_uti"] or "")
                + " "
                + (data["nom_uti"] or "")
            ).strip() or "Aucun utilisateur"
            detail = f"{old_name} → {new_name}"

        events.append(
            {
                "type_evenement": "AFFECTATION",
                "date_evenement": data["dat_aff"],
                "libelle": libelle,
                "detail": detail,
                "obs": data["obs_aff"] or "",
            }
        )

    return events


def _get_breakdown_events(cur, mat_id):
    rows = cur.execute(
        """
        SELECT id_pan, dat_pan, diag_pan, eta_pan, tp, technicien,
               dat_env_rep, dat_ret_rep, obs_rep, pieces_remplacees,
               recommandations, cout_rep
        FROM panne
        WHERE id_mat = ? AND archiv = 'N'
        ORDER BY dat_pan DESC, id_pan DESC
        """,
        (mat_id,),
    ).fetchall()

    events = []
    for row in rows:
        data = dict(row)
        details = {
            "diagnostic": data["diag_pan"] or "",
            "type": data["tp"] or "MAT",
            "technicien": data["technicien"] or "",
            "statut": PANNE_STATUS.get(data["eta_pan"], data["eta_pan"] or ""),
            "date_envoi": data["dat_env_rep"],
            "date_retour": data["dat_ret_rep"],
            "observation_reparation": data["obs_rep"] or "",
            "pieces_remplacees": data["pieces_remplacees"] or "",
            "recommandations": data["recommandations"] or "",
            "cout": data["cout_rep"] or 0,
        }
        events.append(
            {
                "type_evenement": "PANNE",
                "date_evenement": data["dat_pan"],
                "libelle": "Déclaration de panne",
                "detail": data["diag_pan"] or "Panne signalée",
                "obs": "",
                "procedure": details,
            }
        )

    return events


def _get_reform_events(cur, mat_id):
    rows = cur.execute(
        """
        SELECT id_his_ref, etat_reforme, date_evenement, motif_reforme,
               ancien_etat_reforme, dat_cre
        FROM historique_reforme
        WHERE id_mat = ?
        ORDER BY date_evenement DESC, id_his_ref DESC
        """,
        (mat_id,),
    ).fetchall()

    events = []
    for row in rows:
        data = dict(row)
        label = REFORME_LABELS.get(
            data["etat_reforme"], data["etat_reforme"]
        )
        events.append(
            {
                "type_evenement": "REFORME",
                "date_evenement": data["date_evenement"],
                "libelle": label,
                "detail": data["motif_reforme"]
                or ("Changement vers : " + label),
                "obs": "",
                "reforme": {
                    "etat": data["etat_reforme"],
                    "ancien_etat": data["ancien_etat_reforme"] or "AUCUNE",
                    "motif": data["motif_reforme"] or "",
                },
            }
        )

    return events
