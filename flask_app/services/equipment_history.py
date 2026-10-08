"""Services d'historisation du cycle de vie des équipements."""


def log_affectation(
    cur,
    id_mat,
    action,
    id_str,
    id_uti,
    ancien_id_str=None,
    ancien_id_uti=None,
    obs='',
):
    """Enregistre un événement dans l'historique d'affectation."""
    mat = cur.execute(
        "SELECT id_model_mat, id_typ_mat, num_inv, num_ser FROM materiel WHERE id_mat = ?",
        (id_mat,)
    ).fetchone()
    if not mat:
        return

    cur.execute("""
        INSERT INTO affect_mat (
            id_mat, id_str, id_model_mat, id_typ_mat, num_inv, num_ser,
            dat_aff, obs_aff, id_uti, action_aff, ancien_id_str, ancien_id_uti
        ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)
    """, (
        id_mat, id_str, mat['id_model_mat'], mat['id_typ_mat'],
        mat['num_inv'], mat['num_ser'], obs, id_uti, action,
        ancien_id_str, ancien_id_uti
    ))


def log_reforme(
    cur,
    id_mat,
    etat_reforme,
    date_evenement,
    motif_reforme=None,
    ancien_etat_reforme='AUCUNE',
):
    """Conserve une trace immuable de chaque changement déclaré dans le workflow de réforme."""
    cur.execute("""
        INSERT INTO historique_reforme (
            id_mat, etat_reforme, date_evenement, motif_reforme, ancien_etat_reforme
        ) VALUES (?, ?, ?, ?, ?)
    """, (
        id_mat,
        etat_reforme,
        date_evenement,
        motif_reforme,
        ancien_etat_reforme or 'AUCUNE',
    ))
