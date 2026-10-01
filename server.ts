import express from 'express';
import path from 'path';
import { createServer as createViteServer } from 'vite';
import { db, initDatabase } from './server/db.ts';
import {
  testOracleConnection,
  executeOracleSync,
  getOracleSyncHistory,
  generateOracleSqlScript
} from './server/oracleSync.ts';

// Initialize the SQLite database and seed initial reference data
initDatabase();

const app = express();
const PORT = 3000;

// Body parsers with generous limit for equipment images (base64)
app.use(express.json({ limit: '20mb' }));
app.use(express.urlencoded({ extended: true, limit: '20mb' }));

// -------------------------------------------------------------
// REST API ROUTES
// -------------------------------------------------------------

// 1. Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// 2. Reference data (Structures, Types, Modèles, Utilisateurs, Lieux de réparation, Paramètres matériel, Admins)
app.get('/api/references', (req, res) => {
  try {
    const structures = db.prepare("SELECT * FROM structures WHERE archiv = 'N' ORDER BY lib_str").all();
    const types = db.prepare("SELECT * FROM type_mat WHERE archiv = 'N' ORDER BY lib_typ_mat").all();
    const modeles = db.prepare(`
      SELECT m.*, t.lib_typ_mat as type_lib, t.cod_typ_mat as type_code
      FROM model_mat m
      LEFT JOIN type_mat t ON m.id_typ_mat = t.id_typ_mat
      WHERE m.archiv = 'N'
      ORDER BY m.marque_mat, m.model_mat
    `).all();
    const utilisateurs = db.prepare(`
      SELECT u.*, s.lib_str as structure_nom, s.cod_str as structure_code
      FROM utilisateurs u
      LEFT JOIN structures s ON u.id_str_mere = s.id_str
      WHERE u.archiv = 'N'
      ORDER BY u.nom_uti, u.pnom_uti
    `).all();
    const lieuxReparation = db.prepare("SELECT * FROM lieu_rep WHERE archiv = 'N' ORDER BY nom_lieu_rep").all();
    const parametres = db.prepare("SELECT * FROM parametres_materiel WHERE archiv = 'N' ORDER BY categorie, ordre, id_param").all();
    const admins = db.prepare("SELECT id_adm, username, nom_complet, email, role, is_active, dat_cre FROM administrateurs WHERE is_active = 1").all();

    const rawTypeParametres = db.prepare(`
      SELECT p.*, t.cod_typ_mat as type_code, t.lib_typ_mat as type_lib
      FROM parametre_type_mat p
      JOIN type_mat t ON p.id_typ_mat = t.id_typ_mat
      WHERE p.archiv = 'N'
      ORDER BY p.id_typ_mat, p.ordre, p.id_param_type
    `).all() as any[];

    const typeParametres = rawTypeParametres.map(p => {
      let options_predefinies = [];
      if (p.options_predefinies) {
        try {
          options_predefinies = JSON.parse(p.options_predefinies);
        } catch {
          options_predefinies = p.options_predefinies.split(',').map((s: string) => s.trim());
        }
      }
      return {
        ...p,
        options_predefinies
      };
    });

    res.json({
      structures,
      types,
      modeles,
      utilisateurs,
      lieuxReparation,
      parametres,
      typeParametres,
      admins,
    });
  } catch (error: any) {
    console.error('Error fetching references:', error);
    res.status(500).json({ error: error.message });
  }
});

// 3. Real-time Dashboard KPIs & Statistics
app.get('/api/stats', (req, res) => {
  try {
    const totalEquipements = (db.prepare("SELECT COUNT(*) as count FROM materiel WHERE archiv = 'N'").get() as any).count;
    const operationnels = (db.prepare("SELECT COUNT(*) as count FROM materiel WHERE etat_mat = 'OP' AND archiv = 'N'").get() as any).count;
    const enPanne = (db.prepare("SELECT COUNT(*) as count FROM materiel WHERE etat_mat = 'PA' AND archiv = 'N'").get() as any).count;
    const enReparation = (db.prepare("SELECT COUNT(*) as count FROM materiel WHERE etat_mat = 'RE' AND archiv = 'N'").get() as any).count;
    const reformes = (db.prepare("SELECT COUNT(*) as count FROM materiel WHERE etat_mat = 'SO' AND archiv = 'N'").get() as any).count;

    const pannesActives = (db.prepare("SELECT COUNT(*) as count FROM panne WHERE eta_pan IN ('EC', 'AT') AND archiv = 'N'").get() as any).count;
    const pannesResolues = (db.prepare("SELECT COUNT(*) as count FROM panne WHERE eta_pan = 'RP' AND archiv = 'N'").get() as any).count;

    const coutTotalReparations = (db.prepare("SELECT COALESCE(SUM(cout_rep), 0) as total FROM panne WHERE archiv = 'N'").get() as any).total;
    const valeurTotaleParc = (db.prepare("SELECT COALESCE(SUM(valeur_acq), 0) as total FROM materiel WHERE archiv = 'N'").get() as any).total;

    // Répartition par type de matériel
    const repartitionTypes = db.prepare(`
      SELECT t.lib_typ_mat as type, COUNT(m.id_mat) as count
      FROM type_mat t
      LEFT JOIN materiel m ON t.id_typ_mat = m.id_typ_mat AND m.archiv = 'N'
      GROUP BY t.id_typ_mat
      ORDER BY count DESC
    `).all();

    // Répartition par structure / direction
    const repartitionStructures = db.prepare(`
      SELECT s.cod_str as code, s.lib_str as label, COUNT(m.id_mat) as count
      FROM structures s
      LEFT JOIN materiel m ON s.id_str = m.id_str AND m.archiv = 'N'
      GROUP BY s.id_str
      ORDER BY count DESC
    `).all();

    // Répartition par état
    const repartitionEtats = [
      { label: 'Opérationnel', code: 'OP', count: operationnels, color: '#10B981' },
      { label: 'En Panne', code: 'PA', count: enPanne, color: '#EF4444' },
      { label: 'En Réparation', code: 'RE', count: enReparation, color: '#F59E0B' },
      { label: 'Réformé / Sorti', code: 'SO', count: reformes, color: '#6B7280' },
    ];

    // Dernières pannes récentes pour flux en direct
    const fluxPannesRecentes = db.prepare(`
      SELECT p.*, m.num_inv, m.num_ser, mod.marque_mat, mod.model_mat,
             t.lib_typ_mat, s.cod_str, u.nom_uti, u.pnom_uti
      FROM panne p
      JOIN materiel m ON p.id_mat = m.id_mat
      LEFT JOIN model_mat mod ON m.id_model_mat = mod.id_model_mat
      LEFT JOIN type_mat t ON m.id_typ_mat = t.id_typ_mat
      LEFT JOIN structures s ON p.id_str = s.id_str
      LEFT JOIN utilisateurs u ON m.id_uti = u.id_uti
      WHERE p.archiv = 'N'
      ORDER BY p.id_pan DESC
      LIMIT 5
    `).all();

    const tauxDisponibilite = totalEquipements > 0
      ? Math.round((operationnels / totalEquipements) * 100)
      : 100;

    res.json({
      totalEquipements,
      operationnels,
      enPanne,
      enReparation,
      reformes,
      pannesActives,
      pannesResolues,
      coutTotalReparations,
      valeurTotaleParc,
      tauxDisponibilite,
      repartitionTypes,
      repartitionStructures,
      repartitionEtats,
      fluxPannesRecentes,
    });
  } catch (error: any) {
    console.error('Error calculating stats:', error);
    res.status(500).json({ error: error.message });
  }
});

// 4. MATÉRIEL (Équipements) - CRUD
app.get('/api/materiels', (req, res) => {
  try {
    const { search, structure, type, etat } = req.query;

    let query = `
      SELECT m.*,
             s.cod_str as structure_code, s.lib_str as structure_nom,
             t.cod_typ_mat as type_code, t.lib_typ_mat as type_nom,
             mod.model_mat,
             u.nom_uti, u.pnom_uti, u.mail_uti, u.ad_uti
      FROM materiel m
      LEFT JOIN structures s ON m.id_str = s.id_str
      LEFT JOIN type_mat t ON m.id_typ_mat = t.id_typ_mat
      LEFT JOIN model_mat mod ON m.id_model_mat = mod.id_model_mat
      LEFT JOIN utilisateurs u ON m.id_uti = u.id_uti
      WHERE m.archiv = 'N'
    `;

    const params: any[] = [];

    if (structure) {
      query += ` AND m.id_str = ?`;
      params.push(structure);
    }
    if (type) {
      query += ` AND m.id_typ_mat = ?`;
      params.push(type);
    }
    if (etat) {
      query += ` AND m.etat_mat = ?`;
      params.push(etat);
    }
    if (search) {
      query += ` AND (
        m.num_inv LIKE ? OR
        m.num_ser LIKE ? OR
        m.ordi LIKE ? OR
        m.ip LIKE ? OR
        mod.marque_mat LIKE ? OR
        mod.model_mat LIKE ? OR
        u.nom_uti LIKE ? OR
        u.pnom_uti LIKE ?
      )`;
      const term = `%${search}%`;
      params.push(term, term, term, term, term, term, term, term);
    }

    query += ` ORDER BY m.id_mat DESC`;

    const items = db.prepare(query).all(...params);
    res.json(items);
  } catch (error: any) {
    console.error('Error loading equipment:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/materiels/:id', (req, res) => {
  try {
    const id = req.params.id;
    const item = db.prepare(`
      SELECT m.*,
             s.cod_str as structure_code, s.lib_str as structure_nom,
             t.cod_typ_mat as type_code, t.lib_typ_mat as type_nom,
             mod.model_mat,
             u.nom_uti, u.pnom_uti, u.mail_uti, u.ad_uti
      FROM materiel m
      LEFT JOIN structures s ON m.id_str = s.id_str
      LEFT JOIN type_mat t ON m.id_typ_mat = t.id_typ_mat
      LEFT JOIN model_mat mod ON m.id_model_mat = mod.id_model_mat
      LEFT JOIN utilisateurs u ON m.id_uti = u.id_uti
      WHERE m.id_mat = ? AND m.archiv = 'N'
    `).get(id);

    if (!item) {
      return res.status(404).json({ error: 'Équipement non trouvé' });
    }

    // Historique des pannes associées
    const pannes = db.prepare(`
      SELECT p.*, l.nom_lieu_rep
      FROM panne p
      LEFT JOIN lieu_rep l ON p.id_lieu_rep = l.id_lieu_rep
      WHERE p.id_mat = ? AND p.archiv = 'N'
      ORDER BY p.id_pan DESC
    `).all(id);

    // Historique des affectations
    const affectations = db.prepare(`
      SELECT a.*, s.lib_str as structure_nom, u.nom_uti, u.pnom_uti
      FROM affect_mat a
      LEFT JOIN structures s ON a.id_str = s.id_str
      LEFT JOIN utilisateurs u ON a.id_uti = u.id_uti
      WHERE a.id_mat = ? AND a.archiv = 'N'
      ORDER BY a.id_aff_mat DESC
    `).all(id);

    res.json({
      materiel: item,
      pannes,
      affectations,
    });
  } catch (error: any) {
    console.error('Error fetching materiel detail:', error);
    res.status(500).json({ error: error.message });
  }
});

app.post('/api/materiels', (req, res) => {
  try {
    const {
      id_str, id_typ_mat, id_model_mat, marque_mat, num_inv, num_ser,
      dat_acq, dat_mes, etat_mat, obs_mat,
      ram, disk, cpu, freq_cpu, se, net, ordi, ip, id_uti,
      image_url, valeur_acq, specs_json
    } = req.body;

    // Numéro d'inventaire automatique si non renseigné
    let finalNumInv = num_inv;
    if (!finalNumInv || finalNumInv.trim() === '') {
      const year = new Date().getFullYear();
      const lastId = (db.prepare('SELECT MAX(id_mat) as max_id FROM materiel').get() as any).max_id || 0;
      finalNumInv = `INV-${year}-${String(lastId + 1).padStart(3, '0')}`;
    }

    const specsStr = typeof specs_json === 'object' && specs_json !== null
      ? JSON.stringify(specs_json)
      : (specs_json || null);

    if (marque_mat) {
      const brandRef = db.prepare(
        "SELECT id_param FROM parametres_materiel WHERE categorie = 'marque' AND archiv = 'N' AND LOWER(TRIM(valeur)) = LOWER(TRIM(?))"
      ).get(marque_mat);
      if (!brandRef) {
        return res.status(400).json({ error: 'La marque sélectionnée n’existe pas dans le référentiel des marques.' });
      }
    }

    const stmt = db.prepare(`
      INSERT INTO materiel (
        id_str, id_typ_mat, id_model_mat, marque_mat, num_inv, num_ser,
        dat_acq, dat_mes, etat_mat, obs_mat,
        ram, disk, cpu, freq_cpu, se, net, ordi, ip, id_uti,
        image_url, valeur_acq, specs_json, dat_cre, dat_mod
      ) VALUES (
        ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?, ?, ?, ?,
        ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
      )
    `);

    const result = stmt.run(
      id_str || null,
      id_typ_mat || null,
      id_model_mat || null,
      marque_mat || (id_model_mat ? (db.prepare('SELECT marque_mat FROM model_mat WHERE id_model_mat = ?').get(id_model_mat) as any)?.marque_mat : null) || null,
      finalNumInv,
      num_ser || `SN-${Date.now().toString().slice(-6)}`,
      dat_acq || new Date().toISOString().split('T')[0],
      dat_mes || new Date().toISOString().split('T')[0],
      etat_mat || 'OP',
      obs_mat || '',
      ram ? parseInt(ram) : null,
      disk ? parseInt(disk) : null,
      cpu || null,
      freq_cpu || null,
      se || null,
      net || null,
      ordi || null,
      ip || null,
      id_uti || null,
      image_url || null,
      valeur_acq ? parseFloat(valeur_acq) : 0,
      specsStr
    );

    const insertedId = result.lastInsertRowid;

    // Enregistrer l'affectation initiale si utilisateur ou structure sélectionné
    if (id_uti || id_str) {
      db.prepare(`
        INSERT INTO affect_mat (id_mat, id_str, id_model_mat, id_typ_mat, num_inv, num_ser, id_uti, obs_aff)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `).run(insertedId, id_str || null, id_model_mat || null, id_typ_mat || null, finalNumInv, num_ser, id_uti || null, 'Affectation initiale lors de la création');
    }

    res.status(201).json({ id: insertedId, message: 'Équipement créé avec succès' });
  } catch (error: any) {
    console.error('Error creating equipment:', error);
    res.status(500).json({ error: error.message });
  }
});

app.put('/api/materiels/:id', (req, res) => {
  try {
    const id = req.params.id;
    const {
      id_str, id_typ_mat, id_model_mat, marque_mat, num_inv, num_ser,
      dat_acq, dat_mes, etat_mat, obs_mat,
      ram, disk, cpu, freq_cpu, se, net, ordi, ip, id_uti,
      image_url, valeur_acq, dat_sortie, motif_sortie, specs_json
    } = req.body;

    const existing = db.prepare('SELECT * FROM materiel WHERE id_mat = ?').get(id) as any;
    if (!existing) {
      return res.status(404).json({ error: 'Équipement non trouvé' });
    }

    const specsStr = specs_json !== undefined
      ? (typeof specs_json === 'object' && specs_json !== null ? JSON.stringify(specs_json) : specs_json)
      : existing.specs_json;

    if (marque_mat) {
      const brandRef = db.prepare(
        "SELECT id_param FROM parametres_materiel WHERE categorie = 'marque' AND archiv = 'N' AND LOWER(TRIM(valeur)) = LOWER(TRIM(?))"
      ).get(marque_mat);
      if (!brandRef) {
        return res.status(400).json({ error: 'La marque sélectionnée n’existe pas dans le référentiel des marques.' });
      }
    }

    db.prepare(`
      UPDATE materiel SET
        id_str = ?, id_typ_mat = ?, id_model_mat = ?, marque_mat = ?, num_inv = ?, num_ser = ?,
        dat_acq = ?, dat_mes = ?, etat_mat = ?, obs_mat = ?,
        ram = ?, disk = ?, cpu = ?, freq_cpu = ?, se = ?, net = ?, ordi = ?, ip = ?, id_uti = ?,
        image_url = ?, valeur_acq = ?, dat_sortie = ?, motif_sortie = ?, specs_json = ?,
        dat_mod = CURRENT_TIMESTAMP
      WHERE id_mat = ?
    `).run(
      id_str || null,
      id_typ_mat || null,
      id_model_mat || null,
      marque_mat || (id_model_mat ? (db.prepare('SELECT marque_mat FROM model_mat WHERE id_model_mat = ?').get(id_model_mat) as any)?.marque_mat : existing.marque_mat) || existing.marque_mat || null,
      num_inv || existing.num_inv,
      num_ser || existing.num_ser,
      dat_acq || existing.dat_acq,
      dat_mes || existing.dat_mes,
      etat_mat || existing.etat_mat,
      obs_mat !== undefined ? obs_mat : existing.obs_mat,
      ram ? parseInt(ram) : existing.ram,
      disk ? parseInt(disk) : existing.disk,
      cpu !== undefined ? cpu : existing.cpu,
      freq_cpu !== undefined ? freq_cpu : existing.freq_cpu,
      se !== undefined ? se : existing.se,
      net !== undefined ? net : existing.net,
      ordi !== undefined ? ordi : existing.ordi,
      ip !== undefined ? ip : existing.ip,
      id_uti || null,
      image_url !== undefined ? image_url : existing.image_url,
      valeur_acq !== undefined ? parseFloat(valeur_acq) : existing.valeur_acq,
      dat_sortie || null,
      motif_sortie || null,
      specsStr,
      id
    );

    // Si l'utilisateur ou la structure a changé, enregistrer dans l'historique
    if (id_uti && id_uti !== existing.id_uti) {
      db.prepare(`
        INSERT INTO affect_mat (id_mat, id_str, id_model_mat, id_typ_mat, num_inv, num_ser, id_uti, obs_aff)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `).run(id, id_str || existing.id_str, id_model_mat || existing.id_model_mat, id_typ_mat || existing.id_typ_mat, num_inv || existing.num_inv, num_ser || existing.num_ser, id_uti, 'Réaffectation utilisateur');
    }

    res.json({ message: 'Équipement mis à jour avec succès' });
  } catch (error: any) {
    console.error('Error updating equipment:', error);
    res.status(500).json({ error: error.message });
  }
});

app.delete('/api/materiels/:id', (req, res) => {
  try {
    const id = req.params.id;
    db.prepare("UPDATE materiel SET archiv = 'O', dat_mod = CURRENT_TIMESTAMP WHERE id_mat = ?").run(id);
    res.json({ message: 'Équipement archivé avec succès' });
  } catch (error: any) {
    console.error('Error archiving equipment:', error);
    res.status(500).json({ error: error.message });
  }
});

// 5. PANNES & INTERVENTIONS - CRUD + RAPPORT D'INTERVENTION
app.get('/api/pannes', (req, res) => {
  try {
    const { status, type, search } = req.query;

    let query = `
      SELECT p.*,
             m.num_inv, m.num_ser, m.ordi, m.ip, m.image_url as materiel_image,
             mod.marque_mat, mod.model_mat,
             t.lib_typ_mat,
             s.cod_str as structure_code, s.lib_str as structure_nom,
             l.nom_lieu_rep, l.adr_lieu_rep, l.tel_lieu_rep,
             u.nom_uti, u.pnom_uti, u.mail_uti
      FROM panne p
      JOIN materiel m ON p.id_mat = m.id_mat
      LEFT JOIN model_mat mod ON m.id_model_mat = mod.id_model_mat
      LEFT JOIN type_mat t ON m.id_typ_mat = t.id_typ_mat
      LEFT JOIN structures s ON p.id_str = s.id_str
      LEFT JOIN lieu_rep l ON p.id_lieu_rep = l.id_lieu_rep
      LEFT JOIN utilisateurs u ON m.id_uti = u.id_uti
      WHERE p.archiv = 'N'
    `;

    const params: any[] = [];

    if (status) {
      query += ` AND p.eta_pan = ?`;
      params.push(status);
    }
    if (type) {
      query += ` AND p.tp = ?`;
      params.push(type);
    }
    if (search) {
      query += ` AND (
        p.diag_pan LIKE ? OR
        p.obs_rep LIKE ? OR
        m.num_inv LIKE ? OR
        m.num_ser LIKE ? OR
        mod.model_mat LIKE ? OR
        p.technicien LIKE ? OR
        u.nom_uti LIKE ?
      )`;
      const term = `%${search}%`;
      params.push(term, term, term, term, term, term, term);
    }

    query += ` ORDER BY p.id_pan DESC`;

    const pannes = db.prepare(query).all(...params);
    res.json(pannes);
  } catch (error: any) {
    console.error('Error fetching pannes:', error);
    res.status(500).json({ error: error.message });
  }
});

app.get('/api/pannes/:id', (req, res) => {
  try {
    const id = req.params.id;
    const panne = db.prepare(`
      SELECT p.*,
             m.num_inv, m.num_ser, m.ordi, m.ip, m.ram, m.disk, m.cpu, m.se, m.image_url as materiel_image,
             mod.marque_mat, mod.model_mat,
             t.lib_typ_mat,
             s.cod_str as structure_code, s.lib_str as structure_nom,
             l.nom_lieu_rep, l.adr_lieu_rep, l.tel_lieu_rep, l.contact_rep,
             u.nom_uti, u.pnom_uti, u.mail_uti, u.ad_uti
      FROM panne p
      JOIN materiel m ON p.id_mat = m.id_mat
      LEFT JOIN model_mat mod ON m.id_model_mat = mod.id_model_mat
      LEFT JOIN type_mat t ON m.id_typ_mat = t.id_typ_mat
      LEFT JOIN structures s ON p.id_str = s.id_str
      LEFT JOIN lieu_rep l ON p.id_lieu_rep = l.id_lieu_rep
      LEFT JOIN utilisateurs u ON m.id_uti = u.id_uti
      WHERE p.id_pan = ? AND p.archiv = 'N'
    `).get(id);

    if (!panne) {
      return res.status(404).json({ error: 'Panne non trouvée' });
    }

    res.json(panne);
  } catch (error: any) {
    console.error('Error fetching single panne:', error);
    res.status(500).json({ error: error.message });
  }
});

// Déclarer une nouvelle panne (met à jour automatiquement l'état de l'équipement en 'PA' ou 'RE')
app.post('/api/pannes', (req, res) => {
  try {
    const {
      id_mat, dat_pan, diag_pan, id_lieu_rep, tp,
      technicien, obs_rep, eta_pan, cout_rep, pieces_remplacees, recommandations
    } = req.body;

    // Récupérer les informations de l'équipement
    const mat = db.prepare('SELECT * FROM materiel WHERE id_mat = ?').get(id_mat) as any;
    if (!mat) {
      return res.status(400).json({ error: 'Équipement invalide' });
    }

    const stmt = db.prepare(`
      INSERT INTO panne (
        id_mat, id_str, id_typ_mat, id_model_mat, num_inv, num_ser,
        dat_pan, diag_pan, dat_env_rep, id_lieu_rep, obs_rep,
        eta_pan, tp, technicien, cout_rep, pieces_remplacees, recommandations,
        dat_cre, dat_mod
      ) VALUES (
        ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?,
        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
      )
    `);

    const result = stmt.run(
      id_mat,
      mat.id_str,
      mat.id_typ_mat,
      mat.id_model_mat,
      mat.num_inv,
      mat.num_ser,
      dat_pan || new Date().toISOString().split('T')[0],
      diag_pan,
      new Date().toISOString().split('T')[0],
      id_lieu_rep || null,
      obs_rep || null,
      eta_pan || 'EC',
      tp || 'MAT',
      technicien || 'Technicien Support',
      cout_rep ? parseFloat(cout_rep) : 0,
      pieces_remplacees || null,
      recommandations || null
    );

    // Mettre à jour l'état du matériel en panne ('PA') ou en réparation ('RE')
    const nouvelEtatMat = eta_pan === 'AT' ? 'RE' : 'PA';
    db.prepare('UPDATE materiel SET etat_mat = ?, dat_mod = CURRENT_TIMESTAMP WHERE id_mat = ?').run(nouvelEtatMat, id_mat);

    res.status(201).json({ id: result.lastInsertRowid, message: 'Incident enregistré avec succès' });
  } catch (error: any) {
    console.error('Error creating panne:', error);
    res.status(500).json({ error: error.message });
  }
});

// Mettre à jour une panne (si clôturée en 'RP', l'équipement repasse automatiquement en 'OP' opérationnel!)
app.put('/api/pannes/:id', (req, res) => {
  try {
    const id = req.params.id;
    const {
      diag_pan, id_lieu_rep, obs_rep, eta_pan, dat_ret_rep,
      tp, technicien, cout_rep, pieces_remplacees, recommandations
    } = req.body;

    const existing = db.prepare('SELECT * FROM panne WHERE id_pan = ?').get(id) as any;
    if (!existing) {
      return res.status(404).json({ error: 'Panne non trouvée' });
    }

    const isResolved = eta_pan === 'RP';
    const finalRetDate = isResolved && !dat_ret_rep
      ? new Date().toISOString().split('T')[0]
      : (dat_ret_rep || existing.dat_ret_rep);

    db.prepare(`
      UPDATE panne SET
        diag_pan = ?,
        id_lieu_rep = ?,
        obs_rep = ?,
        eta_pan = ?,
        dat_ret_rep = ?,
        tp = ?,
        technicien = ?,
        cout_rep = ?,
        pieces_remplacees = ?,
        recommandations = ?,
        dat_mod = CURRENT_TIMESTAMP
      WHERE id_pan = ?
    `).run(
      diag_pan !== undefined ? diag_pan : existing.diag_pan,
      id_lieu_rep || existing.id_lieu_rep,
      obs_rep !== undefined ? obs_rep : existing.obs_rep,
      eta_pan || existing.eta_pan,
      finalRetDate,
      tp || existing.tp,
      technicien || existing.technicien,
      cout_rep !== undefined ? parseFloat(cout_rep) : existing.cout_rep,
      pieces_remplacees !== undefined ? pieces_remplacees : existing.pieces_remplacees,
      recommandations !== undefined ? recommandations : existing.recommandations,
      id
    );

    // Mettre à jour l'état du matériel en conséquence
    if (eta_pan === 'RP') {
      // Réparé -> Matériel redevient opérationnel
      db.prepare("UPDATE materiel SET etat_mat = 'OP', dat_mod = CURRENT_TIMESTAMP WHERE id_mat = ?").run(existing.id_mat);
    } else if (eta_pan === 'NR') {
      // Non réparable -> Réformé
      db.prepare("UPDATE materiel SET etat_mat = 'SO', dat_sortie = CURRENT_TIMESTAMP, motif_sortie = 'Non réparable suite panne N°' || ?, dat_mod = CURRENT_TIMESTAMP WHERE id_mat = ?").run(id, existing.id_mat);
    } else if (eta_pan === 'AT') {
      db.prepare("UPDATE materiel SET etat_mat = 'RE', dat_mod = CURRENT_TIMESTAMP WHERE id_mat = ?").run(existing.id_mat);
    }

    res.json({ message: 'Panne mise à jour avec succès' });
  } catch (error: any) {
    console.error('Error updating panne:', error);
    res.status(500).json({ error: error.message });
  }
});

// Endpoint officiel: Rapport d'intervention formatté
app.get('/api/pannes/:id/report', (req, res) => {
  try {
    const id = req.params.id;
    const panne = db.prepare(`
      SELECT p.*,
             m.num_inv, m.num_ser, m.ordi, m.ip, m.ram, m.disk, m.cpu, m.freq_cpu, m.se, m.net, m.image_url as materiel_image,
             mod.marque_mat, mod.model_mat,
             t.lib_typ_mat,
             s.cod_str as structure_code, s.lib_str as structure_nom,
             l.nom_lieu_rep, l.adr_lieu_rep, l.tel_lieu_rep, l.contact_rep,
             u.nom_uti, u.pnom_uti, u.mail_uti, u.ad_uti
      FROM panne p
      JOIN materiel m ON p.id_mat = m.id_mat
      LEFT JOIN model_mat mod ON m.id_model_mat = mod.id_model_mat
      LEFT JOIN type_mat t ON m.id_typ_mat = t.id_typ_mat
      LEFT JOIN structures s ON p.id_str = s.id_str
      LEFT JOIN lieu_rep l ON p.id_lieu_rep = l.id_lieu_rep
      LEFT JOIN utilisateurs u ON m.id_uti = u.id_uti
      WHERE p.id_pan = ?
    `).get(id) as any;

    if (!panne) {
      return res.status(404).json({ error: 'Rapport introuvable' });
    }

    const report = {
      numeroRapport: `RPT-INT-${new Date(panne.dat_pan).getFullYear()}-${String(panne.id_pan).padStart(4, '0')}`,
      dateGeneration: new Date().toLocaleDateString('fr-FR', {
        year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
      }),
      societe: {
        nom: 'DIRECTION DES SYSTÈMES D\'INFORMATION',
        sousTitre: 'Service Gestion de Parc & Support Technique',
        contact: 'support-it@societe.com | Tél: 01 40 50 60 00',
      },
      intervention: {
        id: panne.id_pan,
        datePanne: panne.dat_pan,
        dateEnvoi: panne.dat_env_rep,
        dateRetour: panne.dat_ret_rep,
        etat: panne.eta_pan === 'RP' ? 'Clôturée - Équipement Réparé' : (panne.eta_pan === 'AT' ? 'En attente de pièces détachées' : 'En cours d\'expertise / réparation'),
        statutCode: panne.eta_pan,
        typePanne: panne.tp === 'MAT' ? 'Matériel / Hardware' : (panne.tp === 'LOG' ? 'Système & Logiciel' : (panne.tp === 'RES' ? 'Réseau & Connectivité' : 'Alimentation / Électrique')),
        technicien: panne.technicien || 'Technicien DSI',
        lieu: panne.nom_lieu_rep || 'Atelier Interne DSI',
        cout: panne.cout_rep || 0,
        diagnostic: panne.diag_pan,
        travauxRealises: panne.obs_rep || 'Intervention technique standard selon procédure.',
        piecesRemplacees: panne.pieces_remplacees || 'Aucune pièce remplacée.',
        recommandations: panne.recommandations || 'Effectuer des sauvegardes régulières et signaler toute anomalie.',
      },
      equipement: {
        id: panne.id_mat,
        numInventaire: panne.num_inv,
        numSerie: panne.num_ser,
        type: panne.lib_typ_mat,
        marque: panne.marque_mat,
        modele: panne.model_mat,
        nomMachine: panne.ordi || 'N/A',
        adresseIp: panne.ip || 'DHCP',
        systeme: panne.se || 'Standard',
        processeur: `${panne.cpu || ''} ${panne.freq_cpu ? `(${panne.freq_cpu})` : ''}`,
        memoireRam: panne.ram ? `${panne.ram} Go` : 'N/A',
        stockage: panne.disk ? `${panne.disk} Go SSD/HDD` : 'N/A',
        imageUrl: panne.materiel_image,
      },
      utilisateur: {
        nomComplet: panne.nom_uti ? `${panne.pnom_uti} ${panne.nom_uti}` : 'Non assigné',
        email: panne.mail_uti || 'N/A',
        service: panne.structure_nom || 'Non spécifié',
        codeService: panne.structure_code || 'N/A',
      }
    };

    res.json(report);
  } catch (error: any) {
    console.error('Error generating report:', error);
    res.status(500).json({ error: error.message });
  }
});

// 6. CRUD pour les TABLES DE RÉFÉRENCE (Structures, Utilisateurs, Lieux, Types, Modèles)
app.post('/api/structures', (req, res) => {
  try {
    const { cod_str, lib_str } = req.body;
    if (!cod_str || !lib_str) {
      return res.status(400).json({ error: 'Code et libellé requis' });
    }
    const result = db.prepare('INSERT INTO structures (cod_str, lib_str) VALUES (?, ?)').run(cod_str.trim().toUpperCase(), lib_str.trim());
    res.status(201).json({ id: result.lastInsertRowid, message: 'Structure créée avec succès' });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.put('/api/structures/:id', (req, res) => {
  try {
    const { cod_str, lib_str } = req.body;
    db.prepare('UPDATE structures SET cod_str = ?, lib_str = ?, dat_mod = CURRENT_TIMESTAMP WHERE id_str = ?')
      .run(cod_str.trim().toUpperCase(), lib_str.trim(), req.params.id);
    res.json({ message: 'Structure mise à jour' });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.delete('/api/structures/:id', (req, res) => {
  try {
    db.prepare("UPDATE structures SET archiv = 'O', dat_mod = CURRENT_TIMESTAMP WHERE id_str = ?").run(req.params.id);
    res.json({ message: 'Structure archivée' });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.post('/api/utilisateurs', (req, res) => {
  try {
    const { nom_uti, pnom_uti, mail_uti, ad_uti, id_str_mere } = req.body;
    if (!nom_uti || !pnom_uti) {
      return res.status(400).json({ error: 'Nom et prénom requis' });
    }
    const result = db.prepare(`
      INSERT INTO utilisateurs (nom_uti, pnom_uti, mail_uti, ad_uti, id_str_mere)
      VALUES (?, ?, ?, ?, ?)
    `).run(nom_uti.trim(), pnom_uti.trim(), mail_uti?.trim() || null, ad_uti?.trim() || null, id_str_mere ? parseInt(id_str_mere) : null);
    res.status(201).json({ id: result.lastInsertRowid, message: 'Utilisateur créé' });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.put('/api/utilisateurs/:id', (req, res) => {
  try {
    const { nom_uti, pnom_uti, mail_uti, ad_uti, id_str_mere } = req.body;
    db.prepare(`
      UPDATE utilisateurs SET
        nom_uti = ?, pnom_uti = ?, mail_uti = ?, ad_uti = ?, id_str_mere = ?, dat_mod = CURRENT_TIMESTAMP
      WHERE id_uti = ?
    `).run(nom_uti.trim(), pnom_uti.trim(), mail_uti?.trim() || null, ad_uti?.trim() || null, id_str_mere ? parseInt(id_str_mere) : null, req.params.id);
    res.json({ message: 'Utilisateur mis à jour' });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.delete('/api/utilisateurs/:id', (req, res) => {
  try {
    db.prepare("UPDATE utilisateurs SET archiv = 'O', dat_mod = CURRENT_TIMESTAMP WHERE id_uti = ?").run(req.params.id);
    res.json({ message: 'Utilisateur archivé' });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.post('/api/types', (req, res) => {
  try {
    const { cod_typ_mat, lib_typ_mat } = req.body;
    if (!cod_typ_mat || !lib_typ_mat) {
      return res.status(400).json({ error: 'Code et libellé requis' });
    }
    const result = db.prepare('INSERT INTO type_mat (cod_typ_mat, lib_typ_mat) VALUES (?, ?)').run(cod_typ_mat.trim().toUpperCase(), lib_typ_mat.trim());
    res.status(201).json({ id: result.lastInsertRowid });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.get('/api/modeles', (req, res) => {
  try {
    const modeles = db.prepare(`
      SELECT m.*, t.lib_typ_mat as type_lib, t.cod_typ_mat as type_code
      FROM model_mat m
      LEFT JOIN type_mat t ON m.id_typ_mat = t.id_typ_mat
      WHERE m.archiv = 'N'
      ORDER BY m.marque_mat, m.model_mat
    `).all();
    res.json(modeles);
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.post('/api/modeles', (req, res) => {
  try {
    const {
      marque_mat,
      model_mat,
      id_typ_mat,
      default_cpu,
      default_freq_cpu,
      default_ram,
      default_disk,
      default_se,
      default_net,
      description,
      garantie_mois,
      specs_json
    } = req.body;

    if (!marque_mat || !model_mat) {
      return res.status(400).json({ error: 'Marque et modèle obligatoires' });
    }

    const specsStr = typeof specs_json === 'object' && specs_json !== null
      ? JSON.stringify(specs_json)
      : (specs_json || null);

    const result = db.prepare(`
      INSERT INTO model_mat (
        marque_mat, model_mat, id_typ_mat, default_cpu, default_freq_cpu,
        default_ram, default_disk, default_se, default_net, description, garantie_mois, specs_json
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      marque_mat.trim(),
      model_mat.trim(),
      id_typ_mat ? parseInt(id_typ_mat) : null,
      default_cpu?.trim() || null,
      default_freq_cpu?.trim() || null,
      default_ram ? parseInt(default_ram) : null,
      default_disk ? parseInt(default_disk) : null,
      default_se?.trim() || null,
      default_net?.trim() || null,
      description?.trim() || null,
      garantie_mois ? parseInt(garantie_mois) : 36,
      specsStr
    );

    res.status(201).json({ id: result.lastInsertRowid, message: 'Modèle créé avec succès' });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.put('/api/modeles/:id', (req, res) => {
  try {
    const {
      marque_mat,
      model_mat,
      id_typ_mat,
      default_cpu,
      default_freq_cpu,
      default_ram,
      default_disk,
      default_se,
      default_net,
      description,
      garantie_mois,
      specs_json
    } = req.body;

    if (!marque_mat || !model_mat) {
      return res.status(400).json({ error: 'Marque et modèle obligatoires' });
    }

    const existing = db.prepare('SELECT * FROM model_mat WHERE id_model_mat = ?').get(req.params.id) as any;
    if (!existing) {
      return res.status(404).json({ error: 'Modèle non trouvé' });
    }

    const specsStr = specs_json !== undefined
      ? (typeof specs_json === 'object' && specs_json !== null ? JSON.stringify(specs_json) : specs_json)
      : existing.specs_json;

    db.prepare(`
      UPDATE model_mat SET
        marque_mat = ?,
        model_mat = ?,
        id_typ_mat = ?,
        default_cpu = ?,
        default_freq_cpu = ?,
        default_ram = ?,
        default_disk = ?,
        default_se = ?,
        default_net = ?,
        description = ?,
        garantie_mois = ?,
        specs_json = ?,
        dat_mod = CURRENT_TIMESTAMP
      WHERE id_model_mat = ?
    `).run(
      marque_mat.trim(),
      model_mat.trim(),
      id_typ_mat ? parseInt(id_typ_mat) : null,
      default_cpu?.trim() || null,
      default_freq_cpu?.trim() || null,
      default_ram ? parseInt(default_ram) : null,
      default_disk ? parseInt(default_disk) : null,
      default_se?.trim() || null,
      default_net?.trim() || null,
      description?.trim() || null,
      garantie_mois ? parseInt(garantie_mois) : 36,
      specsStr,
      req.params.id
    );

    res.json({ message: 'Modèle mis à jour avec succès' });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.delete('/api/modeles/:id', (req, res) => {
  try {
    db.prepare("UPDATE model_mat SET archiv = 'O', dat_mod = CURRENT_TIMESTAMP WHERE id_model_mat = ?").run(req.params.id);
    res.json({ message: 'Modèle archivé avec succès' });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.post('/api/lieux', (req, res) => {
  try {
    const { nom_lieu_rep, adr_lieu_rep, tel_lieu_rep, contact_rep } = req.body;
    if (!nom_lieu_rep || !nom_lieu_rep.trim()) {
      return res.status(400).json({ error: 'Le nom du centre est requis' });
    }
    const result = db.prepare('INSERT INTO lieu_rep (nom_lieu_rep, adr_lieu_rep, tel_lieu_rep, contact_rep) VALUES (?, ?, ?, ?)').run(
      nom_lieu_rep.trim(),
      adr_lieu_rep?.trim() || null,
      tel_lieu_rep?.trim() || null,
      contact_rep?.trim() || null
    );
    res.status(201).json({ id: result.lastInsertRowid });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

// 7. GESTION DES ADMINISTRATEURS (Accès Administrateur & Ajout de nouveaux admins)
app.get('/api/admins', (req, res) => {
  try {
    const admins = db.prepare(`
      SELECT id_adm, username, nom_complet, email, role, is_active, dat_cre, dat_mod
      FROM administrateurs
      ORDER BY id_adm ASC
    `).all();
    res.json(admins);
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.post('/api/admins', (req, res) => {
  try {
    const { username, nom_complet, email, password, role } = req.body;
    if (!username || !nom_complet || !password) {
      return res.status(400).json({ error: 'Identifiant, nom complet et mot de passe requis' });
    }

    // Check unique username
    const existing = db.prepare('SELECT id_adm FROM administrateurs WHERE username = ?').get(username.trim().toLowerCase());
    if (existing) {
      return res.status(400).json({ error: 'Cet identifiant administrateur est déjà utilisé' });
    }

    const result = db.prepare(`
      INSERT INTO administrateurs (username, nom_complet, email, password, role, is_active)
      VALUES (?, ?, ?, ?, ?, 1)
    `).run(
      username.trim().toLowerCase(),
      nom_complet.trim(),
      email?.trim() || null,
      password,
      role || 'admin'
    );

    res.status(201).json({
      id: result.lastInsertRowid,
      message: 'Nouvel administrateur ajouté avec succès',
      admin: {
        id_adm: result.lastInsertRowid,
        username: username.trim().toLowerCase(),
        nom_complet: nom_complet.trim(),
        email: email?.trim() || null,
        role: role || 'admin',
        is_active: 1
      }
    });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.put('/api/admins/:id', (req, res) => {
  try {
    const id = req.params.id;
    const { nom_complet, email, password, role, is_active } = req.body;

    const current = db.prepare('SELECT * FROM administrateurs WHERE id_adm = ?').get(id) as any;
    if (!current) {
      return res.status(404).json({ error: 'Administrateur non trouvé' });
    }

    const updatedPassword = password && password.trim() !== '' ? password : current.password;

    db.prepare(`
      UPDATE administrateurs SET
        nom_complet = ?,
        email = ?,
        password = ?,
        role = ?,
        is_active = ?,
        dat_mod = CURRENT_TIMESTAMP
      WHERE id_adm = ?
    `).run(
      nom_complet !== undefined ? nom_complet.trim() : current.nom_complet,
      email !== undefined ? email.trim() : current.email,
      updatedPassword,
      role !== undefined ? role : current.role,
      is_active !== undefined ? is_active : current.is_active,
      id
    );

    res.json({ message: 'Administrateur mis à jour' });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.delete('/api/admins/:id', (req, res) => {
  try {
    const id = req.params.id;
    // Don't delete if it's the last super_admin
    const countSuper = (db.prepare("SELECT COUNT(*) as count FROM administrateurs WHERE role = 'super_admin' AND is_active = 1").get() as any).count;
    const target = db.prepare('SELECT role FROM administrateurs WHERE id_adm = ?').get(id) as any;

    if (target?.role === 'super_admin' && countSuper <= 1) {
      return res.status(400).json({ error: 'Impossible de supprimer le dernier Super Administrateur actif' });
    }

    db.prepare('DELETE FROM administrateurs WHERE id_adm = ?').run(id);
    res.json({ message: 'Administrateur supprimé' });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.post('/api/admins/login', (req, res) => {
  try {
    const { username, password } = req.body;
    if (!username || !password) {
      return res.status(400).json({ error: 'Identifiant et mot de passe requis' });
    }

    const admin = db.prepare(`
      SELECT id_adm, username, nom_complet, email, role, is_active
      FROM administrateurs
      WHERE username = ? AND password = ?
    `).get(username.trim().toLowerCase(), password) as any;

    if (!admin) {
      return res.status(401).json({ error: 'Identifiants administrateur incorrects' });
    }

    if (!admin.is_active) {
      return res.status(403).json({ error: 'Ce compte administrateur a été désactivé' });
    }

    res.json({ success: true, admin });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

// 8. GESTION DES PARAMÈTRES MATÉRIELS (CPU, RAM, SE, Disque)
app.get('/api/parametres', (req, res) => {
  try {
    const params = db.prepare("SELECT * FROM parametres_materiel WHERE archiv = 'N' ORDER BY categorie, ordre, id_param").all();
    res.json(params);
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.post('/api/parametres', (req, res) => {
  try {
    const { categorie, valeur, description, ordre } = req.body;
    if (!categorie || !valeur) {
      return res.status(400).json({ error: 'Catégorie et valeur requises' });
    }

    const result = db.prepare(`
      INSERT INTO parametres_materiel (categorie, valeur, description, ordre)
      VALUES (?, ?, ?, ?)
    `).run(categorie.trim().toLowerCase(), valeur.trim(), description?.trim() || null, ordre ? parseInt(ordre) : 0);

    res.status(201).json({ id: result.lastInsertRowid, message: 'Paramètre ajouté avec succès' });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.put('/api/parametres/:id', (req, res) => {
  try {
    const { valeur, description, ordre } = req.body;
    db.prepare(`
      UPDATE parametres_materiel SET
        valeur = ?, description = ?, ordre = ?
      WHERE id_param = ?
    `).run(valeur.trim(), description?.trim() || null, ordre ? parseInt(ordre) : 0, req.params.id);

    res.json({ message: 'Paramètre mis à jour' });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.delete('/api/parametres/:id', (req, res) => {
  try {
    db.prepare("UPDATE parametres_materiel SET archiv = 'O' WHERE id_param = ?").run(req.params.id);
    res.json({ message: 'Paramètre archivé' });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

// 8b. GESTION DES PARAMÈTRES SPÉCIFIQUES PAR TYPE D'ÉQUIPEMENT (parametre_type_mat)
app.get('/api/type-parametres', (req, res) => {
  try {
    const { id_typ_mat } = req.query;
    let query = `
      SELECT p.*, t.cod_typ_mat as type_code, t.lib_typ_mat as type_lib
      FROM parametre_type_mat p
      JOIN type_mat t ON p.id_typ_mat = t.id_typ_mat
      WHERE p.archiv = 'N'
    `;
    const params: any[] = [];
    if (id_typ_mat) {
      query += ` AND p.id_typ_mat = ?`;
      params.push(id_typ_mat);
    }
    query += ` ORDER BY p.id_typ_mat, p.ordre, p.id_param_type`;

    const rawList = db.prepare(query).all(...params) as any[];
    const list = rawList.map(p => {
      let options_predefinies = [];
      if (p.options_predefinies) {
        try {
          options_predefinies = JSON.parse(p.options_predefinies);
        } catch {
          options_predefinies = p.options_predefinies.split(',').map((s: string) => s.trim());
        }
      }
      return {
        ...p,
        options_predefinies
      };
    });

    res.json(list);
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.post('/api/type-parametres', (req, res) => {
  try {
    const {
      id_typ_mat,
      code_param,
      libelle_param,
      categorie_groupe,
      type_champ,
      unite,
      options_predefinies,
      description,
      ordre
    } = req.body;

    if (!id_typ_mat || !code_param || !libelle_param) {
      return res.status(400).json({ error: 'Type de matériel, code et libellé requis' });
    }

    const optionsStr = Array.isArray(options_predefinies)
      ? JSON.stringify(options_predefinies)
      : (options_predefinies || null);

    const result = db.prepare(`
      INSERT INTO parametre_type_mat (
        id_typ_mat, code_param, libelle_param, categorie_groupe,
        type_champ, unite, options_predefinies, description, ordre
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      parseInt(id_typ_mat),
      code_param.trim().toLowerCase(),
      libelle_param.trim(),
      categorie_groupe?.trim() || null,
      type_champ || 'text',
      unite?.trim() || null,
      optionsStr,
      description?.trim() || null,
      ordre ? parseInt(ordre) : 0
    );

    res.status(201).json({ id: result.lastInsertRowid, message: 'Paramètre spécifique créé avec succès' });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.put('/api/type-parametres/:id', (req, res) => {
  try {
    const {
      libelle_param,
      categorie_groupe,
      type_champ,
      unite,
      options_predefinies,
      description,
      ordre
    } = req.body;

    const optionsStr = Array.isArray(options_predefinies)
      ? JSON.stringify(options_predefinies)
      : (options_predefinies !== undefined ? options_predefinies : null);

    db.prepare(`
      UPDATE parametre_type_mat SET
        libelle_param = ?,
        categorie_groupe = ?,
        type_champ = ?,
        unite = ?,
        options_predefinies = ?,
        description = ?,
        ordre = ?,
        dat_mod = CURRENT_TIMESTAMP
      WHERE id_param_type = ?
    `).run(
      libelle_param?.trim(),
      categorie_groupe?.trim() || null,
      type_champ || 'text',
      unite?.trim() || null,
      optionsStr,
      description?.trim() || null,
      ordre ? parseInt(ordre) : 0,
      req.params.id
    );

    res.json({ message: 'Paramètre spécifique mis à jour' });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.delete('/api/type-parametres/:id', (req, res) => {
  try {
    db.prepare("UPDATE parametre_type_mat SET archiv = 'O', dat_mod = CURRENT_TIMESTAMP WHERE id_param_type = ?").run(req.params.id);
    res.json({ message: 'Paramètre spécifique archivé' });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

// 8c. GESTION DE LA SYNCHRONISATION ORACLE DATA SYNC
app.post('/api/oracle-sync/test', async (req, res) => {
  try {
    const result = await testOracleConnection(req.body);
    res.json(result);
  } catch (e: any) {
    res.status(400).json({ error: e.message || 'Échec du test de connexion Oracle' });
  }
});

app.post('/api/oracle-sync/execute', async (req, res) => {
  try {
    const result = await executeOracleSync(req.body);
    res.json(result);
  } catch (e: any) {
    res.status(500).json({ error: e.message || 'Erreur lors de la synchronisation Oracle' });
  }
});

app.get('/api/oracle-sync/history', (req, res) => {
  try {
    const history = getOracleSyncHistory();
    res.json(history);
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.post('/api/oracle-sync/sql-script', (req, res) => {
  try {
    const { schema } = req.body;
    const script = generateOracleSqlScript(schema || 'GPARC_USER');
    res.json({ script });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

// Réinitialiser avec les données de démonstration d'entreprise
app.post('/api/reset-demo-data', (req, res) => {
  try {
    db.exec(`
      DELETE FROM panne;
      DELETE FROM affect_mat;
      DELETE FROM materiel;
      DELETE FROM utilisateurs;
      DELETE FROM lieu_rep;
      DELETE FROM model_mat;
      DELETE FROM type_mat;
      DELETE FROM structures;
    `);
    initDatabase();
    res.json({ message: 'Base de données réinitialisée avec les équipements et pannes témoins.' });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

// -------------------------------------------------------------
// VITE / STATIC SERVING
// -------------------------------------------------------------
async function startServer() {
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`GPARC Server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
