@echo off
REM Script de lancement rapide pour MTG DeckGenPy
REM Placez-vous dans le dossier du projet et lancez ce script

echo ========================================
echo   MTG DeckGenPy - Generateur de Decks
echo ========================================
echo.

REM Vérifier si Python est installé
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe ou n'est pas dans le PATH
    echo Telechargez Python depuis https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Vérifier les dépendances
echo Verification des dependances...
python -c "import pandas" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installation des dependances...
    pip install -r requirements.txt
)

REM Lancer le generateur
echo.
echo Lancement du generateur de decks...
echo.
python scripts\commander_generator3.0.py

echo.
echo ========================================
echo   Generation terminee !
echo ========================================
pause
