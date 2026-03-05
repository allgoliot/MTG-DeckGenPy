# 🎴 MTG DeckGenPy - Générateur de Decks Commander

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Générateur automatique de decks **Magic: The Gathering (Commander/EDH)** basé sur ta collection personnelle, avec support des **brackets officiels EDH**.

---

## ✨ Fonctionnalités

### 🧠 Intelligence Artificielle
- **Scoring intelligent** des cartes par synergies avec le commandant
- **Détection automatique** des tribus et thèmes du commandant
- **Gestion des couleurs** (forces/faiblesses par couleur)
- **Mana base intelligente** avec répartition optimale

### 🎮 Brackets Officiels EDH
| Bracket | Nom | Description |
|---------|-----|-------------|
| 1 | Exhibition | Ultra-Casual, decks thématiques |
| 2 | Core | Niveau préconstruit Commander |
| 3 | Upgraded | Deck optimisé au-delà des précons |
| 4 | Optimized | Haute puissance (cEDH) |

### 📊 Analyse et Vérification
- **Rapport de conformité** détaillé par bracket
- **Vérification des doublons** avec les decks existants
- **Analyse de cohérence** du deck (courbe de mana, synergies)
- **Score de puissance** (1-10)
- **Suggestions d'amélioration** personnalisées

### 🌐 Intégrations
- **Export decklist** compatible avec :
  - [brackcheck.com](https://brackcheck.com/)
  - [Manabox](https://manabox.app/)
  - [EDHREC](https://edhrec.com/)
- **Copie automatique** vers Dropbox (optionnel)

---

## 📦 Installation

### 1. Pré-requis

- **Python 3.8** ou supérieur
- **pip** (gestionnaire de paquets Python)

### 2. Cloner le projet

```bash
git clone https://github.com/TON_USER/MTG-DeckGenPy.git
cd MTG-DeckGenPy
```

### 3. Installer les dépendances

```bash
pip install pandas pyyaml
```

### 4. Préparer ta collection

#### Option A : Utiliser le modèle fourni

1. Copie `collection_modele.csv` vers `collection.csv`
2. Remplis avec tes cartes (voir format ci-dessous)

#### Option B : Format de collection

Le fichier `collection.csv` doit contenir les colonnes suivantes :

```csv
name,type_line,oracle_text,mana_value,color_identity,quantity
"Sol Ring","Artifact","{T}: Add {C}{C}.",1,"{C}",1
"Arcane Signet","Artifact","{T}: Add one mana of any color in your Commander's color identity.",2,"{W}{U}{B}{R}{G}",1
```

**Colonnes requises :**
| Colonne | Description | Exemple |
|---------|-------------|---------|
| `name` | Nom de la carte | `"Lightning Bolt"` |
| `type_line` | Type de carte | `"Instant"` |
| `oracle_text` | Texte de la carte | `"Lightning Bolt deals 3 damage to any target."` |
| `mana_value` | Coût en mana | `1` |
| `color_identity` | Identité de couleur | `"{R}"` |
| `quantity` | Nombre d'exemplaires | `1` |

### 5. Enrichir ta collection

Le script d'enrichissement récupère automatiquement les données depuis l'API Scryfall :

```bash
python scripts/enriching_collection.py
```

Cela va générer `data/collection_enriched.csv` avec toutes les données nécessaires.

---

## 🚀 Utilisation

### 1. Configuration (optionnel)

Copie la configuration exemple :

**Windows :**
```bash
copy conf\config.example.yaml conf\config.yaml
```

**Linux/Mac :**
```bash
cp conf/config.example.yaml conf/config.yaml
```

Puis édite `conf/config.yaml` selon tes préférences :

```yaml
# Nombre de terrains
total_lands: 37
basic_land_count: 10

# Cibles par catégorie
ramp_target: 10
draw_target: 10
removal_target: 8
wipe_target: 2

# Options
enable_tribe_selection: true      # Choisir une tribu
check_existing_decks: true        # Éviter les doublons
```

### 2. Lancer le générateur

**Option A - Script de lancement rapide :**

Windows :
```bash
run.bat
```

Linux/Mac :
```bash
chmod +x run.sh
./run.sh
```

**Option B - Commande directe :**

```bash
python scripts/commander_generator3.0.py
```

### 3. Suivre le processus

1. **Choisir le bracket** (1-4)
2. **Sélectionner un commandant** dans la liste
3. **(Optionnel)** Choisir une tribu/thème
4. Le deck est généré automatiquement

### 4. Consulter les résultats

- **Deck sauvegardé** dans `bibliotheque/Nom-Commandant.txt`
- **Decklist export** dans `exports/Nom-Commandant_decklist.txt`
- **Rapport complet** affiché dans la console

---

## 📋 Exemple de Sortie

```
=== BRACKETS OFFICIELS COMMANDER ===
1: Exhibition (Ultra-Casual)
2: Core (Préconstruit)
3: Upgraded (Amélioré)
4: Optimized (Haute Puissance / cEDH)
Entrez le bracket officiel (1-4) : 2

🎯 Synergies du commandant détectées :
   Tribus : vampire, wizard
   Thèmes : graveyard, lifegain

🃏 TOP 10 DES MEILLEURES CARTES POUR CE DECK :
------------------------------------------------------------
   1. Blood Artist (score: 18.5, mana: 1)
      Synergies : graveyard, vampires
   2. Vampiric Tutor (score: 16.0, mana: 1)
      Synergies : graveyard, tutors
   ...

🏔️  CONSTRUCTION DE LA MANA BASE (3 couleurs)
--------------------------------------------------
   Island: 3 terrains
   Swamp: 4 terrains
   Mountain: 3 terrains

⚡ SÉLECTION DU RAMP (cible: 12 cartes) - Top score
📚 SÉLECTION DE LA PIOCHE (cible: 12 cartes) - Top score
⚔️  SÉLECTION DU REMOVAL (cible: 10 cartes) - Top score
💥 SÉLECTION DES WIPES (cible: 2 cartes) - Top score

✅ DECK COMPLÉTÉ : 99 cartes

============================================================
📊 RAPPORT DE VÉRIFICATION DU BRACKET
============================================================
Bracket ciblé : 2 - Core (Préconstruit)

📈 STATISTIQUES DU DECK
------------------------------
✓ Game Changers: 0/0
✓ Tutors: 3/4
✓ Combos infinis: 0
✓ Coût mana moyen: 2.8

============================================================
✅ Deck CONFORME au bracket ciblé !
============================================================

💪 Score de puissance: 6.5/10

📁 Decklist exportée vers : 'exports/Nom-Commandant_decklist.txt'
   → Copie-colle ce fichier sur https://brackcheck.com/ pour analyse
```

---

## 📁 Structure des Fichiers

```
MTG-DeckGenPy/
├── README.md                       # Documentation principale
├── GUIDE_RAPIDE.md                 # Guide de démarrage rapide
├── LICENSE                         # Licence MIT
├── requirements.txt                # Dépendances Python
├── .gitignore                      # Fichiers à exclure de Git
├── run.bat                         # Lancement rapide (Windows)
├── run.sh                          # Lancement rapide (Linux/Mac)
│
├── scripts/                        # Scripts Python
│   ├── commander_generator3.0.py   # Script principal
│   ├── enriching_collection.py     # Script d'enrichissement
│   └── ...                         # Anciennes versions
│
├── conf/                           # Configuration
│   ├── config.yaml                 # Configuration active (à créer)
│   └── config.example.yaml         # Configuration exemple
│
├── models/                         # Modèles
│   └── collection_modele.csv       # Modèle de collection
│
├── data/                           # Données utilisateur
│   ├── collection.csv              # Ta collection (à créer)
│   └── collection_enriched.csv     # Généré automatiquement
│
├── .qwen/                          # Contexte du projet
│   └── context.md
│
├── bibliotheque/                   # Decks générés (créé automatiquement)
│   └── Nom-Commandant.txt
│
├── exports/                        # Decklists pour analyse (créé automatiquement)
│   └── Nom-Commandant_decklist.txt
│
└── logs/                           # Logs d'exécution (créé automatiquement)
    └── Nom-Commandant_YYYYMMDD_HHMMSS.log
```

---

## ⚙️ Options de Configuration

### `config.yaml` - Paramètres Principaux

```yaml
# Terrains
total_lands: 37                   # Nombre total de terrains
basic_land_count: 10              # Terrains de base

# Cibles par catégorie
ramp_target: 10                   # Cartes de ramp
draw_target: 10                   # Cartes de pioche
removal_target: 8                 # Cartes de removal
wipe_target: 2                    # Board wipes

# Options
enable_tribe_selection: true      # Activer le choix de tribu
check_existing_decks: true        # Vérifier les doublons

# Liste des cartes "Game Changers" (interdites brackets 1-2)
game_changers:
  - "Sol Ring"
  - "Mana Crypt"
  - "Demonic Tutor"
  # ... (liste complète dans config.yaml)
```

---

## 🔍 Analyse et Rapports

### Rapport de Vérification
- **Game Changers** : Nombre et liste des cartes détectées
- **Tutors** : Compte par rapport à la limite du bracket
- **Combos infinis** : Détection et alerte
- **Coût mana moyen** : Comparaison avec les recommandations
- **Courbe de mana** : Visualisation graphique

### Analyse de Cohérence
- **Synergies détectées** : Points forts du deck
- **Problèmes de courbe** : Alertes si déséquilibre
- **Recommandations** : Suggestions d'amélioration

### Warning des Doublons
- **Cartes déjà utilisées** : Liste complète par deck
- **Cartes multi-decks** : Surlignage des cartes les plus utilisées
- **Exclusion des terrains de base** : Non comptabilisés

---

## 🌐 Intégration avec les Sites d'Analyse

### Export Automatique

Le script génère un fichier dans `exports/` compatible avec :

1. **brackcheck.com**
   - Format : Decklist standard
   - Utilisation : Copier-coller pour analyse de bracket

2. **Manabox.app**
   - Format : Decklist avec quantités
   - Utilisation : Import pour prix et disponibilité

3. **EDHREC.com**
   - Format : Decklist catégorisée
   - Utilisation : Comparaison avec les statistiques communautaires

### Exemple de Fichier Export

```
Commander: Lagomos, Hand of Hatred

--- CREATURES ---
1 Lagomos, Hand of Hatred
3 Blood Artist
2 Priest of Fell Rites
...

--- SORTS ET ARTIFACTS ---
1 Sol Ring
1 Arcane Signet
1 Demonic Tutor
...

--- TERRAINS ---
10 Swamp
3 Mountain
1 Command Tower
...
```

---

## 🛠️ Dépannage

### Problèmes Courants

#### `collection_enriched.csv` introuvable
```bash
# Lance le script d'enrichissement
python enriching_collection.py
```

#### Erreur d'encodage
Les fichiers sont lus avec fallback automatique :
- UTF-8 (prioritaire)
- CP1252 (Windows)
- Latin-1

#### Trop de cartes manquantes
Vérifie que ta collection contient assez de cartes dans les couleurs du commandant.

### Logs et Debug

Le script affiche des messages détaillés :
- ✅ Actions réussies
- ⚠️ Avertissements
- ❌ Erreurs

---

## 📝 Licence

Ce projet est distribué sous licence **MIT**. Voir le fichier `LICENSE` pour plus de détails.

---

## 🤝 Contribuer

Les contributions sont les bienvenues ! N'hésite pas à :

1. Fork le projet
2. Créer une branche (`git checkout -b feature/AmazingFeature`)
3. Commit tes changements (`git commit -m 'Add some AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

---

## 📞 Support

- **Issues GitHub** : Pour les bugs et demandes de fonctionnalités
- **Discussions** : Pour les questions générales

---

## 🙏 Remerciements

- **Scryfall API** : Pour les données de cartes
- **EDHREC** : Pour l'inspiration des brackets
- **Communauté MTG** : Pour les retours et tests

---

**Bon jeu et bons decks ! 🎴**
