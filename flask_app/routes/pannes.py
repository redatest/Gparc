"""Routes REST de gestion des pannes et interventions."""

from datetime import datetime
from flask import Blueprint, jsonify, request

try:
    from ..database import get_db
except ImportError:
    from database import get_db

pannes_bp = Blueprint('pannes', __name__)

@pannes_bp.route('/api/pannes', methods=['GET', 'POST'])
def handle_pannes():
    conn = get_db()
    cur = conn.cursor()
    if request.method == 'POST':
        data = request.json or {}
        mat_id = data.get('id_mat')
        if not mat_id:
            conn.close()
            return jsonify({"error": "id_mat requis"}), 400

        cur.execute("""
            INSERT INTO panne (id_mat, id_str, id_typ_mat, id_model_mat, num_inv, num_ser,
                               dat_pan, diag_pan, eta_pan, tp, technicien, obs_rep, pieces_remplacees)
            SELECT id_mat, id_str, id_typ_mat, id_model_mat, num_inv, num_ser, ?, ?, 'EP', ?, ?, ?, ?
            FROM materiel WHERE id_mat = ?
        """, (
            data.get('dat_pan', datetime.now().strftime('%Y-%m-%d')),
            data.get('diag_pan', 'Anomalie signalée'), data.get('tp', 'MAT'),
            data.get('technicien', 'Support DSI'),
            data.get('obs_rep', ''), data.get('pieces_remplacees', ''), mat_id
        ))
        # L'état physique devient "En panne". Le statut de cycle de vie reste indépendant.
        cur.execute("UPDATE materiel SET etat_mat = 'PANNE' WHERE id_mat = ?", (mat_id,))
        conn.commit()
        last_id = cur.lastrowid
        conn.close()
        return jsonify({"id": last_id, "message": "Panne enregistrée"}), 201
    else:
        rows = [dict(r) for r in cur.execute("""
            SELECT p.*, m.num_inv, m.num_ser, m.id_uti,
                   mod.marque_mat, mod.model_mat,
                   t.lib_typ_mat AS type_nom,
                   u.nom_uti, u.pnom_uti,
                   s.lib_str as structure_nom,
                   l.nom_lieu_rep as lieu_reparation, l.categorie_lieu as categorie_lieu_reparation
            FROM panne p
            JOIN materiel m ON p.id_mat = m.id_mat
            LEFT JOIN model_mat mod ON m.id_model_mat = mod.id_model_mat
            LEFT JOIN type_mat t ON m.id_typ_mat = t.id_typ_mat
            LEFT JOIN utilisateurs u ON m.id_uti = u.id_uti
            LEFT JOIN structures s ON p.id_str = s.id_str
            LEFT JOIN lieu_rep l ON p.id_lieu_rep = l.id_lieu_rep
            WHERE p.archiv = 'N' ORDER BY p.id_pan DESC
        """).fetchall()]
        conn.close()
        return jsonify(rows)

@pannes_bp.route('/api/pannes/<int:panne_id>', methods=['PUT'])
def update_panne(panne_id):
    conn = get_db()
    cur = conn.cursor()
    data = request.json or {}

    panne_row = cur.execute("SELECT * FROM panne WHERE id_pan = ?", (panne_id,)).fetchone()
    if not panne_row:
        conn.close()
        return jsonify({"error": "Panne introuvable"}), 404

    eta_pan = data.get('eta_pan') if 'eta_pan' in data else panne_row['eta_pan']
    if eta_pan not in ('EP', 'ER', 'RP', 'IR'):
        conn.close()
        return jsonify({"error": "État de panne invalide. Valeurs : En panne, En réparation, Réparé, Irréparable."}), 400

    id_lieu_rep = data.get('id_lieu_rep') if 'id_lieu_rep' in data else panne_row['id_lieu_rep']
    if id_lieu_rep not in (None, ''):
        if not cur.execute("SELECT 1 FROM lieu_rep WHERE id_lieu_rep = ? AND archiv = 'N'", (id_lieu_rep,)).fetchone():
            conn.close()
            return jsonify({"error": "Lieu de réparation invalide."}), 400
        id_lieu_rep = int(id_lieu_rep)
    else:
        id_lieu_rep = None

    dat_env_rep = data.get('dat_env_rep') if 'dat_env_rep' in data else panne_row['dat_env_rep']
    dat_ret_rep = data.get('dat_ret_rep') if 'dat_ret_rep' in data else panne_row['dat_ret_rep']
    if eta_pan in ('RP', 'IR') and not dat_ret_rep:
        dat_ret_rep = datetime.now().strftime('%Y-%m-%d')

    if eta_pan in ('ER', 'RP', 'IR') and not dat_env_rep:
        conn.close()
        return jsonify({"error": "La date d'envoi à la réparation est obligatoire pour ce traitement."}), 400

    updates = [
        "eta_pan = ?",
        "dat_env_rep = ?",
        "id_lieu_rep = ?",
        "dat_ret_rep = ?"
    ]
    params = [eta_pan, dat_env_rep, id_lieu_rep, dat_ret_rep]

    for field in ('obs_rep', 'recommandations', 'pieces_remplacees'):
        if field in data:
            updates.append(field + " = ?")
            params.append(data.get(field) or '')

    cur.execute("UPDATE panne SET " + ", ".join(updates) + " WHERE id_pan = ?", params + [panne_id])

    etat_mat = {
        'EP': 'PANNE',
        'ER': 'PANNE',
        'RP': 'BON',
        'IR': 'IRREPARABLE'
    }[eta_pan]
    cur.execute("UPDATE materiel SET etat_mat = ?, dat_mod = CURRENT_TIMESTAMP WHERE id_mat = ?", (etat_mat, panne_row['id_mat']))

    conn.commit()
    conn.close()
    return jsonify({"message": "Traitement de la panne mis à jour"})


@pannes_bp.route('/api/pannes/<int:panne_id>/report', methods=['GET'])
def get_panne_report(panne_id):
    conn = get_db()
    cur = conn.cursor()
    row = cur.execute("""
        SELECT p.*, m.num_inv, m.num_ser, m.ordi, m.ip, m.ram, m.disk, m.cpu, m.se, m.image_url,
               mod.marque_mat, mod.model_mat, t.lib_typ_mat, s.lib_str as structure_nom,
               u.nom_uti, u.pnom_uti, u.mail_uti, l.nom_lieu_rep
        FROM panne p
        JOIN materiel m ON p.id_mat = m.id_mat
        LEFT JOIN model_mat mod ON m.id_model_mat = mod.id_model_mat
        LEFT JOIN type_mat t ON m.id_typ_mat = t.id_typ_mat
        LEFT JOIN structures s ON p.id_str = s.id_str
        LEFT JOIN utilisateurs u ON m.id_uti = u.id_uti
        LEFT JOIN lieu_rep l ON p.id_lieu_rep = l.id_lieu_rep
        WHERE p.id_pan = ?
    """, (panne_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Rapport introuvable"}), 404

    d = dict(row)
    return jsonify({
        "numeroRapport": f"RPT-FLASK-{d['id_pan']:04d}",
        "dateGeneration": datetime.now().strftime('%d/%m/%Y %H:%M'),
        "intervention": {
            "id": d['id_pan'],
            "datePanne": d['dat_pan'],
            "diagnostic": d['diag_pan'],
            "statut": d['eta_pan'],
            "technicien": d['technicien'],
            "travaux": d['obs_rep'],
            "observation": d['recommandations'] or '',
            "pieces": d['pieces_remplacees'],
            "recommandations": d['recommandations'],
            "cout": d['cout_rep'],
            "dateReparation": d['dat_ret_rep'],
            "dateRetour": d['dat_ret_rep'],
            "lieuReparation": d['nom_lieu_rep'],
            "typePanne": d['tp']
        },
        "equipement": {
            "numInventaire": d['num_inv'],
            "numSerie": d['num_ser'],
            "marque": d['marque_mat'],
            "modele": d['model_mat'],
            "type": d['lib_typ_mat'],
            "imageUrl": d['image_url']
        },
        "utilisateur": {
            "nom": f"{d['pnom_uti'] or ''} {d['nom_uti'] or ''}".strip() or "Non assigné",
            "service": d['structure_nom'] or "DSI"
        }
    })

