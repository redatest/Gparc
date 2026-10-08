"""Routes REST de gestion des équipements informatiques."""

from datetime import datetime
from flask import Blueprint, jsonify, request

try:
    from ..database import get_db
except ImportError:  # Exécution directe depuis flask_app/
    from database import get_db

try:
    from ..services.equipment_history import log_reforme
    from ..services.equipment_update import update_materiel
    from ..services.equipment_update_workflow import prepare_equipment_update
    from ..services.equipment_assignment import record_assignment_changes
    from ..services.equipment_history_query import build_equipment_history
except ImportError:  # Exécution directe depuis flask_app/
    from services.equipment_history import log_reforme
    from services.equipment_update import update_materiel
    from services.equipment_update_workflow import prepare_equipment_update
    from services.equipment_assignment import record_assignment_changes
    from services.equipment_history_query import build_equipment_history

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
            record_assignment_changes(
                cur, last_id, None, None,
                data.get('id_str') or None, data.get('id_uti') or None
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

        today = datetime.now().strftime('%Y-%m-%d')
        try:
            prepared = prepare_equipment_update(cur, data, existing, today)
        except ValueError as exc:
            conn.close()
            return jsonify({"error": str(exc)}), 400

        marque = prepared["marque"]
        id_model = prepared["id_model"]
        id_typ = prepared["id_typ"]
        id_str = prepared["id_str"]
        id_uti = prepared["id_uti"]
        etat_mat_update = prepared["etat_mat"]
        statut_mat_update = prepared["statut_mat"]
        etat_reforme = prepared["etat_reforme"]
        motif_reforme = prepared["motif_reforme"]
        date_reforme = prepared["date_reforme"]
        annee_reforme = prepared["annee_reforme"]
        lot_reforme = prepared["lot_reforme"]
        date_proposition = prepared["date_proposition"]
        date_validation = prepared["date_validation"]
        decision = prepared["decision"]
        pv_reforme = prepared["pv_reforme"]
        reforme_update = prepared["reforme_update"]

        update_materiel(
            cur,
            mat_id,
            data,
            marque,
            id_model,
            id_typ,
            id_str,
            id_uti,
            etat_mat_update,
            statut_mat_update,
            etat_reforme,
            motif_reforme,
            date_proposition,
            date_validation,
            date_reforme,
            annee_reforme,
            lot_reforme,
            decision,
            pv_reforme,
        )
        old_str = existing['id_str']
        old_uti = existing['id_uti']

        record_assignment_changes(cur, mat_id, old_str, old_uti, id_str, id_uti)

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

    events = build_equipment_history(cur, mat_id)
    conn.close()
    return jsonify(events)
