"""Administration des comptes applicatifs (réservée au super admin)."""
from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash

try:
    from ..database import get_db
except ImportError:
    from database import get_db

admins_bp = Blueprint("admins", __name__)


def _serialize(row):
    return {"id": row["id_admin"], "username": row["username"],
            "full_name": row["full_name"], "role": row["role"],
            "is_active": bool(row["is_active"]), "created_at": row["created_at"]}


@admins_bp.get("/api/admins")
def list_admins():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM admins ORDER BY role DESC, full_name COLLATE NOCASE"
    ).fetchall()
    conn.close()
    return jsonify([_serialize(row) for row in rows])


@admins_bp.post("/api/admins")
def create_admin():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    full_name = str(data.get("full_name", "")).strip()
    password = str(data.get("password", ""))
    if len(username) < 3 or not full_name or len(password) < 10:
        return jsonify({"error": "Nom complet, identifiant (3 caractères minimum) et mot de passe (10 caractères minimum) requis."}), 400
    conn = get_db()
    try:
        cur = conn.execute(
            """INSERT INTO admins (username, full_name, password_hash, role, is_active)
               VALUES (?, ?, ?, 'admin', 1)""",
            (username, full_name, generate_password_hash(password))
        )
        conn.commit()
        row = conn.execute("SELECT * FROM admins WHERE id_admin = ?", (cur.lastrowid,)).fetchone()
        return jsonify(_serialize(row)), 201
    except Exception as exc:
        conn.rollback()
        if "UNIQUE" in str(exc).upper():
            return jsonify({"error": "Cet identifiant est déjà utilisé."}), 409
        raise
    finally:
        conn.close()


@admins_bp.put("/api/admins/<int:admin_id>")
def update_admin(admin_id):
    data = request.get_json(silent=True) or {}
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM admins WHERE id_admin = ? AND role = 'admin'", (admin_id,)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Administrateur simple introuvable."}), 404
    full_name = str(data.get("full_name", row["full_name"])).strip()
    username = str(data.get("username", row["username"])).strip()
    if not full_name or len(username) < 3:
        conn.close()
        return jsonify({"error": "Nom complet et identifiant valides requis."}), 400
    password = str(data.get("password", ""))
    is_active = 1 if data.get("is_active", bool(row["is_active"])) else 0
    if is_active == 0 and admin_id == request.environ.get("gparc_admin_id"):
        conn.close()
        return jsonify({"error": "Vous ne pouvez pas désactiver votre propre compte."}), 400
    try:
        if password:
            if len(password) < 10:
                return jsonify({"error": "Le mot de passe doit contenir au moins 10 caractères."}), 400
            conn.execute(
                """UPDATE admins SET full_name=?, username=?, password_hash=?, is_active=?
                   WHERE id_admin=?""",
                (full_name, username, generate_password_hash(password), is_active, admin_id)
            )
        else:
            conn.execute(
                "UPDATE admins SET full_name=?, username=?, is_active=? WHERE id_admin=?",
                (full_name, username, is_active, admin_id)
            )
        conn.commit()
        updated = conn.execute("SELECT * FROM admins WHERE id_admin=?", (admin_id,)).fetchone()
        return jsonify(_serialize(updated))
    except Exception as exc:
        conn.rollback()
        if "UNIQUE" in str(exc).upper():
            return jsonify({"error": "Cet identifiant est déjà utilisé."}), 409
        raise
    finally:
        conn.close()


@admins_bp.delete("/api/admins/<int:admin_id>")
def deactivate_admin(admin_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM admins WHERE id_admin = ? AND role = 'admin'", (admin_id,)
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"error": "Administrateur simple introuvable."}), 404
    conn.execute("UPDATE admins SET is_active=0 WHERE id_admin=?", (admin_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})
