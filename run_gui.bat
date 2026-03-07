@echo off
REM ==========================================
REM MTG DeckGenPy - Lancement Interface GUI
REM ==========================================

echo ========================================
echo   MTG DeckGenPy - Interface Graphique
echo ========================================
echo.

REM Vérifier si venv existe
if exist "venv\Scripts\activate.bat" (
    echo Activation de l'environnement virtuel...
    call venv\Scripts\activate.bat
) else (
    echo Aucun environnement virtuel detecte, utilisation de Python systeme
)

REM Lancer l'interface graphique
echo Lancement de l'interface graphique...
echo.
python scripts/gui_app.py

REM Garder la fenetre ouverte en cas d'erreur
if errorlevel 1 (
    echo.
    echo Une erreur s'est produite. Appuyez sur une touche pour fermer.
    pause > nul
)
