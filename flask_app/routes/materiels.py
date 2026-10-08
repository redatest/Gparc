"""Routes REST de gestion des équipements informatiques."""

from datetime import datetime
from flask import Blueprint, jsonify, request

try:
    from ..database import get_db
except ImportError:  # Exécution directe depuis flask_app/
    from database import get_db

try:
    from ..services.equipment_history import log_affectation, log_reforme
    from ..services.equipment_references import validate_brand, resolve_model, validate_model
    from ..services.equipment_reform import prepare_reform, status_for_reform
except ImportError:  # Exécution directe depuis flask_app/
    from services.equipment_history import log_affectation, log_reforme
    from services.equipment_references import validate_brand, resolve_model, validate_model
    from services.equipment_reform import prepare_reform, status_for_reform

materiels_bp = Blueprint('materiels', __name__)

@materiels_bp.route('/api/materiels', methods=['GET', 'POST'])
def handle_materiels():
    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        data = request.json or {}
        # Vérifier la marque et résoudre/créer le modèle sélectionné.
        marque = (data.get('marque_mat') or '').strip()
        try:
            validate_brand(cur, marque)
        except ValueError as exc:
            conn.close()
            return jsonify({"error": str(exc)}), 400

        id_model = data.get('id_model_mat') or None
        model_name = (data.get('model_mat_name') or '').strip()
        id_typ = data.get('id_typ_mat') or None

        requested_reforme = data.get('etat_reforme') or 'AUCUNE'
        if requested_reforme != 'AUCUNE':
            conn.close()
            return jsonify({"error": "La réforme d'un équipement se déclare depuis la rubrique « Réforme »."}), 400

        id_model = resolve_model(cur, marque, id_model, model_name, id_typ)

        cur.execute("""
            INSERT INTO materiel (
                id_str, id_typ_mat, id_model_mat, marque_mat, num_inv, num_ser, etat_mat, obs_mat,
                ram, disk, cpu, se, ordi, ip, id_uti, image_url, etat_reforme, motif_reforme,
                date_proposition_reforme, date_validation_reforme, date_reforme, decision_reforme, pv_reforme
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('id_str') or None, id_typ, id_model,
            marque or None,
            data.get('num_inv', f"INV-{datetime.now().strftime('%y%m%d%H%M')}"),
            data.get('num_ser', f"SN-{datetime.now().strftime('%y%m%d%H%M')}"),
            'BON', data.get('obs_mat', ''),
            data.get('ram', 16), data.get('disk', 512),
            data.get('cpu', 'Intel Core i5/i7'), data.get('se', 'Windows 11 Pro'),
            data.get('ordi', ''), data.get('ip', ''), data.get('id_uti') or None,
            data.get('image_url', ''),
            'AUCUNE',
            None,
            None,
            None,
            None,
            None,
            None
        ))
        last_id = cur.lastrowid

        if data.get('id_str') or data.get('id_uti'):
            log_affectation(
                cur, last_id, 'NOUVELLE_AFFECTATION',
                data.get('id_str') or None, data.get('id_uti') or None,
                obs='Nouvelle affectation lors de la création de l’équipement'
            )

        conn.commit()
        conn.close()
        return jsonify({"id": last_id, "message": "Matériel créé avec succès"}), 201

    search = request.args.get('search', '')
    query = """
        SELECT m.*, s.lib_str as structure_nom, s.cod_str as structure_code,
               t.lib_typ_mat as type_nom, t.cod_typ_mat as type_code,
               mod.model_mat, u.nom_uti, u.pnom_uti
        FROM materiel m
        LEFT JOIN structures s ON m.id_str = s.id_str
        LEFT JOIN type_mat t ON m.id_typ_mat = t.id_typ_mat
        LEFT JOIN model_mat mod ON m.id_model_mat = mod.id_model_mat
        LEFT JOIN utilisateurs u ON m.id_uti = u.id_uti
        WHERE m.archiv = 'N'
    """
    params = []
    if search:
        query += " AND (m.num_inv LIKE ? OR m.num_ser LIKE ? OR mod.model_mat LIKE ? OR u.nom_uti LIKE ?)"
        t = f"%{search}%"
        params.extend([t, t, t, t])
    query += " ORDER BY m.id_mat DESC"
    rows = [dict(r) for r in cur.execute(query, params).fetchall()]
    conn.close()
    return jsonify(rows)

@materiels_bp.route('/api/materiels/<int:mat_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_single_materiel(mat_id):
    conn = get_db()
    cur = conn.cursor()

    if request.method == 'PUT':
        data = request.json or {}
        existing = cur.execute("SELECT * FROM materiel WHERE id_mat = ? AND archiv = 'N'", (mat_id,)).fetchone()
        if not existing:
            conn.close()
            return jsonify({"error": "Matériel non trouvé"}), 404

        marque = (data.get('marque_mat') if 'marque_mat' in data else existing['marque_mat'] or '').strip()
        try:
            validate_brand(cur, marque)
        except ValueError as exc:
            conn.close()
            return jsonify({"error": str(exc)}), 400

        id_typ = data.get('id_typ_mat') if 'id_typ_mat' in data else existing['id_typ_mat']
        id_model = data.get('id_model_mat') if 'id_model_mat' in data else existing['id_model_mat']
        model_name = (data.get('model_mat_name') or '').strip()
        id_model = resolve_model(cur, marque, id_model, model_name, id_typ)
        id_str = data.get('id_str') if 'id_str' in data else existing['id_str']
        id_uti = data.get('id_uti') if 'id_uti' in data else existing['id_uti']

        if id_typ is not None and not cur.execute("SELECT 1 FROM type_mat WHERE id_typ_mat = ? AND archiv = 'N'", (id_typ,)).fetchone():
            conn.close(); return jsonify({"error": "Type d'équipement invalide."}), 400
        if id_str is not None and not cur.execute("SELECT 1 FROM structures WHERE id_str = ? AND archiv = 'N'", (id_str,)).fetchone():
            conn.close(); return jsonify({"error": "Structure invalide."}), 400
        if id_uti is not None and not cur.execute("SELECT 1 FROM utilisateurs WHERE id_uti = ? AND archiv = 'N'", (id_uti,)).fetchone():
            conn.close(); return jsonify({"error": "Utilisateur assigné invalide."}), 400
        try:
            reform = prepare_reform(cur, data, existing, datetime.now().strftime('%Y-%m-%d'))
        except ValueError as exc:
            conn.close()
            return jsonify({"error": str(exc)}), 400

        reforme_update = reform["reforme_update"]
        etat_reforme = reform["etat_reforme"]
        motif_reforme = reform["motif_reforme"]
        date_reforme = reform["date_reforme"]
        annee_reforme = reform["annee_reforme"]
        lot_reforme = reform["lot_reforme"]
        date_proposition = reform["date_proposition"]
        date_validation = reform["date_validation"]
        decision = reform["decision"]
        pv_reforme = reform["pv_reforme"]
        try:
            validate_model(cur, id_model, marque, id_typ)
        except ValueError as exc:
            conn.close()
            return jsonify({"error": str(exc)}), 400

        statut_mat_update = status_for_reform(
            etat_reforme,
            reforme_update,
            existing['statut_mat'],
            data.get('statut_mat') if 'statut_mat' in data else None,
        )
        etat_mat_update = data.get('etat_mat') if 'etat_mat' in data else existing['etat_mat']

        if etat_mat_update not in ('BON', 'PANNE', 'IRREPARABLE'):
            conn.close()
            return jsonify({"error": "État de l'équipement invalide. Valeurs autorisées : Bon, En panne, Irréparable."}), 400
        if statut_mat_update not in ('ES', 'PR', 'RF'):
            conn.close()
            return jsonify({"error": "Statut de l'équipement invalide. Valeurs autorisées : En service, Proposé à la réforme, Réformé."}), 400

        cur.execute("""
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
        """, (
            data.get('num_inv'), data.get('num_ser'), marque or None,
            id_model, id_typ, id_str, id_uti, etat_mat_update, statut_mat_update, data.get('obs_mat'),
            data.get('cpu'), data.get('ram'), data.get('disk'), data.get('ip'), data.get('image_url'),
            etat_reforme, motif_reforme, date_proposition, date_validation, date_reforme,
            annee_reforme, lot_reforme, decision, pv_reforme, mat_id
        ))
        old_str = existing['id_str']
        old_uti = existing['id_uti']

        if (old_str is None and old_uti is None) and (id_str is not None or id_uti is not None):
            log_affectation(
                cur, mat_id, 'NOUVELLE_AFFECTATION', id_str, id_uti,
                ancien_id_str=old_str, ancien_id_uti=old_uti,
                obs='Nouvelle affectation de l’équipement'
            )
        else:
            if old_str != id_str:
                log_affectation(
                    cur, mat_id, 'CHANGEMENT_STRUCTURE', id_str, id_uti,
                    ancien_id_str=old_str, ancien_id_uti=old_uti,
                    obs='Changement de structure / direction'
                )
            if old_uti != id_uti:
                log_affectation(
                    cur, mat_id, 'CHANGEMENT_UTILISATEUR', id_str, id_uti,
                    ancien_id_str=old_str, ancien_id_uti=old_uti,
                    obs='Changement d’utilisateur assigné'
                )

        if reforme_update and etat_reforme != (existing['etat_reforme'] or 'AUCUNE'):
            log_reforme(
                cur, mat_id, etat_reforme,
                date_reforme if etat_reforme == 'REFORME' and date_reforme else today,
                motif_reforme,
                existing['etat_reforme'] or 'AUCUNE'
            )

        conn.commit()
        conn.close()
        return jsonify({"message": "Matériel mis à jour avec succès"})

    elif request.method == 'DELETE':
        cur.execute("UPDATE materiel SET archiv = 'O' WHERE id_mat = ?", (mat_id,))
        conn.commit()
        conn.close()
        return jsonify({"message": "Matériel archivé"})

    row = cur.execute("SELECT * FROM materiel WHERE id_mat = ?", (mat_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Matériel non trouvé"}), 404
    return jsonify(dict(row))

@materiels_bp.route('/api/materiels/<int:mat_id>/historique', methods=['GET'])
def get_materiel_historique(mat_id):
    """Historique chronologique complet : affectations, pannes et réformes."""
    conn = get_db()
    cur = conn.cursor()

    exists = cur.execute(
        "SELECT id_mat FROM materiel WHERE id_mat = ? AND archiv = 'N'",
        (mat_id,)
    ).fetchone()
    if not exists:
        conn.close()
        return jsonify({"error": "Matériel non trouvé"}), 404

    events = []

    # 1. Historique des affectations
    rows = cur.execute("""
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
    """, (mat_id,)).fetchall()

    for r in rows: