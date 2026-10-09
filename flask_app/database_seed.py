"""Amorçage des paramètres matériels par défaut."""


def seed_default_parameters(cur):
    """Insère les paramètres initiaux uniquement si le référentiel est vide."""
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
    
