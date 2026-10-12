# GPARC - Gestion du Parc Informatique & Suivi des Pannes & Réformes

Application complète de gestion du parc informatique d'entreprise avec suivi en temps réel des équipements, déclaration et gestion des pannes, gestion des procédure de la réforme, et fournir des fiches d'intervention imprimables.

Cette plateforme est considérée comme une refonte d'une anicienne application conçue sous ORACLE/APEX, et redéployée sous Python/Flask framework.

Elle est conçue sous une architecture (SPA) qui offre un frontend fortement dynamique et découplé, afin d'offrir une meilleur érgonomie à l'utilisateur.

---

## 🖥️ Démarrage

### Méthode 1 : Double-clic direct (Windows)
Double-cliquez simplement sur le fichier :
👉 **`LANCER_GPARC.bat`** (ou `run.bat`)

Le script vérifie Python, installe automatiquement les dépendances Flask si besoin, lance le serveur et **ouvre directement votre navigateur sur `http://127.0.0.1:5000`**.

### Méthode 2 : Lancement en ligne de commande
```bash
# 1. Installer les dépendances Python
pip install flask flask-cors

# 2. Lancer l'application
python app.py
```
👉 Accédez à l'application sur : **http://127.0.0.1:5000**

---

## ⚡ Deux Modes d'Interface Disponibles

1. **⚡ Interface Simple, Souple & Complete** (Active par défaut) :
   - Conçue pour une utilisation quotidienne sans complexité :
   - Recherche rapide d'équipement par N° d'inventaire, série, utilisateur ou bureau.
   - Ajout rapide de matériel en 4 champs clés.
   - Déclaration rapide de panne en 2 clics.
   - Cartes synthétiques des équipements et statuts en temps réel.
   - Tableau de bord avec indicateurs KPI et graphiques d'analyse.
   - Fiches matériels détaillées (processeur, RAM, disque, système, photo, réseau).
   - Cycle de vie des pannes et rapports d'intervention imprimables.
   - Suivi des réformes (proposition, validation, motif, année/lot).
   - Espace Administration (référentiels, modèles, structures, synchronisation Oracle DBA).


