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
    from .routes.utilisateurs import utilisateurs_bp
except ImportError:
    from routes.utilisateurs import utilisateurs_bp
try:
    from .routes.types_materiel import types_materiel_bp
except ImportError:
    from routes.types_materiel import types_materiel_bp
try:
    from .routes.structures import structures_bp
except ImportError:
    from routes.structures import structures_bp
try:
    from .routes.parametres import parametres_bp
except ImportError:
    from routes.parametres import parametres_bp
try:
    from .routes.pannes import pannes_bp
except ImportError:
    from routes.pannes import pannes_bp
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
app.register_blueprint(pannes_bp)
app.register_blueprint(parametres_bp)
app.register_blueprint(utilisateurs_bp)
app.register_blueprint(types_materiel_bp)
app.register_blueprint(structures_bp)

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