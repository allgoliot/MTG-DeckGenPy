# Contexte du Projet - MTG DeckGenPy

**Dernière mise à jour :** 2026-03-07

## 📋 Description

Générateur automatique de decks **Magic: The Gathering (Commander/EDH)** basé sur une collection personnelle, avec support des **brackets officiels EDH** et **vérification des doublons**.

**Architecture actuelle :** CLI et GUI partagent le **MÊME moteur de génération** pour une cohérence parfaite.

---

## 🎯 Fonctionnalités principales

### 🧠 Moteur de Génération Commun
- **Module unique** : `scripts/deck_generator.py`
- **Utilisé par** : CLI (`commander_generator3_0.py`) et GUI (`gui_app.py`)
- **Garantie** : CLI et GUI génèrent **exactement les mêmes decks**

### 🎮 Brackets officiels EDH (1-4)
| Bracket | Nom | Game Changers | Tutors | Combos Infinis |
|---------|-----|---------------|--------|----------------|
| 1 | Exhibition | 0 | 2 | ❌ |
| 2 | Core | 0 | 4 | ❌ |
| 3 | Upgraded | 3 | 6 | ❌ |
| 4 | Optimized | ∞ | ∞ | ✅ |

### 📊 Fonctionnalités Avancées
- **Scoring intelligent** des cartes par synergies avec le commandant
- **Gestion des couleurs** (forces/faiblesses par couleur)
- **Mana base intelligente** avec répartition optimale
- **Filtre de tribu** (créatures UNIQUEMENT)
- **Vérification des doublons** avec les decks existants
- **Export decklist** pour brackcheck.com, Manabox, EDHREC
- **Analyse détaillée** des pré-requis par bracket
- **Rapport de conformité** avec suggestions d'amélioration
- **Score de puissance** du deck (1-10)
- **Logging complet** (effet tee -a) dans `logs/`
- **Affichage coloré** des symboles de mana (⚪🔵⚫🔴🟢)

---

## 📁 Structure des Fichiers

```
MTG-DeckGenPy/
├── README.md                       # Documentation principale
├── GUIDE_RAPIDE.md                 # Guide de démarrage rapide
├── GUIDE_GUI.md                    # Guide de l'interface graphique
├── LICENSE                         # Licence MIT
├── requirements.txt                # Dépendances Python
├── .gitignore                      # Fichiers à exclure de Git
├── run.bat                         # Lancement rapide CLI (Windows)
├── run.sh                          # Lancement rapide CLI (Linux/Mac)
├── run_gui.bat                     # Lancement rapide GUI (Windows)
│
├── scripts/                        # Scripts Python
│   ├── deck_generator.py           # ⭐ MOTEUR COMMUN (CLI + GUI)
│   ├── commander_generator3_0.py   # Interface CLI (Terminal)
│   ├── gui_app.py                  # Interface GUI (NiceGUI)
│   ├── enriching_collection.py     # Script d'enrichissement
│   └── ...backup.py                # Anciennes versions (backup)
│
├── conf/                           # Configuration
│   ├── config.yaml                 # Configuration active
│   └── config.example.yaml         # Configuration exemple
│
├── models/                         # Modèles
│   └── collection_modele.csv       # Modèle de collection
│
├── data/                           # Données utilisateur
│   ├── collection.csv              # Ta collection (à remplir)
│   └── collection_enriched.csv     # Généré automatiquement
│
├── .qwen/                          # Contexte du projet
│   └── context.md                  # Ce fichier
│
├── bibliotheque/                   # Decks générés sauvegardés
├── exports/                        # Decklists formatées pour sites d'analyse
└── logs/                           # Logs d'exécution par deck
```

---

## ⚙️ Configuration actuelle (`conf/config.yaml`)

```yaml
total_lands: 37
basic_land_count: 10
ramp_target: 10
draw_target: 10
removal_target: 8
wipe_target: 2
total_cards: 99
enable_tribe_selection: true
check_existing_decks: true        # Exclut les cartes déjà utilisées
```

---

## 🚀 Utilisation

### Interface Graphique (Recommandé)
```bash
# Windows
run_gui.bat

# Linux/Mac
python scripts/gui_app.py

# Puis ouvrir http://localhost:8080
```

### Terminal (CLI)
```bash
# Windows
run.bat

# Linux/Mac
chmod +x run.sh && ./run.sh

# Ou directement
python scripts/commander_generator3_0.py
```

---

## 🔧 Fonctions du Moteur Commun (`deck_generator.py`)

| Fonction | Rôle |
|----------|------|
| `load_collection()` | Charge la collection depuis CSV |
| `load_library()` | Charge les decks existants pour éviter doublons |
| `generate_deck()` | **Fonction principale** de génération de deck |
| `save_deck()` | Sauvegarde dans bibliotheque/ et exports/ |
| `score_card()` | Score intelligent d'une carte (synergie + utilité) |
| `calculer_synergie_commandant()` | Score la synergie d'une carte avec le commandant |
| `pick_unique()` | Sélectionne des cartes uniques avec contraintes bracket |
| `normalize_card_name()` | Normalise les noms de cartes (exclut set/numéro) |
| `format_colors()` | Formate les couleurs avec symboles (⚪🔵⚫🔴🟢) |
| `extract_tribes()` | Extrait les tribus du type_line |
| `detect_tutor()` | Détecte les tutors |
| `detect_infinite_combo_potential()` | Détecte les combos infinis |
| `detect_mass_land_destruction()` | Détecte la négation de terrain |
| `detect_extra_turn()` | Détecte les tours supplémentaires |

---

## 🏷️ Filtre de Tribu

**IMPORTANT :** Le filtre de tribu ne s'applique **QU'AUX CRÉATURES**.

### Code (`deck_generator.py` ligne ~452)
```python
# Filtre tribu optionnel (créatures uniquement)
if tribes:
    def apply_tribe_filter(row):
        tl = str(row["type_line"]).lower()
        if 'creature' in tl:
            return any(tr.lower() in tl for tr in tribes)
        return True  # Les non-créatures sont toujours incluses

    mask = legal_cards.apply(apply_tribe_filter, axis=1)
    legal_cards = legal_cards[mask]
    log_msg(f"🏷️ Filtre tribu appliqué: {', '.join(tribes)} (créatures uniquement)")
```

### Comportement
- ✅ **Créatures** : Filtrées par tribu sélectionnée
- ✅ **Non-créatures** (ramp, draw, removal, wipes, terrains) : **TOUJOURS incluses**
- ✅ **Log** : Message explicite "(créatures uniquement)"

---

## 📊 Exemple de Deck Généré avec Filtre "Vampire"

```
Commandant: Edgar Markov
Filtre: Vampire (créatures uniquement)

--- CREATURES (25) ---
25 créatures Vampire uniquement
  1x Blood Artist
  1x Edgar Markov
  1x Vampire Champion
  ...

--- SORTS ET ARTIFACTS (37) ---
Toutes les cartes ramp, draw, removal, artifacts
  1x Sol Ring
  1x Arcane Signet
  1x Vampiric Tutor
  ... (NON filtrés par tribu)

--- TERRAINS (37) ---
Tous les terrains
  10x Swamp
  1x Command Tower
  ... (NON filtrés par tribu)
```

---

## 🎨 Interface Graphique (NiceGUI)

### Fonctionnalités GUI
1. **📊 Sélection du Bracket** (1-4) avec descriptions
2. **🎯 Choix du Commandant** :
   - Recherche dans **nom + oracle text + tribu**
   - Aperçu avec image Scryfall (version française)
   - Affichage en temps réel à droite
3. **🏷️ Filtre de Tribu** :
   - Chargement automatique à la sélection du commandant
   - Affiche le **nombre de créatures par tribu**
   - Barre de recherche + boutons "Tout"/"Aucun"
   - 6 colonnes pour optimiser l'espace
4. **⚡ Génération** :
   - Journal en temps réel
   - Utilise `deck_generator.py` (MÊME LOGIQUE QUE CLI)
5. **📚 Bibliothèque** :
   - Page dédiée `/library`
   - Grille des decks avec images des commandants
   - Menu de chargement avec progression (barre + compteur + %)
   - Dialog de détails avec decklist + bouton copier

### Menu de Navigation
- **🎴 MTG DeckGenPy** : Bouton toujours visible → retour à l'accueil
- **📚 Bibliothèque** : Bouton dans l'en-tête → page bibliothèque

---

## 📝 Modifications Récentes (2026-03-07)

### Architecture
- ✨ **Création de `deck_generator.py`** : Moteur commun CLI + GUI
- ✨ **Refonte de `commander_generator3_0.py`** : Utilise `deck_generator.py`
- ✨ **Refonte de `gui_app.py`** : Utilise `deck_generator.py`
- ✅ **Garantie** : CLI et GUI génèrent les MÊMES decks

### Interface Graphique
- ✨ Menu "🎴 MTG DeckGenPy" toujours visible (retour accueil)
- ✨ Recherche étendue (nom + oracle text + tribu)
- ✨ Affichage de l'image du commandant (Scryfall FR)
- ✨ Aperçu en temps réel à droite de la liste
- ✨ Tribus : chargement automatique + compteur par tribu
- ✨ Bibliothèque : page dédiée avec progression de chargement
- ✨ Progression : barre + compteur + pourcentage
- ✨ Decklist : bouton copier dans le presse-papier

### Filtre de Tribu
- ✅ **Ne s'applique QU'AUX CRÉATURES**
- ✅ Les non-créatures (ramp, draw, removal, terrains) sont TOUJOURS incluses
- ✅ Message explicite dans le log : "(créatures uniquement)"

---

## 🛠️ Dépannage

### `collection_enriched.csv` introuvable
```bash
# Lance le script d'enrichissement
python scripts/enriching_collection.py
```

### L'interface GUI ne se lance pas
```bash
# Vérifie les dépendances
pip install -r requirements.txt

# Ou directement
pip install nicegui requests pandas pyyaml
```

### Erreur de port 8080
Modifier le port dans `scripts/gui_app.py` :
```python
ui.run(port=8081)  # Changer 8080 par 8081
```

---

## 📞 Support

- **Issues GitHub** : Bugs et demandes de fonctionnalités
- **Documentation** : `README.md` (CLI) et `GUIDE_GUI.md` (GUI)

---

**Bon jeu et bons decks ! 🎴**
