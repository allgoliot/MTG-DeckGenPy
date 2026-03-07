# 🖥️ MTG DeckGenPy - Guide de l'Interface Graphique

## 🚀 Démarrage Rapide

### Pré-requis

**Important :** Avant de lancer l'interface, assurez-vous que votre collection est enrichie :

```bash
python scripts/enriching_collection.py
```

Cela génère `data/collection_enriched.csv` avec les données complètes depuis Scryfall.

### Lancer l'Interface Graphique

**Windows :**
```bash
run_gui.bat
```

**Linux/Mac :**
```bash
python scripts/gui_app.py
```

L'interface s'ouvrira automatiquement dans votre navigateur à l'adresse : **http://localhost:8080**

---

## ℹ️ Note Technique

L'interface graphique utilise **exactement la même logique** que `scripts/commander_generator3_0.py` :
- Même configuration (`conf/config.yaml`)
- Même scoring intelligent des cartes
- mêmes règles de brackets EDH officiels
- Même vérification des doublons
- Même format d'export

Seule l'interface change : au lieu d'un terminal, vous avez une interface web moderne avec NiceGUI.

---

## 📋 Fonctionnalités de l'Interface

### 1️⃣ Sélection du Bracket EDH

Choisissez le niveau de puissance de votre deck :

| Bracket | Nom | Description |
|---------|-----|-------------|
| **1** | 🎪 Exhibition | Ultra-Casual, decks thématiques |
| **2** | 📦 Core | Niveau préconstruit Commander |
| **3** | ⚡ Upgraded | Deck optimisé au-delà des précons |
| **4** | 🏆 Optimized | Haute puissance (cEDH) |

---

### 2️⃣ Choix du Commandant

**Recherche :**
- Utilisez la barre de recherche pour trouver un commandant par nom
- La liste affiche :
  - 🎨 Les symboles de couleur
  - 🏷️ Les tribus associées
  - 📊 Le bracket recommandé

**Filtrage automatique :**
- Les commandants sont filtrés selon le bracket sélectionné
- Tri par score de force (synergies, utilité)

---

### 3️⃣ Filtre par Tribu (Optionnel)

**Fonctionnement :**
- Cliquez sur "🏷️ Charger les tribus"
- Sélectionnez une ou plusieurs tribus
- Appliquez le filtre pour restreindre la sélection

**Exemples :**
- `vampire`, `wizard`, `elf`, `dragon`, `goblin`, `zombie`

---

### 4️⃣ Génération du Deck

**Processus automatique :**
1. 🏔️ Construction de la mana base
2. ⚡ Sélection du ramp
3. 📚 Sélection de la pioche
4. ⚔️ Sélection du removal
5. 💥 Sélection des wipes
6. 🎴 Complément avec les meilleures cartes

**Journal en temps réel :**
- Suivez la génération étape par étape
- Voir les cartes sélectionnées et exclues

---

### 5️⃣ Résultats et Export

**Après génération :**
- ✅ Deck sauvegardé dans `bibliotheque/`
- 📤 Export formaté dans `exports/`
- 📊 Statistiques du deck
- 📝 Journal complet de génération

**Actions disponibles :**
- 📂 Ouvrir le fichier dans `bibliotheque/`
- 📤 Ouvrir l'export pour brackcheck.com
- 📋 Copier le decklist

---

## 🎨 Interface Utilisateur

### En-tête
```
🎴 MTG DeckGenPy
Générateur de Decks Commander
```

### Sections
1. **Sélection du Bracket** - Radio buttons avec descriptions
2. **Choix du Commandant** - Recherche + liste filtrable
3. **Filtre par Tribu** - Checkboxes multiples
4. **Génération** - Bouton + journal en temps réel
5. **Résultats** - Dialog avec statistiques et actions

---

## ⚙️ Configuration

Le fichier `conf/config.yaml` contrôle :
- Nombre de terrains (`total_lands: 37`)
- Cibles par catégorie (`ramp_target: 10`, etc.)
- Activation du filtre de tribu (`enable_tribe_selection: true`)
- Vérification des doublons (`check_existing_decks: true`)

---

## 🔍 Fonctionnalités Avancées

### Évitement des Doublons
- Vérification automatique dans `bibliotheque/`
- Exclusion des cartes déjà utilisées
- Les terrains de base sont ignorés

### Scoring Intelligent
- Synergie avec le commandant (tribus, thèmes)
- Forces/faiblesses des couleurs
- Utilité générale (ramp, draw, removal)
- Coût en mana optimisé

### Respect des Brackets
- Game Changers limités selon le bracket
- Tutors comptabilisés
- Combos infinis détectés
- Tours supplémentaires contrôlés

---

## 🛠️ Dépannage

### "Collection introuvable"
```bash
# Lancez le script d'enrichissement
python scripts/enriching_collection.py
```

### "Aucun commandant trouvé"
- Vérifiez que `data/collection_enriched.csv` existe
- Assurez-vous d'avoir des créatures légendaires dans votre collection

### L'interface ne se lance pas
```bash
# Vérifiez que NiceGUI est installé
pip install nicegui

# Ou réinstallez les dépendances
pip install -r requirements.txt
```

### Erreur de port 8080
- Modifiez le port dans `scripts/gui_app.py` :
```python
ui.run(port=8081)  # Changer 8080 par 8081
```

---

## 📁 Structure des Fichiers

```
MTG-DeckGenPy/
├── run_gui.bat              # Lancement rapide Windows
├── scripts/
│   └── gui_app.py           # Interface graphique
├── bibliotheque/            # Decks générés
├── exports/                 # Decklists formatées
└── logs/                    # Logs (si utilisation CLI)
```

---

## 🌐 Intégration

### Export pour brackcheck.com
Le fichier dans `exports/` est formaté pour :
- **brackcheck.com** - Analyse de bracket
- **Manabox.app** - Prix et disponibilité
- **EDHREC.com** - Statistiques communautaires

### Format d'Export
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
...

--- TERRAINS ---
10 Swamp
3 Mountain
1 Command Tower
...
```

---

## 💡 Astuces

1. **Commencez par le bracket 2 (Core)** pour un deck équilibré
2. **Utilisez le filtre de tribu** pour des decks thématiques
3. **Consultez le journal** pour comprendre les sélections
4. **Vérifiez l'export** sur brackcheck.com avant de jouer

---

## 🆚 CLI vs GUI

| Fonctionnalité | CLI (Terminal) | GUI (Interface) |
|----------------|----------------|-----------------|
| Sélection bracket | ✅ | ✅ |
| Choix commandant | ✅ | ✅ + Recherche |
| Filtre tribu | ✅ | ✅ + Multiple |
| Génération | ✅ | ✅ + Progress |
| Rapport bracket | ✅ | ✅ |
| Score puissance | ✅ | ❌ (à venir) |
| Logs fichier | ✅ | ❌ |
| Interface visuelle | ❌ | ✅ |

---

## 📞 Support

- **Issues GitHub** : Bugs et demandes de fonctionnalités
- **Documentation** : `README.md` pour la version CLI

---

**Bon jeu et bons decks ! 🎴**
