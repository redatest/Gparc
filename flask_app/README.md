# GPARC - Mode Bureau Standalone (Identique à green-dz)

Cette configuration permet d'exécuter GPARC directement sous Python Flask sur votre poste de travail.

## Démarrage rapide (Windows)
Double-cliquez sur `LANCER_GPARC.bat` situé à la racine du projet.

## Démarrage en ligne de commande :
```bash
# 1. Installation des dépendances Flask
pip install -r requirements.txt

# 2. Lancement du serveur
python app.py
```

Le serveur sera immédiatement accessible sur **http://127.0.0.1:5000** et ouvrira automatiquement la page d'accueil dans votre navigateur.
La base de données SQLite `data/gparc.db` est automatiquement initialisée avec le schéma complet et les équipements de démonstration.
