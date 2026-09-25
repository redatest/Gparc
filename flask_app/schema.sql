-- ==========================================================
-- GPARC - Schéma SQLite moderne (Migration depuis Oracle GPARC)
-- Application de gestion du parc informatique d'entreprise
-- ==========================================================

PRAGMA foreign_keys = ON;

-- 1. Table STRUCTURE (Départements / Directions / Services)
CREATE TABLE IF NOT EXISTS structures (
  id_str INTEGER PRIMARY KEY AUTOINCREMENT,
  cod_str TEXT NOT NULL,
  lib_str TEXT NOT NULL,
  id_str_mere INTEGER,
  archiv TEXT DEFAULT 'N',
  dat_cre DATETIME DEFAULT CURRENT_TIMESTAMP,
  dat_mod DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. Table TYPE_MAT (Catégories et types d'équipements)
CREATE TABLE IF NOT EXISTS type_mat (
  id_typ_mat INTEGER PRIMARY KEY AUTOINCREMENT,
  cod_typ_mat TEXT NOT NULL,
  lib_typ_mat TEXT NOT NULL,
  archiv TEXT DEFAULT 'N',
  dat_cre DATETIME DEFAULT CURRENT_TIMESTAMP,
  dat_mod DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. Table MODEL_MAT (Marques et Modèles)
CREATE TABLE IF NOT EXISTS model_mat (
  id_model_mat INTEGER PRIMARY KEY AUTOINCREMENT,
  marque_mat TEXT NOT NULL,
  model_mat TEXT NOT NULL,
  archiv TEXT DEFAULT 'N',
  dat_cre DATETIME DEFAULT CURRENT_TIMESTAMP,
  dat_mod DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 4. Table LIEU_REP (Ateliers et centres de réparation agréés)
CREATE TABLE IF NOT EXISTS lieu_rep (
  id_lieu_rep INTEGER PRIMARY KEY AUTOINCREMENT,
  nom_lieu_rep TEXT NOT NULL,
  adr_lieu_rep TEXT,
  tel_lieu_rep TEXT,
  contact_rep TEXT,
  archiv TEXT DEFAULT 'N',
  dat_cre DATETIME DEFAULT CURRENT_TIMESTAMP,
  dat_mod DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 5. Table UTILISATEURS (Collaborateurs / Assignataires)
CREATE TABLE IF NOT EXISTS utilisateurs (
  id_uti INTEGER PRIMARY KEY AUTOINCREMENT,
  nom_uti TEXT NOT NULL,
  pnom_uti TEXT NOT NULL,
  mail_uti TEXT,
  ad_uti TEXT,
  net_uti TEXT DEFAULT 'N',
  id_str_mere INTEGER,
  archiv TEXT DEFAULT 'N',
  dat_cre DATETIME DEFAULT CURRENT_TIMESTAMP,
  dat_mod DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (id_str_mere) REFERENCES structures (id_str)
);

-- 6. Table MATERIEL (Inventaire du parc avec image descriptive)
CREATE TABLE IF NOT EXISTS materiel (
  id_mat INTEGER PRIMARY KEY AUTOINCREMENT,
  id_str INTEGER,
  id_typ_mat INTEGER,
  id_model_mat INTEGER,
  num_inv TEXT UNIQUE NOT NULL,
  num_ser TEXT NOT NULL,
  dat_acq DATE,
  dat_mes DATE,
  etat_mat TEXT DEFAULT 'OP', -- 'OP': Opérationnel, 'PA': En panne, 'RE': En réparation, 'SO': Réformé
  obs_mat TEXT,
  dat_sortie DATE,
  motif_sortie TEXT,
  ram INTEGER,            -- Capacité RAM en Go
  disk INTEGER,           -- Capacité stockage en Go
  cpu TEXT,               -- Modèle processeur
  freq_cpu TEXT,          -- Fréquence processeur
  se TEXT,                -- Système d'exploitation
  net TEXT,               -- Interfaces réseau (WiFi, Ethernet)
  ordi TEXT,              -- Nom d'hôte sur le réseau local
  ip TEXT,                -- Adresse IPv4 statique ou DHCP
  id_uti INTEGER,         -- Utilisateur assigné
  disk2 TEXT,
  ram2 INTEGER,
  cpu2 TEXT,
  freq_cpu2 TEXT,
  se2 TEXT,
  net2 TEXT,
  image_url TEXT,         -- Image descriptive ou photo de l'équipement
  valeur_acq REAL DEFAULT 0,
  archiv TEXT DEFAULT 'N',
  dat_cre DATETIME DEFAULT CURRENT_TIMESTAMP,
  dat_mod DATETIME DEFAULT CURRENT_TIMESTAMP,
  etat_reforme TEXT DEFAULT 'AUCUNE',
  motif_reforme TEXT,
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

-- 8. Table PANNE (Incidents et interventions techniques)
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
  eta_pan TEXT DEFAULT 'EC', -- 'EC': En cours, 'RP': Réparé, 'AT': Attente pièces, 'NR': Non réparable
  dat_sortie_pan DATE,
  tp TEXT DEFAULT 'MAT',     -- 'MAT': Matériel, 'LOG': Logiciel, 'RES': Réseau, 'ALIM': Alimentation
  technicien TEXT,
  pieces_remplacees TEXT,
  cout_rep REAL DEFAULT 0,
  recommandations TEXT,
  archiv TEXT DEFAULT 'N',
  dat_cre DATETIME DEFAULT CURRENT_TIMESTAMP,
  dat_mod DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (id_mat) REFERENCES materiel (id_mat),
  FOREIGN KEY (id_str) REFERENCES structures (id_str),
  FOREIGN KEY (id_lieu_rep) REFERENCES lieu_rep (id_lieu_rep)
);

-- 9. Table CARA_MAT (Caractéristiques personnalisées)
CREATE TABLE IF NOT EXISTS cara_mat (
  id_cara_mat INTEGER PRIMARY KEY AUTOINCREMENT,
  lib_cara_mat TEXT NOT NULL,
  fam_cara_mat TEXT NOT NULL,
  archiv TEXT DEFAULT 'N',
  dat_cre DATETIME DEFAULT CURRENT_TIMESTAMP,
  dat_mod DATETIME DEFAULT CURRENT_TIMESTAMP
);
