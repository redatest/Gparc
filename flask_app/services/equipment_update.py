"""Persistance des modifications d'un équipement."""


UPDATE_MATERIEL_SQL = """
    UPDATE materiel SET
        num_inv = COALESCE(?, num_inv),
        num_ser = COALESCE(?, num_ser),
        marque_mat = COALESCE(?, marque_mat),
        id_model_mat = ?,
        id_typ_mat = ?,
        id_str = ?,
        id_uti = ?,
        etat_mat = COALESCE(?, etat_mat),
        statut_mat = COALESCE(?, statut_mat),
        obs_mat = COALESCE(?, obs_mat),
        cpu = COALESCE(?, cpu),
        ram = COALESCE(?, ram),
        disk = COALESCE(?, disk),
        ip = COALESCE(?, ip),
        image_url = COALESCE(?, image_url),
        etat_reforme = ?,
        motif_reforme = ?,
        date_proposition_reforme = ?,
        date_validation_reforme = ?,
        date_reforme = ?,
        annee_reforme = ?,
        lot_reforme = ?,
        decision_reforme = ?,
        pv_reforme = ?,
        dat_mod = CURRENT_TIMESTAMP
    WHERE id_mat = ?
"""


def update_materiel(cur, mat_id, data, marque, id_model, id_typ, id_str, id_uti,
                    etat_mat, statut_mat, etat_reforme, motif_reforme,
                    date_proposition, date_validation, date_reforme,
                    annee_reforme, lot_reforme, decision, pv_reforme):
    """Applique la mise à jour SQL du matériel sans gérer la transaction."""
    cur.execute(
        UPDATE_MATERIEL_SQL,
        (
            data.get("num_inv"),
            data.get("num_ser"),
            marque or None,
            id_model,
            id_typ,
            id_str,
            id_uti,
            etat_mat,
            statut_mat,
            data.get("obs_mat"),
            data.get("cpu"),
            data.get("ram"),
            data.get("disk"),
            data.get("ip"),
            data.get("image_url"),
            etat_reforme,
            motif_reforme,
            date_proposition,
            date_validation,
            date_reforme,
            annee_reforme,
            lot_reforme,
            decision,
            pv_reforme,
            mat_id,
        ),
    )
