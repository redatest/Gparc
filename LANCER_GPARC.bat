@echo off
chcp 65001 >nul
title GPARC - Gestion du Parc Informatique
color 0B

echo ======================================================================
echo          GPARC - APPLICATION DE GESTION DU PARC INFORMATIQUE
echo ======================================================================
echo.
echo [1/3] Verification de l'environnement Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR CRITIQUE] Python n'est pas detecte sur votre machine.
    echo Veuillez telecharger et installer Python depuis : https://www.python.org/downloads/
    echo Pensez a cocher l'option "Add Python to PATH" lors de l'installation.
    echo.
    pause
    exit /b 1
)

echo [2/3] Verification et installation des dependances (Flask, Flask-CORS)...
pip install flask flask-cors >nul 2>&1

echo [3/3] Lancement du serveur GPARC sur http://127.0.0.1:5000 ...
echo.
echo Ouverture automatique de votre navigateur internet...
start "" http://127.0.0.1:5000

echo Serveur demarre avec succes ! Ne fermez pas cette fenetre noire pendant l'utilisation.
echo.
python app.py

pause
