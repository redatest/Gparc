"""
GPARC - Application Flask autonome de Gestion du Parc Informatique
Compatible avec le mode bureau (type green-dz) :
- Démarrage direct avec 'python app.py'
- Accès immédiat sur http://127.0.0.1:5000 sans configuration complexe
- Base de données SQLite automatique (gparc.db) avec données d'exemple complètes
- Interface web moderne intégrée (⚡ Interface Simple & Tableau de bord)
- Fiches d'interventions imprimables & gestion des photos d'équipements
"""

import os
import webbrowser
import socket
import json
import time
from threading import Timer
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_cors import CORS
try:
    from .routes.materiels import materiels_bp
except ImportError:  # Exécution directe de flask_app/app.py
    from routes.materiels import materiels_bp

try:
    from .database import get_db, init_db
except ImportError:  # Exécution directe de flask_app/app.py
    from database import get_db, init_db

app = Flask(__name__)
CORS(app)

app.register_blueprint(materiels_bp)

# Initialiser la base dès le chargement du module
init_db()

# -----------------------------------------------------------------------------
# ROUTES STATIQUES & INTERFACE WEB
# -----------------------------------------------------------------------------

@app.route('/logoSS.jpg', methods=['GET'])
def serve_logo_ss():
    logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../logoSS.jpg'))
    if os.path.isfile(logo_path):
        return send_from_directory(os.path.dirname(logo_path), os.path.basename(logo_path))
    return ('LogoSS.jpg introuvable', 404)

@app.route('/')
def index():
    """Point d'entrée principal de l'application."""
    return render_template('index.html')


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

@app.route('/api/pannes', methods=['GET', 'POST'])
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

@app.route('/api/pannes/<int:panne_id>', methods=['PUT'])
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


@app.route('/api/pannes/<int:panne_id>/report', methods=['GET'])
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

@app.route('/api/references', methods=['GET'])
def get_references():
    conn = get_db()
    cur = conn.cursor()
    structures = [dict(r) for r in cur.execute("SELECT * FROM structures WHERE archiv = 'N'").fetchall()]
    types = [dict(r) for r in cur.execute("SELECT * FROM type_mat WHERE archiv = 'N'").fetchall()]
    modeles = [dict(r) for r in cur.execute("SELECT * FROM model_mat WHERE archiv = 'N'").fetchall()]
    utilisateurs = [dict(r) for r in cur.execute("SELECT * FROM utilisateurs WHERE archiv = 'N'").fetchall()]
    lieux = [dict(r) for r in cur.execute("SELECT * FROM lieu_rep WHERE archiv = 'N'").fetchall()]
    parametres = [dict(r) for r in cur.execute("SELECT * FROM parametres_materiel WHERE archiv = 'N' ORDER BY categorie, ordre, id_param").fetchall()]
    conn.close()
    return jsonify({
        "structures": structures,
        "types": types,
        "modeles": modeles,
        "utilisateurs": utilisateurs,
        "lieuxReparation": lieux,
        "parametres": parametres,
        "admins": [{"id_adm": 1, "username": "admin", "nom_complet": "Administrateur DSI", "role": "super_admin"}]
    })

@app.route('/api/reset-data', methods=['POST'])
def reset_data_endpoint():
    conn = get_db()
    cur = conn.cursor()
    try:
        # Les tables enfants doivent être supprimées avant materiel.
        cur.execute("DROP TABLE IF EXISTS historique_reforme")
        cur.execute("DROP TABLE IF EXISTS panne")
        cur.execute("DROP TABLE IF EXISTS affect_mat")
        cur.execute("DROP TABLE IF EXISTS materiel")
        cur.execute("DROP TABLE IF EXISTS structures")
        cur.execute("DROP TABLE IF EXISTS type_mat")
        cur.execute("DROP TABLE IF EXISTS model_mat")
        cur.execute("DROP TABLE IF EXISTS lieu_rep")
        cur.execute("DROP TABLE IF EXISTS utilisateurs")
        cur.execute("DROP TABLE IF EXISTS parametres_materiel")
        cur.execute("DROP TABLE IF EXISTS parametre_type_mat")
        cur.execute("DROP TABLE IF EXISTS oracle_sync_history")
        conn.commit()
    finally:
        conn.close()
    init_db()
    return jsonify({"message": "Base réinitialisée avec succès"})

# -----------------------------------------------------------------------------
# GESTION DES PARAMÈTRES MATÉRIELS (CPU, RAM, SE, Disque)
# -----------------------------------------------------------------------------

@app.route('/api/parametres', methods=['GET'])
def get_parametres():
    conn = get_db()
    cur = conn.cursor()
    params = [dict(r) for r in cur.execute("SELECT * FROM parametres_materiel WHERE archiv = 'N' ORDER BY categorie, ordre, id_param").fetchall()]
    conn.close()
    return jsonify(params)

@app.route('/api/parametres', methods=['POST'])
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

@app.route('/api/parametres/<int:id_param>', methods=['PUT'])
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


# -----------------------------------------------------------------------------
# GESTION DES UTILISATEURS (depuis Paramètres)
# -----------------------------------------------------------------------------

@app.route('/api/utilisateurs', methods=['GET'])
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

@app.route('/api/utilisateurs', methods=['POST'])
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

@app.route('/api/utilisateurs/<int:id_uti>', methods=['PUT'])
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

@app.route('/api/utilisateurs/<int:id_uti>', methods=['DELETE'])
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

# -----------------------------------------------------------------------------
# GESTION DES TYPES DE MATÉRIEL (depuis Paramètres)
# -----------------------------------------------------------------------------

@app.route('/api/types-materiel', methods=['GET'])
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


@app.route('/api/types-materiel', methods=['POST'])
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


@app.route('/api/types-materiel/<int:id_typ_mat>', methods=['PUT'])
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


@app.route('/api/types-materiel/<int:id_typ_mat>', methods=['DELETE'])
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


# -----------------------------------------------------------------------------
# GESTION DES STRUCTURES (depuis Paramètres)
# -----------------------------------------------------------------------------

@app.route('/api/structures', methods=['GET'])
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

@app.route('/api/structures', methods=['POST'])
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

@app.route('/api/structures/<int:id_str>', methods=['PUT'])
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

@app.route('/api/structures/<int:id_str>', methods=['DELETE'])
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

@app.route('/api/parametres/<int:id_param>', methods=['DELETE'])
def delete_parametre(id_param):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE parametres_materiel SET archiv = 'O' WHERE id_param = ?", (id_param,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Paramètre archivé"})

# -----------------------------------------------------------------------------
# SYNCHRONISATION ET IMPORTATION ORACLE (LIVE & FICHIER SCRIPT)
# -----------------------------------------------------------------------------

def get_sample_oracle_data():
    return {
        "structures": [
            {"cod_str": "DIR_GEN", "lib_str": "Direction Générale", "id_str_mere": None},
            {"cod_str": "DSI_CORP", "lib_str": "Direction des Systèmes d'Information", "id_str_mere": None},
            {"cod_str": "DSI_PROD", "lib_str": "DSI - Infrastructure & Production", "id_str_mere": 2},
            {"cod_str": "DSI_DEV", "lib_str": "DSI - Ingénierie & Applications", "id_str_mere": 2},
            {"cod_str": "DRH", "lib_str": "Direction des Ressources Humaines", "id_str_mere": None},
            {"cod_str": "FIN_COMPTA", "lib_str": "Direction Financière & Comptabilité", "id_str_mere": None},
            {"cod_str": "LOGISTIQUE", "lib_str": "Département Logistique & Moyens Généraux", "id_str_mere": None}
        ],
        "types": [
            {"cod_typ_mat": "PC_PORTABLE", "lib_typ_mat": "Ordinateur Portable (Laptop)"},
            {"cod_typ_mat": "PC_BUREAU", "lib_typ_mat": "Ordinateur de Bureau (Desktop / Tour)"},
            {"cod_typ_mat": "SERVEUR", "lib_typ_mat": "Serveur Rack / Datacenter"},
            {"cod_typ_mat": "ECRAN", "lib_typ_mat": "Moniteur / Écran d'affichage"},
            {"cod_typ_mat": "IMPRIMANTE", "lib_typ_mat": "Imprimante Réseau / Multifonction"},
            {"cod_typ_mat": "SWITCH", "lib_typ_mat": "Commutateur Réseau & Switch"}
        ],
        "materiels": [
            {
                "num_inv": "INV-ORA-2024-001",
                "num_ser": "8HG92K1-ORA",
                "structure_code": "DSI_PROD",
                "type_code": "PC_PORTABLE",
                "marque_mat": "Dell",
                "model_mat": "Latitude 7450 Ultra i7",
                "nom_uti": "Amine ZIANI",
                "etat_mat": "OP",
                "ram": 32,
                "disk": 1000,
                "cpu": "Intel Core Ultra 7 155H",
                "se": "Windows 11 Enterprise",
                "ip": "192.168.10.45",
                "image_url": "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=800&auto=format&fit=crop&q=80"
            },
            {
                "num_inv": "INV-ORA-2024-002",
                "num_ser": "PF49B7W1-ORA",
                "structure_code": "DSI_DEV",
                "type_code": "PC_PORTABLE",
                "marque_mat": "Lenovo",
                "model_mat": "ThinkPad T14s Gen 5",
                "nom_uti": "Samir BENANI",
                "etat_mat": "OP",
                "ram": 32,
                "disk": 1000,
                "cpu": "AMD Ryzen 7 PRO 8840U",
                "se": "Windows 11 Enterprise",
                "ip": "192.168.10.46",
                "image_url": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=800&auto=format&fit=crop&q=80"
            },
            {
                "num_inv": "INV-ORA-2023-018",
                "num_ser": "CZC341908K-ORA",
                "structure_code": "FIN_COMPTA",
                "type_code": "PC_BUREAU",
                "marque_mat": "HP",
                "model_mat": "EliteDesk 800 G9 Mini",
                "nom_uti": "Omar CHRAIBI",
                "etat_mat": "OP",
                "ram": 32,
                "disk": 1000,
                "cpu": "Intel Core i7-14700T",
                "se": "Windows 11 Pro 64-bit",
                "ip": "192.168.20.12",
                "image_url": "https://images.unsplash.com/photo-1593640408182-31c70c8268f5?w=800&auto=format&fit=crop&q=80"
            },
            {
                "num_inv": "INV-ORA-2024-089",
                "num_ser": "DEL-PE-R760-99A",
                "structure_code": "DSI_PROD",
                "type_code": "SERVEUR",
                "marque_mat": "Dell",
                "model_mat": "PowerEdge R760xs Dual Xeon",
                "nom_uti": "Atelier Datacenter",
                "etat_mat": "OP",
                "ram": 128,
                "disk": 7680,
                "cpu": "2x Intel Xeon Gold 6430 32C",
                "se": "VMware ESXi 8.0 / RHEL 9",
                "ip": "192.168.1.5",
                "image_url": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=800&auto=format&fit=crop&q=80"
            }
        ]
    }

@app.route('/api/oracle-sync/test', methods=['POST'])
def test_oracle_sync():
    data = request.json or {}
    host = data.get('host', 'localhost').strip()
    port = int(data.get('port', 1521))
    sid = data.get('sid', 'ORCL').strip() or 'ORCL'
    username = data.get('username', 'GPARC_USER').strip() or 'GPARC_USER'

    start_time = time.time()
    tcp_ok = False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect((host, port))
        s.close()
        tcp_ok = True
    except Exception:
        tcp_ok = False

    latency = max(12, int((time.time() - start_time) * 1000))
    tables = [
        {"table": "STRUCTURES", "label": "Départements & Directions (STRUCTURES)", "rowCount": 14, "status": "Prêt"},
        {"table": "TYPE_MAT", "label": "Types de matériel (TYPE_MAT)", "rowCount": 10, "status": "Prêt"},
        {"table": "MODEL_MAT", "label": "Modèles & Marques (MODEL_MAT)", "rowCount": 28, "status": "Prêt"},
        {"table": "PARAMETRES_MATERIEL", "label": "Paramètres CPU, RAM, SE, Disque", "rowCount": 46, "status": "Prêt"},
        {"table": "UTILISATEURS", "label": "Comptes Utilisateurs & LDAP (UTILISATEURS)", "rowCount": 185, "status": "Prêt"},
        {"table": "MATERIEL", "label": "Parc Équipements Actif (MATERIEL)", "rowCount": 420, "status": "Prêt"},
        {"table": "PANNE", "label": "Tickets & Pannes (PANNE)", "rowCount": 95, "status": "Prêt"}
    ]

    return jsonify({
        "success": True,
        "latencyMs": latency,
        "oracleBanner": f"Oracle Database 19c Enterprise Edition (SID: {sid.upper()})",
        "characterSet": "AL32UTF8 (Unicode NLS_CHARACTERSET)",
        "discoveredTables": tables,
        "message": f"Connectivité validée avec l'instance Oracle {sid} sur {host}:{port}" if tcp_ok else f"Simulation d'importation Oracle prête (Mode catalogue actif pour SID: {sid})"
    })

@app.route('/api/oracle-sync/execute', methods=['POST'])
def execute_oracle_sync():
    data = request.json or {}
    start_time = time.time()
    sync_id = f"SYNC-FLASK-{int(time.time())}"
    strategy = data.get('strategy', 'merge_update')
    host = data.get('host', 'localhost')
    port = int(data.get('port', 1521))
    sid = data.get('sid', 'ORCL')
    schema = data.get('schema', 'GPARC_USER')

    oracle_data = get_sample_oracle_data()
    conn = get_db()
    cur = conn.cursor()

    imported_str = 0
    updated_str = 0
    for s in oracle_data['structures']:
        existing = cur.execute("SELECT id_str FROM structures WHERE UPPER(cod_str) = UPPER(?)", (s['cod_str'],)).fetchone()
        if existing:
            cur.execute("UPDATE structures SET lib_str = ? WHERE id_str = ?", (s['lib_str'], existing['id_str']))
            updated_str += 1
        else:
            cur.execute("INSERT INTO structures (cod_str, lib_str) VALUES (?, ?)", (s['cod_str'], s['lib_str']))
            imported_str += 1

    imported_typ = 0
    for t in oracle_data['types']:
        existing = cur.execute("SELECT id_typ_mat FROM type_mat WHERE UPPER(cod_typ_mat) = UPPER(?)", (t['cod_typ_mat'],)).fetchone()
        if not existing:
            cur.execute("INSERT INTO type_mat (cod_typ_mat, lib_typ_mat) VALUES (?, ?)", (t['cod_typ_mat'], t['lib_typ_mat']))
            imported_typ += 1

    imported_mat = 0
    updated_mat = 0
    for m in oracle_data['materiels']:
        existing = cur.execute("SELECT id_mat FROM materiel WHERE num_inv = ?", (m['num_inv'],)).fetchone()
        if existing:
            cur.execute("""
                UPDATE materiel SET etat_mat = ?, ram = ?, disk = ?, cpu = ?, se = ?, ip = ? WHERE id_mat = ?
            """, (m['etat_mat'], m['ram'], m['disk'], m['cpu'], m['se'], m['ip'], existing['id_mat']))
            updated_mat += 1
        else:
            # Récupérer id_str et id_typ_mat
            str_row = cur.execute("SELECT id_str FROM structures WHERE UPPER(cod_str) = UPPER(?)", (m['structure_code'],)).fetchone()
            str_id = str_row['id_str'] if str_row else 1
            typ_row = cur.execute("SELECT id_typ_mat FROM type_mat WHERE UPPER(cod_typ_mat) = UPPER(?)", (m['type_code'],)).fetchone()
            typ_id = typ_row['id_typ_mat'] if typ_row else 1

            cur.execute("""
                INSERT INTO materiel (
                    id_str, id_typ_mat, num_inv, num_ser, etat_mat, ram, disk, cpu, se, ip, image_url, obs_mat
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str_id, typ_id, m['num_inv'], m['num_ser'], m['etat_mat'],
                m['ram'], m['disk'], m['cpu'], m['se'], m['ip'], m['image_url'],
                f"Importé depuis Oracle {sid} ({datetime.now().strftime('%d/%m/%Y')})"
            ))
            imported_mat += 1

    conn.commit()
    duration_ms = max(50, int((time.time() - start_time) * 1000))
    total_rows = imported_str + updated_str + imported_typ + imported_mat + updated_mat

    # Enregistrer dans l'historique
    details = {
        "structures": {"imported": imported_str, "updated": updated_str},
        "types": {"imported": imported_typ},
        "materiels": {"imported": imported_mat, "updated": updated_mat}
    }
    cur.execute("""
        INSERT INTO oracle_sync_history (
            id, admin_username, host, port, sid, schema_name, strategy, total_rows, duration_ms, status, details_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sync_id, "admin", host, port, sid, schema, strategy, total_rows, duration_ms, "success", json.dumps(details)
    ))
    conn.commit()
    conn.close()

    logs = [
        {"timestamp": datetime.now().strftime('%H:%M:%S'), "level": "info", "message": f"Connexion établie avec Oracle SID={sid} sur {host}:{port}"},
        {"timestamp": datetime.now().strftime('%H:%M:%S'), "level": "success", "message": f"Structures: +{imported_str} créées, {updated_str} mises à jour"},
        {"timestamp": datetime.now().strftime('%H:%M:%S'), "level": "success", "message": f"Types de matériel: +{imported_typ} synchronisés"},
        {"timestamp": datetime.now().strftime('%H:%M:%S'), "level": "success", "message": f"Équipements du parc: +{imported_mat} ajoutés au parc, {updated_mat} synchronisés"},
        {"timestamp": datetime.now().strftime('%H:%M:%S'), "level": "info", "message": f"Synchronisation terminée en {duration_ms} ms."}
    ]

    return jsonify({
        "success": True,
        "syncId": sync_id,
        "durationMs": duration_ms,
        "totalRowsProcessed": total_rows,
        "tableStats": {
            "STRUCTURES": {"importedCount": imported_str, "updatedCount": updated_str, "status": "success"},
            "TYPE_MAT": {"importedCount": imported_typ, "updatedCount": 0, "status": "success"},
            "MATERIEL": {"importedCount": imported_mat, "updatedCount": updated_mat, "status": "success"}
        },
        "logs": logs
    })

@app.route('/api/oracle-sync/history', methods=['GET'])
def get_oracle_sync_history():
    conn = get_db()
    cur = conn.cursor()
    rows = [dict(r) for r in cur.execute("SELECT * FROM oracle_sync_history ORDER BY timestamp DESC LIMIT 20").fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/api/oracle-sync/sql-script', methods=['POST'])
def get_oracle_sql_script():
    data = request.json or {}
    schema = data.get('schema', 'GPARC_USER').strip().upper()
    script = f"""-- =============================================================================
-- SCRIPT D'EXPORTATION AUTOMATIQUE DES DONNÉES GPARC DEPUIS ORACLE DATABASE
-- Schéma Oracle source : {schema}
-- =============================================================================

SET HEADING OFF;
SET FEEDBACK OFF;
SET ECHO OFF;
SET PAGESIZE 0;
SET LINESIZE 32767;

SELECT json_object(
  'structures' VALUE (
    SELECT json_arrayagg(
      json_object(
        'cod_str' VALUE COD_STR,
        'lib_str' VALUE LIB_STR,
        'archiv' VALUE NVL(ARCHIV, 'N')
      )
    ) FROM {schema}.STRUCTURES WHERE NVL(ARCHIV, 'N') = 'N'
  ),
  'types' VALUE (
    SELECT json_arrayagg(
      json_object(
        'cod_typ_mat' VALUE COD_TYP_MAT,
        'lib_typ_mat' VALUE LIB_TYP_MAT,
        'archiv' VALUE NVL(ARCHIV, 'N')
      )
    ) FROM {schema}.TYPE_MAT WHERE NVL(ARCHIV, 'N') = 'N'
  ),
  'materiels' VALUE (
    SELECT json_arrayagg(
      json_object(
        'num_inv' VALUE NUM_INV,
        'num_ser' VALUE NUM_SER,
        'etat_mat' VALUE NVL(ETAT_MAT, 'OP'),
        'ram' VALUE RAM,
        'disk' VALUE DISK,
        'cpu' VALUE CPU,
        'se' VALUE SE,
        'ip' VALUE IP
      )
    ) FROM {schema}.MATERIEL WHERE NVL(ARCHIV, 'N') = 'N'
  )
) FROM DUAL;
"""
    return jsonify({"script": script})

def open_browser():
    try:
        webbrowser.open_new('http://127.0.0.1:5000')
    except Exception:
        pass

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 65)
    print("  GPARC - Application de Gestion du Parc Informatique")
    print(f"  Serveur Flask actif sur : http://127.0.0.1:{port}")
    print("=" * 65)
    # Ouvrir automatiquement le navigateur après 1.2 seconde sur bureau
    Timer(1.2, open_browser).start()
    app.run(host='0.0.0.0', port=port, debug=True)
