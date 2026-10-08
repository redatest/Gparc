"""Routes REST de gestion des structures."""

from flask import Blueprint, jsonify, request

try:
    from ..database import get_db
except ImportError:
    from database import get_db

structures_bp = Blueprint('structures', __name__)

# -----------------------------------------------------------------------------
# GESTION DES STRUCTURES (depuis Paramètres)
# -----------------------------------------------------------------------------

@structures_bp.route('/api/structures', methods=['GET'])
def get_structures():
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT s.*,
               p.lib_str AS structure_mere_nom
        FROM structures s
        LEFT JOIN structures p ON p.id_str = s.id_str_mere
        WHERE s.archiv = 'N'
        ORDER BY s.cod_str, s.lib_str
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@structures_bp.route('/api/structures', methods=['POST'])
def create_structure():
    data = request.json or {}
    code = (data.get('cod_str') or '').strip()
    libelle = (data.get('lib_str') or '').strip()
    parent_id = data.get('id_str_mere')

    if not code or not libelle:
        return jsonify({"error": "Code et libellé de la structure sont requis"}), 400

    try:
        parent_id = int(parent_id) if parent_id not in (None, '', 'null') else None
    except (TypeError, ValueError):
        return jsonify({"error": "Structure mère invalide"}), 400

    conn = get_db()
    cur = conn.cursor()
    if parent_id is not None:
        parent = cur.execute(
            "SELECT id_str FROM structures WHERE id_str = ? AND archiv = 'N'", (parent_id,)
        ).fetchone()
        if not parent:
            conn.close()
            return jsonify({"error": "La structure mère sélectionnée n'existe pas"}), 400

    exists = cur.execute(
        "SELECT id_str FROM structures WHERE UPPER(TRIM(cod_str)) = UPPER(TRIM(?)) AND archiv = 'N'",
        (code,)
    ).fetchone()
    if exists:
        conn.close()
        return jsonify({"error": "Ce code structure existe déjà"}), 409

    cur.execute("""
        INSERT INTO structures (cod_str, lib_str, id_str_mere, archiv)
        VALUES (?, ?, ?, 'N')
    """, (code, libelle, parent_id))
    conn.commit()
    new_id = cur.lastrowid
    row = cur.execute("""
        SELECT s.*, p.lib_str AS structure_mere_nom
        FROM structures s
        LEFT JOIN structures p ON p.id_str = s.id_str_mere
        WHERE s.id_str = ?
    """, (new_id,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201

@structures_bp.route('/api/structures/<int:id_str>', methods=['PUT'])
def update_structure(id_str):
    data = request.json or {}
    code = (data.get('cod_str') or '').strip()
    libelle = (data.get('lib_str') or '').strip()
    parent_id = data.get('id_str_mere')

    if not code or not libelle:
        return jsonify({"error": "Code et libellé de la structure sont requis"}), 400

    try:
        parent_id = int(parent_id) if parent_id not in (None, '', 'null') else None
    except (TypeError, ValueError):
        return jsonify({"error": "Structure mère invalide"}), 400

    if parent_id == id_str:
        return jsonify({"error": "Une structure ne peut pas être sa propre structure mère"}), 400

    conn = get_db()
    cur = conn.cursor()
    current = cur.execute(
        "SELECT id_str FROM structures WHERE id_str = ? AND archiv = 'N'", (id_str,)
    ).fetchone()
    if not current:
        conn.close()
        return jsonify({"error": "Structure introuvable"}), 404

    if parent_id is not None:
        parent = cur.execute(
            "SELECT id_str FROM structures WHERE id_str = ? AND archiv = 'N'", (parent_id,)
        ).fetchone()
        if not parent:
            conn.close()
            return jsonify({"error": "La structure mère sélectionnée n'existe pas"}), 400

    exists = cur.execute("""
        SELECT id_str FROM structures
        WHERE UPPER(TRIM(cod_str)) = UPPER(TRIM(?))
          AND id_str <> ?
          AND archiv = 'N'
    """, (code, id_str)).fetchone()
    if exists:
        conn.close()
        return jsonify({"error": "Ce code structure existe déjà"}), 409

    cur.execute("""
        UPDATE structures
        SET cod_str = ?, lib_str = ?, id_str_mere = ?, dat_cre = CURRENT_TIMESTAMP
        WHERE id_str = ?
    """, (code, libelle, parent_id, id_str))
    conn.commit()
    row = cur.execute("""
        SELECT s.*, p.lib_str AS structure_mere_nom
        FROM structures s
        LEFT JOIN structures p ON p.id_str = s.id_str_mere
        WHERE s.id_str = ?
    """, (id_str,)).fetchone()
    conn.close()
    return jsonify(dict(row))

@structures_bp.route('/api/structures/<int:id_str>', methods=['DELETE'])
def delete_structure(id_str):
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id_str, cod_str, lib_str FROM structures WHERE id_str = ? AND archiv = 'N'",
        (id_str,)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Structure introuvable"}), 404

    # Une structure utilisée par du matériel ou des utilisateurs est archivée,
    # jamais physiquement supprimée, afin de préserver l'historique.
    child_count = cur.execute(
        "SELECT COUNT(*) FROM structures WHERE id_str_mere = ? AND archiv = 'N'", (id_str,)
    ).fetchone()[0]
    if child_count:
        conn.close()
        return jsonify({"error": "Impossible d'archiver cette structure : elle possède des structures filles"}), 409

    cur.execute("UPDATE structures SET archiv = 'O' WHERE id_str = ?", (id_str,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Structure archivée"})

