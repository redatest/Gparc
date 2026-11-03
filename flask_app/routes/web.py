import os
from flask import Blueprint, render_template, send_from_directory, session

try:
    from ..database import get_db
except ImportError:
    from database import get_db

web_bp = Blueprint('web', __name__)


@web_bp.route('/logoSS.jpg', methods=['GET'])
def serve_logo_ss():
    logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logoSS.jpg'))
    if os.path.isfile(logo_path):
        return send_from_directory(os.path.dirname(logo_path), os.path.basename(logo_path))
    return ('LogoSS.jpg introuvable', 404)


@web_bp.route('/')
def index():
    """Affiche l'application uniquement pour un compte actif."""
    admin_id = session.get("admin_id")
    if not admin_id:
        return render_template('login.html')
    conn = get_db()
    admin = conn.execute(
        "SELECT username, role FROM admins WHERE id_admin = ? AND is_active = 1",
        (admin_id,),
    ).fetchone()
    conn.close()
    if not admin:
        session.clear()
        return render_template('login.html')
    session["username"] = admin["username"]
    session["role"] = admin["role"]
    return render_template('index.html')
