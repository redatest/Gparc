"""Routes REST de gestion des équipements informatiques."""

from datetime import datetime
from flask import Blueprint, jsonify, request

try:
    from ..database import get_db
except ImportError:  # Exécution directe depuis flask_app/
    from database import get_db

try:
    from ..services.equipment_creation import create_materiel
    from ..services.equipment_update_actions import apply_equipment_update
    from ..services.equipment_update_workflow import prepare_equipment_update
    from ..services.equipment_history_query import build_equipment_history
    from ..services.equipment_detail_query import get_materiel_by_id
    from ..services.equipment_list_query import list_materiels
except ImportError:  # Exécution directe depuis flask_app/
    from services.equipment_creation import create_materiel
    from services.equipment_update_actions import apply_equipment_update
    from services.equipment_update_workflow import prepare_equipment_update
    from services.equipment_history_query import build_equipment_history
    from services.equipment_detail_query import get_materiel_by_id
    from services.equipment_list_query import list_materiels

materiels_bp = Blueprint('materiels', __name__)

@materiels_bp.route('/api/materiels', methods=['GET', 'POST'])
def handle_materiels():
    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        data = request.json or {}
        try:
            last_id = create_materiel(cur, data)
        except ValueError as exc:
            conn.close()
            return jsonify({"error": str(exc)}), 400

        conn.commit()
        conn.close()
        return jsonify({"id": last_id, "message": "Matériel créé avec succès"}), 201

    search = request.args.get('search', '')
    rows = [dict(r) for r in list_materiels(cur, search)]
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

        apply_equipment_update(cur, mat_id, data, existing, prepared, today)

        conn.commit()
        conn.close()
        return jsonify({"message": "Matériel mis à jour avec succès"})

    elif request.method == 'DELETE':
        cur.execute("UPDATE materiel SET archiv = 'O' WHERE id_mat = ?", (mat_id,))
        conn.commit()
        conn.close()
        return jsonify({"message": "Matériel archivé"})

    row = get_materiel_by_id(cur, mat_id)
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
