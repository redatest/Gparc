"""Routes de synchronisation et d'importation Oracle pour GPARC."""

import json
import socket
import time
from datetime import datetime

from flask import Blueprint, jsonify, request

try:
    from ..database import get_db
except ImportError:
    from database import get_db


oracle_bp = Blueprint('oracle', __name__)


@oracle_bp.route('/api/oracle-sync/test', methods=['POST'])
def test_oracle_sync():
    """Teste une vraie session Oracle, avec authentification."""
    data = request.get_json(silent=True) or {}
    host = str(data.get('host', '')).strip()
    username = str(data.get('username', '')).strip()
    password = data.get('password', '')
    connect_type = str(data.get('connectType', 'service_name')).strip().lower()
    database_name = str(data.get('sid', '')).strip()
    if not host or not username or not password or not database_name:
        return jsonify({"success": False, "message": "Hôte, base Oracle, utilisateur et mot de passe sont obligatoires."}), 400
    try:
        port = int(data.get('port', 1521))
        if not 1 <= port <= 65535:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Le port Oracle doit être compris entre 1 et 65535."}), 400
    if connect_type not in ('service_name', 'sid'):
        return jsonify({"success": False, "message": "Type de connexion Oracle invalide."}), 400
    try:
        import oracledb
    except ImportError:
        return jsonify({"success": False, "message": "Le pilote python-oracledb n'est pas installé dans l'environnement Python qui exécute Gparc."}), 500
    start_time = time.time()
    connection = None
    try:
        args = {"user": username, "password": password, "host": host, "port": port, "tcp_connect_timeout": 5}
        args[connect_type] = database_name
        connection = oracledb.connect(**args)
        cursor = connection.cursor()
        cursor.execute("SELECT SYS_CONTEXT('USERENV', 'DB_NAME'), SYS_CONTEXT('USERENV', 'SERVICE_NAME'), USER FROM dual")
        db_name, service_name, connected_user = cursor.fetchone()
        cursor.close()
        return jsonify({
            "success": True, "latencyMs": int((time.time() - start_time) * 1000),
            "databaseName": db_name or "", "serviceName": service_name or "",
            "username": connected_user or username,
            "message": f"Authentification Oracle réussie sur {host}:{port}."
        })
    except Exception as exc:
        oracle_code = ""
        diagnostic = str(exc).strip()
        try:
            error_obj = exc.args[0] if getattr(exc, "args", None) else None
            oracle_code = (
                getattr(error_obj, "full_code", "")
                or getattr(error_obj, "code", "")
                or ""
            )
        except Exception:
            pass
        # python-oracledb exceptions include diagnostic codes (ORA-/DPY-).
        # Do not return the submitted password or the full connection arguments.
        safe_diagnostic = diagnostic[:500] if diagnostic else "Aucun détail fourni par le pilote Oracle."
        message = (
            f"Échec de la connexion Oracle{f' ({oracle_code})' if oracle_code else ''}. "
            "Consultez le détail technique pour identifier la cause."
        )
        return jsonify({
            "success": False,
            "message": message,
            "oracleCode": oracle_code,
            "details": safe_diagnostic
        }), 400
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


@oracle_bp.route('/api/oracle-sync/execute', methods=['POST'])
def execute_oracle_sync():
    """Bloque l'ancien import simulé jusqu'à l'implémentation du mapping réel."""
    return jsonify({
        "success": False,
        "message": (
            "Importation désactivée : cette version utilisait des données d'exemple et non les données Oracle. "
            "Identifiez les tables et colonnes de la base source avant de préparer une migration réelle."
        )
    }), 501


@oracle_bp.route('/api/oracle-sync/history', methods=['GET'])
def get_oracle_sync_history():
    conn = get_db()
    cur = conn.cursor()
    rows = [dict(r) for r in cur.execute("SELECT * FROM oracle_sync_history ORDER BY timestamp DESC LIMIT 20").fetchall()]
    conn.close()
    return jsonify(rows)


@oracle_bp.route('/api/oracle-sync/sql-script', methods=['POST'])
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
