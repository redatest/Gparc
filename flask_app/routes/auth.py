"""Authentification locale et gestion des comptes GPARC."""
import os

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

try:
    from ..database import get_db
except ImportError:
    from database import get_db

auth_bp = Blueprint("auth", __name__)


def _public_admin(row):
    return {"id": row["id_admin"], "username": row["username"],
            "full_name": row["full_name"], "role": row["role"],
            "is_active": bool(row["is_active"])}


@auth_bp.get("/api/auth/status")
def auth_status():
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM admins").fetchone()[0]
    conn.close()
    return jsonify({"setup_required": count == 0})


@auth_bp.post("/api/auth/setup")
def setup_first_super_admin():
    if request.remote_addr not in ("127.0.0.1", "::1") and os.getenv("GPARC_ALLOW_REMOTE_SETUP") != "1":
        return jsonify({"error": "La création initiale du super administrateur doit être effectuée depuis le poste serveur."}), 403
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    full_name = str(data.get("full_name", "")).strip()
    password = str(data.get("password", ""))
    if len(username) < 3 or not full_name or len(password) < 10:
        return jsonify({"error": "Nom complet, identifiant (3 caractères minimum) et mot de passe (10 caractères minimum) requis."}), 400
    conn = get_db()
    try:
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute("SELECT 1 FROM admins LIMIT 1").fetchone():
            conn.rollback()
            return jsonify({"error": "La configuration initiale est déjà terminée."}), 409
        cur = conn.execute(
            """INSERT INTO admins (username, full_name, password_hash, role, is_active)
               VALUES (?, ?, ?, 'super_admin', 1)""",
            (username, full_name, generate_password_hash(password))
        )
        conn.commit()
        session.clear()
        session["admin_id"] = cur.lastrowid
        session["role"] = "super_admin"
        session["username"] = username
        session.permanent = True
        return jsonify({"success": True})
    finally:
        conn.close()


@auth_bp.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM admins WHERE username = ? COLLATE NOCASE AND is_active = 1",
        (username,)
    ).fetchone()
    conn.close()
    if not row or not check_password_hash(row["password_hash"], password):
        return jsonify({"error": "Identifiant ou mot de passe incorrect."}), 401
    session.clear()
    session["admin_id"] = row["id_admin"]
    session["role"] = row["role"]
    session["username"] = row["username"]
    session.permanent = True
    return jsonify({"success": True, "admin": _public_admin(row)})


@auth_bp.get("/api/auth/me")
def current_admin():
    admin_id = session.get("admin_id")
    if not admin_id:
        return jsonify({"error": "Non authentifié."}), 401
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM admins WHERE id_admin = ? AND is_active = 1", (admin_id,)
    ).fetchone()
    conn.close()
    if not row:
        session.clear()
        return jsonify({"error": "Session expirée."}), 401
    return jsonify(_public_admin(row))


@auth_bp.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify({"success": True})
