"""Routes de synchronisation et d'importation Oracle pour GPARC."""

import json
import os
import socket
import time
import uuid
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
        # Oracle Database 11.2 or earlier requires Thick mode. Configure it
        # before creating any connection; the process must be restarted after
        # changing these environment variables.
        client_dir = os.getenv("ORACLE_CLIENT_LIB_DIR", "").strip()
        thick_mode = os.getenv("ORACLE_THICK_MODE", "").strip().lower() in ("1", "true", "yes", "on")
        if oracledb.is_thin_mode():
            if client_dir:
                oracledb.init_oracle_client(lib_dir=client_dir)
            elif thick_mode:
                oracledb.init_oracle_client()

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


@oracle_bp.route('/api/oracle-sync/schema', methods=['POST'])
def inspect_oracle_schema():
    """Liste en lecture seule les tables/vues et colonnes visibles par l'utilisateur connecté."""
    data = request.get_json(silent=True) or {}
    host = str(data.get('host', '')).strip()
    username = str(data.get('username', '')).strip()
    password = data.get('password', '')
    connect_type = str(data.get('connectType', 'service_name')).strip().lower()
    database_name = str(data.get('sid', '')).strip()
    if not host or not username or not password or not database_name:
        return jsonify({"success": False, "message": "Renseignez l’hôte, la base, l’utilisateur et le mot de passe Oracle."}), 400
    try:
        port = int(data.get('port', 1521))
        if not 1 <= port <= 65535:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Le port Oracle doit être compris entre 1 et 65535."}), 400
    if connect_type not in ('service_name', 'sid'):
        return jsonify({"success": False, "message": "Type de connexion Oracle invalide."}), 400

    connection = None
    try:
        import oracledb
        client_dir = os.getenv("ORACLE_CLIENT_LIB_DIR", "").strip()
        thick_mode = os.getenv("ORACLE_THICK_MODE", "").strip().lower() in ("1", "true", "yes", "on")
        if oracledb.is_thin_mode():
            if client_dir:
                oracledb.init_oracle_client(lib_dir=client_dir)
            elif thick_mode:
                oracledb.init_oracle_client()

        args = {"user": username, "password": password, "host": host, "port": port, "tcp_connect_timeout": 8}
        args[connect_type] = database_name
        connection = oracledb.connect(**args)
        cursor = connection.cursor()
        cursor.execute("""
            SELECT t.table_name, 'TABLE' AS table_type, c.column_name, c.data_type,
                   c.data_length, c.nullable, tc.comments AS table_comment,
                   cc.comments AS column_comment
              FROM user_tables t
              JOIN user_tab_columns c ON c.table_name = t.table_name
              LEFT JOIN user_tab_comments tc ON tc.table_name = t.table_name
              LEFT JOIN user_col_comments cc
                ON cc.table_name = c.table_name AND cc.column_name = c.column_name
             ORDER BY t.table_name, c.column_id
        """)
        rows = cursor.fetchall()
        # Include views as well: they are often used to expose legacy application data.
        cursor.execute("""
            SELECT v.view_name, c.column_name, c.data_type, c.data_length, c.nullable,
                   vc.comments AS view_comment, cc.comments AS column_comment
              FROM user_views v
              JOIN user_tab_columns c ON c.table_name = v.view_name
              LEFT JOIN user_tab_comments vc ON vc.table_name = v.view_name
              LEFT JOIN user_col_comments cc
                ON cc.table_name = c.table_name AND cc.column_name = c.column_name
             ORDER BY v.view_name, c.column_id
        """)
        view_rows = cursor.fetchall()
        cursor.close()

        objects = {}
        for name, object_type, column, data_type, length, nullable, table_comment, column_comment in rows:
            item = objects.setdefault(name, {"name": name, "type": "TABLE", "comment": table_comment or "", "columns": []})
            item["columns"].append({"name": column, "dataType": data_type, "length": length, "nullable": nullable == "Y", "comment": column_comment or ""})
        for name, column, data_type, length, nullable, view_comment, column_comment in view_rows:
            item = objects.setdefault(name, {"name": name, "type": "VIEW", "comment": view_comment or "", "columns": []})
            item["type"] = "VIEW"
            item["columns"].append({"name": column, "dataType": data_type, "length": length, "nullable": nullable == "Y", "comment": column_comment or ""})

        return jsonify({
            "success": True,
            "username": username.upper(),
            "objectCount": len(objects),
            "objects": list(objects.values()),
            "message": f"Exploration terminée : {len(objects)} tables/vues visibles, sans modification de la base Oracle."
        })
    except Exception as exc:
        diagnostic = str(exc).strip()[:500] or "Aucun détail fourni par le pilote Oracle."
        return jsonify({"success": False, "message": "Impossible d’explorer le schéma Oracle.", "details": diagnostic}), 400
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


def _open_oracle_connection(data):
    """Ouvre Oracle avec les mêmes paramètres que le test de connexion."""
    host = str(data.get('host', '')).strip()
    username = str(data.get('username', '')).strip()
    password = data.get('password', '')
    connect_type = str(data.get('connectType', 'service_name')).strip().lower()
    database_name = str(data.get('sid', '')).strip()
    if not host or not username or not password or not database_name:
        raise ValueError("Hôte, base Oracle, utilisateur et mot de passe sont obligatoires.")
    try:
        port = int(data.get('port', 1521))
        if not 1 <= port <= 65535:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("Le port Oracle doit être compris entre 1 et 65535.")
    if connect_type not in ('service_name', 'sid'):
        raise ValueError("Type de connexion Oracle invalide.")
    import oracledb
    client_dir = os.getenv("ORACLE_CLIENT_LIB_DIR", "").strip()
    thick_mode = os.getenv("ORACLE_THICK_MODE", "").strip().lower() in ("1", "true", "yes", "on")
    if oracledb.is_thin_mode():
        if client_dir:
            oracledb.init_oracle_client(lib_dir=client_dir)
        elif thick_mode:
            oracledb.init_oracle_client()
    args = {"user": username, "password": password, "host": host, "port": port, "tcp_connect_timeout": 8}
    args[connect_type] = database_name
    return oracledb.connect(**args), host, port, username, database_name


def _load_oracle_source(connection):
    try:
        from ..oracle_importer import _read_source, preview_source
    except ImportError:
        from oracle_importer import _read_source, preview_source
    source = _read_source(connection)
    return source, preview_source(source)


@oracle_bp.route('/api/oracle-sync/preview', methods=['POST'])
def preview_oracle_sync():
    """Prévisualise les volumes et anomalies sans modifier SQLite."""
    connection = None
    try:
        data = request.get_json(silent=True) or {}
        connection, host, port, username, database_name = _open_oracle_connection(data)
        source, preview = _load_oracle_source(connection)
        return jsonify({
            "success": True, "host": host, "port": port, "username": username,
            "databaseName": database_name, "preview": preview,
            "message": "Prévisualisation terminée. Aucune donnée locale n'a été modifiée."
        })
    except ImportError:
        return jsonify({"success": False, "message": "Le pilote python-oracledb n'est pas installé."}), 500
    except Exception as exc:
        return jsonify({"success": False, "message": "Prévisualisation Oracle impossible.", "details": str(exc)[:500]}), 400
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


@oracle_bp.route('/api/oracle-sync/execute', methods=['POST'])
def execute_oracle_sync():
    """Remplace les données de démonstration par Oracle, avec sauvegarde et transaction."""
    connection = None
    started = time.time()
    data = request.get_json(silent=True) or {}
    try:
        connection, host, port, username, database_name = _open_oracle_connection(data)
        source, preview = _load_oracle_source(connection)
        if not source.get("MATERIEL") and not source.get("STRUCTURE"):
            return jsonify({"success": False, "message": "Import annulé : aucune donnée de matériel ou de structure n'a été trouvée."}), 400
        try:
            from ..oracle_importer import import_source
        except ImportError:
            from oracle_importer import import_source
        result = import_source(source)
        duration_ms = int((time.time() - started) * 1000)
        local = get_db()
        try:
            local.execute("""
                INSERT INTO oracle_sync_history
                (id, admin_username, host, port, sid, schema_name, strategy, total_rows, duration_ms, status, details_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result["batchId"], None, host, port, database_name, username, "replace_demo",
                preview["totalRows"], duration_ms, "SUCCESS",
                json.dumps({"sourceCounts": result["counts"], "operationalCounts": result["operationalCounts"], "backupPath": result["backupPath"]}, ensure_ascii=False)
            ))
            local.commit()
        except Exception:
            local.rollback()
        finally:
            local.close()
        result["durationMs"] = duration_ms
        return jsonify(result)
    except ImportError:
        return jsonify({"success": False, "message": "Le pilote python-oracledb n'est pas installé."}), 500
    except Exception as exc:
        try:
            local = get_db()
            local.execute("""
                INSERT INTO oracle_sync_history
                (id, host, port, sid, schema_name, strategy, duration_ms, status, details_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()), data.get("host"), data.get("port", 1521), data.get("sid"),
                data.get("username"), "replace_demo", int((time.time() - started) * 1000),
                "ERROR", json.dumps({"error": str(exc)[:500]}, ensure_ascii=False)
            ))
            local.commit()
            local.close()
        except Exception:
            pass
        return jsonify({"success": False, "message": "Import Oracle échoué ; la transaction locale a été annulée.", "details": str(exc)[:500]}), 400
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


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
