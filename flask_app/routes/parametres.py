"""Routes REST de gestion des paramètres matériels."""

from flask import Blueprint, jsonify, request

try:
    from ..database import get_db
except ImportError:  # Exécution directe depuis flask_app/
    from database import get_db

parametres_bp = Blueprint('parametres', __name__)

@parametres_bp.route('/api/parametres', methods=['GET'])
def get_parametres():
    conn = get_db()
    cur = conn.cursor()
    params = [dict(r) for r in cur.execute("SELECT * FROM parametres_materiel WHERE archiv = 'N' ORDER BY categorie, ordre, id_param").fetchall()]
    conn.close()
    return jsonify(params)

@parametres_bp.route('/api/parametres', methods=['POST'])
def create_parametre():
    data = request.json or {}
    categorie = data.get('categorie', '').strip().lower()
    valeur = data.get('valeur', '').strip()
    description = data.get('description', '').strip() or None
    ordre = int(data.get('ordre', 0))

    if not categorie or not valeur:
        return jsonify({"error": "Catégorie et valeur requises"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO parametres_materiel (categorie, valeur, description, ordre) VALUES (?, ?, ?, ?)",
                (categorie, valeur, description, ordre))
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return jsonify({"id": pid, "message": "Paramètre créé avec succès"}), 201

@parametres_bp.route('/api/parametres/<int:id_param>', methods=['PUT'])
def update_parametre(id_param):
    data = request.json or {}
    valeur = data.get('valeur', '').strip()
    description = data.get('description', '').strip() or None
    ordre = int(data.get('ordre', 0))

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE parametres_materiel SET valeur = ?, description = ?, ordre = ? WHERE id_param = ?",
                (valeur, description, ordre, id_param))
    conn.commit()
    conn.close()
    return jsonify({"message": "Paramètre mis à jour"})


