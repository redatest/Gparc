"""Routes REST de gestion des équipements informatiques."""

from datetime import datetime
from flask import Blueprint, jsonify, request

try:
    from ..database import get_db
except ImportError:  # Exécution directe depuis flask_app/
    from database import get_db

materiels_bp = Blueprint('materiels', __name__)

def log_affectation(cur, id_mat, action, id_str, id_uti, ancien_id_str=None, ancien_id_uti=None, obs=''):
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


# Initialiser la base dès le chargement du module
init_db()

# -----------------------------------------------------------------------------
# ROUTES STATIQUES & INTERFACE WEB
# -----------------------------------------------------------------------------

@materiels_bp.route('/logoSS.jpg', methods=['GET'])
def serve_logo_ss():
    logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../logoSS.jpg'))
    if os.path.isfile(logo_path):
        return send_from_directory(os.path.dirname(logo_path), os.path.basename(logo_path))
    return ('LogoSS.jpg introuvable', 404)

@app.route('/')
def index():
    """Point d'entrée principal de l'application."""
    return render_template('index.html')

# -----------------------------------------------------------------------------
# ROUTES API REST
# -----------------------------------------------------------------------------

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "backend": "Python Flask 3.0", "time": datetime.now().isoformat()})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    conn = get_db()
    cur = conn.cursor()

    total = cur.execute("SELECT COUNT(*) FROM materiel WHERE archiv = 'N'").fetchone()[0]
    op = cur.execute("SELECT COUNT(*) FROM materiel WHERE etat_mat = 'BON' AND archiv = 'N'").fetchone()[0]
    pa = cur.execute("SELECT COUNT(*) FROM materiel WHERE etat_mat = 'PANNE' AND archiv = 'N'").fetchone()[0]
    en_reparation = cur.execute("""
        SELECT COUNT(DISTINCT id_mat)
        FROM panne
        WHERE eta_pan = 'ER'
          AND archiv = 'N'
    """).fetchone()[0]
    so = cur.execute("SELECT COUNT(*) FROM materiel WHERE statut_mat = 'RF' AND archiv = 'N'").fetchone()[0]
    pannes_actives = cur.execute("SELECT COUNT(*) FROM panne WHERE eta_pan IN ('EP', 'ER') AND archiv = 'N'").fetchone()[0]
    pannes_resolues = cur.execute("SELECT COUNT(*) FROM panne WHERE eta_pan IN ('RP','IR') AND archiv = 'N'").fetchone()[0]

    repart_type = [dict(row) for row in cur.execute("""
        SELECT t.lib_typ_mat as type, COUNT(m.id_mat) as count
        FROM type_mat t
        LEFT JOIN materiel m ON t.id_typ_mat = m.id_typ_mat AND m.archiv = 'N'
        GROUP BY t.id_typ_mat ORDER BY count DESC
    """).fetchall()]

    repart_str = [dict(row) for row in cur.execute("""
        SELECT s.cod_str as code, s.lib_str as label, COUNT(m.id_mat) as count
        FROM structures s
        LEFT JOIN materiel m ON s.id_str = m.id_str AND m.archiv = 'N'
        GROUP BY s.id_str ORDER BY count DESC
    """).fetchall()]

    conn.close()
    return jsonify({
        "totalEquipements": total,
        "operationnels": op,
        "enPanne": pa,
        "enReparation": en_reparation,
        "reformes": so,
        "pannesActives": pannes_actives,
        "pannesResolues": pannes_resolues,
        "tauxDisponibilite": round((op / total * 100) if total > 0 else 100, 1),
        "repartitionTypes": repart_type,
        "repartitionStructures": repart_str
    })

@app.route('/api/materiels', methods=['GET', 'POST'])
def handle_materiels():
    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        data = request.json or {}
        # Vérifier la marque et résoudre/créer le modèle sélectionné.
        marque = (data.get('marque_mat') or '').strip()
        if marque:
            brand_ref = cur.execute("SELECT id_param FROM parametres_materiel WHERE categorie = 'marque' AND archiv = 'N' AND LOWER(TRIM(valeur)) = LOWER(?)", (marque,)).fetchone()
            if not brand_ref:
                return jsonify({"error": "La marque sélectionnée n’existe pas dans le référentiel des marques."}), 400

        id_model = data.get('id_model_mat') or None
        model_name = (data.get('model_mat_name') or '').strip()
        id_typ = data.get('id_typ_mat') or None

        requested_reforme = data.get('etat_reforme') or 'AUCUNE'
        if requested_reforme != 'AUCUNE':
            conn.close()
            return jsonify({"error": "La réforme d'un équipement se déclare depuis la rubrique « Réforme »."}), 400

        if model_name and marque:
            model_row = cur.execute(
                "SELECT id_model_mat FROM model_mat WHERE archiv = 'N' AND LOWER(TRIM(model_mat)) = LOWER(?) AND LOWER(TRIM(marque_mat)) = LOWER(?) AND (id_typ_mat = ? OR id_typ_mat IS NULL)",
                (model_name, marque, id_typ)
            ).fetchone()
            if model_row:
                id_model = model_row['id_model_mat']
            else:
                cur.execute(
                    "INSERT INTO model_mat (marque_mat, model_mat, id_typ_mat) VALUES (?, ?, ?)",
                    (marque, model_name, id_typ)
                )
                id_model = cur.lastrowid

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

@app.route('/api/materiels/<int:mat_id>', methods=['GET', 'PUT', 'DELETE'])
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
        if marque:
            brand_ref = cur.execute("SELECT id_param FROM parametres_materiel WHERE categorie = 'marque' AND archiv = 'N' AND LOWER(TRIM(valeur)) = LOWER(?)", (marque,)).fetchone()
            if not brand_ref:
                conn.close()
                return jsonify({"error": "La marque sélectionnée n'existe pas dans le référentiel des marques."}), 400

        id_typ = data.get('id_typ_mat') if 'id_typ_mat' in data else existing['id_typ_mat']
        id_model = data.get('id_model_mat') if 'id_model_mat' in data else existing['id_model_mat']
        model_name = (data.get('model_mat_name') or '').strip()
        if model_name and marque:
            model_row = cur.execute(
                "SELECT id_model_mat FROM model_mat WHERE archiv = 'N' AND LOWER(TRIM(model_mat)) = LOWER(?) AND LOWER(TRIM(marque_mat)) = LOWER(?) AND (id_typ_mat = ? OR id_typ_mat IS NULL)",
                (model_name, marque, id_typ)
            ).fetchone()
            if model_row:
                id_model = model_row['id_model_mat']
            else:
                cur.execute(
                    "INSERT INTO model_mat (marque_mat, model_mat, id_typ_mat) VALUES (?, ?, ?)",
                    (marque, model_name, id_typ)
                )
                id_model = cur.lastrowid
        id_str = data.get('id_str') if 'id_str' in data else existing['id_str']
        id_uti = data.get('id_uti') if 'id_uti' in data else existing['id_uti']

        if id_typ is not None and not cur.execute("SELECT 1 FROM type_mat WHERE id_typ_mat = ? AND archiv = 'N'", (id_typ,)).fetchone():
            conn.close(); return jsonify({"error": "Type d'équipement invalide."}), 400
        if id_str is not None and not cur.execute("SELECT 1 FROM structures WHERE id_str = ? AND archiv = 'N'", (id_str,)).fetchone():
            conn.close(); return jsonify({"error": "Structure invalide."}), 400
        if id_uti is not None and not cur.execute("SELECT 1 FROM utilisateurs WHERE id_uti = ? AND archiv = 'N'", (id_uti,)).fetchone():
            conn.close(); return jsonify({"error": "Utilisateur assigné invalide."}), 400
        reforme_update = 'etat_reforme' in data
        etat_reforme = data.get('etat_reforme') if reforme_update else (existing['etat_reforme'] or 'AUCUNE')
        motif_reforme = data.get('motif_reforme') if reforme_update else existing['motif_reforme']
        date_reforme = data.get('date_reforme') if reforme_update else existing['date_reforme']
        annee_reforme = data.get('annee_reforme') if reforme_update else existing['annee_reforme']
        lot_reforme = data.get('lot_reforme') if reforme_update else existing['lot_reforme']
        today = datetime.now().strftime('%Y-%m-%d')

        if etat_reforme not in ('AUCUNE', 'PROPOSEE', 'REFORME'):
            conn.close()
            return jsonify({"error": "État de réforme invalide."}), 400

        if etat_reforme == 'REFORME':
            if not date_reforme:
                conn.close()
                return jsonify({"error": "La date de réforme est obligatoire."}), 400
            if not annee_reforme:
                conn.close()
                return jsonify({"error": "L'année de réforme est obligatoire."}), 400
            try:
                annee_reforme = int(annee_reforme)
            except (TypeError, ValueError):
                conn.close()
                return jsonify({"error": "L'année de réforme doit être un nombre valide."}), 400
            if annee_reforme < 2000 or annee_reforme > 2100:
                conn.close()
                return jsonify({"error": "L'année de réforme doit être comprise entre 2000 et 2100."}), 400
            if not lot_reforme or not str(lot_reforme).strip():
                conn.close()
                return jsonify({"error": "Le N° de lot de réforme est obligatoire."}), 400
            if not motif_reforme or not str(motif_reforme).strip():
                conn.close()
                return jsonify({"error": "Le motif de réforme est obligatoire."}), 400
            lot_reforme = str(lot_reforme).strip()
            lot_ref = cur.execute("""
                SELECT id_param
                FROM parametres_materiel
                WHERE categorie = 'lot_reforme'
                  AND archiv = 'N'
                  AND LOWER(TRIM(valeur)) = LOWER(TRIM(?))
                LIMIT 1
            """, (lot_reforme,)).fetchone()
            if not lot_ref:
                conn.close()
                return jsonify({"error": "Le N° de lot sélectionné n'existe pas dans le référentiel des lots de réforme."}), 400
            date_proposition = existing['date_proposition_reforme'] or today
        elif etat_reforme == 'PROPOSEE':
            date_proposition = today
            date_reforme = None
            annee_reforme = None
            lot_reforme = None
            motif_reforme = None
        else:
            date_proposition = None
            date_reforme = None
            annee_reforme = None
            lot_reforme = None
            motif_reforme = None

        date_validation = None
        decision = None
        pv_reforme = None

        if id_model is not None:
            model = cur.execute("SELECT marque_mat, id_typ_mat FROM model_mat WHERE id_model_mat = ? AND archiv = 'N'", (id_model,)).fetchone()
            if not model:
                conn.close(); return jsonify({"error": "Modèle invalide."}), 400
            if marque and (model['marque_mat'] or '').strip().lower() != marque.lower():
                conn.close(); return jsonify({"error": "Le modèle sélectionné ne correspond pas à la marque."}), 400
            if id_typ is not None and model['id_typ_mat'] is not None and int(model['id_typ_mat']) != int(id_typ):
                conn.close(); return jsonify({"error": "Le modèle sélectionné ne correspond pas au type."}), 400

        statut_mat_update = ({'AUCUNE': 'ES', 'PROPOSEE': 'PR', 'REFORME': 'RF'}.get(etat_reforme, 'ES')) if reforme_update else (data.get('statut_mat') if 'statut_mat' in data else (existing['statut_mat'] or 'ES'))
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

def log_reforme(cur, id_mat, etat_reforme, date_evenement, motif_reforme=None, ancien_etat_reforme='AUCUNE'):
    """Conserve une trace immuable de chaque changement déclaré dans le workflow de réforme."""
    cur.execute("""
        INSERT INTO historique_reforme (
            id_mat, etat_reforme, date_evenement, motif_reforme, ancien_etat_reforme
        ) VALUES (?, ?, ?, ?, ?)
    """, (id_mat, etat_reforme, date_evenement, motif_reforme, ancien_etat_reforme or 'AUCUNE'))


@app.route('/api/materiels/<int:mat_id>/historique', methods=['GET'])
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
        d = dict(r)
        if d['action_aff'] == 'NOUVELLE_AFFECTATION':
            libelle = 'Nouvelle affectation'
            detail = d['structure_nom'] or 'Structure non précisée'
            if d['nom_uti']:
                detail += ' — ' + ((d['pnom_uti'] or '') + ' ' + (d['nom_uti'] or '')).strip()
        elif d['action_aff'] == 'CHANGEMENT_STRUCTURE':
            libelle = 'Changement de structure'
            detail = f"{d['ancienne_structure_nom'] or 'Aucune structure'} → {d['structure_nom'] or 'Aucune structure'}"
        else:
            libelle = 'Changement d’utilisateur'
            old_name = ((d['ancien_pnom_uti'] or '') + ' ' + (d['ancien_nom_uti'] or '')).strip() or 'Aucun utilisateur'
            new_name = ((d['pnom_uti'] or '') + ' ' + (d['nom_uti'] or '')).strip() or 'Aucun utilisateur'
            detail = f"{old_name} → {new_name}"
        events.append({
            'type_evenement': 'AFFECTATION',
            'date_evenement': d['dat_aff'],
            'libelle': libelle,
            'detail': detail,
            'obs': d['obs_aff'] or ''
        })

    # 2. Procédures de panne
    pannes = cur.execute("""
        SELECT id_pan, dat_pan, diag_pan, eta_pan, tp, technicien,
               dat_env_rep, dat_ret_rep, obs_rep, pieces_remplacees,
               recommandations, cout_rep
        FROM panne
        WHERE id_mat = ? AND archiv = 'N'
        ORDER BY dat_pan DESC, id_pan DESC
    """, (mat_id,)).fetchall()

    panne_status = {
        'EP': 'En panne',
        'ER': 'En réparation',
        'RP': 'Réparé',
        'IR': 'Irréparable',
        'EC': 'En panne',
        'AT': 'En réparation',
        'NR': 'Irréparable'
    }
    for p in pannes:
        d = dict(p)
        details = {
            'diagnostic': d['diag_pan'] or '',
            'type': d['tp'] or 'MAT',
            'technicien': d['technicien'] or '',
            'statut': panne_status.get(d['eta_pan'], d['eta_pan'] or ''),
            'date_envoi': d['dat_env_rep'],
            'date_retour': d['dat_ret_rep'],
            'observation_reparation': d['obs_rep'] or '',
            'pieces_remplacees': d['pieces_remplacees'] or '',
            'recommandations': d['recommandations'] or '',
            'cout': d['cout_rep'] or 0
        }
        events.append({
            'type_evenement': 'PANNE',
            'date_evenement': d['dat_pan'],
            'libelle': 'Déclaration de panne',
            'detail': d['diag_pan'] or 'Panne signalée',
            'obs': '',
            'procedure': details
        })

    # 3. Procédures de réforme
    reformes = cur.execute("""
        SELECT id_his_ref, etat_reforme, date_evenement, motif_reforme,
               ancien_etat_reforme, dat_cre
        FROM historique_reforme
        WHERE id_mat = ?
        ORDER BY date_evenement DESC, id_his_ref DESC
    """, (mat_id,)).fetchall()

    reforme_labels = {
        'AUCUNE': 'Remise en service',
        'PROPOSEE': 'Proposé à la réforme',
        'REFORME': 'Réformé'
    }
    for r in reformes:
        d = dict(r)
        events.append({
            'type_evenement': 'REFORME',
            'date_evenement': d['date_evenement'],
            'libelle': reforme_labels.get(d['etat_reforme'], d['etat_reforme']),
            'detail': d['motif_reforme'] or ('Changement vers : ' + reforme_labels.get(d['etat_reforme'], d['etat_reforme'])),
            'obs': '',
            'reforme': {
                'etat': d['etat_reforme'],
                'ancien_etat': d['ancien_etat_reforme'] or 'AUCUNE',
                'motif': d['motif_reforme'] or ''
            }
        })

    events.sort(key=lambda e: (e.get('date_evenement') or '', e.get('type_evenement') or ''), reverse=True)
    conn.close()
    return jsonify(events)

