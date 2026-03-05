# Contexte du Projet - MTG DeckGenPy

## 📋 Description
Générateur automatique de decks Magic: The Gathering (Commander/EDH) basé sur une collection personnelle, avec support des **brackets officiels EDH** et **vérification des doublons**.

## 🎯 Fonctionnalités principales
- **Brackets officiels EDH** (1-4 : Exhibition, Core, Upgraded, Optimized)
- **Scoring intelligent** des cartes par synergies avec le commandant
- **Gestion des couleurs** (forces/faiblesses par couleur)
- **Mana base intelligente** (répartition par couleur)
- **Vérification des doublons** avec les decks existants (`check_existing_decks`)
- **Export decklist** pour brackcheck.com, Manabox, EDHREC
- **Analyse détaillée** des pré-requis par bracket
- **Rapport de conformité** avec suggestions d'amélioration
- **Score de puissance** du deck (1-10)
- **Logging complet** (effet tee -a) dans `logs/`
- **Affichage coloré** des symboles de mana (⚪🔵⚫🔴🟢)

## 📁 Fichiers importants

| Fichier | Rôle |
|---------|------|
| `scripts/commander_generator3.0.py` | Script principal de génération |
| `scripts/enriching_collection.py` | Script d'enrichissement de la collection |
| `conf/config.yaml` | Configuration active (à créer) |
| `conf/config.example.yaml` | Configuration exemple |
| `models/collection_modele.csv` | Modèle de collection |
| `data/collection.csv` | Collection brute (à remplir) |
| `data/collection_enriched.csv` | Collection enrichie (généré) |
| `bibliotheque/` | Decks générés sauvegardés (créé auto) |
| `exports/` | Decklists formatées pour sites d'analyse (créé auto) |
| `logs/` | Logs d'exécution par deck (créé auto) |

## ⚙️ Configuration actuelle (`conf/config.yaml`)

```yaml
total_lands: 37
basic_land_count: 10
ramp_target: 10
draw_target: 10
removal_target: 8
wipe_target: 2
total_cards: 99
enable_tribe_selection: false
check_existing_decks: true        # Exclut les cartes déjà utilisées
```

## 🎮 Brackets EDH officiels supportés

| Bracket | Nom | Game Changers | Tutors | Combos Infinis |
|---------|-----|---------------|--------|----------------|
| 1 | Exhibition | 0 | 2 | ❌ |
| 2 | Core | 0 | 4 | ❌ |
| 3 | Upgraded | 3 | 6 | ❌ |
| 4 | Optimized | ∞ | ∞ | ✅ |

## 📝 Modifications récentes
- **2026-03-05** : Affichage coloré des symboles de mana (⚪🔵⚫🔴🟢)
- **2026-03-05** : Logging complet (effet tee -a) dans logs/
- **2026-03-05** : Correction sélection intelligente (score préservé)
- **2026-03-05** : Warning doublons avec liste des cartes
- **2026-03-05** : Option check_existing_decks (exclusion par nom de carte)
- **2026-03-05** : Structure dossiers (conf/, logs/, exports/, bibliotheque/)
- **2026-03-05** : Scoring intelligent par synergie commandant
- **2026-03-05** : Gestion couleurs (forces/faiblesses)
- **2026-03-05** : Mana base intelligente (répartition par couleur)

## 🔧 Fonctions utilitaires clés

| Fonction | Rôle |
|----------|------|
| `detect_infinite_combo_potential()` | Détecte les combos infinis |
| `detect_mass_land_destruction()` | Détecte la négation de terrain |
| `detect_extra_turn()` | Détecte les tours supplémentaires |
| `detect_tutor()` | Détecte les tutors |
| `pick_unique()` | Sélectionne des cartes uniques avec contraintes |
| `analyser_conformite_bracket()` | Vérifie la conformité du deck au bracket |
| `afficher_rapport_bracket()` | Affiche le rapport de vérification |
| `calculer_score_puissance()` | Calcule un score 1-10 de puissance |
| `analyser_coherence_deck()` | Analyse la cohérence interne du deck |
| `analyser_pre_requis_bracket()` | Analyse détaillée des pré-requis par bracket |
| `afficher_pre_requis_bracket()` | Affiche les pré-requis et cartes détectées |
| `extraire_tribus_commandant()` | Extrait tribus et thèmes du commandant |
| `calculer_synergie_commandant()` | Score la synergie d'une carte avec le commandant |
| `calculer_bonus_couleur()` | Applique les forces/faiblesses des couleurs |
| `score_card()` | Score intelligent d'une carte (synergie + utilité) |
| `score_terrain()` | Score les terrains par utilité |
| `normalize_card_name()` | Normalise les noms de cartes (exclut set/numéro) |
| `format_colors()` | Formate les couleurs avec symboles (⚪🔵⚫🔴🟢) |
| `TeeHandler` | Redirige sortie console + fichier log (tee -a) |

## 🚀 Utilisation

```bash
python scripts/commander_generator3.0.py
```

1. Choisir le bracket (1-4)
2. Sélectionner un commandant (affiché avec symboles de mana ⚪🔵⚫🔴🟢)
3. (Optionnel) Choisir une tribu
4. Le deck est généré dans `bibliotheque/`
5. **Rapport de vérification** affiché avec score de puissance
6. **Analyse détaillée** des pré-requis par bracket
7. **Export decklist** dans `exports/` pour analyse sur brackcheck.com
8. **Warning des doublons** avec les decks existants
9. **Log complet** sauvegardé dans `logs/Nom-Commandant_YYYYMMDD_HHMMSS.log`
10. Copie automatique vers Dropbox (si disponible)

## 📌 Notes importantes
- Les cartes "Game Changers" sont listées dans `conf/config.yaml`
- `check_existing_decks: true` exclut les cartes déjà utilisées (par nom normalisé)
- `normalize_card_name()` ignore set code et numéro de collecte
- Encodage des fichiers : UTF-8 avec fallback cp1252/latin-1
- Le scoring intelligent préserve les synergies pendant toute la sélection
- Les terrains de base sont exclus des statistiques de CMC
- Les logs contiennent EXACTEMENT la sortie du terminal (mot pour mot)
- Les symboles de mana n'affichent pas l'incolore (C)

## 🔧 Pré-requis d'installation

### Python
- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)

### Bibliothèques Python
```bash
pip install pandas pyyaml
```

### Fichiers requis
1. `data/collection.csv` - Ta collection de cartes (format modèle fourni)
2. `scripts/enriching_collection.py` - Script pour enrichir la collection avec les données Scryfall
3. `conf/config.yaml` - Configuration (copie depuis `conf/config.example.yaml`)

### Structure des fichiers
```
MTG-DeckGenPy/
├── scripts/
│   ├── commander_generator3.0.py    # Script principal
│   └── enriching_collection.py       # Script d'enrichissement
├── conf/
│   ├── config.yaml                   # Configuration active
│   └── config.example.yaml           # Configuration exemple
├── models/
│   └── collection_modele.csv         # Modèle de collection
├── data/
│   ├── collection.csv                # Ta collection (à créer)
│   └── collection_enriched.csv       # Généré automatiquement
├── bibliotheque/                     # Decks générés (créé auto)
├── exports/                          # Decklists pour analyse (créé auto)
└── logs/                             # Logs d'exécution (créé auto)
```
