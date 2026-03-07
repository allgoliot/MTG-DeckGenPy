# 🚀 Guide de Démarrage Rapide

## Installation en 5 minutes

### 1. Installer Python

Télécharge et installe Python 3.8+ depuis [python.org](https://www.python.org/downloads/)

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Préparer ta collection

**Option A - Utiliser le modèle :**
```bash
# Copie le modèle et remplis-le
copy models\collection_modele.csv data\collection.csv
# Édite data\collection.csv avec tes cartes
```

**Option B - Import depuis un autre outil :**
- MTG Arena → Exporte vers CSV
- Magic Workstation → Exporte vers CSV
- Manuel → Utilise le format du modèle

### 4. Enrichir la collection

```bash
python scripts/enriching_collection.py
```

Ce script va :
- Lire `data/collection.csv`
- Interroger l'API Scryfall
- Générer `data/collection_enriched.csv`

### 5. Générer un deck !

**Windows :**
```bash
run.bat
```

**Linux/Mac :**
```bash
chmod +x run.sh
./run.sh
```

**Commande directe :**
```bash
python scripts/commander_generator3_0.py
```

---

## Commandes Utiles

| Commande | Description |
|----------|-------------|
| `run.bat` ou `./run.sh` | Lancement rapide |
| `python scripts/commander_generator3_0.py` | Générer un deck |
| `python scripts/enriching_collection.py` | Mettre à jour la collection |
| `pip install -r requirements.txt` | Installer les dépendances |

---

## Structure des Fichiers

```
MTG-DeckGenPy/
├── scripts/
│   └── commander_generator3_0.py   # ← Script principal
├── conf/
│   ├── config.yaml                 # ← Configuration (à créer)
│   └── config.example.yaml         # ← Exemple
├── data/
│   ├── collection.csv              # ← À remplir avec tes cartes
│   └── collection_enriched.csv     # ← Généré automatiquement
├── bibliotheque/                   # ← Tes decks générés (créé auto)
├── exports/                        # ← Decklists pour analyse (créé auto)
└── logs/                           # ← Logs d'exécution (créé auto)
```

---

## Premier Deck

1. Lance : `run.bat` (Windows) ou `./run.sh` (Linux/Mac)
2. Choisis le bracket (2 = Core, recommandé pour débuter)
3. Choisis ton commandant
4. (Optionnel) Choisis une tribu
5. Ton deck est dans `bibliotheque/` !

---

## Besoin d'Aide ?

- 📖 Lis le [README.md](README.md) complet
- 🐛 Ouvre une issue sur GitHub
- 💬 Discute avec la communauté

---

**Bon jeu ! 🎴**
