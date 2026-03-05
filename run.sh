#!/bin/bash
# Script de lancement rapide pour MTG DeckGenPy
# Placez-vous dans le dossier du projet et lancez ce script

echo "========================================"
echo "  MTG DeckGenPy - Générateur de Decks"
echo "========================================"
echo ""

# Vérifier si Python est installé
if ! command -v python3 &> /dev/null; then
    echo "[ERREUR] Python n'est pas installé ou n'est pas dans le PATH"
    echo "Installez Python depuis https://www.python.org/downloads/"
    exit 1
fi

# Vérifier les dépendances
echo "Vérification des dépendances..."
if ! python3 -c "import pandas" &> /dev/null; then
    echo "[INFO] Installation des dépendances..."
    pip3 install -r requirements.txt
fi

# Lancer le générateur
echo ""
echo "Lancement du générateur de decks..."
echo ""
python3 scripts/commander_generator3.0.py

echo ""
echo "========================================"
echo "  Génération terminée !"
echo "========================================"
