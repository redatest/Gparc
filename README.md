# GPARC - Gestion du Parc Informatique & Suivi des Pannes

Application complète de gestion du parc informatique d'entreprise avec suivi en temps réel des équipements, attachement de photos, déclaration et gestion des pannes, et fiches d'intervention imprimables.

---

## 🖥️ Démarrage sur Bureau (Mode Standalone type Green-DZ)

Si vous utilisez l'application sur votre bureau Windows/Linux/Mac (comme l'application **green-dz**) :

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
👉 Accédez à l'application sur : **http://127.0.0.1:5000** (avec base SQLite automatique `data/gparc.db`).

---

## 🚀 Démarrage en Mode Développement Node.js / Vite (Port 3000)

Si vous développez avec Node.js :
```bash
npm install
npm run dev
```
👉 Accédez à l'application sur : **http://localhost:3000**

---

## ⚡ Deux Modes d'Interface Disponibles

1. **⚡ Interface Simple & Rapide** (Active par défaut) :
   - Conçue pour une utilisation quotidienne sans complexité :
   - Recherche rapide d'équipement par N° d'inventaire, série, utilisateur ou bureau.
   - Ajout rapide de matériel en 4 champs clés.
   - Déclaration rapide de panne en 2 clics.
   - Cartes synthétiques des équipements et statuts en temps réel.

2. **📊 Interface Complète / Expert** :
   - Tableau de bord avec indicateurs KPI et graphiques d'analyse.
   - Fiches matériels détaillées (processeur, RAM, disque, système, photo, réseau).
   - Cycle de vie des pannes et rapports d'intervention imprimables.
   - Espace Administration (référentiels, modèles, structures, synchronisation Oracle DBA).

Vous pouvez basculer entre les deux modes à tout moment depuis la barre supérieure ou les boutons dédiés.

---

## 🛡️ Mode Autonome / Hors-ligne (Zero-Failure Guarantee)
Si votre serveur backend n'est pas démarré ou si vous lancez l'application en mode client seul (ex: `npx vite`), l'application s'exécute automatiquement en **Mode Autonome / Hors-ligne** :
- Les données de test et référentiels sont préchargés instantanément.
- Vous pouvez ajouter du matériel, déclarer des pannes et tester toutes les fonctionnalités directement dans le navigateur (persistance `localStorage`).
- Dès que le serveur `npm run dev` est actif, vous pouvez cliquer sur **Reconnecter** pour synchroniser avec la base SQLite.

---

## 📦 Scripts Disponibles

- `npm run dev` : Démarre le serveur local sur `http://localhost:3000`.
- `npm run build` : Compile le frontend Vite et le serveur esbuild dans `dist/`.
- `npm start` : Démarre le serveur de production compilé.
- `npm run lint` : Vérifie les types TypeScript (`tsc --noEmit`).
