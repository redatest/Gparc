import os
from flask import Blueprint, render_template, send_from_directory, session

web_bp = Blueprint('web', __name__)


@web_bp.route('/logoSS.jpg', methods=['GET'])
def serve_logo_ss():
    logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../logoSS.jpg'))
    if os.path.isfile(logo_path):
        return send_from_directory(os.path.dirname(logo_path), os.path.basename(logo_path))
    return ('LogoSS.jpg introuvable', 404)


@web_bp.route('/')
def index():
    """Affiche l'application après authentification, sinon l'écran de connexion."""
    if not session.get("admin_id"):
        return render_template('login.html')
    return render_template('index.html')
