"""Routes REST de gestion des types de matériel."""

from flask import Blueprint, jsonify, request

try:
    from ..database import get_db
except ImportError:  # Exécution directe depuis flask_app/
    from database import get_db

types_materiel_bp = Blueprint('types_materiel', __name__)

# -----------------------------------------------------------------------------
# GESTION DES TYPES DE MATÉRIEL (depuis Paramètres)
# -----------------------------------------------------------------------------

@types_materiel_bp.route('/api/types-materiel', methods=['GET'])
def get_types_materiel():
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT t.*, COUNT(m.id_mat) AS nb_materiels
        FROM type_mat t
        LEFT JOIN materiel m ON m.id_typ_mat = t.id_typ_mat AND m.archiv = 'N'
        WHERE t.archiv = 'N'
        GROUP BY t.id_typ_mat
        ORDER BY t.lib_typ_mat, t.cod_typ_mat
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@types_materiel_bp.route('/api/types-materiel', methods=['POST'])
def create_type_materiel():
    data = request.json or {}
    code = (data.get('cod_typ_mat') or '').strip()
    libelle = (data.get('lib_typ_mat') or '').strip()

    if not code or not libelle:
        return jsonify({"error": "Code et libellé du type sont requis"}), 400

    conn = get_db()
    cur = conn.cursor()
    exists = cur.execute("""
        SELECT id_typ_mat FROM type_mat
        WHERE (UPPER(TRIM(cod_typ_mat)) = UPPER(TRIM(?))
               OR UPPER(TRIM(lib_typ_mat)) = UPPER(TRIM(?)))
          AND archiv = 'N'
    """, (code, libelle)).fetchone()
    if exists:
        conn.close()
        return jsonify({"error": "Ce code ou ce libellé de type existe déjà"}), 409

    cur.execute("""
        INSERT INTO type_mat (cod_typ_mat, lib_typ_mat, archiv)
        VALUES (?, ?, 'N')
    """, (code, libelle))
    conn.commit()
    new_id = cur.lastrowid
    row = cur.execute("""
        SELECT t.*, COUNT(m.id_mat) AS nb_materiels
        FROM type_mat t
        LEFT JOIN materiel m ON m.id_typ_mat = t.id_typ_mat AND m.archiv = 'N'
        WHERE t.id_typ_mat = ?
        GROUP BY t.id_typ_mat
    """, (new_id,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201


@types_materiel_bp.route('/api/types-materiel/<int:id_typ_mat>', methods=['PUT'])
def update_type_materiel(id_typ_mat):
    data = request.json or {}
    code = (data.get('cod_typ_mat') or '').strip()
    libelle = (data.get('lib_typ_mat') or '').strip()

    if not code or not libelle:
        return jsonify({"error": "Code et libellé du type sont requis"}), 400

    conn = get_db()
    cur = conn.cursor()
    current = cur.execute(
        "SELECT id_typ_mat FROM type_mat WHERE id_typ_mat = ? AND archiv = 'N'",
        (id_typ_mat,)
    ).fetchone()
    if not current:
        conn.close()
        return jsonify({"error": "Type de matériel introuvable"}), 404

    exists = cur.execute("""
        SELECT id_typ_mat FROM type_mat
        WHERE (UPPER(TRIM(cod_typ_mat)) = UPPER(TRIM(?))
               OR UPPER(TRIM(lib_typ_mat)) = UPPER(TRIM(?)))
          AND id_typ_mat <> ?
          AND archiv = 'N'
    """, (code, libelle, id_typ_mat)).fetchone()
    if exists:
        conn.close()
        return jsonify({"error": "Ce code ou ce libellé de type existe déjà"}), 409

    cur.execute("""
        UPDATE type_mat
        SET cod_typ_mat = ?, lib_typ_mat = ?
        WHERE id_typ_mat = ?
    """, (code, libelle, id_typ_mat))
    conn.commit()
    row = cur.execute("""
        SELECT t.*, COUNT(m.id_mat) AS nb_materiels
        FROM type_mat t
        LEFT JOIN materiel m ON m.id_typ_mat = t.id_typ_mat AND m.archiv = 'N'
        WHERE t.id_typ_mat = ?
        GROUP BY t.id_typ_mat
    """, (id_typ_mat,)).fetchone()
    conn.close()
    return jsonify(dict(row))


@types_materiel_bp.route('/api/types-materiel/<int:id_typ_mat>', methods=['DELETE'])
def delete_type_materiel(id_typ_mat):
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id_typ_mat, cod_typ_mat, lib_typ_mat FROM type_mat WHERE id_typ_mat = ? AND archiv = 'N'",
        (id_typ_mat,)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Type de matériel introuvable"}), 404

    used_count = cur.execute(
        "SELECT COUNT(*) FROM materiel WHERE id_typ_mat = ? AND archiv = 'N'",
        (id_typ_mat,)
    ).fetchone()[0]
    if used_count:
        conn.close()
        return jsonify({"error": f"Impossible d'archiver ce type : {used_count} matériel(s) l'utilisent encore"}), 409

    cur.execute("UPDATE type_mat SET archiv = 'O' WHERE id_typ_mat = ?", (id_typ_mat,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Type de matériel archivé"})


