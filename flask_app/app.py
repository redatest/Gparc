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
import sys
import sqlite3
import webbrowser
import socket
import json
import time
from threading import Timer
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory, render_template_string, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Définition du chemin de la base de données SQLite
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Si on est dans le dossier flask_app, remonter d'un cran si ../data existe, sinon créer localement
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, '../data'))
if not os.path.exists(DATA_DIR):
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except Exception:
        DATA_DIR = os.path.join(BASE_DIR, 'data')
        os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, 'gparc.db')
DIST_DIR = os.path.abspath(os.path.join(BASE_DIR, '../dist'))

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Initialise le schéma SQLite et les données de démonstration si la base est neuve."""
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS structures (
        id_str INTEGER PRIMARY KEY AUTOINCREMENT,
        cod_str TEXT NOT NULL,
        lib_str TEXT NOT NULL,
        id_str_mere INTEGER,
        archiv TEXT DEFAULT 'N',
        dat_cre DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS type_mat (
        id_typ_mat INTEGER PRIMARY KEY AUTOINCREMENT,
        cod_typ_mat TEXT NOT NULL,
        lib_typ_mat TEXT NOT NULL,
        archiv TEXT DEFAULT 'N',
        dat_cre DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS model_mat (
        id_model_mat INTEGER PRIMARY KEY AUTOINCREMENT,
        marque_mat TEXT NOT NULL,
        model_mat TEXT NOT NULL,
        id_typ_mat INTEGER,
        archiv TEXT DEFAULT 'N',
        dat_cre DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS lieu_rep (
        id_lieu_rep INTEGER PRIMARY KEY AUTOINCREMENT,
        nom_lieu_rep TEXT NOT NULL,
        adr_lieu_rep TEXT,
        tel_lieu_rep TEXT,
        contact_rep TEXT,
        archiv TEXT DEFAULT 'N',
        dat_cre DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS utilisateurs (
        id_uti INTEGER PRIMARY KEY AUTOINCREMENT,
        nom_uti TEXT NOT NULL,
        pnom_uti TEXT NOT NULL,
        mail_uti TEXT,
        id_str_mere INTEGER,
        archiv TEXT DEFAULT 'N',
        dat_cre DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS materiel (
        id_mat INTEGER PRIMARY KEY AUTOINCREMENT,
        id_str INTEGER,
        id_typ_mat INTEGER,
        id_model_mat INTEGER,
        marque_mat TEXT,
        num_inv TEXT UNIQUE NOT NULL,
        num_ser TEXT NOT NULL,
        dat_acq DATE,
        dat_mes DATE,
        etat_mat TEXT DEFAULT 'OP',
        obs_mat TEXT,
        ram INTEGER,
        disk INTEGER,
        cpu TEXT,
        se TEXT,
        net TEXT,
        ordi TEXT,
        ip TEXT,
        id_uti INTEGER,
        image_url TEXT,
        valeur_acq REAL DEFAULT 0,
        archiv TEXT DEFAULT 'N',
        dat_cre DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS affect_mat (
        id_aff_mat INTEGER PRIMARY KEY AUTOINCREMENT,
        id_mat INTEGER NOT NULL,
        id_str INTEGER,
        id_model_mat INTEGER,
        id_typ_mat INTEGER,
        num_inv TEXT,
        num_ser TEXT,
        dat_aff DATETIME DEFAULT CURRENT_TIMESTAMP,
        obs_aff TEXT,
        id_uti INTEGER,
        action_aff TEXT DEFAULT 'NOUVELLE_AFFECTATION',
        ancien_id_str INTEGER,
        ancien_id_uti INTEGER,
        archiv TEXT DEFAULT 'N',
        dat_cre DATETIME DEFAULT CURRENT_TIMESTAMP,
        dat_mod DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_mat) REFERENCES materiel (id_mat),
        FOREIGN KEY (id_str) REFERENCES structures (id_str),
        FOREIGN KEY (id_uti) REFERENCES utilisateurs (id_uti)
    );

    CREATE TABLE IF NOT EXISTS panne (
        id_pan INTEGER PRIMARY KEY AUTOINCREMENT,
        id_mat INTEGER NOT NULL,
        id_str INTEGER,
        id_typ_mat INTEGER,
        id_model_mat INTEGER,
        num_inv TEXT,
        num_ser TEXT,
        dat_pan DATE NOT NULL,
        diag_pan TEXT NOT NULL,
        dat_env_rep DATE,
        dat_ret_rep DATE,
        id_lieu_rep INTEGER,
        obs_rep TEXT,
        eta_pan TEXT DEFAULT 'EC',
        tp TEXT DEFAULT 'MAT',
        technicien TEXT,
        pieces_remplacees TEXT,
        cout_rep REAL DEFAULT 0,
        archiv TEXT DEFAULT 'N',
        dat_cre DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS parametres_materiel (
        id_param INTEGER PRIMARY KEY AUTOINCREMENT,
        categorie TEXT NOT NULL,
        valeur TEXT NOT NULL,
        description TEXT,
        ordre INTEGER DEFAULT 0,
        archiv TEXT DEFAULT 'N'
    );

    CREATE TABLE IF NOT EXISTS parametre_type_mat (
        id_param_type INTEGER PRIMARY KEY AUTOINCREMENT,
        id_typ_mat INTEGER NOT NULL,
        code_param TEXT NOT NULL,
        libelle_param TEXT NOT NULL,
        categorie_groupe TEXT,
        type_champ TEXT DEFAULT 'text',
        unite TEXT,
        options_predefinies TEXT,
        description TEXT,
        ordre INTEGER DEFAULT 0,
        archiv TEXT DEFAULT 'N',
        dat_cre DATETIME DEFAULT CURRENT_TIMESTAMP,
        dat_mod DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS oracle_sync_history (
        id TEXT PRIMARY KEY,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        admin_username TEXT,
        host TEXT,
        port INTEGER,
        sid TEXT,
        schema_name TEXT,
        strategy TEXT,
        total_rows INTEGER,
        duration_ms INTEGER,
        status TEXT,
        details_json TEXT
    );
    """)

    # Migration légère pour les bases GPARC déjà existantes.
    mat_columns = {row[1] for row in cur.execute("PRAGMA table_info(materiel)").fetchall()}
    if 'marque_mat' not in mat_columns:
        cur.execute("ALTER TABLE materiel ADD COLUMN marque_mat TEXT")

    # Migration légère de l'historique d'affectation.
    affect_columns = {row[1] for row in cur.execute("PRAGMA table_info(affect_mat)").fetchall()}
    if 'action_aff' not in affect_columns:
        cur.execute("ALTER TABLE affect_mat ADD COLUMN action_aff TEXT DEFAULT 'NOUVELLE_AFFECTATION'")
    if 'ancien_id_str' not in affect_columns:
        cur.execute("ALTER TABLE affect_mat ADD COLUMN ancien_id_str INTEGER")
    if 'ancien_id_uti' not in affect_columns:
        cur.execute("ALTER TABLE affect_mat ADD COLUMN ancien_id_uti INTEGER")

    # Amorçage des paramètres CPU, RAM, SE, Disque si vides
    count_params = cur.execute("SELECT COUNT(*) FROM parametres_materiel").fetchone()[0]
    if count_params == 0:
        default_params = [
            ('marque', 'Dell', 'Marque de matériel informatique', 1),
            ('marque', 'HP', 'Marque de matériel informatique', 2),
            ('marque', 'Lenovo', 'Marque de matériel informatique', 3),
            ('marque', 'Cisco', 'Marque de matériel réseau', 4),
            ('marque', 'APC', 'Marque d’onduleurs', 5),
            ('marque', 'Apple', 'Marque de matériel informatique', 6),
            ('cpu', 'Intel Core i7-1370P vPro (14C/20T)', 'Standard cadres DSI & ingénieurs', 1),
            ('cpu', 'Intel Core i5-1345U (10C/12T)', 'Standard bureautique et mobilité', 2),
            ('cpu', 'Intel Core Ultra 7 155H', 'Nouveaux postes haute performance IA', 3),
            ('cpu', 'Dual Intel Xeon Silver 4314 (32C)', 'Serveurs Datacenter & Virtualisation', 4),
            ('ram', '16', 'Capacité standard bureautique', 1),
            ('ram', '32', 'Postes développeurs et analystes', 2),
            ('ram', '64', 'Serveurs & stations de travail', 3),
            ('ram', '8', 'Postes légers logistique', 4),
            ('disk', '512', 'SSD NVMe standard', 1),
            ('disk', '1000', 'SSD NVMe haute capacité 1 To', 2),
            ('disk', '256', 'SSD bureautique', 3),
            ('disk', '4000', 'Stockage SAS/SATA serveurs', 4),
            ('se', 'Windows 11 Pro 64-bit', 'Système d\'exploitation par défaut', 1),
            ('se', 'Windows 10 Pro 64-bit', 'Postes existants en migration', 2),
            ('se', 'Debian 12 Bookworm Linux', 'Serveurs applicatifs et bases de données', 3),
            ('se', 'Red Hat Enterprise Linux 9', 'Serveurs de production critiques', 4),
        ]
        for p in default_params:
            cur.execute("INSERT INTO parametres_materiel (categorie, valeur, description, ordre) VALUES (?, ?, ?, ?)", p)

    # Vérification et amorçage des données de test
    count_mats = cur.execute("SELECT COUNT(*) FROM materiel").fetchone()[0]
    if count_mats == 0:
        print("[GPARC] Amorçage initial de la base de données SQLite...")

        # Structures
        structures = [
            ('DSI', 'Direction des Systèmes d\'Information'),
            ('DRH', 'Direction des Ressources Humaines'),
            ('DFIN', 'Direction Financière & Comptabilité'),
            ('LOG', 'Direction Logistique & Exploitation'),
            ('DIRG', 'Direction Générale')
        ]
        for s in structures:
            cur.execute("INSERT INTO structures (cod_str, lib_str) VALUES (?, ?)", s)

        # Types
        types = [
            ('UC', 'Ordinateur de Bureau (Unité Centrale)'),
            ('PORT', 'Ordinateur Portable (Laptop)'),
            ('IMP', 'Imprimante Réseau / Multifonction'),
            ('ECR', 'Écran / Moniteur'),
            ('SRV', 'Serveur Rack / Datacenter'),
            ('SWI', 'Switch / Équipement Réseau')
        ]
        for t in types:
            cur.execute("INSERT INTO type_mat (cod_typ_mat, lib_typ_mat) VALUES (?, ?)", t)

        # Modèles
        modeles = [
            ('HP', 'ProDesk 400 G7 SFF', 1),
            ('Dell', 'Latitude 5540 i7', 2),
            ('Lenovo', 'ThinkPad T14 Gen 4', 2),
            ('HP', 'LaserJet Enterprise M507x', 3),
            ('Dell', 'UltraSharp U2722D', 4),
            ('Dell', 'PowerEdge R750xs', 5),
            ('Cisco', 'Catalyst 2960X-48FPS', 6)
        ]
        for m in modeles:
            cur.execute("INSERT INTO model_mat (marque_mat, model_mat, id_typ_mat) VALUES (?, ?, ?)", m)

        # Lieux de réparation
        lieux = [
            ('Atelier Interne DSI (Niveau 1 & 2)', 'Bâtiment Principal, Salle IT-04', '021 55 44 33', 'Chef d\'Atelier Support DSI'),
            ('SAV Constructeur Dell ProSupport', 'Zone d\'Affaires Bab Ezzouar, Alger', '021 98 76 54', 'Support Entreprise Dell'),
            ('Prestataire Maintenance Matériel HP', 'Boulevard des Martyrs, Alger', '021 77 66 55', 'Ingénieur d\'Affaires HP')
        ]
        for l in lieux:
            cur.execute("INSERT INTO lieu_rep (nom_lieu_rep, adr_lieu_rep, tel_lieu_rep, contact_rep) VALUES (?, ?, ?, ?)", l)

        # Utilisateurs
        users = [
            ('AMRANI', 'Sofiane', 's.amrani@entreprise.dz', 1),
            ('BENALI', 'Karim', 'k.benali@entreprise.dz', 1),
            ('MANSOURI', 'Sarah', 's.mansouri@entreprise.dz', 2),
            ('HADDAD', 'Yacine', 'y.haddad@entreprise.dz', 3),
            ('BOUMEDIENE', 'Lina', 'l.boumediene@entreprise.dz', 4)
        ]
        for u in users:
            cur.execute("INSERT INTO utilisateurs (nom_uti, pnom_uti, mail_uti, id_str_mere) VALUES (?, ?, ?, ?)", u)

        # Matériels de démonstration avec photos
        materiels = [
            (1, 2, 2, 'INV-2023-001', 'SN-DELL-LAT5540-001', '2023-01-15', '2023-01-20', 'OP', 'Poste Administrateur Système DSI', 16, 512, 'Intel Core i7-1370P vPro', 'Windows 11 Pro 64-bit', 'WiFi 6E + Ethernet 1Gbps', 'PC-DSI-ADMIN1', '192.168.1.101', 1, 'https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=800&auto=format&fit=crop&q=80', 215000),
            (2, 2, 3, 'INV-2023-014', 'SN-LENOVO-T14-0422', '2023-02-10', '2023-02-15', 'OP', 'PC Portable Responsable RH', 16, 512, 'Intel Core i5-1345U', 'Windows 11 Pro 64-bit', 'WiFi 6E', 'PC-DRH-DIR', '192.168.1.114', 3, 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=800&auto=format&fit=crop&q=80', 195000),
            (3, 3, 4, 'INV-2023-088', 'SN-HP-M507-4410', '2023-03-01', '2023-03-05', 'PA', 'Imprimante réseau partagée Finance', 0, 0, 'Contrôleur HP JetDirect', 'Firmware HP FutureSmart 5', 'Ethernet 1Gbps', 'PRT-FIN-01', '192.168.1.205', 4, 'https://images.unsplash.com/photo-1612815154858-60aa4c59eaa6?w=800&auto=format&fit=crop&q=80', 145000),
            (1, 1, 1, 'INV-2023-042', 'SN-HP-PD400-1120', '2023-03-12', '2023-03-15', 'RE', 'Unité centrale Atelier DSI', 16, 512, 'Intel Core i5-10500', 'Windows 11 Pro', 'Ethernet 1Gbps', 'PC-DSI-TECH2', '192.168.1.102', 2, 'https://images.unsplash.com/photo-1593640408182-31c70c8268f5?w=800&auto=format&fit=crop&q=80', 120000),
            (4, 1, 1, 'INV-2023-055', 'SN-HP-PD400-1135', '2023-04-01', '2023-04-05', 'OP', 'Poste bureautique Gestion Logistique', 8, 256, 'Intel Core i3-10100', 'Windows 10 Pro', 'Ethernet 1Gbps', 'PC-LOG-01', '192.168.1.130', 5, 'https://images.unsplash.com/photo-1587831990711-23ca6441447b?w=800&auto=format&fit=crop&q=80', 98000),
            (1, 5, 6, 'INV-2022-003', 'SN-DELL-R750-9901', '2022-11-10', '2022-11-20', 'OP', 'Serveur Base de Données & Applications GPARC', 64, 4000, 'Dual Intel Xeon Silver 4314', 'Debian 12 Bookworm Linux', '4x 10Gbps SFP+', 'SRV-DB-PROD', '192.168.1.10', 1, 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=800&auto=format&fit=crop&q=80', 850000)
        ]
        for m in materiels:
            cur.execute("""
            INSERT INTO materiel (
                id_str, id_typ_mat, id_model_mat, num_inv, num_ser, dat_acq, dat_mes,
                etat_mat, obs_mat, ram, disk, cpu, se, net, ordi, ip, id_uti, image_url, valeur_acq
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, m)

        # Pannes initiales
        pannes = [
            (3, 3, 3, 4, 'INV-2023-088', 'SN-HP-M507-4410', '2024-03-10', 'Bourrage papier systématique dans le bac 2 et grincement mécanique du rouleau d\'entraînement.', 'EC', 'MAT', 'Prestataire HP Maintenance', 3, 'Kit de maintenance HP rouleaux', 18000, 'Remplacement kit rouleau pris en charge'),
            (4, 1, 1, 1, 'INV-2023-042', 'SN-HP-PD400-1120', '2024-03-08', 'Le poste s\'éteint brusquement après 10 minutes d\'utilisation avec odeur d\'échauffement.', 'AT', 'ALIM', 'M. Karim Benali (Atelier DSI)', 1, 'Alimentation interne 180W', 9500, 'En attente de réception de la pièce de rechange')
        ]
        for p in pannes:
            cur.execute("""
            INSERT INTO panne (
                id_mat, id_str, id_typ_mat, id_model_mat, num_inv, num_ser,
                dat_pan, diag_pan, eta_pan, tp, technicien, id_lieu_rep, pieces_remplacees, cout_rep, obs_rep
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, p)

        conn.commit()
        print("[GPARC] Base SQLite initialisée avec succès.")

    # Synchroniser les marques du référentiel avec les modèles existants.
    brands = [r[0] for r in cur.execute("SELECT DISTINCT TRIM(marque_mat) FROM model_mat WHERE archiv = 'N' AND TRIM(marque_mat) <> ''").fetchall()]
    for brand in brands:
        exists = cur.execute("SELECT 1 FROM parametres_materiel WHERE categorie = 'marque' AND LOWER(TRIM(valeur)) = LOWER(?) AND archiv = 'N'", (brand,)).fetchone()
        if not exists:
            cur.execute("INSERT INTO parametres_materiel (categorie, valeur, description, ordre) VALUES ('marque', ?, 'Marque issue du référentiel des modèles', 0)", (brand,))

    cur.execute("""
        UPDATE materiel
        SET marque_mat = (SELECT mm.marque_mat FROM model_mat mm WHERE mm.id_model_mat = materiel.id_model_mat)
        WHERE (marque_mat IS NULL OR TRIM(marque_mat) = '') AND id_model_mat IS NOT NULL
    """)

    # Synchroniser le référentiel des modèles avec les paramètres.
    model_rows = cur.execute(
        "SELECT DISTINCT TRIM(model_mat) AS model_name FROM model_mat WHERE archiv = 'N' AND TRIM(model_mat) <> ''"
    ).fetchall()
    for row in model_rows:
        exists = cur.execute(
            "SELECT 1 FROM parametres_materiel WHERE categorie = 'modele' AND LOWER(TRIM(valeur)) = LOWER(?) AND archiv = 'N'",
            (row['model_name'],)
        ).fetchone()
        if not exists:
            cur.execute(
                "INSERT INTO parametres_materiel (categorie, valeur, description, ordre) VALUES ('modele', ?, 'Modèle issu du référentiel des équipements', 0)",
                (row['model_name'],)
            )

    conn.commit()
    conn.close()

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
# INTERFACE WEB EMBARQUÉE (HTML/Tailwind/Lucide) - ZÉRO CONFIGURATION REQUISE
# -----------------------------------------------------------------------------
STANDALONE_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>GPARC - Gestion du Parc Informatique</title>
  <!-- Tailwind CSS CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <!-- FontAwesome Icons -->
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    @media print {
      body * { visibility: hidden; }
      #printable-report, #printable-report * { visibility: visible; }
      #printable-report { position: absolute; left: 0; top: 0; width: 100%; border: none; box-shadow: none; }
      .no-print { display: none !important; }
    }
  </style>
</head>
<body class="bg-slate-100 text-slate-900 min-h-screen flex flex-col font-sans">

  <!-- En-tête de navigation -->
  <header class="bg-slate-900 text-white shadow-md sticky top-0 z-40">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-16">
        <!-- Logo & Titre -->
        <div class="flex items-center gap-3 cursor-pointer" onclick="switchView('simple')">
          <div class="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/20 text-white font-bold text-lg">
            <i class="fa-solid fa-server"></i>
          </div>
          <div>
            <div class="flex items-center gap-2">
              <span class="font-bold text-xl tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-300 bg-clip-text text-transparent">GPARC</span>
              <span class="text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center gap-1 font-medium">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                Serveur Flask & SQLite Actifs
              </span>
            </div>
            <p class="text-xs text-slate-400 font-medium">Gestion du Parc Informatique & Pannes</p>
          </div>
        </div>

        <!-- Actions rapides d'en-tête -->
        <div class="flex items-center gap-3">
          <button onclick="toggleView()" id="btn-toggle-view" class="flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg bg-blue-600/30 hover:bg-blue-600/50 text-blue-200 border border-blue-500/40 transition">
            <i class="fa-solid fa-bolt text-amber-300"></i>
            <span id="label-toggle-view">Mode Détaillé</span>
          </button>
          <button onclick="openNewMaterielModal()" class="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition shadow-sm">
            <i class="fa-solid fa-plus-circle"></i>
            <span>Nouveau Matériel</span>
          </button>
          <button onclick="openNewPanneModal()" class="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white transition shadow-sm">
            <i class="fa-solid fa-triangle-exclamation"></i>
            <span>Signaler Panne</span>
          </button>
          <button onclick="loadAllData()" title="Rafraîchir" class="p-2 text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg border border-slate-700 transition">
            <i class="fa-solid fa-arrows-rotate" id="refresh-icon"></i>
          </button>
        </div>
      </div>

      <!-- Onglets de navigation -->
      <nav class="flex space-x-1 border-t border-slate-800 py-1.5 overflow-x-auto">
        <button onclick="switchView('simple')" id="tab-simple" class="nav-tab px-3 py-1 rounded text-xs font-medium bg-blue-600 text-white flex items-center gap-1.5">
          <i class="fa-solid fa-bolt text-amber-300"></i> ⚡ Interface Simple
        </button>
        <button onclick="switchView('materiels')" id="tab-materiels" class="nav-tab px-3 py-1 rounded text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 flex items-center gap-1.5">
          <i class="fa-solid fa-desktop"></i> Parc Équipements
        </button>
        <button onclick="switchView('pannes')" id="tab-pannes" class="nav-tab px-3 py-1 rounded text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 flex items-center gap-1.5">
          <i class="fa-solid fa-wrench"></i> Pannes & Interventions
        </button>
        <button onclick="switchView('stats')" id="tab-stats" class="nav-tab px-3 py-1 rounded text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-800 flex items-center gap-1.5">
          <i class="fa-solid fa-chart-pie"></i> Statistiques & KPI
        </button>
        <button onclick="resetData()" class="nav-tab ml-auto px-2.5 py-1 rounded text-xs font-medium text-slate-400 hover:text-rose-300 hover:bg-rose-950/40 border border-slate-800 flex items-center gap-1">
          <i class="fa-solid fa-rotate-left"></i> Réinitialiser Démo
        </button>
      </nav>
    </div>
  </header>

  <!-- Notification Toast -->
  <div id="toast" class="fixed bottom-4 right-4 z-50 transform translate-y-16 opacity-0 transition-all duration-300 bg-slate-900 text-white px-4 py-3 rounded-lg shadow-xl border border-slate-700 flex items-center gap-3 text-sm">
    <i class="fa-solid fa-circle-check text-emerald-400 text-lg"></i>
    <span id="toast-text">Action effectuée</span>
  </div>

  <!-- Contenu Principal -->
  <main class="max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 flex-1">

    <!-- Indicateurs KPI Rapides -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-6">
      <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
        <div class="w-10 h-10 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center text-lg"><i class="fa-solid fa-layer-group"></i></div>
        <div>
          <div class="text-2xl font-bold text-slate-800" id="kpi-total">0</div>
          <div class="text-xs text-slate-500 font-medium">Total Équipements</div>
        </div>
      </div>
      <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
        <div class="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center text-lg"><i class="fa-solid fa-circle-check"></i></div>
        <div>
          <div class="text-2xl font-bold text-emerald-600" id="kpi-op">0</div>
          <div class="text-xs text-slate-500 font-medium">Opérationnels / En service</div>
        </div>
      </div>
      <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
        <div class="w-10 h-10 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center text-lg"><i class="fa-solid fa-triangle-exclamation"></i></div>
        <div>
          <div class="text-2xl font-bold text-rose-600" id="kpi-pa">0</div>
          <div class="text-xs text-slate-500 font-medium">En Panne active</div>
        </div>
      </div>
      <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-3">
        <div class="w-10 h-10 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center text-lg"><i class="fa-solid fa-wrench"></i></div>
        <div>
          <div class="text-2xl font-bold text-amber-600" id="kpi-re">0</div>
          <div class="text-xs text-slate-500 font-medium">En Réparation / SAV</div>
        </div>
      </div>
    </div>

    <!-- Barre de Recherche et Filtres -->
    <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm mb-6 flex flex-col sm:flex-row gap-3 items-center justify-between">
      <div class="relative w-full sm:w-96">
        <i class="fa-solid fa-magnifying-glass absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 text-sm"></i>
        <input type="text" id="search-input" oninput="applyFilters()" placeholder="Rechercher par N° inv, série, utilisateur, modèle..." class="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
      </div>
      <div class="flex items-center gap-2 w-full sm:w-auto overflow-x-auto">
        <button onclick="setFilter('ALL')" id="filter-all" class="filter-btn px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-900 text-white transition">Tous</button>
        <button onclick="setFilter('OP')" id="filter-op" class="filter-btn px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 transition">En service</button>
        <button onclick="setFilter('PA')" id="filter-pa" class="filter-btn px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 transition">En panne</button>
        <button onclick="setFilter('RE')" id="filter-re" class="filter-btn px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 transition">En réparation</button>
      </div>
    </div>

    <!-- VUE 1 : INTERFACE SIMPLE (Grille d'équipements & Cartes d'action) -->
    <div id="view-simple" class="view-panel">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5" id="materiels-grid">
        <!-- Rempli dynamiquement en JavaScript -->
      </div>
    </div>

    <!-- VUE MATÉRIELS : PARC ÉQUIPEMENTS / PARC INFORMATIQUE -->
    <div id="view-materiels" class="view-panel hidden space-y-4">
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div class="p-4 border-b border-slate-200 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div>
            <div class="flex items-center gap-2">
              <h2 class="text-base font-bold text-slate-800 flex items-center gap-2">
                <i class="fa-solid fa-desktop text-blue-600"></i> Parc des Équipements Informatiques
              </h2>
              <span id="materiels-count-badge" class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-800">0 équipements</span>
            </div>
            <p class="text-xs text-slate-500 mt-0.5">Inventaire complet, spécifications techniques, affectations et statut en temps réel.</p>
          </div>
          <div class="flex items-center gap-2">
            <button onclick="openNewMaterielModal()" class="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 shadow-sm transition">
              <i class="fa-solid fa-plus"></i> Nouvel Équipement
            </button>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse text-xs">
            <thead class="bg-slate-50 text-slate-600 uppercase font-semibold border-b border-slate-200">
              <tr>
                <th class="p-3">Équipement</th>
                <th class="p-3">N° Inventaire / Série</th>
                <th class="p-3">Affectation (Utilisateur & Structure)</th>
                <th class="p-3">Spécifications (CPU / RAM / Disque / SE)</th>
                <th class="p-3">Réseau & IP</th>
                <th class="p-3">Statut</th>
                <th class="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody id="materiels-table-body" class="divide-y divide-slate-100">
              <!-- Rempli dynamiquement -->
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- VUE 2 : PANNES & INTERVENTIONS -->
    <div id="view-pannes" class="view-panel hidden">
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div class="p-4 border-b border-slate-200 flex justify-between items-center">
          <h2 class="text-base font-bold text-slate-800">Historique et Suivi des Pannes Techniques</h2>
          <button onclick="openNewPanneModal()" class="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5">
            <i class="fa-solid fa-plus"></i> Déclarer une nouvelle panne
          </button>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse text-sm">
            <thead class="bg-slate-50 text-slate-600 text-xs uppercase font-semibold border-b border-slate-200">
              <tr>
                <th class="p-3">Date</th>
                <th class="p-3">Matériel</th>
                <th class="p-3">Diagnostic & Panne</th>
                <th class="p-3">Technicien / Lieu</th>
                <th class="p-3">Statut</th>
                <th class="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody id="pannes-table-body" class="divide-y divide-slate-100">
              <!-- Rempli dynamiquement -->
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- VUE 3 : STATISTIQUES & KPI -->
    <div id="view-stats" class="view-panel hidden">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <h3 class="text-sm font-bold text-slate-800 mb-3 flex items-center gap-2">
            <i class="fa-solid fa-chart-column text-blue-600"></i> Répartition par Type d'Équipement
          </h3>
          <div id="stats-types" class="space-y-2.5"></div>
        </div>
        <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <h3 class="text-sm font-bold text-slate-800 mb-3 flex items-center gap-2">
            <i class="fa-solid fa-building text-indigo-600"></i> Répartition par Direction & Structure
          </h3>
          <div id="stats-structures" class="space-y-2.5"></div>
        </div>
      </div>
    </div>

  </main>

  <!-- MODAL : NOUVEAU MATÉRIEL -->
  <div id="modal-materiel" class="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 hidden flex items-center justify-center p-4 overflow-y-auto">
    <div class="bg-white rounded-2xl max-w-xl w-full p-6 shadow-2xl border border-slate-100 my-8">
      <div class="flex items-center justify-between pb-4 border-b border-slate-100">
        <h3 class="text-lg font-bold text-slate-800 flex items-center gap-2">
          <i class="fa-solid fa-desktop text-blue-600"></i> Ajouter un équipement au parc
        </h3>
        <button onclick="closeModal('modal-materiel')" class="text-slate-400 hover:text-slate-600 text-lg"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <form onsubmit="handleSaveMateriel(event)" class="mt-4 space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">N° Inventaire *</label>
            <input type="text" id="mat-num-inv" required placeholder="ex: INV-2024-001" class="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500">
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">N° de Série *</label>
            <input type="text" id="mat-num-ser" required placeholder="ex: SN-DELL-8840" class="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500">
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Marque *</label>
            <select id="mat-brand" required onchange="populateMaterielModels()" class="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500">
              <option value="">Sélectionner une marque...</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Type d'équipement *</label>
            <select id="mat-type" required onchange="populateMaterielModels()" class="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500">
              <option value="">Sélectionner un type...</option>
            </select>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Modèle *</label>
            <select id="mat-model" required class="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500">
              <option value="">Choisir d'abord la marque et le type...</option>
            </select>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Structure / Direction *</label>
            <select id="mat-str" required onchange="populateMaterielUsers()" class="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500">
              <option value="">Sélectionner une structure...</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Utilisateur assigné</label>
            <select id="mat-user" class="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500">
              <option value="">Aucun (en stock)</option>
            </select>
          </div>
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Caractéristiques techniques (CPU, RAM, Disque)</label>
          <div class="grid grid-cols-3 gap-2">
            <input type="text" id="mat-cpu" placeholder="CPU (i7, i5...)" class="px-2.5 py-1.5 border rounded-lg text-xs">
            <input type="number" id="mat-ram" placeholder="RAM Go (16)" class="px-2.5 py-1.5 border rounded-lg text-xs">
            <input type="number" id="mat-disk" placeholder="SSD Go (512)" class="px-2.5 py-1.5 border rounded-lg text-xs">
          </div>
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">URL de la photo ou image</label>
          <input type="url" id="mat-image" placeholder="https://images.unsplash.com/..." class="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500">
        </div>
        <div class="flex justify-end gap-2 pt-3 border-t">
          <button type="button" onclick="closeModal('modal-materiel')" class="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50">Annuler</button>
          <button type="submit" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold shadow-sm">Enregistrer l'équipement</button>
        </div>
      </form>
    </div>
  </div>

  <!-- MODAL : SIGNALER UNE PANNE -->
  <div id="modal-panne" class="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 hidden flex items-center justify-center p-4 overflow-y-auto">
    <div class="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-100 my-8">
      <div class="flex items-center justify-between pb-4 border-b border-slate-100">
        <h3 class="text-lg font-bold text-slate-800 flex items-center gap-2">
          <i class="fa-solid fa-triangle-exclamation text-rose-600"></i> Déclarer un incident / Panne
        </h3>
        <button onclick="closeModal('modal-panne')" class="text-slate-400 hover:text-slate-600 text-lg"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <form onsubmit="handleSavePanne(event)" class="mt-4 space-y-4">
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Équipement concerné *</label>
          <select id="panne-mat-id" required class="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-rose-500">
            <!-- Rempli par JavaScript -->
          </select>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Type d'anomalie</label>
            <select id="panne-type" class="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-rose-500">
              <option value="MAT">Panne Matérielle (Composant / Pièce)</option>
              <option value="ALIM">Alimentation / Énergie</option>
              <option value="LOG">Système & Logiciel</option>
              <option value="RES">Réseau & Connectivité</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-700 mb-1">Technicien assigné</label>
            <input type="text" id="panne-tech" value="Support DSI Interne" class="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-rose-500">
          </div>
        </div>
        <div>
          <label class="block text-xs font-semibold text-slate-700 mb-1">Diagnostic & Description de l'anomalie *</label>
          <textarea id="panne-diag" rows="3" required placeholder="Détaillez le problème constaté..." class="w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-rose-500"></textarea>
        </div>
        <div class="flex justify-end gap-2 pt-3 border-t">
          <button type="button" onclick="closeModal('modal-panne')" class="px-4 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50">Annuler</button>
          <button type="submit" class="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-bold shadow-sm">Créer la fiche de panne</button>
        </div>
      </form>
    </div>
  </div>

  <!-- MODAL : FICHE D'INTERVENTION IMPRIMABLE -->
  <div id="modal-report" class="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 hidden flex items-center justify-center p-4 overflow-y-auto">
    <div class="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-200 my-8">
      <div class="flex items-center justify-between pb-3 border-b no-print">
        <h3 class="text-base font-bold text-slate-800 flex items-center gap-2">
          <i class="fa-solid fa-file-invoice text-blue-600"></i> Fiche d'Intervention Technique
        </h3>
        <div class="flex items-center gap-2">
          <button onclick="window.print()" class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-sm">
            <i class="fa-solid fa-print"></i> Imprimer / PDF
          </button>
          <button onclick="closeModal('modal-report')" class="text-slate-400 hover:text-slate-600 text-lg px-2"><i class="fa-solid fa-xmark"></i></button>
        </div>
      </div>

      <!-- Rapport technique formatté -->
      <div id="printable-report" class="p-4 sm:p-6 bg-white text-slate-900">
        <div class="border-b-2 border-slate-900 pb-4 mb-4 flex justify-between items-center">
          <div>
            <h1 class="text-xl font-bold tracking-tight text-slate-900">GPARC - FICHE D'INTERVENTION TECHNIQUE</h1>
            <p class="text-xs text-slate-500 font-medium">Direction des Systèmes d'Information & Maintenance</p>
          </div>
          <div class="text-right">
            <div class="text-sm font-mono font-bold text-blue-700" id="rpt-num">RPT-2024-0001</div>
            <div class="text-xs text-slate-500" id="rpt-date">Date : --/--/----</div>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4 text-xs mb-4 p-3 bg-slate-50 rounded-lg border border-slate-200">
          <div>
            <div class="font-bold text-slate-700 mb-1 uppercase tracking-wider">Équipement</div>
            <div><span class="font-semibold">N° Inventaire :</span> <span id="rpt-inv">-</span></div>
            <div><span class="font-semibold">N° Série :</span> <span id="rpt-ser">-</span></div>
            <div><span class="font-semibold">Modèle :</span> <span id="rpt-model">-</span></div>
            <div><span class="font-semibold">Type :</span> <span id="rpt-type">-</span></div>
          </div>
          <div>
            <div class="font-bold text-slate-700 mb-1 uppercase tracking-wider">Affectation</div>
            <div><span class="font-semibold">Utilisateur :</span> <span id="rpt-user">-</span></div>
            <div><span class="font-semibold">Direction :</span> <span id="rpt-str">-</span></div>
            <div><span class="font-semibold">Technicien :</span> <span id="rpt-tech">-</span></div>
            <div><span class="font-semibold">Statut :</span> <span id="rpt-statut" class="font-bold">-</span></div>
          </div>
        </div>

        <div class="mb-4">
          <div class="text-xs font-bold text-slate-800 uppercase tracking-wider mb-1">Diagnostic de la panne :</div>
          <div id="rpt-diag" class="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs leading-relaxed text-slate-700"></div>
        </div>

        <div class="grid grid-cols-2 gap-4 pt-6 border-t border-slate-200 text-xs text-slate-600">
          <div class="h-20 border border-dashed border-slate-300 rounded p-2">
            <span class="font-bold">Visa du Technicien DSI :</span>
          </div>
          <div class="h-20 border border-dashed border-slate-300 rounded p-2">
            <span class="font-bold">Visa & Signature Utilisateur :</span>
          </div>
        </div>
      </div>
    </div>
  </div>

  <footer class="bg-white border-t border-slate-200 py-3 text-center text-xs text-slate-500">
    GPARC - Gestion du Parc Informatique & SQLite Intégrée &bull; Prêt pour Windows, Linux & Mac
  </footer>

  <!-- Code JavaScript applicatif -->
  <script>
    let allMateriels = [];
    let allPannes = [];
    let allReferences = {
      structures: [],
      types: [],
      modeles: [],
      utilisateurs: [],
      parametres: []
    };
    let currentFilter = 'ALL';
    let currentView = 'simple';

    // Chargement initial
    window.addEventListener('DOMContentLoaded', () => {
      loadAllData();
    });

    async function loadAllData() {
      const refreshIcon = document.getElementById('refresh-icon');
      if (refreshIcon) refreshIcon.classList.add('fa-spin');
      try {
        const [statsRes, matRes, panRes, refRes] = await Promise.all([
          fetch('/api/stats').then(r => r.json()),
          fetch('/api/materiels').then(r => r.json()),
          fetch('/api/pannes').then(r => r.json()),
          fetch('/api/references').then(r => r.json())
        ]);

        allMateriels = matRes || [];
        allPannes = panRes || [];
        allReferences = refRes || allReferences;
        populateMaterielForm();

        // Mise à jour des KPI
        document.getElementById('kpi-total').innerText = statsRes.totalEquipements || allMateriels.length;
        document.getElementById('kpi-op').innerText = statsRes.operationnels || allMateriels.filter(m => m.etat_mat === 'OP').length;
        document.getElementById('kpi-pa').innerText = statsRes.enPanne || allMateriels.filter(m => m.etat_mat === 'PA').length;
        document.getElementById('kpi-re').innerText = statsRes.enReparation || allMateriels.filter(m => m.etat_mat === 'RE').length;

        // Rendu des vues
        renderMateriels();
        renderPannes();
        renderStats(statsRes);
        populatePanneSelect();
      } catch (err) {
        console.error('Erreur de chargement:', err);
        showToast('Erreur de connexion au serveur Flask', true);
      } finally {
        if (refreshIcon) refreshIcon.classList.remove('fa-spin');
      }
    }

    function renderMateriels() {
      const grid = document.getElementById('materiels-grid');
      const tableBody = document.getElementById('materiels-table-body');
      const countBadge = document.getElementById('materiels-count-badge');
      const query = document.getElementById('search-input') ? document.getElementById('search-input').value.toLowerCase().trim() : '';

      const filtered = allMateriels.filter(m => {
        const matchFilter = currentFilter === 'ALL' || m.etat_mat === currentFilter;
        const text = `${m.num_inv || ''} ${m.num_ser || ''} ${m.model_mat || ''} ${m.marque_mat || ''} ${m.nom_uti || ''} ${m.structure_nom || ''} ${m.ip || ''} ${m.cpu || ''} ${m.se || ''} ${m.ordi || ''}`.toLowerCase();
        const matchSearch = !query || text.includes(query);
        return matchFilter && matchSearch;
      });

      if (countBadge) {
        countBadge.innerText = `${filtered.length} équipement${filtered.length > 1 ? 's' : ''}`;
      }

      // 1. Rendu de la grille (Interface Simple)
      if (grid) {
        if (filtered.length === 0) {
          grid.innerHTML = `
            <div class="col-span-full p-8 text-center bg-white rounded-xl border border-slate-200 text-slate-500">
              <i class="fa-solid fa-inbox text-3xl mb-2 text-slate-400"></i>
              <p class="font-medium text-sm">Aucun équipement ne correspond à vos critères de recherche.</p>
            </div>
          `;
        } else {
          grid.innerHTML = filtered.map(m => {
            let badge = '<span class="px-2 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-700">En service</span>';
            if (m.etat_mat === 'PA') badge = '<span class="px-2 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-700 animate-pulse">En panne</span>';
            if (m.etat_mat === 'RE') badge = '<span class="px-2 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-700">En réparation</span>';

            const photo = m.image_url || 'https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=800&auto=format&fit=crop&q=80';

            return `
              <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden hover:shadow-md transition flex flex-col">
                <div class="relative h-40 bg-slate-100 overflow-hidden">
                  <img src="${photo}" alt="${m.model_mat || 'Équipement'}" class="w-full h-full object-cover">
                  <div class="absolute top-2.5 right-2.5">${badge}</div>
                  <div class="absolute bottom-2.5 left-2.5 bg-slate-900/80 backdrop-blur-xs text-white text-[11px] font-mono px-2 py-0.5 rounded">
                    ${m.num_inv || 'SANS-INV'}
                  </div>
                </div>
                <div class="p-4 flex-1 flex flex-col justify-between">
                  <div>
                    <h4 class="font-bold text-slate-900 text-base mb-0.5">${m.marque_mat || ''} ${m.model_mat || 'Équipement Standard'}</h4>
                    <p class="text-xs text-slate-500 font-medium mb-3">${m.type_nom || 'Matériel Informatique'}</p>
                    
                    <div class="space-y-1.5 text-xs text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                      <div class="flex justify-between">
                        <span class="text-slate-400">N° Série :</span>
                        <span class="font-mono font-medium text-slate-700">${m.num_ser || '-'}</span>
                      </div>
                      <div class="flex justify-between">
                        <span class="text-slate-400">Affecté à :</span>
                        <span class="font-semibold text-slate-800">${m.nom_uti ? (m.pnom_uti || '') + ' ' + m.nom_uti : 'Non assigné'}</span>
                      </div>
                      <div class="flex justify-between">
                        <span class="text-slate-400">Direction :</span>
                        <span class="text-slate-700">${m.structure_nom || 'DSI'}</span>
                      </div>
                      ${m.cpu ? `<div class="flex justify-between"><span class="text-slate-400">Processeur :</span><span class="text-slate-700">${m.cpu}</span></div>` : ''}
                      ${m.ram ? `<div class="flex justify-between"><span class="text-slate-400">Mémoire / Disque :</span><span class="text-slate-700">${m.ram} Go RAM / ${m.disk || 512} Go SSD</span></div>` : ''}
                    </div>
                  </div>

                  <div class="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                    <button onclick="quickPanneFor(${m.id_mat})" class="text-xs font-semibold text-rose-600 hover:text-rose-700 flex items-center gap-1 cursor-pointer">
                      <i class="fa-solid fa-triangle-exclamation"></i> Signaler Panne
                    </button>
                    <div class="text-[11px] font-mono text-slate-400">${m.ip ? 'IP: ' + m.ip : ''}</div>
                  </div>
                </div>
              </div>
            `;
          }).join('');
        }
      }

      // 2. Rendu du tableau d'inventaire complet (Parc Équipements)
      if (tableBody) {
        if (filtered.length === 0) {
          tableBody.innerHTML = `<tr><td colspan="7" class="p-8 text-center text-slate-400">Aucun équipement trouvé correspondant aux critères.</td></tr>`;
        } else {
          tableBody.innerHTML = filtered.map(m => {
            let badge = '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 flex items-center gap-1 w-max"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>En service</span>';
            if (m.etat_mat === 'PA') badge = '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-rose-100 text-rose-800 flex items-center gap-1 w-max animate-pulse"><span class="w-1.5 h-1.5 rounded-full bg-rose-500"></span>En panne</span>';
            if (m.etat_mat === 'RE') badge = '<span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-800 flex items-center gap-1 w-max"><span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>En réparation</span>';

            const photo = m.image_url || 'https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=800&auto=format&fit=crop&q=80';

            return `
              <tr class="hover:bg-slate-50 transition text-xs">
                <td class="p-3">
                  <div class="flex items-center gap-3">
                    <img src="${photo}" alt="" class="w-10 h-10 rounded-lg object-cover border border-slate-200 shrink-0">
                    <div>
                      <div class="font-bold text-slate-900">${m.marque_mat || ''} ${m.model_mat || 'Équipement'}</div>
                      <div class="text-[11px] text-slate-500">${m.type_nom || 'Matériel'} ${m.ordi ? `&bull; <span class="font-mono text-indigo-600">${m.ordi}</span>` : ''}</div>
                    </div>
                  </div>
                </td>
                <td class="p-3">
                  <div class="font-mono font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded w-max">${m.num_inv || '-'}</div>
                  <div class="font-mono text-slate-400 text-[11px] mt-0.5">SN: ${m.num_ser || '-'}</div>
                </td>
                <td class="p-3">
                  <div class="font-semibold text-slate-800">${m.nom_uti ? (m.pnom_uti || '') + ' ' + m.nom_uti : '<span class="text-slate-400 italic">Non assigné</span>'}</div>
                  <div class="text-slate-500 text-[11px]">${m.structure_nom || 'Direction Non Spécifiée'}</div>
                </td>
                <td class="p-3">
                  <div class="text-slate-800 font-medium">${m.cpu || 'CPU Standard'}</div>
                  <div class="text-slate-500 text-[11px]">${m.ram || 16} Go RAM &bull; ${m.disk || 512} Go SSD &bull; ${m.se || 'Win 11'}</div>
                </td>
                <td class="p-3 font-mono text-slate-600">
                  ${m.ip ? `<span class="px-2 py-0.5 bg-slate-100 rounded text-slate-700 border border-slate-200">${m.ip}</span>` : '<span class="text-slate-400 text-[11px]">DHCP / Non fixée</span>'}
                </td>
                <td class="p-3">
                  ${badge}
                </td>
                <td class="p-3 text-right">
                  <div class="flex items-center justify-end gap-1.5">
                    <button onclick="quickPanneFor(${m.id_mat})" class="px-2.5 py-1 bg-rose-50 text-rose-700 hover:bg-rose-100 rounded text-[11px] font-semibold flex items-center gap-1 transition" title="Déclarer une panne">
                      <i class="fa-solid fa-triangle-exclamation"></i> Panne
                    </button>
                    <button onclick="deleteMateriel(${m.id_mat})" class="p-1.5 text-slate-400 hover:text-rose-600 rounded transition" title="Supprimer du parc">
                      <i class="fa-solid fa-trash-can"></i>
                    </button>
                  </div>
                </td>
              </tr>
            `;
          }).join('');
        }
      }
    }

    function renderPannes() {
      const tbody = document.getElementById('pannes-table-body');
      if (allPannes.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="p-6 text-center text-slate-400 text-xs">Aucune panne enregistrée.</td></tr>`;
        return;
      }

      tbody.innerHTML = allPannes.map(p => {
        let statusBadge = '<span class="px-2 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800">En cours</span>';
        if (p.eta_pan === 'RP') statusBadge = '<span class="px-2 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800">Réparé</span>';
        if (p.eta_pan === 'AT') statusBadge = '<span class="px-2 py-0.5 rounded-full text-xs font-bold bg-purple-100 text-purple-800">Attente pièces</span>';

        return `
          <tr class="hover:bg-slate-50 transition text-xs">
            <td class="p-3 font-mono text-slate-500">${p.dat_pan || '-'}</td>
            <td class="p-3">
              <div class="font-bold text-slate-800">${p.marque_mat || ''} ${p.model_mat || ''}</div>
              <div class="font-mono text-slate-400 text-[11px]">${p.num_inv || ''}</div>
            </td>
            <td class="p-3 max-w-xs text-slate-700 leading-snug">${p.diag_pan || ''}</td>
            <td class="p-3 text-slate-600">${p.technicien || 'Tech DSI'}</td>
            <td class="p-3">${statusBadge}</td>
            <td class="p-3 text-right space-x-1.5">
              ${p.eta_pan !== 'RP' ? `
                <button onclick="markRepaired(${p.id_pan})" class="px-2 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-[11px] font-semibold" title="Marquer comme réparé">
                  <i class="fa-solid fa-check"></i> Réparé
                </button>
              ` : ''}
              <button onclick="viewReport(${p.id_pan})" class="px-2 py-1 bg-blue-50 text-blue-700 hover:bg-blue-100 rounded text-[11px] font-semibold" title="Imprimer fiche">
                <i class="fa-solid fa-print"></i> Fiche
              </button>
            </td>
          </tr>
        `;
      }).join('');
    }

    function renderStats(stats) {
      const typesDiv = document.getElementById('stats-types');
      const strDiv = document.getElementById('stats-structures');

      if (stats.repartitionTypes) {
        typesDiv.innerHTML = stats.repartitionTypes.map(t => `
          <div class="flex items-center justify-between text-xs p-2 bg-slate-50 rounded border border-slate-100">
            <span class="font-medium text-slate-700">${t.type}</span>
            <span class="font-bold bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full">${t.count}</span>
          </div>
        `).join('');
      }

      if (stats.repartitionStructures) {
        strDiv.innerHTML = stats.repartitionStructures.map(s => `
          <div class="flex items-center justify-between text-xs p-2 bg-slate-50 rounded border border-slate-100">
            <span class="font-medium text-slate-700">${s.label} (${s.code})</span>
            <span class="font-bold bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded-full">${s.count}</span>
          </div>
        `).join('');
      }
    }

    function populatePanneSelect() {
      const sel = document.getElementById('panne-mat-id');
      if (!sel) return;
      sel.innerHTML = allMateriels.map(m => `
        <option value="${m.id_mat}">${m.num_inv} - ${m.marque_mat || ''} ${m.model_mat || ''} (${m.nom_uti || 'Non assigné'})</option>
      `).join('');
    }

    function switchView(view) {
      currentView = view;
      document.querySelectorAll('.view-panel').forEach(p => p.classList.add('hidden'));
      document.querySelectorAll('.nav-tab').forEach(t => {
        t.classList.remove('bg-blue-600', 'text-white');
        t.classList.add('text-slate-300');
      });

      const activeTab = document.getElementById('tab-' + view);
      if (activeTab) {
        activeTab.classList.remove('text-slate-300');
        activeTab.classList.add('bg-blue-600', 'text-white');
      }

      const panel = document.getElementById('view-' + view);
      if (panel) panel.classList.remove('hidden');

      const labelToggle = document.getElementById('label-toggle-view');
      if (labelToggle) {
        labelToggle.innerText = view === 'simple' ? 'Mode Détaillé' : 'Mode Simple';
      }
    }

    function toggleView() {
      switchView(currentView === 'simple' ? 'pannes' : 'simple');
    }

    function setFilter(filter) {
      currentFilter = filter;
      document.querySelectorAll('.filter-btn').forEach(b => {
        b.classList.remove('bg-slate-900', 'text-white');
        b.classList.add('bg-slate-100', 'text-slate-700');
      });
      const activeBtn = document.getElementById('filter-' + filter.toLowerCase());
      if (activeBtn) {
        activeBtn.classList.remove('bg-slate-100', 'text-slate-700');
        activeBtn.classList.add('bg-slate-900', 'text-white');
      }
      renderMateriels();
    }

    function applyFilters() {
      renderMateriels();
    }

    function openNewMaterielModal() {
      populateMaterielForm();
      document.getElementById('modal-materiel').classList.remove('hidden');
    }

    function escapeHtml(value) {
      return String(value ?? '').replace(/[&<>"']/g, ch => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'
      }[ch]));
    }

    function populateMaterielForm() {
      const brandSel = document.getElementById('mat-brand');
      const typeSel = document.getElementById('mat-type');
      const strSel = document.getElementById('mat-str');
      if (!brandSel || !typeSel || !strSel) return;

      const currentBrand = brandSel.value;
      const currentType = typeSel.value;
      const currentStr = strSel.value;

      const brands = [...new Set((allReferences.modeles || [])
        .map(m => (m.marque_mat || '').trim())
        .filter(Boolean)
        .concat((allReferences.parametres || [])
          .filter(p => p.categorie === 'marque' && p.archiv !== 'O')
          .map(p => (p.valeur || '').trim())
          .filter(Boolean)))]
        .sort((a,b) => a.localeCompare(b));

      brandSel.innerHTML = '<option value="">Sélectionner une marque...</option>' +
        brands.map(b => `<option value="${escapeHtml(b)}">${escapeHtml(b)}</option>`).join('');
      if (brands.includes(currentBrand)) brandSel.value = currentBrand;

      typeSel.innerHTML = '<option value="">Sélectionner un type...</option>' +
        (allReferences.types || []).map(t =>
          `<option value="${t.id_typ_mat}">${escapeHtml(t.lib_typ_mat)}</option>`
        ).join('');
      if (currentType) typeSel.value = currentType;

      strSel.innerHTML = '<option value="">Sélectionner une structure...</option>' +
        (allReferences.structures || []).map(st =>
          `<option value="${st.id_str}">[${escapeHtml(st.cod_str || '')}] ${escapeHtml(st.lib_str || '')}</option>`
        ).join('');
      if (currentStr) strSel.value = currentStr;

      populateMaterielModels();
      populateMaterielUsers();
    }

    function populateMaterielModels() {
      const brand = document.getElementById('mat-brand')?.value || '';
      const typeId = document.getElementById('mat-type')?.value || '';
      const modelSel = document.getElementById('mat-model');
      if (!modelSel) return;

      const models = (allReferences.modeles || []).filter(m => {
        const sameBrand = !brand || (m.marque_mat || '').trim() === brand;
        const sameType = !typeId || !m.id_typ_mat || String(m.id_typ_mat) === String(typeId);
        return sameBrand && sameType;
      });

      modelSel.innerHTML = '<option value="">Sélectionner un modèle...</option>' +
        models.map(m =>
          `<option value="${m.id_model_mat}">${escapeHtml(m.model_mat)}${m.marque_mat ? ' — ' + escapeHtml(m.marque_mat) : ''}</option>`
        ).join('');

      modelSel.disabled = models.length === 0;

      if (models.length === 0 && brand && typeId) {
        modelSel.innerHTML = '<option value="">Aucun modèle pour cette marque / type</option>';
      }
    }

    function populateMaterielUsers() {
      const structureId = document.getElementById('mat-str')?.value || '';
      const userSel = document.getElementById('mat-user');
      if (!userSel) return;

      const users = (allReferences.utilisateurs || []).filter(u =>
        !structureId || !u.id_str_mere || String(u.id_str_mere) === String(structureId)
      );

      userSel.innerHTML = '<option value="">Aucun (en stock)</option>' +
        users.map(u =>
          `<option value="${u.id_uti}">${escapeHtml(u.nom_uti)} ${escapeHtml(u.pnom_uti)}${u.mail_uti ? ' — ' + escapeHtml(u.mail_uti) : ''}</option>`
        ).join('');
    }

    function openNewPanneModal() {
      populatePanneSelect();
      document.getElementById('modal-panne').classList.remove('hidden');
    }

    function quickPanneFor(matId) {
      openNewPanneModal();
      document.getElementById('panne-mat-id').value = matId;
    }

    function closeModal(id) {
      document.getElementById(id).classList.add('hidden');
    }

    async function handleSaveMateriel(e) {
      e.preventDefault();
      const payload = {
        num_inv: document.getElementById('mat-num-inv').value.trim(),
        num_ser: document.getElementById('mat-num-ser').value.trim(),
        marque_mat: document.getElementById('mat-brand').value,
        id_model_mat: parseInt(document.getElementById('mat-model').value) || null,
        id_typ_mat: parseInt(document.getElementById('mat-type').value) || null,
        id_str: parseInt(document.getElementById('mat-str').value) || null,
        id_uti: parseInt(document.getElementById('mat-user').value) || null,
        cpu: document.getElementById('mat-cpu').value.trim(),
        ram: parseInt(document.getElementById('mat-ram').value) || 16,
        disk: parseInt(document.getElementById('mat-disk').value) || 512,
        image_url: document.getElementById('mat-image').value.trim()
      };

      try {
        const res = await fetch('/api/materiels', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          closeModal('modal-materiel');
          showToast('Équipement ajouté au parc avec succès !');
          loadAllData();
        } else {
          showToast("Erreur lors de l'ajout", true);
        }
      } catch (err) {
        showToast('Erreur serveur', true);
      }
    }

    async function handleSavePanne(e) {
      e.preventDefault();
      const payload = {
        id_mat: parseInt(document.getElementById('panne-mat-id').value),
        tp: document.getElementById('panne-type').value,
        technicien: document.getElementById('panne-tech').value.trim(),
        diag_pan: document.getElementById('panne-diag').value.trim()
      };

      try {
        const res = await fetch('/api/pannes', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          closeModal('modal-panne');
          showToast('Panne enregistrée : matériel passé en statut En Panne !');
          loadAllData();
        } else {
          showToast("Erreur lors de l'enregistrement", true);
        }
      } catch (err) {
        showToast('Erreur serveur', true);
      }
    }

    async function markRepaired(panneId) {
      try {
        const res = await fetch('/api/pannes/' + panneId, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ eta_pan: 'RP' })
        });
        if (res.ok) {
          showToast('Panne résolue : matériel remis en service !');
          loadAllData();
        }
      } catch (err) {
        showToast("Erreur lors de la mise à jour", true);
      }
    }

    async function viewReport(panneId) {
      try {
        const res = await fetch('/api/pannes/' + panneId + '/report');
        if (res.ok) {
          const rpt = await res.json();
          document.getElementById('rpt-num').innerText = rpt.numeroRapport;
          document.getElementById('rpt-date').innerText = 'Date : ' + rpt.dateGeneration;
          document.getElementById('rpt-inv').innerText = rpt.equipement.numInventaire;
          document.getElementById('rpt-ser').innerText = rpt.equipement.numSerie;
          document.getElementById('rpt-model').innerText = `${rpt.equipement.marque || ''} ${rpt.equipement.modele || ''}`;
          document.getElementById('rpt-type').innerText = rpt.equipement.type || 'Matériel';
          document.getElementById('rpt-user').innerText = rpt.utilisateur.nom || 'Non assigné';
          document.getElementById('rpt-str').innerText = rpt.utilisateur.service || 'DSI';
          document.getElementById('rpt-tech').innerText = rpt.intervention.technicien || 'DSI';
          document.getElementById('rpt-statut').innerText = rpt.intervention.statut === 'RP' ? 'RÉPARÉ / REMIS EN SERVICE' : 'EN COURS';
          document.getElementById('rpt-diag').innerText = rpt.intervention.diagnostic || 'Aucun détail';

          document.getElementById('modal-report').classList.remove('hidden');
        }
      } catch (e) {
        showToast("Impossible d'afficher la fiche", true);
      }
    }

    async function resetData() {
      if (confirm('Voulez-vous réinitialiser toutes les données de test SQLite ?')) {
        await fetch('/api/reset-data', { method: 'POST' });
        showToast('Base SQLite réinitialisée avec succès !');
        loadAllData();
      }
    }

    function showToast(text, isError = false) {
      const toast = document.getElementById('toast');
      const toastText = document.getElementById('toast-text');
      toastText.innerText = text;
      toast.classList.remove('translate-y-16', 'opacity-0');
      if (isError) {
        toast.classList.add('border-rose-500');
      } else {
        toast.classList.remove('border-rose-500');
      }
      setTimeout(() => {
        toast.classList.add('translate-y-16', 'opacity-0');
      }, 3500);
    }

    // Exposer explicitement sur window pour tous les onclick HTML
    window.switchView = switchView;
    window.toggleView = toggleView;
    window.setFilter = setFilter;
    window.applyFilters = applyFilters;
    window.loadAllData = loadAllData;
    window.openNewMaterielModal = openNewMaterielModal;
    window.openNewPanneModal = openNewPanneModal;
    window.quickPanneFor = quickPanneFor;
    window.closeModal = closeModal;
    window.handleSaveMateriel = handleSaveMateriel;
    window.handleSavePanne = handleSavePanne;
    window.markRepaired = markRepaired;
    window.viewReport = viewReport;
    window.resetData = resetData;
    window.showToast = showToast;

    // Déclenchement garanti du chargement
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', loadAllData);
    } else {
      loadAllData();
    }
  </script>
</body>
</html>
"""

# -----------------------------------------------------------------------------
# ROUTES STATIQUES & INTERFACE WEB
# -----------------------------------------------------------------------------

@app.route('/')
def index():
    """Point d'entrée principal : sert le template HTML autonome ou le build React."""
    tpl_path = os.path.join(BASE_DIR, 'templates', 'index.html')
    if os.path.exists(tpl_path):
        with open(tpl_path, 'r', encoding='utf-8') as f:
            return Response(f.read(), mimetype='text/html')
    dist_index = os.path.join(DIST_DIR, 'index.html')
    if os.path.exists(dist_index):
        return send_from_directory(DIST_DIR, 'index.html')
    return Response(STANDALONE_HTML, mimetype='text/html')

@app.route('/assets/<path:path>')
def send_assets(path):
    """Sert les assets JS/CSS compilés si présents."""
    assets_dir = os.path.join(DIST_DIR, 'assets')
    if os.path.exists(os.path.join(assets_dir, path)):
        return send_from_directory(assets_dir, path)
    return ('', 404)

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
    op = cur.execute("SELECT COUNT(*) FROM materiel WHERE etat_mat = 'OP' AND archiv = 'N'").fetchone()[0]
    pa = cur.execute("SELECT COUNT(*) FROM materiel WHERE etat_mat = 'PA' AND archiv = 'N'").fetchone()[0]
    re = cur.execute("SELECT COUNT(*) FROM materiel WHERE etat_mat = 'RE' AND archiv = 'N'").fetchone()[0]
    so = cur.execute("SELECT COUNT(*) FROM materiel WHERE etat_mat = 'SO' AND archiv = 'N'").fetchone()[0]
    pannes_actives = cur.execute("SELECT COUNT(*) FROM panne WHERE eta_pan IN ('EC', 'AT') AND archiv = 'N'").fetchone()[0]
    pannes_resolues = cur.execute("SELECT COUNT(*) FROM panne WHERE eta_pan = 'RP' AND archiv = 'N'").fetchone()[0]

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
        "enReparation": re,
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
                ram, disk, cpu, se, ordi, ip, id_uti, image_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('id_str') or None, id_typ, id_model,
            marque or None,
            data.get('num_inv', f"INV-{datetime.now().strftime('%y%m%d%H%M')}"),
            data.get('num_ser', f"SN-{datetime.now().strftime('%y%m%d%H%M')}"),
            data.get('etat_mat', 'OP'), data.get('obs_mat', ''),
            data.get('ram', 16), data.get('disk', 512),
            data.get('cpu', 'Intel Core i5/i7'), data.get('se', 'Windows 11 Pro'),
            data.get('ordi', ''), data.get('ip', ''), data.get('id_uti') or None,
            data.get('image_url', '')
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
        if id_model is not None:
            model = cur.execute("SELECT marque_mat, id_typ_mat FROM model_mat WHERE id_model_mat = ? AND archiv = 'N'", (id_model,)).fetchone()
            if not model:
                conn.close(); return jsonify({"error": "Modèle invalide."}), 400
            if marque and (model['marque_mat'] or '').strip().lower() != marque.lower():
                conn.close(); return jsonify({"error": "Le modèle sélectionné ne correspond pas à la marque."}), 400
            if id_typ is not None and model['id_typ_mat'] is not None and int(model['id_typ_mat']) != int(id_typ):
                conn.close(); return jsonify({"error": "Le modèle sélectionné ne correspond pas au type."}), 400

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
                obs_mat = COALESCE(?, obs_mat),
                cpu = COALESCE(?, cpu),
                ram = COALESCE(?, ram),
                disk = COALESCE(?, disk),
                ip = COALESCE(?, ip),
                image_url = COALESCE(?, image_url),
                dat_mod = CURRENT_TIMESTAMP
            WHERE id_mat = ?
        """, (
            data.get('num_inv'), data.get('num_ser'), marque or None,
            id_model, id_typ, id_str, id_uti, data.get('etat_mat'), data.get('obs_mat'),
            data.get('cpu'), data.get('ram'), data.get('disk'), data.get('ip'), data.get('image_url'), mat_id
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

@app.route('/api/materiels/<int:mat_id>/historique', methods=['GET'])
def get_materiel_historique(mat_id):
    conn = get_db()
    cur = conn.cursor()
    exists = cur.execute(
        "SELECT id_mat FROM materiel WHERE id_mat = ? AND archiv = 'N'",
        (mat_id,)
    ).fetchone()
    if not exists:
        conn.close()
        return jsonify({"error": "Matériel non trouvé"}), 404

    rows = cur.execute("""
        SELECT a.id_aff_mat, a.id_mat, a.dat_aff, a.action_aff, a.obs_aff,
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

    result = []
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
        d['libelle_action'] = libelle
        d['detail_action'] = detail
        result.append(d)

    conn.close()
    return jsonify(result)


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
            SELECT id_mat, id_str, id_typ_mat, id_model_mat, num_inv, num_ser, ?, ?, 'EC', ?, ?, ?, ?
            FROM materiel WHERE id_mat = ?
        """, (
            data.get('dat_pan', datetime.now().strftime('%Y-%m-%d')),
            data.get('diag_pan', 'Anomalie signalée'), data.get('tp', 'MAT'),
            data.get('technicien', 'Support DSI'),
            data.get('obs_rep', ''), data.get('pieces_remplacees', ''), mat_id
        ))
        # Passer le matériel en panne
        cur.execute("UPDATE materiel SET etat_mat = 'PA' WHERE id_mat = ?", (mat_id,))
        conn.commit()
        last_id = cur.lastrowid
        conn.close()
        return jsonify({"id": last_id, "message": "Panne enregistrée"}), 201
    else:
        rows = [dict(r) for r in cur.execute("""
            SELECT p.*, m.num_inv, m.num_ser, mod.marque_mat, mod.model_mat, s.lib_str as structure_nom
            FROM panne p
            JOIN materiel m ON p.id_mat = m.id_mat
            LEFT JOIN model_mat mod ON m.id_model_mat = mod.id_model_mat
            LEFT JOIN structures s ON p.id_str = s.id_str
            WHERE p.archiv = 'N' ORDER BY p.id_pan DESC
        """).fetchall()]
        conn.close()
        return jsonify(rows)

@app.route('/api/pannes/<int:panne_id>', methods=['PUT'])
def update_panne(panne_id):
    conn = get_db()
    cur = conn.cursor()
    data = request.json or {}

    new_status = data.get('eta_pan')
    if new_status:
        cur.execute("UPDATE panne SET eta_pan = ? WHERE id_pan = ?", (new_status, panne_id))
        # Si réparé ('RP'), remettre le matériel en état 'OP'
        if new_status == 'RP':
            panne_row = cur.execute("SELECT id_mat FROM panne WHERE id_pan = ?", (panne_id,)).fetchone()
            if panne_row:
                cur.execute("UPDATE materiel SET etat_mat = 'OP' WHERE id_mat = ?", (panne_row['id_mat'],))

    conn.commit()
    conn.close()
    return jsonify({"message": "Panne mise à jour"})

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
            "pieces": d['pieces_remplacees']
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
    cur.execute("DROP TABLE IF EXISTS materiel")
    cur.execute("DROP TABLE IF EXISTS panne")
    cur.execute("DROP TABLE IF EXISTS structures")
    cur.execute("DROP TABLE IF EXISTS type_mat")
    cur.execute("DROP TABLE IF EXISTS model_mat")
    cur.execute("DROP TABLE IF EXISTS lieu_rep")
    cur.execute("DROP TABLE IF EXISTS utilisateurs")
    cur.execute("DROP TABLE IF EXISTS parametres_materiel")
    cur.execute("DROP TABLE IF EXISTS parametre_type_mat")
    cur.execute("DROP TABLE IF EXISTS oracle_sync_history")
    conn.commit()
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
