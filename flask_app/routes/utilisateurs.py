"""Routes REST de gestion des utilisateurs."""

from flask import Blueprint, jsonify, request

try:
    from ..database import get_db
except ImportError:  # Exécution directe depuis flask_app/
    from database import get_db

utilisateurs_bp = Blueprint('utilisateurs', __name__)

@utilisateurs_bp.route('/api/utilisateurs', methods=['GET'])
def get_utilisateurs():
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT u.*, s.cod_str, s.lib_str
        FROM utilisateurs u
        LEFT JOIN structures s ON s.id_str = u.id_str_mere
        WHERE u.archiv = 'N'
        ORDER BY u.nom_uti, u.pnom_uti
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@utilisateurs_bp.route('/api/utilisateurs', methods=['POST'])
def create_utilisateur():
    data = request.json or {}
    nom = (data.get('nom_uti') or '').strip()
    prenom = (data.get('pnom_uti') or '').strip()
    mail = (data.get('mail_uti') or '').strip() or None
    structure_id = data.get('id_str_mere')

    if not nom or not prenom:
        return jsonify({"error": "Nom et prénom sont requis"}), 400

    try:
        structure_id = int(structure_id) if structure_id not in (None, '', 'null') else None
    except (TypeError, ValueError):
        return jsonify({"error": "Structure invalide"}), 400

    conn = get_db()
    cur = conn.cursor()
    if structure_id is not None:
        exists = cur.execute(
            "SELECT id_str FROM structures WHERE id_str = ? AND archiv = 'N'", (structure_id,)
        ).fetchone()
        if not exists:
            conn.close()
            return jsonify({"error": "La structure sélectionnée n'existe pas"}), 400

    cur.execute("""
        INSERT INTO utilisateurs (nom_uti, pnom_uti, mail_uti, id_str_mere, archiv)
        VALUES (?, ?, ?, ?, 'N')
    """, (nom, prenom, mail, structure_id))
    conn.commit()
    user_id = cur.lastrowid
    row = cur.execute("""
        SELECT u.*, s.cod_str, s.lib_str
        FROM utilisateurs u
        LEFT JOIN structures s ON s.id_str = u.id_str_mere
        WHERE u.id_uti = ?
    """, (user_id,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201

@utilisateurs_bp.route('/api/utilisateurs/<int:id_uti>', methods=['PUT'])
def update_utilisateur(id_uti):
    data = request.json or {}
    nom = (data.get('nom_uti') or '').strip()
    prenom = (data.get('pnom_uti') or '').strip()
    mail = (data.get('mail_uti') or '').strip() or None
    structure_id = data.get('id_str_mere')

    if not nom or not prenom:
        return jsonify({"error": "Nom et prénom sont requis"}), 400

    try:
        structure_id = int(structure_id) if structure_id not in (None, '', 'null') else None
    except (TypeError, ValueError):
        return jsonify({"error": "Structure invalide"}), 400

    conn = get_db()
    cur = conn.cursor()
    current = cur.execute(
        "SELECT id_uti FROM utilisateurs WHERE id_uti = ? AND archiv = 'N'", (id_uti,)
    ).fetchone()
    if not current:
        conn.close()
        return jsonify({"error": "Utilisateur introuvable"}), 404

    if structure_id is not None:
        exists = cur.execute(
            "SELECT id_str FROM structures WHERE id_str = ? AND archiv = 'N'", (structure_id,)
        ).fetchone()
        if not exists:
            conn.close()
            return jsonify({"error": "La structure sélectionnée n'existe pas"}), 400

    cur.execute("""
        UPDATE utilisateurs
        SET nom_uti = ?, pnom_uti = ?, mail_uti = ?, id_str_mere = ?, dat_cre = CURRENT_TIMESTAMP
        WHERE id_uti = ?
    """, (nom, prenom, mail, structure_id, id_uti))
    conn.commit()
    row = cur.execute("""
        SELECT u.*, s.cod_str, s.lib_str
        FROM utilisateurs u
        LEFT JOIN structures s ON s.id_str = u.id_str_mere
        WHERE u.id_uti = ?
    """, (id_uti,)).fetchone()
    conn.close()
    return jsonify(dict(row))

@utilisateurs_bp.route('/api/utilisateurs/<int:id_uti>', methods=['DELETE'])
def delete_utilisateur(id_uti):
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute(
        "SELECT id_uti FROM utilisateurs WHERE id_uti = ? AND archiv = 'N'", (id_uti,)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Utilisateur introuvable"}), 404

    # Archivage pour préserver les affectations et leur historique.
    cur.execute("UPDATE utilisateurs SET archiv = 'O' WHERE id_uti = ?", (id_uti,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Utilisateur archivé"})

