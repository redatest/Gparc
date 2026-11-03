# GPARC - Gestion du Parc Informatique

Application locale Flask avec base SQLite.

## Démarrage (Windows)
Double-cliquez sur `LANCER_GPARC.bat` à la racine du projet.

## Démarrage manuel
```bash
pip install -r requirements.txt
python app.py
```

Ouvrez ensuite **http://127.0.0.1:5000**.

## Première connexion
Au premier démarrage, GPARC affiche un formulaire de configuration permettant de créer le compte **Super administrateur**. Cette première création doit être effectuée depuis le poste serveur (localhost), afin qu'un utilisateur du réseau ne puisse pas s'approprier le compte initial. Aucun identifiant ou mot de passe initial n'est préconfiguré. Pour autoriser explicitement une configuration distante, définir `GPARC_ALLOW_REMOTE_SETUP=1` avant le lancement.

Le super administrateur crée ensuite les comptes des administrateurs simples depuis le pavé **Administration**. Les administrateurs simples ont accès aux fonctions de gestion du parc, mais pas à l'import Oracle ni à l'administration des comptes.

Les mots de passe sont stockés sous forme de hash. Les sessions sont conservées dans un cookie sécurisé HttpOnly pendant sept jours et peuvent être terminées avec le bouton **Déconnexion**. La clé de session est générée localement dans le dossier de données (fichier caché `.gparc_secret_key`) ; ne pas supprimer ce fichier si les sessions doivent rester valides après redémarrage.

Pour un déploiement HTTPS, définir `GPARC_COOKIE_SECURE=1` et conserver le fichier de clé hors du dépôt. La variable `GPARC_SECRET_KEY` peut également fournir explicitement une clé stable.
