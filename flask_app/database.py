"""Accès et initialisation de la base SQLite de GPARC."""

import os
import sqlite3

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

def get_db():
    # timeout : si la base est momentanément verrouillée par une autre écriture,
    # SQLite patiente jusqu'à 15s au lieu d'échouer immédiatement avec "database is locked".
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL : autorise les lectures concurrentes pendant une écriture (au lieu de verrouiller
    # tout le fichier). Essentiel dès que plusieurs postes utilisent l'app en même temps.
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 15000")
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
        dat_cre DATETIME DEFAULT CURRENT_TIMESTAMP,
        etat_reforme TEXT DEFAULT 'AUCUNE',
        motif_reforme TEXT,
        date_proposition_reforme DATE,
        date_validation_reforme DATE,
        date_reforme DATE,
        decision_reforme TEXT,
        pv_reforme TEXT
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
        categorie_lieu TEXT DEFAULT 'EXTERIEUR',
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
        dat_cre DATETIME DEFAULT CURRENT_TIMESTAMP,
        statut_mat TEXT DEFAULT 'ES',
        etat_reforme TEXT DEFAULT 'AUCUNE',
        motif_reforme TEXT
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
        eta_pan TEXT DEFAULT 'EP',
        tp TEXT DEFAULT 'MAT',
        technicien TEXT,
        pieces_remplacees TEXT,
        recommandations TEXT,
        cout_rep REAL DEFAULT 0,
        archiv TEXT DEFAULT 'N',
        dat_cre DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS historique_reforme (
        id_his_ref INTEGER PRIMARY KEY AUTOINCREMENT,
        id_mat INTEGER NOT NULL,
        etat_reforme TEXT NOT NULL,
        date_evenement DATE NOT NULL,
        motif_reforme TEXT,
        ancien_etat_reforme TEXT,
        dat_cre DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (id_mat) REFERENCES materiel (id_mat)
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

    # Migrations légères pour les bases GPARC déjà existantes.
    # CREATE TABLE IF NOT EXISTS ne modifie pas une table déjà présente :
    # on complète donc explicitement les colonnes ajoutées dans les versions
    # récentes de l'application.
    mat_columns = {row[1] for row in cur.execute("PRAGMA table_info(materiel)").fetchall()}
    if 'marque_mat' not in mat_columns:
        cur.execute("ALTER TABLE materiel ADD COLUMN marque_mat TEXT")
    if 'dat_mod' not in mat_columns:
        # Nullable volontairement : SQLite n'autorise pas toujours
        # l'ajout d'un DEFAULT CURRENT_TIMESTAMP via ALTER TABLE.
        cur.execute("ALTER TABLE materiel ADD COLUMN dat_mod DATETIME")
        cur.execute("UPDATE materiel SET dat_mod = COALESCE(dat_cre, CURRENT_TIMESTAMP) WHERE dat_mod IS NULL")
    if 'etat_reforme' not in mat_columns:
        cur.execute("ALTER TABLE materiel ADD COLUMN etat_reforme TEXT DEFAULT 'AUCUNE'")
        cur.execute("UPDATE materiel SET etat_reforme = 'AUCUNE' WHERE etat_reforme IS NULL")
    if 'motif_reforme' not in mat_columns:
        cur.execute("ALTER TABLE materiel ADD COLUMN motif_reforme TEXT")
    if 'date_proposition_reforme' not in mat_columns:
        cur.execute("ALTER TABLE materiel ADD COLUMN date_proposition_reforme DATE")
    if 'date_validation_reforme' not in mat_columns:
        cur.execute("ALTER TABLE materiel ADD COLUMN date_validation_reforme DATE")
    if 'date_reforme' not in mat_columns:
        cur.execute("ALTER TABLE materiel ADD COLUMN date_reforme DATE")
    if 'annee_reforme' not in mat_columns:
        cur.execute("ALTER TABLE materiel ADD COLUMN annee_reforme INTEGER")
    if 'lot_reforme' not in mat_columns:
        cur.execute("ALTER TABLE materiel ADD COLUMN lot_reforme TEXT")
    if 'decision_reforme' not in mat_columns:
        cur.execute("ALTER TABLE materiel ADD COLUMN decision_reforme TEXT")
    if 'pv_reforme' not in mat_columns:
        cur.execute("ALTER TABLE materiel ADD COLUMN pv_reforme TEXT")
    if 'statut_mat' not in mat_columns:
        cur.execute("ALTER TABLE materiel ADD COLUMN statut_mat TEXT DEFAULT 'ES'")
    # Séparation stricte entre le statut de cycle de vie et l'état physique.
    cur.execute("""
        UPDATE materiel
        SET statut_mat = CASE
            WHEN etat_reforme = 'PROPOSEE' THEN 'PR'
            WHEN etat_reforme = 'REFORME' THEN 'RF'
            ELSE COALESCE(NULLIF(statut_mat, ''), 'ES')
        END
        WHERE statut_mat IS NULL OR statut_mat = '' OR etat_reforme IN ('PROPOSEE','REFORME')
    """)
    cur.execute("""
        UPDATE materiel
        SET etat_mat = CASE
            WHEN etat_mat = 'OP' THEN 'BON'
            WHEN etat_mat IN ('PA','RE') THEN 'PANNE'
            WHEN etat_mat = 'SO' THEN 'BON'
            WHEN etat_mat IS NULL OR etat_mat = '' THEN 'BON'
            ELSE etat_mat
        END
    """)

    # Migration légère des lieux de réparation.
    lieu_columns = {row[1] for row in cur.execute("PRAGMA table_info(lieu_rep)").fetchall()}
    if 'categorie_lieu' not in lieu_columns:
        cur.execute("ALTER TABLE lieu_rep ADD COLUMN categorie_lieu TEXT DEFAULT 'EXTERIEUR'")
        cur.execute("""
            UPDATE lieu_rep
            SET categorie_lieu = CASE
                WHEN LOWER(nom_lieu_rep) LIKE '%atelier%' OR LOWER(nom_lieu_rep) LIKE '%interne%' THEN 'LOCAL'
                ELSE 'EXTERIEUR'
            END
        """)

    # Migration légère de la procédure de panne.
    # Les anciennes bases peuvent ne pas contenir les colonnes ajoutées
    # pour documenter complètement une réparation.
    panne_columns = {row[1] for row in cur.execute("PRAGMA table_info(panne)").fetchall()}
    if 'pieces_remplacees' not in panne_columns:
        cur.execute("ALTER TABLE panne ADD COLUMN pieces_remplacees TEXT")
    if 'recommandations' not in panne_columns:
        cur.execute("ALTER TABLE panne ADD COLUMN recommandations TEXT")
    if 'cout_rep' not in panne_columns:
        cur.execute("ALTER TABLE panne ADD COLUMN cout_rep REAL DEFAULT 0")
    # Harmonisation des anciens codes de traitement de panne.
    cur.execute("""
        UPDATE panne
        SET eta_pan = CASE
            WHEN eta_pan = 'EC' THEN 'EP'
            WHEN eta_pan = 'AT' THEN 'ER'
            WHEN eta_pan = 'NR' THEN 'IR'
            ELSE eta_pan
        END
        WHERE eta_pan IN ('EC','AT','NR')
    """)

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
            categorie = 'LOCAL' if 'atelier' in (l[0] or '').lower() or 'interne' in (l[0] or '').lower() else 'EXTERIEUR'
            cur.execute("INSERT INTO lieu_rep (nom_lieu_rep, adr_lieu_rep, tel_lieu_rep, contact_rep, categorie_lieu) VALUES (?, ?, ?, ?, ?)", (*l, categorie))

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

        # Normaliser les données de démonstration vers la nouvelle séparation.
        cur.execute("""
            UPDATE materiel
            SET statut_mat = 'ES',
                etat_mat = CASE
                    WHEN etat_mat IN ('PA','RE') THEN 'PANNE'
                    ELSE 'BON'
                END
        """)
        cur.execute("""
            UPDATE panne
            SET eta_pan = CASE
                WHEN eta_pan = 'EC' THEN 'EP'
                WHEN eta_pan = 'AT' THEN 'ER'
                WHEN eta_pan = 'NR' THEN 'IR'
                ELSE eta_pan
            END
        """)

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
