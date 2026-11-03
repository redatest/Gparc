"""GPARC - Gestion du Parc Informatique."""
import os
import secrets
import webbrowser
from datetime import timedelta

from flask import Flask, g, jsonify, request, session

try:
    from .routes import (
        materiels_bp, pannes_bp, parametres_bp, utilisateurs_bp,
        types_materiel_bp, structures_bp, oracle_bp, system_bp, web_bp,
        auth_bp, admins_bp,
    )
    from .database import DB_PATH, init_db, get_db
except ImportError:
    from routes import (
        materiels_bp, pannes_bp, parametres_bp, utilisateurs_bp,
        types_materiel_bp, structures_bp, oracle_bp, system_bp, web_bp,
        auth_bp, admins_bp,
    )
    from database import DB_PATH, init_db, get_db

app = Flask(__name__)

def _load_secret_key():
    configured = os.getenv("GPARC_SECRET_KEY")
    if configured:
        return configured
    secret_path = os.path.join(os.path.dirname(DB_PATH), ".gparc_secret_key")
    os.makedirs(os.path.dirname(secret_path), exist_ok=True)
    try:
        with open(secret_path, "r", encoding="utf-8") as secret_file:
            value = secret_file.read().strip()
            if value:
                return value
    except OSError:
        pass
    value = secrets.token_hex(48)
    with open(secret_path, "w", encoding="utf-8") as secret_file:
        secret_file.write(value)
    try:
        os.chmod(secret_path, 0o600)
    except OSError:
        pass
    return value

app.secret_key = _load_secret_key()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("GPARC_COOKIE_SECURE", "").lower() in ("1", "true", "yes"),
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
)

for blueprint in (
    materiels_bp, pannes_bp, parametres_bp, utilisateurs_bp,
    types_materiel_bp, structures_bp, oracle_bp, system_bp,
    auth_bp, admins_bp, web_bp,
):
    app.register_blueprint(blueprint)


@app.before_request
def require_authenticated_admin():
    if not request.path.startswith("/api/"):
        return None
    public_auth_routes = {
        "/api/auth/status", "/api/auth/setup", "/api/auth/login",
    }
    if request.path in public_auth_routes:
        return None

    admin_id = session.get("admin_id")
    if not admin_id:
        return jsonify({"error": "Authentification requise.", "auth_required": True}), 401

    conn = get_db()
    admin = conn.execute(
        "SELECT id_admin, username, role, is_active FROM admins WHERE id_admin = ?",
        (admin_id,),
    ).fetchone()
    conn.close()
    if not admin or not admin["is_active"]:
        session.clear()
        return jsonify({"error": "Session invalide ou compte désactivé.", "auth_required": True}), 401

    g.current_admin = dict(admin)
    request.environ["gparc_admin_id"] = admin["id_admin"]
    session["role"] = admin["role"]
    session["username"] = admin["username"]

    if request.path.startswith("/api/oracle-sync/") and admin["role"] != "super_admin":
        return jsonify({"error": "Cette fonctionnalité est réservée au super administrateur."}), 403
    if request.path.startswith("/api/admins") and admin["role"] != "super_admin":
        return jsonify({"error": "La gestion des administrateurs est réservée au super administrateur."}), 403
    if request.path == "/api/reset-data" and admin["role"] != "super_admin":
        return jsonify({"error": "Action réservée au super administrateur."}), 403
    return None


# Initialiser le schéma SQLite et ses migrations au démarrage.
init_db()


def open_browser():
    try:
        webbrowser.open_new("http://127.0.0.1:5000")
    except Exception:
        pass
