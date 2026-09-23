import { DatabaseSync } from 'node:sqlite';
import path from 'path';
import fs from 'fs';

const dataDir = path.join(process.cwd(), 'data');
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
}

const dbPath = path.join(dataDir, 'gparc.db');
export const db = new DatabaseSync(dbPath);

// Enable foreign keys and WAL mode for high performance
db.exec(`
  PRAGMA foreign_keys = ON;
  PRAGMA journal_mode = WAL;
`);

export function initDatabase() {
  db.exec(`
    -- 1. Table STRUCTURE (Départements / Services)
    CREATE TABLE IF NOT EXISTS structures (
      id_str INTEGER PRIMARY KEY AUTOINCREMENT,
      cod_str TEXT NOT NULL,
      lib_str TEXT NOT NULL,
      id_str_mere INTEGER,
      archiv TEXT DEFAULT 'N',
      dat_cre TEXT DEFAULT CURRENT_TIMESTAMP,
      dat_mod TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- 2. Table TYPE_MAT (Types de matériel)
    CREATE TABLE IF NOT EXISTS type_mat (
      id_typ_mat INTEGER PRIMARY KEY AUTOINCREMENT,
      cod_typ_mat TEXT NOT NULL,
      lib_typ_mat TEXT NOT NULL,
      archiv TEXT DEFAULT 'N',
      dat_cre TEXT DEFAULT CURRENT_TIMESTAMP,
      dat_mod TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- 3. Table MODEL_MAT (Marques, Modèles et Paramètres Techniques Standards)
    CREATE TABLE IF NOT EXISTS model_mat (
      id_model_mat INTEGER PRIMARY KEY AUTOINCREMENT,
      marque_mat TEXT NOT NULL,
      model_mat TEXT NOT NULL,
      id_typ_mat INTEGER,
      default_cpu TEXT,
      default_freq_cpu TEXT,
      default_ram INTEGER,
      default_disk INTEGER,
      default_se TEXT,
      default_net TEXT,
      description TEXT,
      garantie_mois INTEGER DEFAULT 36,
      archiv TEXT DEFAULT 'N',
      dat_cre TEXT DEFAULT CURRENT_TIMESTAMP,
      dat_mod TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (id_typ_mat) REFERENCES type_mat (id_typ_mat)
    );

    -- 4. Table LIEU_REP (Ateliers et centres de réparation)
    CREATE TABLE IF NOT EXISTS lieu_rep (
      id_lieu_rep INTEGER PRIMARY KEY AUTOINCREMENT,
      nom_lieu_rep TEXT NOT NULL,
      adr_lieu_rep TEXT,
      tel_lieu_rep TEXT,
      contact_rep TEXT,
      archiv TEXT DEFAULT 'N',
      dat_cre TEXT DEFAULT CURRENT_TIMESTAMP,
      dat_mod TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- 5. Table UTI (Utilisateurs / Employés)
    CREATE TABLE IF NOT EXISTS utilisateurs (
      id_uti INTEGER PRIMARY KEY AUTOINCREMENT,
      nom_uti TEXT NOT NULL,
      pnom_uti TEXT NOT NULL,
      mail_uti TEXT,
      ad_uti TEXT,
      net_uti TEXT DEFAULT 'N',
      id_str_mere INTEGER,
      archiv TEXT DEFAULT 'N',
      dat_cre TEXT DEFAULT CURRENT_TIMESTAMP,
      dat_mod TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (id_str_mere) REFERENCES structures (id_str)
    );

    -- 6. Table MATERIEL (Parc Équipements)
    CREATE TABLE IF NOT EXISTS materiel (
      id_mat INTEGER PRIMARY KEY AUTOINCREMENT,
      id_str INTEGER,
      id_typ_mat INTEGER,
      id_model_mat INTEGER,
      marque_mat TEXT,
      num_inv TEXT UNIQUE NOT NULL,
      num_ser TEXT NOT NULL,
      dat_acq TEXT,
      dat_mes TEXT,
      etat_mat TEXT DEFAULT 'OP', -- 'OP': Opérationnel, 'PA': En panne, 'RE': En réparation, 'MA': Maintenance, 'SO': Réformé
      obs_mat TEXT,
      dat_sortie TEXT,
      motif_sortie TEXT,
      ram INTEGER,
      disk INTEGER,
      cpu TEXT,
      freq_cpu TEXT,
      se TEXT,
      net TEXT,
      ordi TEXT,
      ip TEXT,
      id_uti INTEGER,
      disk2 TEXT,
      ram2 INTEGER,
      cpu2 TEXT,
      freq_cpu2 TEXT,
      se2 TEXT,
      net2 TEXT,
      image_url TEXT,
      valeur_acq REAL DEFAULT 0,
      archiv TEXT DEFAULT 'N',
      dat_cre TEXT DEFAULT CURRENT_TIMESTAMP,
      dat_mod TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (id_str) REFERENCES structures (id_str),
      FOREIGN KEY (id_typ_mat) REFERENCES type_mat (id_typ_mat),
      FOREIGN KEY (id_model_mat) REFERENCES model_mat (id_model_mat),
      FOREIGN KEY (id_uti) REFERENCES utilisateurs (id_uti)
    );

    -- 7. Table AFFECT_MAT (Historique des affectations)
    CREATE TABLE IF NOT EXISTS affect_mat (
      id_aff_mat INTEGER PRIMARY KEY AUTOINCREMENT,
      id_mat INTEGER NOT NULL,
      id_str INTEGER,
      id_model_mat INTEGER,
      id_typ_mat INTEGER,
      num_inv TEXT,
      num_ser TEXT,
      dat_aff TEXT DEFAULT CURRENT_TIMESTAMP,
      obs_aff TEXT,
      id_uti INTEGER,
      archiv TEXT DEFAULT 'N',
      dat_cre TEXT DEFAULT CURRENT_TIMESTAMP,
      dat_mod TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (id_mat) REFERENCES materiel (id_mat),
      FOREIGN KEY (id_str) REFERENCES structures (id_str),
      FOREIGN KEY (id_uti) REFERENCES utilisateurs (id_uti)
    );

    -- 8. Table PANNE (Incidents, Pannes et Interventions)
    CREATE TABLE IF NOT EXISTS panne (
      id_pan INTEGER PRIMARY KEY AUTOINCREMENT,
      id_mat INTEGER NOT NULL,
      id_str INTEGER,
      id_typ_mat INTEGER,
      id_model_mat INTEGER,
      num_inv TEXT,
      num_ser TEXT,
      dat_pan TEXT NOT NULL,
      diag_pan TEXT NOT NULL,
      dat_env_rep TEXT,
      dat_ret_rep TEXT,
      id_lieu_rep INTEGER,
      obs_rep TEXT,
      eta_pan TEXT DEFAULT 'EC', -- 'EC': En cours, 'RP': Réparé, 'AT': Attente pièces, 'NR': Non réparable
      dat_sortie_pan TEXT,
      tp TEXT DEFAULT 'MAT', -- 'MAT': Matériel, 'LOG': Logiciel, 'RES': Réseau, 'ALIM': Alimentation, 'AUT': Autre
      technicien TEXT,
      pieces_remplacees TEXT,
      cout_rep REAL DEFAULT 0,
      recommandations TEXT,
      archiv TEXT DEFAULT 'N',
      dat_cre TEXT DEFAULT CURRENT_TIMESTAMP,
      dat_mod TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (id_mat) REFERENCES materiel (id_mat),
      FOREIGN KEY (id_str) REFERENCES structures (id_str),
      FOREIGN KEY (id_lieu_rep) REFERENCES lieu_rep (id_lieu_rep)
    );

    -- 9. Table CARA_MAT (Caractéristiques techniques supplémentaires)
    CREATE TABLE IF NOT EXISTS cara_mat (
      id_cara_mat INTEGER PRIMARY KEY AUTOINCREMENT,
      lib_cara_mat TEXT NOT NULL,
      fam_cara_mat TEXT NOT NULL,
      archiv TEXT DEFAULT 'N',
      dat_cre TEXT DEFAULT CURRENT_TIMESTAMP,
      dat_mod TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- 10. Table ADMINISTRATEURS (Accès d'administration et privilèges)
    CREATE TABLE IF NOT EXISTS administrateurs (
      id_adm INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE NOT NULL,
      nom_complet TEXT NOT NULL,
      email TEXT,
      password TEXT NOT NULL,
      role TEXT DEFAULT 'admin', -- 'super_admin', 'admin', 'technicien'
      is_active INTEGER DEFAULT 1,
      dat_cre TEXT DEFAULT CURRENT_TIMESTAMP,
      dat_mod TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- 11. Table PARAMETRES_MATERIEL (Dictionnaire de configuration standard : CPU, RAM, SE, Disque)
    CREATE TABLE IF NOT EXISTS parametres_materiel (
      id_param INTEGER PRIMARY KEY AUTOINCREMENT,
      categorie TEXT NOT NULL, -- 'marque', 'cpu', 'ram', 'se', 'disk'
      valeur TEXT NOT NULL,
      description TEXT,
      ordre INTEGER DEFAULT 0,
      archiv TEXT DEFAULT 'N',
      dat_cre TEXT DEFAULT CURRENT_TIMESTAMP
    );

    -- 12. Table PARAMETRE_TYPE_MAT (Paramètres techniques spécifiques à chaque type d'équipement)
    CREATE TABLE IF NOT EXISTS parametre_type_mat (
      id_param_type INTEGER PRIMARY KEY AUTOINCREMENT,
      id_typ_mat INTEGER NOT NULL,
      code_param TEXT NOT NULL,
      libelle_param TEXT NOT NULL,
      categorie_groupe TEXT DEFAULT 'Technique',
      type_champ TEXT DEFAULT 'text', -- 'text', 'number', 'select'
      unite TEXT,
      options_predefinies TEXT, -- JSON array de suggestions ou options
      description TEXT,
      ordre INTEGER DEFAULT 0,
      archiv TEXT DEFAULT 'N',
      dat_cre TEXT DEFAULT CURRENT_TIMESTAMP,
      dat_mod TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (id_typ_mat) REFERENCES type_mat (id_typ_mat)
    );
  `);

  migrateModelMatSchema();
  seedInitialData();
  seedAdminAndParameters();
  seedTypeSpecificParameters();
  updateModelMatDefaults();
  ensureBrandParametersAndMaterialBrands();
}

function seedAdminAndParameters() {
  // Seed admins if table is empty
  const checkAdmins = db.prepare('SELECT COUNT(*) as count FROM administrateurs').get() as { count: number };
  if (checkAdmins.count === 0) {
    const insertAdmin = db.prepare(`
      INSERT INTO administrateurs (username, nom_complet, email, password, role, is_active)
      VALUES (?, ?, ?, ?, ?, ?)
    `);
    insertAdmin.run('admin', 'Administrateur Principal', 'admin.parc@societe.com', 'admin123', 'super_admin', 1);
    insertAdmin.run('support_admin', 'Responsable Support IT', 'support.dsi@societe.com', 'support123', 'admin', 1);
    insertAdmin.run('tech_sav', 'Technicien Gestionnaire', 'tech.parc@societe.com', 'tech123', 'technicien', 1);
    console.log('Default administrateurs seeded.');
  }

  // Seed parameters if table is empty
  const checkParams = db.prepare('SELECT COUNT(*) as count FROM parametres_materiel').get() as { count: number };
  if (checkParams.count === 0) {
    const insertParam = db.prepare(`
      INSERT INTO parametres_materiel (categorie, valeur, description, ordre)
      VALUES (?, ?, ?, ?)
    `);

    // CPUs
    const cpus = [
      { val: 'Intel Core i7-1370P (14C / 5.2 GHz)', desc: 'PC Portables Ultra-performance', ord: 1 },
      { val: 'Intel Core i5-13500 (14C / 4.8 GHz)', desc: 'PC Fixes Entreprise', ord: 2 },
      { val: 'Intel Core i7-12700 (12C / 4.9 GHz)', desc: 'Stations de travail CAO', ord: 3 },
      { val: 'AMD Ryzen 7 PRO 7840U (8C / 5.1 GHz)', desc: 'Portables légers Pro', ord: 4 },
      { val: 'Intel Xeon Silver 4314 (16C / 2.4 GHz)', desc: 'Serveurs Datacenter & Virtualisation', ord: 5 },
      { val: 'Apple M3 Pro (12 Coeurs)', desc: 'MacBook Pro Direction & Design', ord: 6 },
      { val: 'Intel Core i9-13900K (24C / 5.8 GHz)', desc: 'Stations de calcul intensif', ord: 7 },
    ];
    for (const c of cpus) insertParam.run('cpu', c.val, c.desc, c.ord);

    // RAM
    const rams = [
      { val: '8', desc: '8 Go DDR4 / DDR5 - Standard bureautique', ord: 1 },
      { val: '16', desc: '16 Go DDR4 / DDR5 - Recommandé bureautique avancée', ord: 2 },
      { val: '32', desc: '32 Go DDR5 5600MHz - Développeurs & Ingénieurs', ord: 3 },
      { val: '64', desc: '64 Go DDR5 - Stations de travail & DAO', ord: 4 },
      { val: '128', desc: '128 Go ECC Registrée - Serveurs & Hyperviseurs', ord: 5 },
    ];
    for (const r of rams) insertParam.run('ram', r.val, r.desc, r.ord);

    // Systèmes d'exploitation (SE)
    const ses = [
      { val: 'Windows 11 Pro 64-bit', desc: 'Standard bureautique actuel', ord: 1 },
      { val: 'Windows 10 Entreprise LTSC', desc: 'Environnements stables & terminaux', ord: 2 },
      { val: 'Ubuntu Linux 24.04 LTS Desktop', desc: 'Postes R&D & Systèmes', ord: 3 },
      { val: 'macOS Sonoma (v14)', desc: 'Équipements Apple Mac', ord: 4 },
      { val: 'Debian 12 Bookworm Server', desc: 'Serveurs d\'infrastructure Linux', ord: 5 },
      { val: 'Windows Server 2022 Standard', desc: 'Serveurs Active Directory & Fichiers', ord: 6 },
      { val: 'Red Hat Enterprise Linux 9', desc: 'Serveurs de bases de données & ERP', ord: 7 },
    ];
    for (const s of ses) insertParam.run('se', s.val, s.desc, s.ord);

    // Disques (Go)
    const disks = [
      { val: '256', desc: '256 Go SSD NVMe M.2 - Postes bureautiques légers', ord: 1 },
      { val: '512', desc: '512 Go SSD NVMe PCIe 4.0 - Standard parc', ord: 2 },
      { val: '1000', desc: '1000 Go (1 To) SSD NVMe haute vitesse', ord: 3 },
      { val: '2000', desc: '2000 Go (2 To) SSD NVMe - Postes de calcul & vidéo', ord: 4 },
      { val: '4000', desc: '4000 Go (4 To) RAID Entreprise - Stockage local serveur', ord: 5 },
    ];
    for (const d of disks) insertParam.run('disk', d.val, d.desc, d.ord);

    console.log('Default parametres_materiel seeded.');
  }
}

function seedInitialData() {
  const checkCount = db.prepare('SELECT COUNT(*) as count FROM structures').get() as { count: number };
  if (checkCount.count > 0) {
    return;
  }

  console.log('Seeding initial GPARC database with reference and sample IT park data...');

  // 1. Structures
  const insertStr = db.prepare('INSERT INTO structures (cod_str, lib_str) VALUES (?, ?)');
  insertStr.run('DSI', 'Direction des Systèmes d\'Information');
  insertStr.run('RH', 'Direction des Ressources Humaines');
  insertStr.run('FIN', 'Direction Administrative & Financière');
  insertStr.run('LOG', 'Direction Logistique & Exploitation');
  insertStr.run('COM', 'Département Commercial & Marketing');
  insertStr.run('DIR', 'Direction Générale');

  // 2. Types de Matériel
  const insertType = db.prepare('INSERT INTO type_mat (cod_typ_mat, lib_typ_mat) VALUES (?, ?)');
  insertType.run('LAP', 'PC Portable');
  insertType.run('DSK', 'PC Bureau / Station de travail');
  insertType.run('SRV', 'Serveur Rack / Tour');
  insertType.run('PRT', 'Imprimante / Multifonction Réseau');
  insertType.run('SWI', 'Switch / Équipement Réseau');
  insertType.run('UPS', 'Onduleur Haute Disponibilité');
  insertType.run('SCR', 'Écran Professionnel');

  // 3. Modèles de Matériel
  const insertModel = db.prepare('INSERT INTO model_mat (marque_mat, model_mat) VALUES (?, ?)');
  insertModel.run('Dell', 'Latitude 5540');
  insertModel.run('Lenovo', 'ThinkPad T14 Gen 4');
  insertModel.run('HP', 'EliteBook 840 G9');
  insertModel.run('Dell', 'OptiPlex 7010');
  insertModel.run('Dell', 'PowerEdge R750xs');
  insertModel.run('HP', 'Color LaserJet Pro M479fdw');
  insertModel.run('Cisco', 'Catalyst 2960X-48FPS');
  insertModel.run('APC', 'Smart-UPS SMT2200RMI2UC');

  // 4. Lieux de Réparation
  const insertLieu = db.prepare('INSERT INTO lieu_rep (nom_lieu_rep, adr_lieu_rep, tel_lieu_rep, contact_rep) VALUES (?, ?, ?, ?)');
  insertLieu.run('Atelier Interne DSI', 'Bâtiment B - Niveau -1, Salle IT-04', '01 40 50 60 01', 'Équipe Support Support N2');
  insertLieu.run('SAV Constructeur Dell ProSupport', 'Parc Technologique Sud - 75015 Paris', '08 25 38 71 00', 'Centre Réparations Matériel Dell');
  insertLieu.run('HP Express Center Maintenance', '12 Avenue de l\'Informatique - 92000 Nanterre', '01 70 48 53 19', 'Service Agréé HP');
  insertLieu.run('Cisco TAC & Maintenance Réseau', 'Plateforme Support Datacenter', '08 00 90 85 85', 'Ingénieur Réseau Certifié');

  // 5. Utilisateurs
  const insertUti = db.prepare('INSERT INTO utilisateurs (nom_uti, pnom_uti, mail_uti, ad_uti, net_uti, id_str_mere) VALUES (?, ?, ?, ?, ?, ?)');
  insertUti.run('Benali', 'Amina', 'a.benali@societe.com', 'abenali', 'O', 2);
  insertUti.run('Martin', 'Alexandre', 'a.martin@societe.com', 'amartin', 'O', 1);
  insertUti.run('Laurent', 'Sophie', 's.laurent@societe.com', 'slaurent', 'O', 3);
  insertUti.run('Meziani', 'Karim', 'k.meziani@societe.com', 'kmeziani', 'O', 5);
  insertUti.run('Dubois', 'Julien', 'j.dubois@societe.com', 'jdubois', 'O', 4);
  insertUti.run('Chevalier', 'Claire', 'c.chevalier@societe.com', 'cchevalier', 'O', 6);
  insertUti.run('Haddad', 'Tariq', 't.haddad@societe.com', 'thaddad', 'O', 1);

  // 6. Matériel (avec images représentatives)
  const insertMat = db.prepare(`
    INSERT INTO materiel (
      id_str, id_typ_mat, id_model_mat, num_inv, num_ser, dat_acq, dat_mes,
      etat_mat, obs_mat, ram, disk, cpu, freq_cpu, se, net, ordi, ip, id_uti,
      image_url, valeur_acq
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);

  insertMat.run(
    1, 1, 1, 'INV-2024-001', 'SN-DL78219A', '2024-01-15', '2024-01-20',
    'OP', 'PC portable principal admin système', 32, 1000, 'Intel Core i7-1370P', '2.50 GHz',
    'Windows 11 Pro 64-bit', 'Wi-Fi 6E + Ethernet 1Gbps', 'DSI-LAP-001', '192.168.10.45', 2,
    'https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=600&auto=format&fit=crop&q=80', 1450.00
  );

  insertMat.run(
    2, 1, 2, 'INV-2024-002', 'SN-LN49200B', '2023-11-10', '2023-11-15',
    'OP', 'PC portable service ressources humaines', 16, 512, 'AMD Ryzen 7 PRO 7840U', '3.30 GHz',
    'Windows 11 Enterprise', 'Wi-Fi 6 + Bluetooth 5.2', 'RH-LAP-003', '192.168.10.72', 1,
    'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=600&auto=format&fit=crop&q=80', 1280.00
  );

  insertMat.run(
    3, 1, 3, 'INV-2023-014', 'SN-HP99182C', '2023-06-05', '2023-06-12',
    'PA', 'Écran scintillant et extinction inopinée suite surchauffe', 16, 512, 'Intel Core i5-1245U', '1.60 GHz',
    'Windows 11 Pro', 'Wi-Fi 6', 'FIN-LAP-002', '192.168.10.88', 3,
    'https://images.unsplash.com/photo-1541807084-5c52b6b3adef?w=600&auto=format&fit=crop&q=80', 1190.00
  );

  insertMat.run(
    1, 3, 5, 'INV-2022-005', 'SN-SRV-9011X', '2022-09-01', '2022-09-10',
    'OP', 'Serveur virtualisation VMware vSphere ESXi production', 128, 4000, '2x Intel Xeon Silver 4314', '2.40 GHz',
    'VMware ESXi 8.0', '4x 10GbE SFP+ Redondant', 'SRV-PROD-01', '192.168.10.10', 7,
    'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=600&auto=format&fit=crop&q=80', 8900.00
  );

  insertMat.run(
    1, 5, 7, 'INV-2021-022', 'SN-CSCO-2960A', '2021-04-18', '2021-04-25',
    'OP', 'Switch coeur de réseau baie informatique centrale', 0, 0, 'Cisco Dual Core ASIC', '800 MHz',
    'Cisco IOS 15.2', '48 Ports Gigabit PoE+ / 4 SFP+', 'SW-BAT-B', '192.168.10.2', 7,
    'https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=600&auto=format&fit=crop&q=80', 2400.00
  );

  insertMat.run(
    5, 4, 6, 'INV-2023-030', 'SN-PRT-479FDW', '2023-03-22', '2023-03-25',
    'RE', 'Bourrage papier récurrent et bloc de fusion défectueux', 2, 64, 'ARM Cortex-A9', '1.2 GHz',
    'Firmware HP FutureSmart', 'Ethernet 1Gbps + Wi-Fi Direct', 'PRT-COM-01', '192.168.10.150', 4,
    'https://images.unsplash.com/photo-1612815154858-60aa4c59eaa6?w=600&auto=format&fit=crop&q=80', 650.00
  );

  insertMat.run(
    1, 6, 8, 'INV-2022-009', 'SN-APC-2200R', '2022-10-14', '2022-10-15',
    'OP', 'Onduleur baie serveurs baie principale, autonomie 45 min', 0, 0, 'Microcontrôleur APC', 'N/A',
    'SmartSlot NMC3', 'Carte Management Réseau Web', 'UPS-SRV-01', '192.168.10.5', 7,
    'https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=600&auto=format&fit=crop&q=80', 1750.00
  );

  insertMat.run(
    4, 2, 4, 'INV-2023-044', 'SN-DL-OPTI70', '2023-08-01', '2023-08-05',
    'OP', 'Poste fixe logistique atelier expédition', 16, 512, 'Intel Core i5-13500', '2.50 GHz',
    'Windows 11 Pro', 'Ethernet Gigabit', 'LOG-DSK-001', '192.168.10.112', 5,
    'https://images.unsplash.com/photo-1593640408182-31c70c8268f5?w=600&auto=format&fit=crop&q=80', 890.00
  );

  // 7. Affectations historiques
  const insertAff = db.prepare(`
    INSERT INTO affect_mat (id_mat, id_str, id_model_mat, id_typ_mat, num_inv, num_ser, dat_aff, obs_aff, id_uti)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);
  insertAff.run(1, 1, 1, 1, 'INV-2024-001', 'SN-DL78219A', '2024-01-20', 'Attribution nouvel administrateur système', 2);
  insertAff.run(2, 2, 2, 1, 'INV-2024-002', 'SN-LN49200B', '2023-11-15', 'Remplacement ancien PC portable RH réformé', 1);
  insertAff.run(3, 3, 3, 1, 'INV-2023-014', 'SN-HP99182C', '2023-06-12', 'Attribution responsable comptabilité', 3);
  insertAff.run(6, 5, 4, 6, 'INV-2023-030', 'SN-PRT-479FDW', '2023-03-25', 'Mise à disposition service commercial', 4);

  // 8. Pannes et Interventions
  const insertPanne = db.prepare(`
    INSERT INTO panne (
      id_mat, id_str, id_typ_mat, id_model_mat, num_inv, num_ser, dat_pan,
      diag_pan, dat_env_rep, dat_ret_rep, id_lieu_rep, obs_rep, eta_pan,
      tp, technicien, pieces_remplacees, cout_rep, recommandations
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);

  // Panne 1: Active / En attente intervention
  insertPanne.run(
    3, 3, 1, 3, 'INV-2023-014', 'SN-HP99182C', '2024-09-18',
    'Écran noir au démarrage, ventilateur tourne à vitesse maximale. Défaillance probable carte mère ou connecteur nappe écran.',
    '2024-09-19', null, 3, 'Diagnostic en cours au centre technique HP', 'EC',
    'MAT', 'M. Tariq Haddad (Technicien DSI)', 'Nappe vidéo eDP & Pâte thermique', 180.00,
    'Prêter un laptop de secours temporaire à la collaboratrice le temps de l\'expertise.'
  );

  // Panne 2: En cours de réparation atelier
  insertPanne.run(
    6, 5, 4, 6, 'INV-2023-030', 'SN-PRT-479FDW', '2024-09-12',
    'Bourrage papier systématique en bac 2 et trace noire verticale sur les impressions couleur.',
    '2024-09-13', null, 1, 'Remplacement rouleaux d\'entraînement et nettoyage unité tambour.', 'AT',
    'MAT', 'M. Alexandre Martin (Support N2)', 'Kit rouleaux pick-up roller + unité tambour cyan', 95.00,
    'Rappeler aux utilisateurs d\'utiliser du papier 80g standard non humide.'
  );

  // Panne 3: Clôturée / Réparée avec succès
  insertPanne.run(
    1, 1, 1, 1, 'INV-2024-001', 'SN-DL78219A', '2024-05-10',
    'Déconnexion intempestive du port USB-C Thunderbolt lors de l\'ancrage sur station d\'accueil.',
    '2024-05-11', '2024-05-12', 1, 'Mise à jour du microprogramme BIOS v1.14 et pilote Thunderbolt Intel. Nettoyage physique du port.', 'RP',
    'LOG', 'M. Tariq Haddad (Technicien DSI)', 'Aucune pièce (résolution logicielle et firmware)', 0.00,
    'Vérifier régulièrement les mises à jour Windows Update et Dell Command Update.'
  );

  console.log('GPARC database seeded successfully.');
}

function ensureBrandParametersAndMaterialBrands() {
  try {
    // Existing equipment keeps the brand explicitly on MATERIEL.
    db.exec(`
      UPDATE materiel
      SET marque_mat = (
        SELECT mm.marque_mat FROM model_mat mm WHERE mm.id_model_mat = materiel.id_model_mat
      )
      WHERE (marque_mat IS NULL OR TRIM(marque_mat) = '') AND id_model_mat IS NOT NULL
    `);

    // The Administration > Paramètres > Marques list is automatically built from MODEL_MAT.
    db.exec(`
      INSERT INTO parametres_materiel (categorie, valeur, description, ordre)
      SELECT 'marque', mm.marque_mat, 'Marque issue du référentiel des modèles',
             ROW_NUMBER() OVER (ORDER BY mm.marque_mat)
      FROM (
        SELECT DISTINCT TRIM(marque_mat) AS marque_mat
        FROM model_mat
        WHERE archiv = 'N' AND TRIM(marque_mat) <> ''
      ) mm
      WHERE NOT EXISTS (
        SELECT 1 FROM parametres_materiel p
        WHERE p.categorie = 'marque'
          AND LOWER(TRIM(p.valeur)) = LOWER(mm.marque_mat)
          AND p.archiv = 'N'
      )
    `);
  } catch (err) {
    console.error('Error synchronizing brand parameters:', err);
  }
}

function migrateModelMatSchema() {
  try {
    const columns = db.prepare("PRAGMA table_info(model_mat)").all() as Array<{ name: string }>;
    const colNames = new Set(columns.map(c => c.name));

    if (!colNames.has('id_typ_mat')) {
      db.exec("ALTER TABLE model_mat ADD COLUMN id_typ_mat INTEGER REFERENCES type_mat(id_typ_mat)");
    }
    if (!colNames.has('default_cpu')) {
      db.exec("ALTER TABLE model_mat ADD COLUMN default_cpu TEXT");
    }
    if (!colNames.has('default_freq_cpu')) {
      db.exec("ALTER TABLE model_mat ADD COLUMN default_freq_cpu TEXT");
    }
    if (!colNames.has('default_ram')) {
      db.exec("ALTER TABLE model_mat ADD COLUMN default_ram INTEGER");
    }
    if (!colNames.has('default_disk')) {
      db.exec("ALTER TABLE model_mat ADD COLUMN default_disk INTEGER");
    }
    if (!colNames.has('default_se')) {
      db.exec("ALTER TABLE model_mat ADD COLUMN default_se TEXT");
    }
    if (!colNames.has('default_net')) {
      db.exec("ALTER TABLE model_mat ADD COLUMN default_net TEXT");
    }
    if (!colNames.has('description')) {
      db.exec("ALTER TABLE model_mat ADD COLUMN description TEXT");
    }
    if (!colNames.has('garantie_mois')) {
      db.exec("ALTER TABLE model_mat ADD COLUMN garantie_mois INTEGER DEFAULT 36");
    }
    if (!colNames.has('specs_json')) {
      db.exec("ALTER TABLE model_mat ADD COLUMN specs_json TEXT");
    }

    // Also migrate materiel to support specs_json
    const matCols = db.prepare("PRAGMA table_info(materiel)").all() as Array<{ name: string }>;
    const matColNames = new Set(matCols.map(c => c.name));
    if (!matColNames.has('marque_mat')) {
      db.exec("ALTER TABLE materiel ADD COLUMN marque_mat TEXT");
    }
    if (!matColNames.has('specs_json')) {
      db.exec("ALTER TABLE materiel ADD COLUMN specs_json TEXT");
    }

    // Backfill the brand for existing equipment from its selected model.
    db.exec(`
      UPDATE materiel
      SET marque_mat = (SELECT mm.marque_mat FROM model_mat mm WHERE mm.id_model_mat = materiel.id_model_mat)
      WHERE (marque_mat IS NULL OR TRIM(marque_mat) = '') AND id_model_mat IS NOT NULL
    `);

  } catch (err) {
    console.error('Migration error for model_mat/materiel:', err);
  }
}

// -------------------------------------------------------------
// SEED: PARAMÈTRES TECHNIQUES SPÉCIFIQUES PAR TYPE DE MATÉRIEL
// -------------------------------------------------------------
function seedTypeSpecificParameters() {
  try {
    const types = db.prepare("SELECT id_typ_mat, cod_typ_mat FROM type_mat WHERE archiv = 'N'").all() as Array<{ id_typ_mat: number; cod_typ_mat: string }>;
    const typeMap: Record<string, number> = {};
    types.forEach(t => { typeMap[t.cod_typ_mat] = t.id_typ_mat; });

    const insertParamType = db.prepare(`
      INSERT INTO parametre_type_mat (
        id_typ_mat, code_param, libelle_param, categorie_groupe, type_champ, unite, options_predefinies, description, ordre
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);

    const typeParamsDefinition: Record<string, Array<{
      code: string;
      libelle: string;
      groupe: string;
      typeChamp: 'text' | 'number' | 'select';
      unite?: string;
      options: string[];
      description: string;
      ordre: number;
    }>> = {
      // 1. PC Portable (LAP)
      LAP: [
        {
          code: 'cpu',
          libelle: 'Processeur (CPU)',
          groupe: 'Performance',
          typeChamp: 'select',
          options: ['Intel Core i7-1370P (14C / 5.2 GHz)', 'AMD Ryzen 7 PRO 7840U (8C / 5.1 GHz)', 'Intel Core i5-1340P (12C / 4.6 GHz)', 'Apple M3 Pro (12 Coeurs)', 'Intel Core Ultra 7 155H (16C)'],
          description: 'Modèle et génération du processeur mobile',
          ordre: 1,
        },
        {
          code: 'freq_cpu',
          libelle: 'Fréquence / Mode Turbo',
          groupe: 'Performance',
          typeChamp: 'text',
          options: ['2.80 GHz / Turbo 5.2 GHz', '3.30 GHz / Turbo 5.1 GHz', '1.90 GHz / Turbo 4.6 GHz', '4.05 GHz Boost'],
          description: 'Fréquence de base et fréquence maximale turbo',
          ordre: 2,
        },
        {
          code: 'ram',
          libelle: 'Mémoire RAM',
          groupe: 'Performance',
          typeChamp: 'select',
          unite: 'Go',
          options: ['8', '16', '18', '32', '64'],
          description: 'Capacité de mémoire vive DDR5 ou LPDDR5',
          ordre: 3,
        },
        {
          code: 'disk',
          libelle: 'Stockage SSD NVMe',
          groupe: 'Stockage',
          typeChamp: 'select',
          unite: 'Go',
          options: ['256', '512', '1000', '2000'],
          description: 'Capacité du disque SSD haute performance',
          ordre: 4,
        },
        {
          code: 'se',
          libelle: 'Système d\'Exploitation',
          groupe: 'Logiciel',
          typeChamp: 'select',
          options: ['Windows 11 Pro 64-bit', 'Windows 11 Entreprise LTSC', 'macOS Sonoma 14', 'Ubuntu 24.04 LTS Desktop'],
          description: 'Système d\'exploitation préinstallé sur le poste',
          ordre: 5,
        },
        {
          code: 'taille_ecran',
          libelle: 'Taille de l\'écran',
          groupe: 'Affichage',
          typeChamp: 'select',
          unite: 'pouces',
          options: ['13.3"', '14.0"', '14.2" Liquid Retina', '15.6"', '16.0"'],
          description: 'Diagonale de la dalle d\'affichage du portable',
          ordre: 6,
        },
        {
          code: 'net',
          libelle: 'Connectivité & Réseau',
          groupe: 'Réseau',
          typeChamp: 'select',
          options: ['Wi-Fi 6E AX211 + Bluetooth 5.3 + RJ45 Gigabit', 'Wi-Fi 6E + 4G LTE Fibocom + RJ45', 'Wi-Fi 7 + Bluetooth 5.4', 'Wi-Fi 6E + Thunderbolt 4'],
          description: 'Normes Wi-Fi, Bluetooth et interfaces réseau filaires',
          ordre: 7,
        },
        {
          code: 'autonomie_batt',
          libelle: 'Batterie & Autonomie',
          groupe: 'Énergie',
          typeChamp: 'text',
          unite: 'Wh',
          options: ['54 Wh (env. 9h autonomie)', '70 Wh (env. 13h autonomie)', '86 Wh (env. 16h autonomie)', '99.6 Wh'],
          description: 'Capacité de la batterie intégrée en Watt-heures',
          ordre: 8,
        },
      ],

      // 2. PC Bureau / Station de travail (DSK)
      DSK: [
        {
          code: 'cpu',
          libelle: 'Processeur (CPU)',
          groupe: 'Performance',
          typeChamp: 'select',
          options: ['Intel Core i5-13500 (14C / 4.8 GHz)', 'Intel Core i7-13700 (16C / 5.2 GHz)', 'Intel Core i9-13900K (24C / 5.8 GHz)', 'AMD Ryzen 9 7900X (12C / 5.6 GHz)'],
          description: 'Processeur de bureau haute puissance',
          ordre: 1,
        },
        {
          code: 'freq_cpu',
          libelle: 'Fréquence d\'horloge',
          groupe: 'Performance',
          typeChamp: 'text',
          options: ['2.50 GHz / Turbo 4.8 GHz', '2.10 GHz / Turbo 5.2 GHz', '3.00 GHz / Turbo 5.8 GHz'],
          description: 'Fréquences de fonctionnement nominale et turbo',
          ordre: 2,
        },
        {
          code: 'ram',
          libelle: 'Mémoire RAM',
          groupe: 'Performance',
          typeChamp: 'select',
          unite: 'Go',
          options: ['8', '16', '32', '64', '128'],
          description: 'Capacité de RAM DDR4 / DDR5',
          ordre: 3,
        },
        {
          code: 'disk',
          libelle: 'Stockage Principal (SSD)',
          groupe: 'Stockage',
          typeChamp: 'select',
          unite: 'Go',
          options: ['512', '1000', '2000', '4000'],
          description: 'Disque système SSD PCIe NVMe M.2',
          ordre: 4,
        },
        {
          code: 'se',
          libelle: 'Système d\'Exploitation',
          groupe: 'Logiciel',
          typeChamp: 'select',
          options: ['Windows 11 Pro 64-bit', 'Windows 10 Entreprise LTSC', 'Ubuntu 24.04 LTS Desktop', 'Red Hat Enterprise Linux 9'],
          description: 'OS installé sur l\'unité centrale',
          ordre: 5,
        },
        {
          code: 'gpu',
          libelle: 'Carte Graphique / GPU',
          groupe: 'Affichage',
          typeChamp: 'select',
          options: ['Intel UHD Graphics 770 (Intégré)', 'NVIDIA RTX A2000 12Go GDDR6 (Pro DAO/CAO)', 'NVIDIA GeForce RTX 4070 12Go', 'AMD Radeon PRO W6600 8Go'],
          description: 'Carte graphique dédiée ou chipset vidéo intégré',
          ordre: 6,
        },
        {
          code: 'format_boitier',
          libelle: 'Format du boîtier',
          groupe: 'Châssis',
          typeChamp: 'select',
          options: ['Small Form Factor (SFF)', 'Tour Moyenne (Mini-Tower)', 'Micro / Mini PC (1 Litre)', 'Tour Format Élargi'],
          description: 'Encombrement et facteur de forme du châssis',
          ordre: 7,
        },
        {
          code: 'sorties_video',
          libelle: 'Sorties Vidéo & Ports',
          groupe: 'Connectique',
          typeChamp: 'text',
          options: ['2x DisplayPort 1.4 + 1x HDMI 2.0', '3x DisplayPort 1.4 + 1x USB-C DP', '2x HDMI 2.1 + 2x DisplayPort'],
          description: 'Interfaces d\'affichage pour double ou triple écran',
          ordre: 8,
        },
      ],

      // 3. Serveur Rack / Tour (SRV)
      SRV: [
        {
          code: 'cpu',
          libelle: 'Processeurs / Sockets',
          groupe: 'Calcul',
          typeChamp: 'select',
          options: ['2x Intel Xeon Silver 4314 (32C / 64T total)', '2x Intel Xeon Gold 6330 (56C / 112T)', '1x AMD EPYC 7543 (32 Coeurs / 64T)', '2x AMD EPYC 9354 (64 Coeurs)'],
          description: 'Architecture processeur biprocesseur ou multiprocesseur',
          ordre: 1,
        },
        {
          code: 'ram',
          libelle: 'Mémoire RAM ECC Registrée',
          groupe: 'Calcul',
          typeChamp: 'select',
          unite: 'Go',
          options: ['64', '128', '256', '512', '1024'],
          description: 'Mémoire avec correction d\'erreurs (ECC RDIMM)',
          ordre: 2,
        },
        {
          code: 'disk',
          libelle: 'Stockage RAID & Disques',
          groupe: 'Stockage',
          typeChamp: 'select',
          options: ['4x 960 Go SSD SAS Hot-Plug RAID 10', '8x 1.92 To SSD SAS Hot-Plug RAID 5', '6x 4 To SAS 12G 10K RAID 6', '2x 480 Go SSD NVMe RAID 1 (OS) + 4x 3.84 To NVMe'],
          description: 'Grappe de disques durs / SSD tolérante aux pannes',
          ordre: 3,
        },
        {
          code: 'controleur_raid',
          libelle: 'Contrôleur RAID Matériel',
          groupe: 'Stockage',
          typeChamp: 'select',
          options: ['PERC H755 8Go NV Cache', 'HPE Smart Array P408i-a SR Gen10 (2Go Cache)', 'Broadcom MegaRAID 9560-8i', 'Contrôleur HBA SAS 12Gbps (ZFS)'],
          description: 'Carte contrôleur RAID avec cache protégé sur batterie/flash',
          ordre: 4,
        },
        {
          code: 'format_chassis',
          libelle: 'Format Châssis Rack',
          groupe: 'Châssis',
          typeChamp: 'select',
          options: ['Rack 1U', 'Rack 2U', 'Rack 4U', 'Tour convertible Rack 5U'],
          description: 'Hauteur d\'unité en baie informatique (U)',
          ordre: 5,
        },
        {
          code: 'alim_redondante',
          libelle: 'Alimentation Redondante',
          groupe: 'Énergie',
          typeChamp: 'select',
          options: ['Double alimentation 800W Hot-Plug Platinum', 'Double alimentation 1100W Hot-Plug Titanium', 'Double alimentation 1400W 80 Plus Platinum'],
          description: 'Blocs d\'alimentation 1+1 interchangeables à chaud',
          ordre: 6,
        },
        {
          code: 'interfaces_reseau',
          libelle: 'Interfaces Réseau Datacenter',
          groupe: 'Réseau',
          typeChamp: 'select',
          options: ['Dual 10GbE SFP+ + Quad GbE RJ45', 'Dual 25GbE SFP28 + Dual 10GbE SFP+', 'Quad 10GbE Base-T RJ45'],
          description: 'Cartes réseau haut débit avec agrégation de liens LACP',
          ordre: 7,
        },
        {
          code: 'hyperviseur',
          libelle: 'Système / Hyperviseur',
          groupe: 'Système',
          typeChamp: 'select',
          options: ['VMware ESXi 8.0 Update 2', 'Proxmox VE 8.2 Enterprise', 'Debian 12 Bookworm Server', 'Windows Server 2022 Datacenter', 'Red Hat Enterprise Linux 9'],
          description: 'Plateforme de virtualisation ou OS hôte serveur',
          ordre: 8,
        },
      ],

      // 4. Imprimante / Multifonction Réseau (PRT)
      PRT: [
        {
          code: 'technologie',
          libelle: 'Technologie d\'impression',
          groupe: 'Moteur d\'impression',
          typeChamp: 'select',
          options: ['Laser Couleur Électrophotographique', 'Laser Monochrome Haute Vitesse', 'Jet d\'encre Professionnel PageWide', 'Transfert Thermique Industriel'],
          description: 'Technologie laser toner ou jet d\'encre entreprise',
          ordre: 1,
        },
        {
          code: 'fonctions',
          libelle: 'Fonctions du périphérique',
          groupe: 'Fonctionnalités',
          typeChamp: 'select',
          options: ['Multifonction 4-en-1 (Impression, Numérisation, Copie, Fax)', 'Multifonction 3-en-1 (Impression, Numérisation, Copie)', 'Imprimante Réseau Simple'],
          description: 'Modules et fonctionnalités combinées',
          ordre: 2,
        },
        {
          code: 'vitesse_ppm',
          libelle: 'Vitesse d\'impression',
          groupe: 'Performance',
          typeChamp: 'select',
          unite: 'ppm',
          options: ['27 ppm couleur/noir', '38 ppm couleur/noir', '45 ppm noir / 40 ppm couleur', '55 ppm'],
          description: 'Nombre de pages par minute (ppm) en A4',
          ordre: 3,
        },
        {
          code: 'recto_verso',
          libelle: 'Recto-verso automatique',
          groupe: 'Papier',
          typeChamp: 'select',
          options: ['Oui (Impression et Numérisation DADF monopasse)', 'Oui (Impression recto-verso automatique)', 'Non (Recto simple)'],
          description: 'Gestion automatique du retournement papier et scanner',
          ordre: 4,
        },
        {
          code: 'formats_papier',
          libelle: 'Formats papier supportés',
          groupe: 'Papier',
          typeChamp: 'select',
          options: ['A4, A5, B5, Enveloppes, Cartes', 'A3, A4, A5, Formats personnalisés', 'A4 / Lettre standard'],
          description: 'Dimensions et formats de supports compatibles',
          ordre: 5,
        },
        {
          code: 'capacite_bacs',
          libelle: 'Capacité bacs papier',
          groupe: 'Papier',
          typeChamp: 'select',
          options: ['Bac standard 250 feuilles + Bac universel 50 feuilles', '2x Bacs 550 feuilles (1100 feuilles total)', '4x Bacs 550 feuilles + Bypass 100 f. (2300 feuilles)'],
          description: 'Nombre de feuilles contenues dans les magasins papier',
          ordre: 6,
        },
        {
          code: 'resolution_dpi',
          libelle: 'Résolution maximale',
          groupe: 'Qualité',
          typeChamp: 'select',
          unite: 'dpi',
          options: ['1200 x 1200 dpi', '2400 x 600 dpi HP ImageREt 3600', '4800 x 1200 dpi optimisés'],
          description: 'Finesse de trame et résolution d\'impression en points par pouce',
          ordre: 7,
        },
        {
          code: 'connectivite',
          libelle: 'Connectivité Réseau & Protocoles',
          groupe: 'Réseau',
          typeChamp: 'select',
          options: ['Gigabit Ethernet RJ45 + Wi-Fi bibande 2.4/5GHz + USB hôte', 'Ethernet 1Gbps + Wi-Fi Direct + NFC Touch-to-Print', 'Ethernet RJ45 10/100/1000 + USB 2.0'],
          description: 'Interfaces réseau filaires, sans fil et impression mobile AirPrint/Mopria',
          ordre: 8,
        },
      ],

      // 5. Switch / Équipement Réseau (SWI)
      SWI: [
        {
          code: 'nb_ports',
          libelle: 'Nombre total de ports',
          groupe: 'Commutation',
          typeChamp: 'select',
          options: ['8 Ports RJ45', '16 Ports RJ45', '24 Ports RJ45', '48 Ports RJ45'],
          description: 'Nombre de ports RJ45 d\'accès utilisateurs ou serveurs',
          ordre: 1,
        },
        {
          code: 'vitesse_ports',
          libelle: 'Débit des ports d\'accès',
          groupe: 'Débit',
          typeChamp: 'select',
          options: ['Gigabit 10/100/1000 Mbps RJ45', 'Multi-Gigabit 2.5G/5G/10G Ethernet', '10G Base-T RJ45'],
          description: 'Débit unitaire des ports commutés',
          ordre: 2,
        },
        {
          code: 'norme_poe',
          libelle: 'Norme d\'Alimentation PoE',
          groupe: 'PoE',
          typeChamp: 'select',
          options: ['PoE+ (802.3at - jusqu\'à 30W par port)', 'PoE++ (802.3bt Type 3/4 - 60W/90W)', 'PoE standard (802.3af - 15.4W)', 'Non-PoE (Ports data uniquement)'],
          description: 'Capacité à téléalimenter les téléphones IP, caméras et bornes Wi-Fi',
          ordre: 3,
        },
        {
          code: 'budget_poe_w',
          libelle: 'Budget PoE Total',
          groupe: 'PoE',
          typeChamp: 'select',
          unite: 'Watts',
          options: ['370 W', '740 W', '180 W', '1440 W (avec double alimentation)', '0 W (Non PoE)'],
          description: 'Puissance totale délivrable pour les équipements PoE connectés',
          ordre: 4,
        },
        {
          code: 'ports_uplink',
          libelle: 'Ports Uplink d\'Interconnexion',
          groupe: 'Réseau',
          typeChamp: 'select',
          options: ['4x 1G SFP', '4x 10G SFP+', '2x 40G QSFP+', '2x 10G SFP+ + 2x 1G SFP'],
          description: 'Ports optiques fibre pour liaison vers le cœur de réseau',
          ordre: 5,
        },
        {
          code: 'niveau_commutation',
          libelle: 'Niveau de Routage / Commutation',
          groupe: 'Fonctionnalités',
          typeChamp: 'select',
          options: ['Layer 2+ (VLANs 802.1Q, QoS, LACP, Spanning-Tree)', 'Layer 3 manageable (Routage IPv4/IPv6 statique & dynamique OSPF, BGP, RIP)', 'Layer 2 standard'],
          description: 'Capacités de commutation niveau 2 ou routage niveau 3',
          ordre: 6,
        },
        {
          code: 'capacite_commutation',
          libelle: 'Capacité de commutation',
          groupe: 'Performance',
          typeChamp: 'text',
          unite: 'Gbps',
          options: ['104 Gbps (non-bloquant)', '176 Gbps', '128 Gbps', '256 Gbps'],
          description: 'Bande passante interne de la matrice de commutation (Backplane)',
          ordre: 7,
        },
        {
          code: 'management',
          libelle: 'Administration & Protocoles',
          groupe: 'Gestion',
          typeChamp: 'select',
          options: ['Web GUI HTTPS + CLI SSH + SNMP v3 + Cloud Management', 'CLI Cisco IOS + Telnet/SSH + SNMP v1/v2c/v3', 'Cloud Dashboard (Meraki / Aruba Central)'],
          description: 'Interfaces et protocoles d\'administration réseau',
          ordre: 8,
        },
      ],

      // 6. Onduleur Haute Disponibilité (UPS)
      UPS: [
        {
          code: 'puissance_va',
          libelle: 'Puissance apparente (VA)',
          groupe: 'Capacité',
          typeChamp: 'select',
          unite: 'VA',
          options: ['1000 VA', '1500 VA', '2200 VA', '3000 VA', '5000 VA', '10000 VA (10 kVA)'],
          description: 'Puissance électrique apparente supportée',
          ordre: 1,
        },
        {
          code: 'puissance_watts',
          libelle: 'Puissance active (Watts)',
          groupe: 'Capacité',
          typeChamp: 'select',
          unite: 'Watts',
          options: ['900 W', '1350 W', '1980 W', '2700 W', '4500 W', '9000 W'],
          description: 'Puissance active réelle disponible pour la charge',
          ordre: 2,
        },
        {
          code: 'technologie_onduleur',
          libelle: 'Technologie de régulation',
          groupe: 'Technologie',
          typeChamp: 'select',
          options: ['Line-Interactive (Onde sinusoïdale pure)', 'On-Line Double Conversion (VFI-SS-111)', 'Off-Line / Veille passive'],
          description: 'Topologie de protection contre les micro-coupures et variations de tension',
          ordre: 3,
        },
        {
          code: 'autonomie_min',
          libelle: 'Autonomie estimée à mi-charge',
          groupe: 'Autonomie',
          typeChamp: 'select',
          unite: 'min',
          options: ['15 min', '30 min', '45 min', '60 min', '90 min (avec pack additionnel)'],
          description: 'Durée de maintien sur batterie en cas de coupure secteur totale',
          ordre: 4,
        },
        {
          code: 'format_chassis',
          libelle: 'Facteur de forme & Montage',
          groupe: 'Châssis',
          typeChamp: 'select',
          options: ['Rack 2U / Tour convertible', 'Rack 3U', 'Tour autonome verticale', 'Rack 4U'],
          description: 'Format physique pour baie informatique 19" ou pose au sol',
          ordre: 5,
        },
        {
          code: 'prises_sortie',
          libelle: 'Types et nombre de prises',
          groupe: 'Connectique',
          typeChamp: 'select',
          options: ['8x IEC C13 + 2x IEC C19', '6x Prises françaises NF / Schuko 230V', '8x IEC C13 + 1x Prise Schuko', 'Bornier direct + 4x IEC C13'],
          description: 'Connecteurs de sortie secourus et filtrés',
          ordre: 6,
        },
        {
          code: 'carte_reseau',
          libelle: 'Carte de gestion réseau à distance',
          groupe: 'Supervision',
          typeChamp: 'select',
          options: ['Carte NMC Web/SNMP installée (SmartSlot)', 'Port USB + Série RS232 + Carte NMC optionnelle', 'Module SmartConnect Cloud intégré'],
          description: 'Carte de supervision IP avec arrêt propre automatisé des serveurs (PowerChute)',
          ordre: 7,
        },
        {
          code: 'tension_regulation',
          libelle: 'Tension de régulation nominale',
          groupe: 'Énergie',
          typeChamp: 'text',
          unite: 'V',
          options: ['230V AC (Tolérance 160-286V) 50/60 Hz', '220V / 230V / 240V AC configurable'],
          description: 'Tension électrique nominale d\'entrée et de sortie',
          ordre: 8,
        },
      ],

      // 7. Écran Professionnel (SCR)
      SCR: [
        {
          code: 'taille_diagonale',
          libelle: 'Taille diagonale',
          groupe: 'Affichage',
          typeChamp: 'select',
          unite: 'pouces',
          options: ['24" (60.5 cm)', '27" (68.6 cm)', '32" (81.3 cm)', '34" Incurvé UltraWide (86.4 cm)'],
          description: 'Taille en pouces de la surface visible de la dalle',
          ordre: 1,
        },
        {
          code: 'resolution',
          libelle: 'Résolution native',
          groupe: 'Affichage',
          typeChamp: 'select',
          options: ['Full HD 1920 x 1080 (16:9)', '2K QHD 2560 x 1440 (16:9)', '4K UHD 3840 x 2160 (16:9)', 'UWQHD 3440 x 1440 (21:9)'],
          description: 'Définition d\'affichage native en pixels',
          ordre: 2,
        },
        {
          code: 'type_dalle',
          libelle: 'Technologie de la dalle',
          groupe: 'Affichage',
          typeChamp: 'select',
          options: ['IPS Pro (Couleurs fidèles 99% sRGB / DCI-P3)', 'VA (Contraste élevé 3000:1)', 'Fast-IPS 1ms', 'OLED Haute Définition'],
          description: 'Technologie de cristaux liquides ou diodes émettrices',
          ordre: 3,
        },
        {
          code: 'taux_rafraichissement',
          libelle: 'Taux de rafraîchissement',
          groupe: 'Performance',
          typeChamp: 'select',
          unite: 'Hz',
          options: ['60 Hz', '75 Hz', '100 Hz', '144 Hz', '165 Hz'],
          description: 'Fréquence de rafraîchissement de l\'affichage',
          ordre: 4,
        },
        {
          code: 'connectique_video',
          libelle: 'Connectique d\'entrée',
          groupe: 'Connectique',
          typeChamp: 'select',
          options: ['HDMI 2.0 + DisplayPort 1.4 + USB-C (Power Delivery 90W)', '2x HDMI 2.1 + 1x DisplayPort 1.4', 'HDMI 1.4 + DisplayPort 1.2 + VGA'],
          description: 'Ports vidéo HDMI, DisplayPort et entrée USB-C avec charge PC',
          ordre: 5,
        },
        {
          code: 'hub_dock',
          libelle: 'Hub USB & Fonctions Docking',
          groupe: 'Connectique',
          typeChamp: 'select',
          options: ['Hub 4x USB 3.2 + Port Ethernet RJ45 Gigabit intégré + KVM', 'Hub 4x USB-A 3.0', 'Hub 2x USB + Sortie audio'],
          description: 'Hub USB intégré et fonction de réplication de ports Ethernet',
          ordre: 6,
        },
        {
          code: 'ergonomie',
          libelle: 'Ergonomie & Réglages du pied',
          groupe: 'Ergonomie',
          typeChamp: 'select',
          options: ['Pied réglable en hauteur (150mm) + Pivot 90° portrait + Inclinaison + Rotation', 'Inclinaison seule (-5° / +21°)', 'Support VESA 100x100mm sans pied'],
          description: 'Possibilités d\'ajustement physique et orientation',
          ordre: 7,
        },
      ],
    };

    const checkExistingStmt = db.prepare('SELECT id_param_type FROM parametre_type_mat WHERE id_typ_mat = ? AND code_param = ?');

    for (const [typeCode, params] of Object.entries(typeParamsDefinition)) {
      const typeId = typeMap[typeCode];
      if (!typeId) continue;

      for (const p of params) {
        const existing = checkExistingStmt.get(typeId, p.code);
        if (!existing) {
          insertParamType.run(
            typeId,
            p.code,
            p.libelle,
            p.groupe,
            p.typeChamp,
            p.unite || null,
            JSON.stringify(p.options),
            p.description,
            p.ordre
          );
        }
      }
    }
    console.log('Type-specific equipment parameters seeded successfully.');
  } catch (err) {
    console.error('Error seeding type-specific parameters:', err);
  }
}

function updateModelMatDefaults() {
  try {
    // Find type IDs dynamically
    const types = db.prepare("SELECT id_typ_mat, cod_typ_mat FROM type_mat").all() as Array<{ id_typ_mat: number; cod_typ_mat: string }>;
    const typeMap: Record<string, number> = {};
    types.forEach(t => { typeMap[t.cod_typ_mat] = t.id_typ_mat; });

    const modelsDefaults = [
      {
        marque: 'Dell',
        model: 'Latitude 5540',
        typeCode: 'LAP',
        cpu: 'Intel Core i7-1370P (14C / 5.2 GHz)',
        freq: '2.80 GHz / Turbo 5.2 GHz',
        ram: 16,
        disk: 512,
        se: 'Windows 11 Pro 64-bit',
        net: 'Wi-Fi 6E AX211 + RJ45 Gigabit',
        desc: 'PC Portable 15.6" Full HD antireflet, Clavier rétroéclairé, 2x Thunderbolt 4, batterie 54Wh',
        garantie: 36,
        specs: {
          cpu: 'Intel Core i7-1370P (14C / 5.2 GHz)',
          freq_cpu: '2.80 GHz / Turbo 5.2 GHz',
          ram: '16',
          disk: '512',
          se: 'Windows 11 Pro 64-bit',
          taille_ecran: '15.6"',
          net: 'Wi-Fi 6E AX211 + Bluetooth 5.3 + RJ45 Gigabit',
          autonomie_batt: '54 Wh (env. 9h autonomie)'
        }
      },
      {
        marque: 'Lenovo',
        model: 'ThinkPad T14 Gen 4',
        typeCode: 'LAP',
        cpu: 'AMD Ryzen 7 PRO 7840U (8C / 5.1 GHz)',
        freq: '3.30 GHz / Turbo 5.1 GHz',
        ram: 32,
        disk: 1000,
        se: 'Windows 11 Pro 64-bit',
        net: 'Wi-Fi 6E + Module 4G LTE Fibocom + RJ45',
        desc: 'PC Portable 14" WUXGA Low Power, Châssis renforcé magnésium/carbone, lecteur d\'empreintes et puce TPM 2.0',
        garantie: 36,
        specs: {
          cpu: 'AMD Ryzen 7 PRO 7840U (8C / 5.1 GHz)',
          freq_cpu: '3.30 GHz / Turbo 5.1 GHz',
          ram: '32',
          disk: '1000',
          se: 'Windows 11 Pro 64-bit',
          taille_ecran: '14.0"',
          net: 'Wi-Fi 6E + 4G LTE Fibocom + RJ45',
          autonomie_batt: '54 Wh (env. 9h autonomie)'
        }
      },
      {
        marque: 'HP',
        model: 'EliteBook 840 G9',
        typeCode: 'LAP',
        cpu: 'Intel Core i7-12700 (12C / 4.9 GHz)',
        freq: '2.10 GHz / Turbo 4.8 GHz',
        ram: 16,
        disk: 512,
        se: 'Windows 11 Pro 64-bit',
        net: 'Wi-Fi 6E + Bluetooth 5.3 + RJ45 via adaptateur',
        desc: 'PC Portable Ultra-léger aluminium brossé 14", Caméra 5MP IR avec obturateur physique HP Sure Shutter',
        garantie: 36,
        specs: {
          cpu: 'Intel Core i7-12700 (12C / 4.9 GHz)',
          freq_cpu: '2.10 GHz / Turbo 4.8 GHz',
          ram: '16',
          disk: '512',
          se: 'Windows 11 Pro 64-bit',
          taille_ecran: '14.0"',
          net: 'Wi-Fi 6E AX211 + Bluetooth 5.3 + RJ45 Gigabit',
          autonomie_batt: '54 Wh (env. 9h autonomie)'
        }
      },
      {
        marque: 'Dell',
        model: 'OptiPlex 7010',
        typeCode: 'DSK',
        cpu: 'Intel Core i5-13500 (14C / 4.8 GHz)',
        freq: '2.50 GHz / Turbo 4.8 GHz',
        ram: 16,
        disk: 512,
        se: 'Windows 11 Pro 64-bit',
        net: 'Ethernet Gigabit RJ45 1000 Mbps',
        desc: 'Unité Centrale Small Form Factor (SFF), 4x USB 3.2 Gen 1, 2x DisplayPort 1.4a, Alimentation 80 Plus Bronze',
        garantie: 36,
        specs: {
          cpu: 'Intel Core i5-13500 (14C / 4.8 GHz)',
          freq_cpu: '2.50 GHz / Turbo 4.8 GHz',
          ram: '16',
          disk: '512',
          se: 'Windows 11 Pro 64-bit',
          gpu: 'Intel UHD Graphics 770 (Intégré)',
          format_boitier: 'Small Form Factor (SFF)',
          sorties_video: '2x DisplayPort 1.4 + 1x HDMI 2.0'
        }
      },
      {
        marque: 'Dell',
        model: 'PowerEdge R750xs',
        typeCode: 'SRV',
        cpu: '2x Intel Xeon Silver 4314 (32C / 64T total)',
        freq: '2.40 GHz / Turbo 3.4 GHz',
        ram: 64,
        disk: 2000,
        se: 'Debian 12 Bookworm / Proxmox VE 8',
        net: 'Dual 10GbE SFP+ Broadcom + Quad GbE RJ45',
        desc: 'Serveur Rack 2U biprocesseur, Contrôleur RAID PERC H755 8Go NV Cache, Double alimentation redondante 800W hot-plug',
        garantie: 60,
        specs: {
          cpu: '2x Intel Xeon Silver 4314 (32C / 64T total)',
          ram: '64',
          disk: '4x 960 Go SSD SAS Hot-Plug RAID 10',
          controleur_raid: 'PERC H755 8Go NV Cache',
          format_chassis: 'Rack 2U',
          alim_redondante: 'Double alimentation 800W Hot-Plug Platinum',
          interfaces_reseau: 'Dual 10GbE SFP+ + Quad GbE RJ45',
          hyperviseur: 'Proxmox VE 8.2 Enterprise'
        }
      },
      {
        marque: 'HP',
        model: 'Color LaserJet Pro M479fdw',
        typeCode: 'PRT',
        cpu: 'Contrôleur HP FutureSmart',
        freq: '1.20 GHz',
        ram: 1,
        disk: 4,
        se: 'Firmware HP FutureSmart 5.6',
        net: 'Gigabit Ethernet RJ45 + Wi-Fi bibande 2.4/5GHz',
        desc: 'Multifonction Laser Couleur 4-en-1 (Impression, Numérisation recto-verso monopasse, Copie, Fax), 27 ppm',
        garantie: 24,
        specs: {
          technologie: 'Laser Couleur Électrophotographique',
          fonctions: 'Multifonction 4-en-1 (Impression, Numérisation, Copie, Fax)',
          vitesse_ppm: '27 ppm couleur/noir',
          recto_verso: 'Oui (Impression et Numérisation DADF monopasse)',
          formats_papier: 'A4, A5, B5, Enveloppes, Cartes',
          capacite_bacs: 'Bac standard 250 feuilles + Bac universel 50 feuilles',
          resolution_dpi: '1200 x 1200 dpi',
          connectivite: 'Gigabit Ethernet RJ45 + Wi-Fi bibande 2.4/5GHz + USB hôte'
        }
      },
      {
        marque: 'Cisco',
        model: 'Catalyst 2960X-48FPS',
        typeCode: 'SWI',
        cpu: 'Dual Core ASIC Cisco',
        freq: '600 MHz',
        ram: 1,
        disk: 1,
        se: 'Cisco IOS 15.2(7)E7 LAN Base',
        net: '48x Gigabit PoE+ (budget 370W) + 4x 1G SFP',
        desc: 'Switch manageable niveau 2/3 d\'entreprise, empilement FlexStack-Plus 80 Gbps, budget PoE 370W',
        garantie: 60,
        specs: {
          nb_ports: '48 Ports RJ45',
          vitesse_ports: 'Gigabit 10/100/1000 Mbps RJ45',
          norme_poe: 'PoE+ (802.3at - jusqu\'à 30W par port)',
          budget_poe_w: '370 W',
          ports_uplink: '4x 1G SFP',
          niveau_commutation: 'Layer 2+ (VLANs 802.1Q, QoS, LACP, Spanning-Tree)',
          capacite_commutation: '104 Gbps (non-bloquant)',
          management: 'CLI Cisco IOS + Telnet/SSH + SNMP v1/v2c/v3'
        }
      },
      {
        marque: 'APC',
        model: 'Smart-UPS SMT2200RMI2UC',
        typeCode: 'UPS',
        cpu: 'Microcontrôleur APC DSP',
        freq: '50/60 Hz',
        ram: 0,
        disk: 0,
        se: 'SmartSlot NMC3 Firmware',
        net: 'Port SmartSlot + RJ45 Cloud Monitoring',
        desc: 'Onduleur Line-interactive Rack 2U 2200VA / 1980W à onde sinusoïdale pure, autonomie 45 min, carte réseau NMC3',
        garantie: 36,
        specs: {
          puissance_va: '2200 VA',
          puissance_watts: '1980 W',
          technologie_onduleur: 'Line-Interactive (Onde sinusoïdale pure)',
          autonomie_min: '45 min',
          format_chassis: 'Rack 2U / Tour convertible',
          prises_sortie: '8x IEC C13 + 2x IEC C19',
          carte_reseau: 'Carte NMC Web/SNMP installée (SmartSlot)',
          tension_regulation: '230V AC (Tolérance 160-286V) 50/60 Hz'
        }
      },
      {
        marque: 'Apple',
        model: 'MacBook Pro 14 M3 Pro',
        typeCode: 'LAP',
        cpu: 'Apple M3 Pro (12 Coeurs)',
        freq: '4.05 GHz Boost',
        ram: 18,
        disk: 512,
        se: 'macOS Sonoma 14',
        net: 'Wi-Fi 6E (802.11ax) + Bluetooth 5.3',
        desc: 'Écran Liquid Retina XDR 14.2" 120Hz ProMotion, 3x ports Thunderbolt 4, port HDMI, lecteur SDXC, MagSafe 3',
        garantie: 36,
        specs: {
          cpu: 'Apple M3 Pro (12 Coeurs)',
          freq_cpu: '4.05 GHz Boost',
          ram: '18',
          disk: '512',
          se: 'macOS Sonoma 14',
          taille_ecran: '14.2" Liquid Retina',
          net: 'Wi-Fi 6E + Thunderbolt 4',
          autonomie_batt: '70 Wh (env. 13h autonomie)'
        }
      },
      {
        marque: 'Samsung',
        model: 'ViewFinity S80PB 27"',
        typeCode: 'SCR',
        cpu: 'Scaler UHD Realtek',
        freq: '60 Hz Refresh Rate',
        ram: 0,
        disk: 0,
        se: 'Firmware OSD Moniteur',
        net: 'Hub USB-C avec port Ethernet RJ45 1Gbps',
        desc: 'Moniteur professionnel 27" IPS UHD 4K (3840 x 2160), HDR400, Hub USB-C avec Power Delivery 90W et port LAN RJ45 intégré',
        garantie: 36,
        specs: {
          taille_diagonale: '27" (68.6 cm)',
          resolution: '4K UHD 3840 x 2160 (16:9)',
          type_dalle: 'IPS Pro (Couleurs fidèles 99% sRGB / DCI-P3)',
          taux_rafraichissement: '60 Hz',
          connectique_video: 'HDMI 2.0 + DisplayPort 1.4 + USB-C (Power Delivery 90W)',
          hub_dock: 'Hub 4x USB 3.2 + Port Ethernet RJ45 Gigabit intégré + KVM',
          ergonomie: 'Pied réglable en hauteur (150mm) + Pivot 90° portrait + Inclinaison + Rotation'
        }
      }
    ];

    const updateStmt = db.prepare(`
      UPDATE model_mat SET
        id_typ_mat = COALESCE(?, id_typ_mat),
        default_cpu = COALESCE(?, default_cpu),
        default_freq_cpu = COALESCE(?, default_freq_cpu),
        default_ram = COALESCE(?, default_ram),
        default_disk = COALESCE(?, default_disk),
        default_se = COALESCE(?, default_se),
        default_net = COALESCE(?, default_net),
        description = COALESCE(?, description),
        garantie_mois = COALESCE(?, garantie_mois),
        specs_json = ?
      WHERE marque_mat = ? AND model_mat = ?
    `);

    const insertStmt = db.prepare(`
      INSERT INTO model_mat (
        marque_mat, model_mat, id_typ_mat, default_cpu, default_freq_cpu,
        default_ram, default_disk, default_se, default_net, description, garantie_mois, specs_json
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);

    for (const m of modelsDefaults) {
      const typId = typeMap[m.typeCode] || null;
      const specsStr = JSON.stringify(m.specs);
      const existing = db.prepare("SELECT id_model_mat FROM model_mat WHERE marque_mat = ? AND model_mat = ?").get(m.marque, m.model) as any;
      if (existing) {
        updateStmt.run(typId, m.cpu, m.freq, m.ram, m.disk, m.se, m.net, m.desc, m.garantie, specsStr, m.marque, m.model);
      } else {
        insertStmt.run(m.marque, m.model, typId, m.cpu, m.freq, m.ram, m.disk, m.se, m.net, m.desc, m.garantie, specsStr);
      }
    }

    // Also update existing materiels with their specs_json if empty
    const materiels = db.prepare("SELECT id_mat, id_model_mat, id_typ_mat, specs_json FROM materiel").all() as Array<{ id_mat: number; id_model_mat: number; id_typ_mat: number; specs_json: string }>;
    for (const mat of materiels) {
      if (!mat.specs_json && mat.id_model_mat) {
        const model = db.prepare("SELECT specs_json FROM model_mat WHERE id_model_mat = ?").get(mat.id_model_mat) as any;
        if (model?.specs_json) {
          db.prepare("UPDATE materiel SET specs_json = ? WHERE id_mat = ?").run(model.specs_json, mat.id_mat);
        }
      }
    }

    console.log('Equipment models technical parameters initialized with type-specific specs.');
  } catch (err) {
    console.error('Error in updateModelMatDefaults:', err);
  }
}
