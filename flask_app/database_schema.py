"""Schéma de création des tables SQLite utilisé par database.init_db."""

SCHEMA_SQL = r'''
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
    '''
