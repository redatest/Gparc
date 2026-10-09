"""Amorçage des données de démonstration pour une base GPARC neuve."""


def seed_demo_data(conn, cur):
    """Insère les données initiales uniquement si aucun matériel n'existe."""
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
    
