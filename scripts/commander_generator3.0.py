import pandas as pd
import random
import ast
import os
import re
import yaml
import sys
from datetime import datetime
from collections import Counter

# ==========================================
# CONFIGURATION DES CHEMINS
# ==========================================
# Le script est dans scripts/, donc on remonte d'un niveau
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Chemins absolus
CONFIG_PATH = os.path.join(BASE_DIR, "conf", "config.yaml")
COLLECTION_PATH = os.path.join(BASE_DIR, "data", "collection_enriched.csv")

# Dossiers de sortie
BIBLIO_DIR = os.path.join(BASE_DIR, "bibliotheque")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# Créer les dossiers nécessaires
os.makedirs(BIBLIO_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# ==========================================
# CONFIGURATION DU LOGGING (EFFET TEE)
# ==========================================
# Cette classe permet de capturer TOUTE la sortie console dans le log
class TeeHandler:
    """Redirige la sortie vers la console ET un fichier de log (comme tee -a)."""
    
    def __init__(self, *streams):
        self.streams = streams
    
    def write(self, text):
        for stream in self.streams:
            stream.write(text)
            stream.flush()
    
    def flush(self):
        for stream in self.streams:
            stream.flush()

# Compteurs globaux utilisés dans tout le script
deck_strategy_counts = Counter()
library_cards_used = {}  # nom normalisé -> dict(nom_fichier -> nombre)

# =============================
# GESTION DE LA CONFIGURATION
# =============================

def load_config(path=CONFIG_PATH):
    """Charge la configuration depuis le fichier YAML.
    Le fichier doit contenir toutes les clés requises.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Fichier de configuration {path!r} introuvable.\n"
                               f"Assurez-vous que conf/config.yaml existe dans le dossier principal.\n"
                               f"Tu peux copier conf/config.example.yaml vers conf/config.yaml")
    with open(path, "r", encoding="utf-8") as f:
        try:
            cfg = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise RuntimeError("Erreur de lecture de config.yaml") from e
    if not isinstance(cfg, dict):
        raise ValueError("config.yaml doit contenir un dictionnaire de paramètres")
    return cfg

# charger la configuration une fois
config = load_config()

# exposer les variables pratiques (lève KeyError si manquant)
LIB_DIR = BIBLIO_DIR  # Utiliser le dossier bibliotheque créé
TOTAL_LANDS = config["total_lands"]
BASIC_LAND_COUNT = config["basic_land_count"]
RAMP_TARGET = config["ramp_target"]
DRAW_TARGET = config["draw_target"]
REMOVAL_TARGET = config["removal_target"]
WIPE_TARGET = config["wipe_target"]
TOTAL_CARDS = config["total_cards"]
STRATEGY_KEYWORDS = config["strategy_keywords"]
RAMP_WORDS = config["ramp_words"]
DRAW_WORDS = config["draw_words"]
REMOVAL_WORDS = config["removal_words"]
WIPE_WORDS = config["wipe_words"]
BRACKET_PENALTIES = config["bracket_penalties"]
ENABLE_TRIBE_SELECTION = config.get("enable_tribe_selection", True)
CHECK_EXISTING_DECKS = config.get("check_existing_decks", True)


# =============================
# FONCTIONS UTILITAIRES
# =============================

def parse_colors(color_string):
    """Parse la chaîne de couleurs en un ensemble."""
    try:
        return set(ast.literal_eval(color_string))
    except Exception:
        return set()

def normalize_card_name(name: str) -> str:
    """Normalise le nom de la carte (supprime quantité, set, numéro, foil, minuscules).
    
    Formats supportés:
    - "1 Sol Ring"
    - "1 Sol Ring (C17) 35"
    - "1 Sol Ring (C17) 35 *F*"
    - "Sol Ring (M21) 242"
    
    Retourne uniquement le nom de la carte en minuscules.
    """
    name = str(name).strip()
    
    # Supprimer les commentaires
    if '//' in name:
        name = name.split('//')[0].strip()
    
    # Supprimer la quantité initiale si présente
    parts = name.split(maxsplit=1)
    if parts and parts[0].isdigit():
        name = parts[-1]
    
    # Supprimer les indicateurs foil (*F*, *FOIL*, etc.) - DOIT ÊTRE FAIT EN PREMIER
    name = re.sub(r'\s*\*[^*]*\*', '', name, flags=re.IGNORECASE)
    
    # Supprimer le set code entre parenthèses (XXX) où XXX est 2-5 lettres/chiffres
    name = re.sub(r'\s*\([A-Za-z0-9]{2,5}\)', '', name)
    
    # Supprimer les numéros de collecte en fin de ligne (chiffres seuls)
    name = re.sub(r'\s+\d+\s*$', '', name)
    
    # Nettoyer les espaces multiples et convertir en minuscules
    name = ' '.join(name.split()).lower()
    
    return name

def debug_normalize_card(name: str) -> str:
    """Version debug de normalize_card_name pour afficher ce qui se passe."""
    original = name
    name = str(name).strip()
    parts = name.split(maxsplit=1)
    if parts and parts[0].isdigit():
        name = parts[-1]
    result = name.lower()
    print(f"      [DEBUG] '{original}' → '{result}'")
    return result

def contains_any(text, keywords):
    """Vérifie si le texte contient l'un des mots-clés."""
    text = str(text).lower()
    return any(word in text for word in keywords)

# détecter les combos infinis potentiels dans l'oracle text
INFINITE_COMBO_KEYWORDS = [
    "infinite", "untap", "sacrifice a creature", "return from graveyard",
    "whenever you cast", "whenever a creature dies", "copy target",
    "exile target card from a graveyard", "you may cast it without paying",
    "whenever this creature deals combat damage", "deathtouch", "first strike",
    "double strike", "haste", "vigilance", "trample", "lifelink",
    "whenever you gain life", "whenever a token enters", "populate"
]

def detect_infinite_combo_potential(oracle_text):
    """Détecte si une carte a un potentiel de combo infini (2+ cartes)."""
    text = str(oracle_text).lower()
    # Compte les mots-clés de combo
    combo_count = sum(1 for kw in INFINITE_COMBO_KEYWORDS if kw in text)
    # Une carte avec 2+ mots-clés de combo est suspecte
    return combo_count >= 2

# détecter la négation de terrain (mass land destruction)
LAND_DESTRUCTION_KEYWORDS = [
    "destroy all lands", "destroy each land", "sacrifice a land",
    "bury all lands", "exile all lands", "destroy all nonbasic lands"
]

def detect_mass_land_destruction(oracle_text):
    """Détecte si une carte est une négation de terrain massive."""
    text = str(oracle_text).lower()
    return any(kw in text for kw in LAND_DESTRUCTION_KEYWORDS)

# détecter les tours supplémentaires
EXTRA_TURN_KEYWORDS = ["extra turn", "take another turn", "after this turn"]

def detect_extra_turn(oracle_text):
    """Détecte si une carte donne un tour supplémentaire."""
    text = str(oracle_text).lower()
    return any(kw in text for kw in EXTRA_TURN_KEYWORDS)

# détecter les tutors (recherche dans la bibliothèque)
TUTOR_KEYWORDS = ["search your library", "search your graveyard",
                  "put a card from your library", "tutor"]

def detect_tutor(oracle_text):
    """Détecte si une carte est un tutor."""
    text = str(oracle_text).lower()
    return any(kw in text for kw in TUTOR_KEYWORDS)

def card_strategies(text):
    """Calcule l'ensemble des stratégies pour un texte d'oracle donné."""
    return {s for s, kws in STRATEGY_KEYWORDS.items() if contains_any(text, kws)}

# =============================
# 1. CHARGER LA COLLECTION
# =============================

print(f"Chargement de la collection depuis : {COLLECTION_PATH}")
collection = pd.read_csv(COLLECTION_PATH)

# normaliser les noms de colonnes pour éviter les problèmes de casse/espaces
collection.columns = (collection.columns
                      .str.strip()
                      .str.lower()
                      .str.replace(' ', '_', regex=False))

collection["colors_parsed"] = collection["color_identity"].apply(parse_colors)

# =============================
# 2. DIFFICULTÉ (bracket officiel EDH)
# =============================

print("=== BRACKETS OFFICIELS COMMANDER ===")
print("1: Exhibition (Ultra-Casual)")
print("2: Core (Préconstruit)")
print("3: Upgraded (Amélioré)")
print("4: Optimized (Haute Puissance / cEDH)")
bracket_input = input("Entrez le bracket officiel (1-4) : ").strip()
try:
    BRACKET_LEVEL = int(bracket_input)
    if BRACKET_LEVEL < 1 or BRACKET_LEVEL > 4:
        raise ValueError
except ValueError:
    print("Bracket invalide, utilisation du niveau 2 (Core).")
    BRACKET_LEVEL = 2

# afficher les règles du bracket choisi si disponibles
bracket_desc = config.get("bracket_rules", {}).get(BRACKET_LEVEL)
if bracket_desc:
    print("\n--- Règles du bracket choisi ---")
    print(bracket_desc)
    print("--- fin des règles ---\n")

# charger les contraintes pour le bracket choisi ; vide par défaut
BRACKET_CONSTRAINTS = config.get("bracket_constraints", {}).get(BRACKET_LEVEL, {})

# fraction utilisée pour pénaliser les cartes à haut score (1=Exhibition -> 4=Optimized)
BRACKET_PENALTIES = config.get("bracket_penalties", {1: 0.6, 2: 0.3, 3: 0.1, 4: 0.0})
PENALTY = BRACKET_PENALTIES.get(BRACKET_LEVEL, 0.3)

# TOTAL_CARDS reste à 99 par défaut (peut être modifié manuellement ci-dessus)
# =============================
# 3. TROUVER LES COMMANDANTS
# =============================

# appliquer le filtre de commandant spécifique au bracket ; quantité >0 et créature légendaire
commanders = collection[
    (collection["type_line"].str.contains("Legendary Creature", na=False)) &
    (collection["quantity"] > 0)
]

if not commanders.empty:
    # fonction auxiliaire pour extraire les sous-types de créature depuis type_line
    def extract_tribes(tl):
        tl = str(tl).lower()
        if 'creature' not in tl:
            return []
        if '—' in tl:
            return [w.strip() for w in tl.split('—',1)[1].split()]
        return []

    def commander_strength(row):
        """Calcule le score de force d'un commandant."""
        text = str(row.get("oracle_text", "")).lower()
        mv = row.get("mana_value", 0)
        score = 0
        if contains_any(text, RAMP_WORDS):
            score += 1
        if contains_any(text, DRAW_WORDS):
            score += 1
        if contains_any(text, REMOVAL_WORDS):
            score += 1
        if contains_any(text, WIPE_WORDS):
            score += 1
        if "creature" in str(row.get("type_line", "")).lower():
            score += 1
        score -= mv * 0.1
        return score

    commanders = commanders.copy()
    # ajouter la colonne tribes pour l'affichage
    commanders["tribes"] = commanders["type_line"].apply(extract_tribes)
    commanders["strength_score"] = commanders.apply(commander_strength, axis=1)
    commanders = commanders.sort_values("strength_score")
    # calculer le bracket_group (1..4) basé sur la position pour les BRACKETS EDH OFFICIELS
    n = len(commanders)
    group_size = max(1, n // 4)  # 4 brackets au lieu de 5
    # assigner le numéro de groupe
    group_nums = []
    for idx in range(n):
        grp = min(4, idx // group_size + 1)
        group_nums.append(grp)
    commanders["bracket_group"] = group_nums
    # filtrer selon le niveau choisi
    if BRACKET_LEVEL == 1:
        commanders = commanders[commanders["bracket_group"] == 1]
    elif BRACKET_LEVEL == 4:
        commanders = commanders[commanders["bracket_group"] == 4]
    else:
        commanders = commanders[commanders["bracket_group"] == BRACKET_LEVEL]

# SUPPRIMER LES DOUBLONS (certains commandants peuvent apparaître plusieurs fois)
# Garder uniquement la première occurrence basée sur le nom
commanders = commanders.drop_duplicates(subset=['name'], keep='first')
print(f"\n🎯 {len(commanders)} commandants uniques disponibles pour le bracket {BRACKET_LEVEL}\n")

# menu de sélection interactif avec confirmation de l'oracle text
commander = None
while commander is None:
    print("Commandants disponibles :")
    for idx, row in commanders.reset_index(drop=True).iterrows():
        colors = row.get('colors_parsed', set())
        bracket_grp = row.get('bracket_group', '?')
        tribes = row.get('tribes', [])
        tribe_str = f" [{' '.join(tribes)}]" if tribes else ""
        print(f"{idx+1}. {row['name']}{tribe_str} [bracket {bracket_grp}] ({','.join(sorted(colors))})")
    try:
        choice = int(input("Entrez le numéro du commandant à utiliser : ")) - 1
        if choice < 0 or choice >= len(commanders):
            print("Numéro invalide, recommencez.")
            continue
    except ValueError:
        print("Veuillez entrer un nombre.")
        continue

    candidate = commanders.iloc[choice]
    print("\nOracle text du commandant sélectionné :")
    print(candidate.get('oracle_text', '(aucun texte)'))
    confirm = input("Confirmer ce commandant ? (o/n) : ").strip().lower()
    if confirm.startswith('o'):
        commander = candidate
        commander_colors = commander["colors_parsed"]
        print("Commandant choisi :", commander["name"])
        print("Bracket :", commander.get('bracket_group'))
        ctribes = extract_tribes(commander.get('type_line',""))
        if ctribes:
            print("Tribu(s) :", ",".join(ctribes))
        print("Couleurs :", commander_colors)
        # initialiser les compteurs de stratégie avec les thèmes du commandant
        # pour favoriser les cartes synergiques
        commander_strats = card_strategies(commander.get('oracle_text', ''))
        for s in commander_strats:
            deck_strategy_counts[s] += 1
    else:
        print("Choix annulé, veuillez sélectionner un autre commandant.\n")

# =============================
# 4. FILTRER LES CARTES LÉGALES
# =============================

legal_cards = collection[
    collection["colors_parsed"].apply(lambda c: c.issubset(commander_colors))
].copy()

legal_cards = legal_cards[legal_cards["name"] != commander["name"]]

# demander à l'utilisateur s'il veut se restreindre à une tribu/thème
# cette étape peut être désactivée via config.yaml
if ENABLE_TRIBE_SELECTION:
    # calculer les mots de tribus distincts depuis le type_line des cartes légales
    all_types = legal_cards["type_line"].dropna().str.lower().unique()
    # afficher aussi les tribus du commandant pour aider la sélection
    comm_tribes = extract_tribes(commander.get('type_line',""))
    if comm_tribes:
        print(f"Tribu(s) du commandant : {', '.join(comm_tribes)}")
    tribe_set = set()
    for tl in all_types:
        # les types de créature viennent après le tiret '—'
        parts = tl.split('—')
        if len(parts) > 1:
            types = parts[1]
        else:
            types = parts[0]
        for word in re.split(r"[^a-z]+", types):
            if word:
                tribe_set.add(word)
    tribes_list = sorted(tribe_set)
    if tribes_list:
        print("Tribus disponibles :")
        for idx, tr in enumerate(tribes_list, start=1):
            print(f"{idx}. {tr}")
        sel = input("Sélectionnez un ou plusieurs numéros (ex. 1-3,5) ou laissez vide pour aucune restriction : ").strip()
        if sel:
            chosen = set()
            for part in sel.split(','):
                if '-' in part:
                    a,b = part.split('-',1)
                    try:
                        a=int(a); b=int(b)
                        for i in range(a,b+1):
                            if 1 <= i <= len(tribes_list): chosen.add(tribes_list[i-1])
                    except ValueError:
                        continue
                else:
                    try:
                        i=int(part)
                        if 1 <= i <= len(tribes_list): chosen.add(tribes_list[i-1])
                    except ValueError:
                        continue
            if chosen:
                # appliquer le filtre de tribu uniquement aux cartes de créature
                mask = legal_cards["type_line"].str.lower().apply(
                    lambda tl: ("creature" in tl and any(tr in tl for tr in chosen))
                )
                legal_cards = legal_cards[mask]
                print(f"Application du filtre tribu : {', '.join(chosen)} -> {len(legal_cards)} cartes restantes")
    else:
        print("Aucune tribu détectée dans la collection.")
else:
    print("Sélection de tribu désactivée (via config.yaml).")

# appliquer les contraintes de bracket pour éliminer les options illégales (RÈGLES EDH OFFICIELLES)
gc_list = set(config.get("game_changers", []))
max_gc = BRACKET_CONSTRAINTS.get("max_game_changers")
allow_infinite_combos = BRACKET_CONSTRAINTS.get("allow_infinite_combos", False)
allow_mass_land_destruction = BRACKET_CONSTRAINTS.get("allow_mass_land_destruction", False)
allow_extra_turns = BRACKET_CONSTRAINTS.get("allow_extra_turns", False)

# game changers : exclure entièrement si max_game_changers == 0
if max_gc == 0 and gc_list:
    legal_cards = legal_cards[~legal_cards["name"].isin(gc_list)]

# cartes à tour supplémentaire : exclure si non autorisé
if not allow_extra_turns:
    legal_cards = legal_cards[~legal_cards["oracle_text"].apply(detect_extra_turn)]
    print("Filtre: cartes à tour supplémentaire exclues.")

# négation de terrain massive : exclure si non autorisé
if not allow_mass_land_destruction:
    legal_cards = legal_cards[~legal_cards["oracle_text"].apply(detect_mass_land_destruction)]
    print("Filtre: négation de terrain massive exclue.")

# combos infinis : exclure les cartes à potentiel de combo si non autorisé
if not allow_infinite_combos:
    legal_cards = legal_cards[~legal_cards["oracle_text"].apply(detect_infinite_combo_potential)]
    print("Filtre: cartes à potentiel de combo infini exclues.")

# les tutors sont gérés pendant le comptage dans pick_unique

# =============================
# 5. DÉTECTER LA STRATÉGIE
# =============================

strategy_scores = {}

for strategy, keywords in STRATEGY_KEYWORDS.items():
    score = sum(contains_any(commander["oracle_text"], keywords) for _ in keywords)
    strategy_scores[strategy] = score

detected_strategy = max(strategy_scores, key=strategy_scores.get)

print("Stratégie détectée :", detected_strategy)

# =============================
# 6. SCORING INTELLIGENT DES CARTES
# =============================

# Définition des forces/faiblesses par couleur
COLOR_STRENGTHS = {
    'W': {  # Blanc
        'strong': ['tokens', 'lifegain', 'wipe', 'removal'],
        'weak': ['draw', 'ramp'],
        'bonus_cards': ['token', 'sacrifice', 'gain life', 'protection']
    },
    'U': {  # Bleu
        'strong': ['draw', 'counters', 'spellslinger'],
        'weak': ['removal', 'ramp'],
        'bonus_cards': ['draw', 'counter', 'bounce', 'instant', 'sorcery']
    },
    'B': {  # Noir
        'strong': ['removal', 'graveyard', 'tutors'],
        'weak': ['wipe'],
        'bonus_cards': ['graveyard', 'sacrifice', 'dies', 'destroy']
    },
    'R': {  # Rouge
        'strong': ['ramp', 'removal', 'spellslinger'],
        'weak': ['draw', 'graveyard'],
        'bonus_cards': ['dragon', 'warrior', 'direct damage', 'sacrifice']
    },
    'G': {  # Vert
        'strong': ['ramp', 'tokens', 'counters'],
        'weak': ['removal', 'draw'],
        'bonus_cards': ['ramp', 'token', 'creature', '+1/+1', 'trample']
    }
}

# Mots-clés de synergies par type de commandant
COMMANDANT_SYNERGIES = {
    'tokens': ['token', 'create', 'populate', 'army', 'soldier', 'wizard', 'clue'],
    'graveyard': ['graveyard', 'dies', 'sacrifice', 'mill', 'return', 'reanimate'],
    'artifacts': ['artifact', 'equip', 'construct', 'modular'],
    'counters': ['counter', '+1/+1', 'charge', 'time'],
    'lifegain': ['gain life', 'lifelink', 'soulbond'],
    'spellslinger': ['instant', 'sorcery', 'copy', 'cascade'],
    'dragons': ['dragon', 'flying', 'legendary'],
    'vampires': ['vampire', 'lifegain', 'sacrifice'],
    'zombies': ['zombie', 'graveyard', 'mill'],
    'elves': ['elf', 'druid', 'ramp', 'token'],
    'goblins': ['goblin', 'sacrifice', 'token'],
    'wizards': ['wizard', 'instant', 'sorcery', 'draw']
}

def extraire_tribus_commandant(commander_row):
    """Extrait les tribus et thèmes du commandant."""
    tribus = []
    themes = []
    
    # Extraire les tribus du type_line
    type_line = str(commander_row.get('type_line', '')).lower()
    if '—' in type_line:
        tribus = [t.strip() for t in type_line.split('—')[1].split()]
    
    # Extraire les thèmes de l'oracle_text
    oracle_text = str(commander_row.get('oracle_text', '')).lower()
    
    for theme, keywords in COMMANDANT_SYNERGIES.items():
        if any(kw in oracle_text for kw in keywords):
            themes.append(theme)
    
    return tribus, themes

def calculer_synergie_commandant(carte_row, commander_tribus, commander_themes):
    """Calcule le score de synergie d'une carte avec le commandant."""
    synergie = 0
    texte = str(carte_row.get('oracle_text', '')).lower()
    type_line = str(carte_row.get('type_line', '')).lower()
    nom = str(carte_row.get('name', '')).lower()
    
    # Bonus pour les tribus du commandant
    for tribu in commander_tribus:
        if tribu in type_line:
            synergie += 5  # Fort bonus pour la tribu
    
    # Bonus pour les thèmes du commandant
    for theme in commander_themes:
        keywords = COMMANDANT_SYNERGIES.get(theme, [])
        if any(kw in texte or kw in nom for kw in keywords):
            synergie += 3  # Bonus pour la synergie thématique
    
    # Bonus pour les cartes qui mentionnent le nom du commandant (partners, etc.)
    if 'partner' in texte and len(commander_tribus) > 0:
        synergie += 2
    
    return synergie

def calculer_bonus_couleur(carte_row, couleurs_commandant):
    """Calcule le bonus/malus basé sur les couleurs du commandant."""
    bonus = 0
    texte = str(carte_row.get('oracle_text', '')).lower()
    type_line = str(carte_row.get('type_line', '')).lower()
    
    # Pour chaque couleur du commandant, appliquer les forces
    for couleur in couleurs_commandant:
        forces = COLOR_STRENGTHS.get(couleur, {}).get('strong', [])
        faiblesses = COLOR_STRENGTHS.get(couleur, {}).get('weak', [])
        bonus_cartes = COLOR_STRENGTHS.get(couleur, {}).get('bonus_cards', [])
        
        # Bonus si la carte correspond aux forces de la couleur
        for force in forces:
            if force in COMMANDANT_SYNERGIES:
                if any(kw in texte for kw in COMMANDANT_SYNERGIES[force]):
                    bonus += 1
        
        # Bonus pour les cartes clés de la couleur
        for mot_cle in bonus_cartes:
            if mot_cle in texte or mot_cle in type_line:
                bonus += 0.5
    
    # Malus si la carte correspond aux faiblesses de la couleur
    # (le script sera moins enclin à sélectionner ces cartes)
    for couleur in couleurs_commandant:
        faiblesses = COLOR_STRENGTHS.get(couleur, {}).get('weak', [])
        for faiblesse in faiblesses:
            if faiblesse in COMMANDANT_SYNERGIES:
                if any(kw in texte for kw in COMMANDANT_SYNERGIES[faiblesse]):
                    bonus -= 0.5  # Léger malus
    
    return bonus

def score_card(row, commander_tribus=None, commander_themes=None, couleurs_commandant=None):
    """Calcule le score intelligent d'une carte.
    
    Prend en compte:
    - Synergie avec le commandant (tribus, thèmes)
    - Forces/faiblesses des couleurs
    - Utilité générale (ramp, draw, removal, wipe)
    - Coût en mana
    - Type de carte
    """
    score = 0
    texte = str(row["oracle_text"]).lower()
    mv = row["mana_value"]
    type_line = str(row["type_line"]).lower()
    
    # 1. Synergie avec le commandant (PRIORITÉ MAX)
    if commander_tribus and commander_themes:
        synergie_cmd = calculer_synergie_commandant(row, commander_tribus, commander_themes)
        score += synergie_cmd * 2  # Multiplicateur pour prioriser les synergies
    
    # 2. Bonus/malus des couleurs
    if couleurs_commandant:
        bonus_couleur = calculer_bonus_couleur(row, couleurs_commandant)
        score += bonus_couleur
    
    # 3. Synergie avec la stratégie détectée
    if contains_any(texte, STRATEGY_KEYWORDS.get(detected_strategy, [])):
        score += 4  # Augmenté de 3 à 4
    
    # 4. Utilité générale (ramp, draw, removal, wipe)
    if contains_any(texte, RAMP_WORDS):
        score += 3  # Augmenté de 2 à 3 (ramp très important)
    
    if contains_any(texte, DRAW_WORDS):
        score += 3  # Augmenté de 2 à 3 (draw très important)
    
    if contains_any(texte, REMOVAL_WORDS):
        score += 2
    
    if contains_any(texte, WIPE_WORDS):
        score += 4  # Augmenté de 3 à 4 (wipes rares et puissants)
    
    # 5. Bonus pour les créatures (plus interactif)
    if "creature" in type_line:
        score += 1.5  # Augmenté de 1 à 1.5
        
        # Bonus supplémentaire pour les créatures avec capacités
        if 'whenever' in texte or 'enter the battlefield' in texte:
            score += 1
    
    # 6. Bonus pour les artifacts utiles
    if "artifact" in type_line and "equipment" not in type_line:
        if contains_any(texte, RAMP_WORDS) or contains_any(texte, DRAW_WORDS):
            score += 2
    
    # 7. Pénalité progressive selon le coût en mana
    if mv >= 7:
        score -= 3  # Augmenté de 2 à 3
    elif mv >= 6:
        score -= 1.5
    elif mv >= 5:
        score -= 0.5
    
    # 8. Bonus pour les cartes à faible coût (plus consistantes)
    if mv <= 2:
        score += 1
    elif mv <= 3:
        score += 0.5
    
    # 9. Bonus pour les cartes légendaires (synergie potentielle)
    if "legendary" in type_line:
        score += 1
    
    return score

# Extraire les tribus et thèmes du commandant une fois pour toutes
commander_tribus, commander_themes = extraire_tribus_commandant(commander)
print(f"\n🎯 Synergies du commandant détectées :")
if commander_tribus:
    print(f"   Tribus : {', '.join(commander_tribus)}")
if commander_themes:
    print(f"   Thèmes : {', '.join(commander_themes)}")
print()

# Calculer le score intelligent pour toutes les cartes
legal_cards["score"] = legal_cards.apply(
    lambda row: score_card(row, commander_tribus, commander_themes, commander_colors),
    axis=1
)

# calculer l'ensemble des stratégies pour chaque carte
legal_cards = legal_cards.copy()
legal_cards["strategies"] = legal_cards["oracle_text"].apply(card_strategies)
legal_cards = legal_cards.sort_values(by="score", ascending=False)

# Afficher les meilleures cartes pour le deck
print("🃏 TOP 10 DES MEILLEURES CARTES POUR CE DECK :")
print("-" * 60)
top_10 = legal_cards.head(10)
for idx, row in top_10.iterrows():
    score = row['score']
    nom = row['name']
    mv = row['mana_value']
    strategies = row.get('strategies', set())
    print(f"   {idx+1}. {nom} (score: {score:.1f}, mana: {mv})")
    if strategies:
        print(f"      Synergies : {', '.join(strategies)}")
print()


# =============================
# 7. CONSTRUCTION DU DECK
# =============================

# fonction auxiliaire pour détecter les terrains de base (règle Commander)
basic_land_names = {"plains", "island", "swamp", "mountain", "forest"}

def is_basic_land(row):
    """Vérifie si une carte est un terrain de base."""
    tl = str(row.get("type_line", "")).lower()
    name = str(row.get("name", "")).strip().lower()
    return "basic land" in tl or name in basic_land_names

# compteurs de contraintes pour le deck actuel
constraint_stats = {"game_changers": 0, "tutors": 0, "extra_turns": 0}

# Liste pour tracker les cartes exclues (doublons avec la bibliothèque)
excluded_cards = []  # [{carte: nom, decks: [liste de decks]}]

def pick_unique(df, limit, used):
    """Sélectionne jusqu'à `limit` cartes uniques depuis un dataframe.
    
    Utilise une sélection gloutonne en prenant toujours la carte avec
    le meilleur score ajusté, en respectant les contraintes de bracket.
    """
    picked = []
    available = df.copy()
    while len(picked) < limit and not available.empty:
        # filtrer les doublons et les cartes déjà dans la bibliothèque
        mask = ~available["name"].str.lower().isin(used)
        if mask.any():
            available = available[mask]
        else:
            break

        # calculer le score ajusté en fonction des stratégies du deck
        def adj_score(row):
            # Utiliser combined_score s'il existe (pour les terrains), sinon score normal
            base = row.get("combined_score", row.get("score", 0))
            # appliquer la pénalité de difficulté : les brackets faciles réduisent le score
            base = base * (1 - PENALTY)
            sy = sum(deck_strategy_counts.get(s, 0) for s in row.get("strategies", []))
            return base + sy
        available = available.copy()
        available["adj_score"] = available.apply(adj_score, axis=1)

        # sélectionner le meilleur candidat
        best = available.sort_values("adj_score", ascending=False).iloc[0]

        # appliquer les contraintes de bracket avant d'ajouter la carte
        name = best["name"]
        oracle = str(best.get("oracle_text", "")).lower()
        
        # game changers : vérifier si on a atteint la limite
        if max_gc is not None and max_gc != 0:
            if name in gc_list and constraint_stats["game_changers"] >= max_gc:
                available = available[available["name"] != name]
                continue
        elif max_gc == 0:
            # brackets 1-2 : aucun game changer autorisé
            if name in gc_list:
                available = available[available["name"] != name]
                continue
        
        # tutors : vérifier si on a atteint la limite
        max_t = BRACKET_CONSTRAINTS.get("max_tutors")
        is_tutor = detect_tutor(oracle)
        if max_t is not None and max_t != 0:
            if is_tutor and constraint_stats["tutors"] >= max_t:
                available = available[available["name"] != name]
                continue
        elif max_t == 0:
            # aucun tutor autorisé
            if is_tutor:
                available = available[available["name"] != name]
                continue
        
        # cartes à tour supplémentaire : vérifier si autorisé et limite
        max_extra = BRACKET_CONSTRAINTS.get("max_extra_turns")
        is_extra_turn = detect_extra_turn(oracle)
        if is_extra_turn:
            if not allow_extra_turns:
                available = available[available["name"] != name]
                continue
            if max_extra is not None and max_extra != 0 and constraint_stats["extra_turns"] >= max_extra:
                available = available[available["name"] != name]
                continue
        
        # négation de terrain massive : vérifier si autorisé
        is_mld = detect_mass_land_destruction(oracle)
        if is_mld and not allow_mass_land_destruction:
            available = available[available["name"] != name]
            continue
        
        # potentiel de combo infini : vérifier si autorisé
        is_combo = detect_infinite_combo_potential(oracle)
        if is_combo and not allow_infinite_combos:
            available = available[available["name"] != name]
            continue

        lname = normalize_card_name(name)
        # si c'est un terrain de base, ignorer la restriction de bibliothèque
        # Cette vérification n'est faite que si CHECK_EXISTING_DECKS est True
        if CHECK_EXISTING_DECKS and lname in library_cards_used and not is_basic_land(best):
            origins = library_cards_used.get(lname, {})
            info = ", ".join(f"{fn}({cnt})" for fn,cnt in origins.items())
            print(f"Carte déjà présente dans {info}, exclue : {name}")
            # Tracker la carte exclue pour l'analyse
            excluded_cards.append({
                'carte': name,
                'decks': list(origins.keys()),
                'count': sum(origins.values())
            })
            # retirer cette carte et continuer
            available = available[available["name"] != name]
            continue

        picked.append(name)
        used.add(lname)
        # mettre à jour les compteurs de stratégie
        for s in best.get("strategies", []):
            deck_strategy_counts[s] += 1
        # mettre à jour les compteurs de contraintes
        if name in gc_list:
            constraint_stats["game_changers"] += 1
        if is_tutor:
            constraint_stats["tutors"] += 1
        if is_extra_turn:
            constraint_stats["extra_turns"] += 1
        # retirer la carte sélectionnée des disponibles
        available = available[available["name"] != name]
    return picked

# préparer les variables pour la construction du deck
used_names = set()
deck = []

# réinitialiser les compteurs de stratégie pour le deck actuel
deck_strategy_counts = Counter()

# construire la carte des cartes déjà présentes dans les decks de la bibliothèque
# -> {nom_normalisé: {nom_fichier: nombre}}
# Cette étape est TOUJOURS effectuée (pour info même si check_existing_decks: false)
library_cards_used = {}
library_check_done = False

print("\n📚 VÉRIFICATION DES DECKS EXISTANTS DANS LA BIBLIOTHÈQUE...")
if os.path.isdir(LIB_DIR):
    decks_trouves = []
    for fname in os.listdir(LIB_DIR):
        # Ignorer le deck en cours de création
        current_filename = os.path.basename(filename) if "filename" in locals() else ""
        if fname == current_filename:
            continue

        path = os.path.join(LIB_DIR, fname)
        if not os.path.isfile(path):
            continue

        decks_trouves.append(fname)
        
        # essayer plusieurs encodages pour la compatibilité
        for enc in ['utf-8', 'cp1252', 'latin-1']:
            try:
                with open(path, 'r', encoding=enc) as lp:
                    cartes_lues = 0
                    for line in lp:
                        line = line.strip()
                        if not line or line.startswith("//"):
                            continue
                        # normaliser le nom de la carte (supprimer la quantité)
                        lname = normalize_card_name(line)
                        if lname not in library_cards_used:
                            library_cards_used[lname] = {}
                        library_cards_used[lname][fname] = library_cards_used[lname].get(fname, 0) + 1
                        cartes_lues += 1
                    print(f"   📄 {fname}: {cartes_lues} cartes lues")
                break  # lecture réussie, passer au fichier suivant
            except UnicodeDecodeError:
                continue  # essayer l'encodage suivant

    nb_decks = len(decks_trouves)
    nb_cartes_uniques = len(library_cards_used)
    print(f"   📊 Total: {nb_decks} deck(s), {nb_cartes_uniques} cartes uniques déjà utilisées")
    library_check_done = True
else:
    print("   Bibliothèque introuvable, aucune vérification effectuée")

# Si check_existing_decks est false, on affiche un warning mais on continue
if not CHECK_EXISTING_DECKS:
    print("\n⚠️  VÉRIFICATION DES DOUBLONS DÉSACTIVÉE (config.yaml)")
    print("   Les cartes seront sélectionnées SANS éviter les doublons")

# d'abord ajouter un nombre fixe de terrains de base (hors collection)
# Gestion INTELLIGENTE de la mana base selon les couleurs du commandant
color_to_basic = {"W": "plains", "U": "island", "B": "swamp",
                  "R": "mountain", "G": "forest"}

# Calculer la répartition des terrains de base selon les couleurs
allowed_basics = [color_to_basic[c] for c in commander_colors if c in color_to_basic]
if not allowed_basics:
    allowed_basics = list(basic_land_names)

# Répartir les terrains de base proportionnellement aux couleurs
# Pour un commandant 2 couleurs : 5/5
# Pour un commandant 3 couleurs : 3/3/4
# Pour un commandant 4 couleurs : 2/2/3/3
nb_couleurs = len(allowed_basics)
terrains_par_couleur = BASIC_LAND_COUNT // nb_couleurs
reste = BASIC_LAND_COUNT % nb_couleurs

print(f"\n🏔️  CONSTRUCTION DE LA MANA BASE ({len(commander_colors)} couleurs)")
print("-" * 50)

for i, couleur in enumerate(allowed_basics):
    # Ajouter un terrain supplémentaire pour les premières couleurs s'il y a un reste
    nombre = terrains_par_couleur + (1 if i < reste else 0)
    for j in range(nombre):
        deck.append(couleur.capitalize())
    print(f"   {couleur.capitalize()}: {nombre} terrains")

print(f"   Total terrains de base: {len([c for c in deck if c.lower() in basic_land_names])}")
print()

# ensuite sélectionner les terrains restants depuis la collection, hors terrains de base
# Priorité aux terrains qui produisent plusieurs couleurs et ont des utilités
# IMPORTANT: On combine le score intelligent (synergies) avec le score terrain (utilité)
special_lands = legal_cards[
    (legal_cards["type_line"].str.contains("Land", na=False)) &
    ~legal_cards["name"].str.lower().isin(basic_land_names)
].copy()

# Score bonus pour les terrains selon leur utilité
def score_terrain(row):
    """Score les terrains par utilité."""
    score = 0
    texte = str(row.get('oracle_text', '')).lower()
    
    # Terrain qui produit plusieurs couleurs
    if 'add' in texte and texte.count('{') >= 2:
        score += 3
    elif 'add' in texte:
        score += 1
    
    # Terrain avec capacité utile
    if 'draw' in texte:
        score += 2
    if 'search' in texte:
        score += 2
    if 'gain life' in texte:
        score += 1
    if 'tap' in texte and 'untap' in texte:
        score += 2
    
    # Terrain légendaire (Command Tower, etc.)
    if 'legendary' in str(row.get('type_line', '')).lower():
        score += 1
    
    # Terrain qui entre untapped
    if 'enters the battlefield tapped' not in texte:
        score += 1
    
    return score

if not special_lands.empty:
    # Ajouter le score terrain au score intelligent existant
    special_lands['terrain_score'] = special_lands.apply(score_terrain, axis=1)
    # COMBINER les deux scores : score intelligent + score terrain
    # Le score intelligent inclut déjà les synergies avec le commandant
    if 'score' in special_lands.columns:
        special_lands['combined_score'] = special_lands['score'] + special_lands['terrain_score']
        special_lands = special_lands.sort_values('combined_score', ascending=False)
        print(f"\n🏔️  SÉLECTION DES TERRAINS SPÉCIAUX ({TOTAL_LANDS - BASIC_LAND_COUNT} cartes) - Top score combiné")
    else:
        special_lands = special_lands.sort_values('terrain_score', ascending=False)
        print(f"\n🏔️  SÉLECTION DES TERRAINS SPÉCIAUX ({TOTAL_LANDS - BASIC_LAND_COUNT} cartes) - Top utilité")

deck += pick_unique(special_lands, TOTAL_LANDS - BASIC_LAND_COUNT, used_names)

# marquer les types de terrains de base choisis dans used_names pour éviter les doublons
for bl in allowed_basics:
    used_names.add(bl.lower())

nonlands = legal_cards[~legal_cards["type_line"].str.contains("Land", na=False)]

# ==========================================
# SÉLECTION INTELLIGENTE PAR CATÉGORIE
# ==========================================
# IMPORTANT: On sélectionne les MEILLEURES cartes de chaque catégorie
# en se basant sur le score INTELLIGENT calculé plus haut (synergies, couleurs, etc.)

# Ajuster les cibles selon les couleurs du commandant
# Certaines couleurs ont plus de mal à trouver certaines cartes
ramp_adjust = 0
draw_adjust = 0
removal_adjust = 0
wipe_adjust = 0

# Le vert a beaucoup de ramp, le bleu a beaucoup de draw
if 'G' in commander_colors:
    ramp_adjust = 2  # Plus de ramp disponible
if 'U' in commander_colors:
    draw_adjust = 2  # Plus de draw disponible
if 'W' in commander_colors:
    wipe_adjust = 1  # Blanc a plus de wipes
if 'B' in commander_colors:
    removal_adjust = 2  # Noir a beaucoup de removal

# Ramp (accélération de mana) - PRIORITÉ ÉLEVÉE
# Filtrer les cartes ramp ET pré-server leur score intelligent
ramp_cards = nonlands[nonlands["oracle_text"].str.contains('|'.join(RAMP_WORDS), na=False)].copy()
if not ramp_cards.empty and 'score' in ramp_cards.columns:
    ramp_cards = ramp_cards.sort_values('score', ascending=False)
ramp_cible = max(0, RAMP_TARGET + ramp_adjust)
print(f"\n⚡ SÉLECTION DU RAMP (cible: {ramp_cible} cartes) - Top score")
deck += pick_unique(ramp_cards, ramp_cible, used_names)

# Draw (pioche) - PRIORITÉ ÉLEVÉE
# Filtrer les cartes draw ET pré-server leur score intelligent
draw_cards = nonlands[nonlands["oracle_text"].str.contains('|'.join(DRAW_WORDS), na=False)].copy()
if not draw_cards.empty and 'score' in draw_cards.columns:
    draw_cards = draw_cards.sort_values('score', ascending=False)
draw_cible = max(0, DRAW_TARGET + draw_adjust)
print(f"📚 SÉLECTION DE LA PIOCHE (cible: {draw_cible} cartes) - Top score")
deck += pick_unique(draw_cards, draw_cible, used_names)

# Removal (élimination de menaces)
# Filtrer les cartes removal ET pré-server leur score intelligent
removal_cards = nonlands[nonlands["oracle_text"].str.contains('|'.join(REMOVAL_WORDS), na=False)].copy()
if not removal_cards.empty and 'score' in removal_cards.columns:
    removal_cards = removal_cards.sort_values('score', ascending=False)
removal_cible = max(0, REMOVAL_TARGET + removal_adjust)
print(f"⚔️  SÉLECTION DU REMOVAL (cible: {removal_cible} cartes) - Top score")
deck += pick_unique(removal_cards, removal_cible, used_names)

# Wipes (destruction de board)
# Filtrer les cartes wipe ET pré-server leur score intelligent
wipe_cards = nonlands[nonlands["oracle_text"].str.contains('|'.join(WIPE_WORDS), na=False)].copy()
if not wipe_cards.empty and 'score' in wipe_cards.columns:
    wipe_cards = wipe_cards.sort_values('score', ascending=False)
print(f"💥 SÉLECTION DES WIPES (cible: {WIPE_TARGET} cartes) - Top score")
deck += pick_unique(wipe_cards, WIPE_TARGET, used_names)

# Compléter avec les meilleures cartes restantes (synergies prioritaires)
# Ces cartes sont DÉJÀ triées par score intelligent
remaining = TOTAL_CARDS - len(deck)
print(f"🎴 COMPLÉMENT AVEC LES MEILLEURES CARTES RESTANTES ({remaining} cartes)")
others = nonlands[~nonlands["name"].str.lower().isin(used_names)].copy()
if not others.empty and 'score' in others.columns:
    others = others.sort_values('score', ascending=False)
deck += pick_unique(others, remaining, used_names)

print(f"\n✅ DECK COMPLÉTÉ : {len(deck)} cartes")

# =============================
# 8. EXPORT DU DECK
# =============================

# noms des brackets officiels
BRACKET_NAMES = {
    1: "Exhibition (Ultra-Casual)",
    2: "Core (Préconstruit)",
    3: "Upgraded (Amélioré)",
    4: "Optimized (Haute Puissance)"
}

# préparer la liste du deck et le nom du commandant
final_deck = deck[:TOTAL_CARDS]
commander_name = commander["name"]

# Configuration du logging pour ce deck (EFFET TEE - comme shell tee -a)
safe_name = re.sub(r"[^A-Za-z0-9]+", "-", commander_name).strip("-")
log_filename = os.path.join(LOGS_DIR, f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Ouvrir le fichier de log
log_file = open(log_filename, "w", encoding="utf-8")

# Créer le handler Tee qui écrit à la fois dans la console ET le fichier
tee = TeeHandler(sys.stdout, log_file)

# Rediriger toute la sortie print() vers le Tee
sys.stdout = tee

# Les messages importants sont déjà affichés via print()
# Tout sera automatiquement capturé dans le log grâce au Tee

# si le filtrage ou le manque de cartes a produit moins que prévu, demander à l'utilisateur
missing = TOTAL_CARDS - len(final_deck)
if missing > 0:
    print(f"Attention : le deck ne comporte que {len(final_deck)} cartes, il en manque {missing}.")
    extras = input("Entrez des noms de cartes à ajouter (séparés par des virgules), ou laissez vide pour ignorer : ").strip()
    if extras:
        for name in extras.split(','):
            name = name.strip()
            if name:
                final_deck.append(name)
        if len(final_deck) < TOTAL_CARDS:
            print(f"Il manque encore {TOTAL_CARDS-len(final_deck)} cartes après ajout.")
    else:
        print("Aucun ajout manuel effectué.")

# s'assurer que le répertoire de la bibliothèque existe
# LIB_DIR est déjà défini plus haut avec le chemin absolu
os.makedirs(LIB_DIR, exist_ok=True)

# nettoyer le nom du commandant pour le nom de fichier : supprimer les caractères spéciaux
safe_name = re.sub(r"[^A-Za-z0-9]+", "-", commander_name).strip("-")
filename = os.path.join(LIB_DIR, f"{safe_name}.txt")

# vérifier si le fichier existe déjà
if os.path.exists(filename):
    answer = input(f"Un deck pour '{commander_name}' existe déjà. Le régénérer ? (o/n) : ").strip().lower()
    if not answer.startswith('o'):
        print("Utilisation du deck existant, aucune modification apportée.")
        exit(0)

with open(filename, "w", encoding="utf-8") as f:
    # marqueur de commentaire pour l'import Manabox
    f.write("// COMMANDER\n")
    # écrire le commandant sur sa propre ligne
    f.write(f"{commander_name}\n")
    # enregistrer le bracket de difficulté choisi (brackets EDH officiels)
    bracket_name = BRACKET_NAMES.get(BRACKET_LEVEL, f"Bracket {BRACKET_LEVEL}")
    f.write(f"// EDH Bracket: {bracket_name}\n")
    f.write(f"// niveau de bracket: {BRACKET_LEVEL}\n")
    # ajouter un résumé des contraintes
    max_gc_str = str(BRACKET_CONSTRAINTS.get('max_game_changers')) if BRACKET_CONSTRAINTS.get('max_game_changers') else "illimité"
    max_tutors_str = str(BRACKET_CONSTRAINTS.get('max_tutors')) if BRACKET_CONSTRAINTS.get('max_tutors') else "illimité"
    max_extra_str = str(BRACKET_CONSTRAINTS.get('max_extra_turns')) if BRACKET_CONSTRAINTS.get('max_extra_turns') else "illimité"
    f.write(f"// game_changers utilisés: {constraint_stats['game_changers']}/{max_gc_str}\n")
    f.write(f"// tutors utilisés: {constraint_stats['tutors']}/{max_tutors_str}\n")
    f.write(f"// tours supplémentaires utilisés: {constraint_stats['extra_turns']}/{max_extra_str}\n")
    # ligne blanche séparatrice
    f.write("\n")

    # écrire le reste des cartes avec les quantités
    counts = Counter(final_deck)
    for name, cnt in counts.items():
        f.write(f"{cnt} {name}\n")

print(f"Deck généré et sauvegardé dans '{filename}' !")
# export_status et score_puissance seront affichés plus tard
print("=" * 60)

# =============================
# 9. VÉRIFICATION DU BRACKET
# =============================

def analyser_conformite_bracket(deck_cards, bracket_level, bracket_constraints):
    """Analyse la conformité du deck par rapport au bracket ciblé.

    Retourne un dictionnaire avec les statistiques et la conformité.
    """
    rapport = {
        'bracket_cible': bracket_level,
        'game_changers': 0,
        'game_changers_list': [],  # liste des noms de cartes
        'max_game_changers': bracket_constraints.get('max_game_changers'),
        'tutors': 0,
        'tutors_list': [],  # liste des noms de cartes
        'max_tutors': bracket_constraints.get('max_tutors'),
        'combos_infinis': 0,
        'combos_list': [],
        'tours_supplementaires': 0,
        'destruction_terrain': 0,
        'cout_mana_moyen': 0.0,
        'courbe_mana': {},
        'conforme': True,
        'avertissements': []
    }

    gc_list = set(config.get("game_changers", []))
    couts_mana = []

    for carte_nom in deck_cards:
        # normaliser le nom pour la comparaison
        carte_normalisee = normalize_card_name(carte_nom)

        # chercher la carte dans la collection
        match = collection[collection['name'].str.lower() == carte_normalisee]
        if match.empty:
            continue

        carte_info = match.iloc[0]
        oracle_text = str(carte_info.get('oracle_text', '')).lower()

        # compter les game changers (avec nom de la carte)
        if carte_nom in gc_list:
            rapport['game_changers'] += 1
            rapport['game_changers_list'].append(carte_nom)

        # compter les tutors (avec nom de la carte)
        if detect_tutor(oracle_text):
            rapport['tutors'] += 1
            rapport['tutors_list'].append(carte_nom)

        # compter les combos infinis
        if detect_infinite_combo_potential(oracle_text):
            rapport['combos_infinis'] += 1
            rapport['combos_list'].append(carte_nom)

        # compter les tours supplémentaires
        if detect_extra_turn(oracle_text):
            rapport['tours_supplementaires'] += 1

        # compter la destruction de terrain
        if detect_mass_land_destruction(oracle_text):
            rapport['destruction_terrain'] += 1

        # récupérer le coût de mana
        mv = carte_info.get('mana_value', 0)
        if mv is not None:
            couts_mana.append(float(mv))

    # calculer le coût mana moyen
    if couts_mana:
        rapport['cout_mana_moyen'] = round(sum(couts_mana) / len(couts_mana), 2)

    # calculer la courbe de mana
    for cmc in couts_mana:
        tranche = int(cmc)
        rapport['courbe_mana'][tranche] = rapport['courbe_mana'].get(tranche, 0) + 1

    # vérifier la conformité selon le bracket
    max_gc = rapport['max_game_changers']
    if max_gc is not None and max_gc != 0:
        if rapport['game_changers'] > max_gc:
            rapport['conforme'] = False
            rapport['avertissements'].append(
                f"Trop de Game Changers: {rapport['game_changers']}/{max_gc}"
            )
    elif max_gc == 0 and rapport['game_changers'] > 0:
        rapport['conforme'] = False
        rapport['avertissements'].append(
            f"Game Changers non autorisés dans ce bracket: {rapport['game_changers']} détectés"
        )
    
    max_tutors = rapport['max_tutors']
    if max_tutors is not None and max_tutors != 0:
        if rapport['tutors'] > max_tutors:
            rapport['conforme'] = False
            rapport['avertissements'].append(
                f"Trop de Tutors: {rapport['tutors']}/{max_tutors}"
            )
    elif max_tutors == 0 and rapport['tutors'] > 0:
        rapport['conforme'] = False
        rapport['avertissements'].append(
            f"Tutors non autorisés dans ce bracket: {rapport['tutors']} détectés"
        )
    
    if not bracket_constraints.get('allow_infinite_combos', False) and rapport['combos_infinis'] > 0:
        rapport['conforme'] = False
        rapport['avertissements'].append(
            f"Combos infinis détectés: {rapport['combos_infinis']} (non autorisés)"
        )
    
    if not bracket_constraints.get('allow_mass_land_destruction', False) and rapport['destruction_terrain'] > 0:
        rapport['conforme'] = False
        rapport['avertissements'].append(
            f"Destruction de terrain détectée: {rapport['destruction_terrain']} (non autorisé)"
        )
    
    # vérifier le coût mana moyen pour les brackets 1-2
    if bracket_level <= 2 and rapport['cout_mana_moyen'] > 3.5:
        rapport['avertissements'].append(
            f"Coût mana moyen élevé: {rapport['cout_mana_moyen']} (recommandé: < 3.5 pour brackets 1-2)"
        )
    
    return rapport


def afficher_rapport_bracket(rapport):
    """Affiche un rapport formaté de la conformité du deck."""
    print("\n" + "=" * 50)
    print("📊 RAPPORT DE VÉRIFICATION DU BRACKET")
    print("=" * 50)

    bracket_names = {
        1: "Exhibition (Ultra-Casual)",
        2: "Core (Préconstruit)",
        3: "Upgraded (Amélioré)",
        4: "Optimized (Haute Puissance)"
    }

    print(f"Bracket ciblé : {rapport['bracket_cible']} - {bracket_names.get(rapport['bracket_cible'], 'Inconnu')}")
    print()

    # Statistiques
    print("📈 STATISTIQUES DU DECK")
    print("-" * 30)

    # Game Changers
    max_gc = rapport['max_game_changers']
    max_gc_str = str(max_gc) if max_gc else "∞"
    status_gc = "✓" if (max_gc is None or rapport['game_changers'] <= max_gc) else "✗"
    print(f"{status_gc} Game Changers: {rapport['game_changers']}/{max_gc_str}")
    
    # Afficher la liste des Game Changers détectés
    if rapport['game_changers_list']:
        print("   Cartes interdites détectées :")
        for carte in rapport['game_changers_list']:
            print(f"      • {carte}")

    # Tutors
    max_tutors = rapport['max_tutors']
    max_tutors_str = str(max_tutors) if max_tutors else "∞"
    status_tutors = "✓" if (max_tutors is None or rapport['tutors'] <= max_tutors) else "✗"
    print(f"{status_tutors} Tutors: {rapport['tutors']}/{max_tutors_str}")
    
    # Afficher la liste des Tutors détectés
    if rapport['tutors_list'] and BRACKET_CONSTRAINTS.get('max_tutors') == 0:
        print("   Tutors détectés (interdits dans ce bracket) :")
        for carte in rapport['tutors_list'][:5]:  # limiter à 5 pour l'affichage
            print(f"      • {carte}")
        if len(rapport['tutors_list']) > 5:
            print(f"      ... et {len(rapport['tutors_list']) - 5} autres")

    # Combos infinis
    status_combos = "✓" if rapport['combos_infinis'] == 0 else "⚠"
    print(f"{status_combos} Combos infinis: {rapport['combos_infinis']}")
    
    # Afficher la liste des combos potentiels
    if rapport['combos_list']:
        print("   Cartes à potentiel combo :")
        for carte in rapport['combos_list'][:5]:  # limiter à 5 pour l'affichage
            print(f"      • {carte}")
        if len(rapport['combos_list']) > 5:
            print(f"      ... et {len(rapport['combos_list']) - 5} autres")

    # Tours supplémentaires
    print(f"  Tours supplémentaires: {rapport['tours_supplementaires']}")

    # Destruction de terrain
    status_mld = "✓" if rapport['destruction_terrain'] == 0 else "⚠"
    print(f"{status_mld} Destruction de terrain: {rapport['destruction_terrain']}")

    # Coût mana moyen
    cmc = rapport['cout_mana_moyen']
    status_cmc = "✓" if cmc <= 3.5 else "⚠"
    print(f"{status_cmc} Coût mana moyen: {cmc}")

    print()
    print("📊 COURBE DE MANA")
    print("-" * 30)
    courbe = rapport['courbe_mana']
    for cmc in sorted(courbe.keys()):
        if courbe[cmc] > 0:
            barre = "█" * min(courbe[cmc], 20)  # limiter la longueur
            print(f"  {cmc}: {barre} ({courbe[cmc]})")

    print()
    print("=" * 50)

    # Conformité globale
    if rapport['conforme'] and not rapport['avertissements']:
        print("✅ Deck CONFORME au bracket ciblé !")
    else:
        print("⚠️  ATTENTION - Problèmes détectés :")
        for avertissement in rapport['avertissements']:
            print(f"   • {avertissement}")
        if not rapport['conforme']:
            print("\n❌ Le deck n'est PAS conforme au bracket ciblé.")
        else:
            print("\n⚠️  Le deck est conforme mais avec des avertissements.")

    print("=" * 50 + "\n")


def calculer_score_puissance(rapport):
    """Calcule un score de puissance du deck de 1 à 10."""
    score = 5.0  # score de base

    # Game changers augmentent la puissance
    if rapport['game_changers'] > 0:
        score += min(rapport['game_changers'] * 0.5, 2.0)

    # Tutors augmentent légèrement la puissance
    if rapport['tutors'] > 0:
        score += min(rapport['tutors'] * 0.2, 1.0)

    # Combos infinis augmentent beaucoup la puissance
    if rapport['combos_infinis'] > 0:
        score += min(rapport['combos_infinis'] * 1.0, 2.0)

    # Coût mana moyen bas = deck plus rapide
    if rapport['cout_mana_moyen'] < 2.5:
        score += 0.5
    elif rapport['cout_mana_moyen'] > 4.0:
        score -= 0.5

    # Normaliser entre 1 et 10
    score = max(1, min(10, score))

    return round(score, 1)


def analyser_coherence_deck(deck_cards, commander_name):
    """Analyse la cohérence interne du deck (synergies, courbe, etc.)."""
    coherence = {
        'commandant': commander_name,
        'synergies_detectees': [],
        'cartes_en_conflit': [],
        'problemes_courbe': [],
        'recommandations': []
    }

    gc_list = set(config.get("game_changers", []))
    cartes_ramp = 0
    cartes_draw = 0
    cartes_removal = 0
    couts_mana = []

    for carte_nom in deck_cards:
        carte_normalisee = normalize_card_name(carte_nom)
        match = collection[collection['name'].str.lower() == carte_normalisee]
        if match.empty:
            continue

        carte_info = match.iloc[0]
        oracle_text = str(carte_info.get('oracle_text', '')).lower()
        type_line = str(carte_info.get('type_line', '')).lower()

        mv = carte_info.get('mana_value', 0)
        if mv is not None:
            couts_mana.append(float(mv))

        # Compter les types de cartes
        if detect_tutor(oracle_text) or 'ramp' in oracle_text or 'search' in oracle_text:
            cartes_ramp += 1
        if 'draw' in oracle_text or 'pioche' in oracle_text:
            cartes_draw += 1
        if 'destroy' in oracle_text or 'exile' in oracle_text:
            cartes_removal += 1

    # Vérifier la courbe de mana
    if couts_mana:
        cmc_moyen = sum(couts_mana) / len(couts_mana)
        if cmc_moyen > 4.5:
            coherence['problemes_courbe'].append(
                f"Courbe de mana élevée (moyenne: {cmc_moyen:.2f})"
            )
            coherence['recommandations'].append(
                "Remplacer certaines cartes chères par des équivalents moins coûteux"
            )
        elif cmc_moyen < 2.0:
            coherence['problemes_courbe'].append(
                f"Courbe de mana très basse (moyenne: {cmc_moyen:.2f})"
            )
            coherence['recommandations'].append(
                "Ajouter des cartes de fin de partie"
            )

    # Vérifier l'équilibre des types de cartes
    if cartes_ramp < 5:
        coherence['recommandations'].append(
            f"Peu de ramp détecté ({cartes_ramp}): envisager d'en ajouter"
        )
    if cartes_draw < 5:
        coherence['recommandations'].append(
            f"Peu de pioche détectée ({cartes_draw}): envisager d'en ajouter"
        )
    if cartes_removal < 3:
        coherence['recommandations'].append(
            f"Peu de removal détecté ({cartes_removal}): envisager d'en ajouter"
        )

    # Détecter les synergies
    if cartes_ramp >= 10 and cartes_draw >= 8:
        coherence['synergies_detectees'].append(
            "Bon équilibre ramp/pioche - deck consistant"
        )

    return coherence


def afficher_coherence_deck(coherence):
    """Affiche l'analyse de cohérence du deck."""
    print("\n" + "=" * 50)
    print("🔍 ANALYSE DE COHÉRENCE DU DECK")
    print("=" * 50)

    print(f"Commandant: {coherence['commandant']}")
    print()

    if coherence['synergies_detectees']:
        print("✅ SYNERGIES DÉTECTÉES :")
        for syn in coherence['synergies_detectees']:
            print(f"   • {syn}")
        print()

    if coherence['problemes_courbe']:
        print("⚠️  PROBLÈMES DE COURBE DE MANA :")
        for prob in coherence['problemes_courbe']:
            print(f"   • {prob}")
        print()

    if coherence['recommandations']:
        print("💡 RECOMMANDATIONS DE COHÉRENCE :")
        for rec in coherence['recommandations']:
            print(f"   • {rec}")
        print()

    if not coherence['synergies_detectees'] and not coherence['problemes_courbe'] and not coherence['recommandations']:
        print("✅ Deck cohérent et équilibré !")

    print("=" * 50 + "\n")


def analyser_pre_requis_bracket(deck_cards, bracket_level):
    """Analyse détaillée des pré-requis par bracket et quelles cartes les remplissent."""
    
    # Définition des pré-requis officiels EDH par bracket
    pre_requis = {
        1: {
            'nom': "Exhibition (Ultra-Casual)",
            'game_changers_max': 0,
            'tutors_max': 2,
            'combos_infinis': False,
            'extra_turns': False,
            'mass_land_destruction': False,
            'cmc_moyen_max': 3.5,
            'description': "Deck thématique, non optimisé, sans combos"
        },
        2: {
            'nom': "Core (Préconstruit)",
            'game_changers_max': 0,
            'tutors_max': 4,
            'combos_infinis': False,
            'extra_turns': False,
            'mass_land_destruction': False,
            'cmc_moyen_max': 3.8,
            'description': "Niveau préconstruit Commander, moteurs puissants"
        },
        3: {
            'nom': "Upgraded (Amélioré)",
            'game_changers_max': 3,
            'tutors_max': 6,
            'combos_infinis': False,
            'extra_turns': False,
            'mass_land_destruction': False,
            'cmc_moyen_max': 4.2,
            'description': "Deck optimisé au-delà des préconstruits"
        },
        4: {
            'nom': "Optimized (Haute Puissance)",
            'game_changers_max': None,  # illimité
            'tutors_max': None,
            'combos_infinis': True,
            'extra_turns': True,
            'mass_land_destruction': True,
            'cmc_moyen_max': None,
            'description': "Deck fully optimised, cEDH"
        }
    }
    
    gc_list = set(config.get("game_changers", []))
    analyse = {
        'bracket_cible': bracket_level,
        'pre_requis_bracket': pre_requis.get(bracket_level, {}),
        'cartes_par_categorie': {
            'game_changers': [],
            'tutors': [],
            'combos': [],
            'extra_turns': [],
            'ramp': [],
            'draw': [],
            'removal': [],
            'wipes': []
        },
        'statistiques': {
            'cmc_moyen': 0.0,
            'total_cartes': len(deck_cards),
            'game_changers_count': 0,
            'tutors_count': 0,
            'combos_count': 0
        },
        'conformite_par_categorie': {}
    }
    
    couts_mana = []
    
    for carte_nom in deck_cards:
        carte_normalisee = normalize_card_name(carte_nom)
        match = collection[collection['name'].str.lower() == carte_normalisee]
        if match.empty:
            continue
        
        carte_info = match.iloc[0]
        oracle_text = str(carte_info.get('oracle_text', '')).lower()
        mv = carte_info.get('mana_value', 0)
        
        if mv is not None:
            couts_mana.append(float(mv))
        
        # Catégoriser la carte
        if carte_nom in gc_list:
            analyse['cartes_par_categorie']['game_changers'].append(carte_nom)
            analyse['statistiques']['game_changers_count'] += 1

        if detect_tutor(oracle_text):
            analyse['cartes_par_categorie']['tutors'].append(carte_nom)
            analyse['statistiques']['tutors_count'] += 1

        if detect_infinite_combo_potential(oracle_text):
            analyse['cartes_par_categorie']['combos'].append(carte_nom)
            analyse['statistiques']['combos_count'] += 1

        if detect_extra_turn(oracle_text):
            analyse['cartes_par_categorie']['extra_turns'].append(carte_nom)

        # Autres catégories pour l'analyse
        # RAMP : exclure les terrains de base (ils sont comptés ailleurs)
        type_line = str(carte_info.get('type_line', '')).lower()
        if contains_any(oracle_text, RAMP_WORDS) and 'land' not in type_line:
            analyse['cartes_par_categorie']['ramp'].append(carte_nom)
        if contains_any(oracle_text, DRAW_WORDS):
            analyse['cartes_par_categorie']['draw'].append(carte_nom)
        if contains_any(oracle_text, REMOVAL_WORDS):
            analyse['cartes_par_categorie']['removal'].append(carte_nom)
        if contains_any(oracle_text, WIPE_WORDS):
            analyse['cartes_par_categorie']['wipes'].append(carte_nom)
        
        # Calculer la courbe de mana (EXCLUT les cartes à mana 0 comme les terrains)
        if mv is not None and mv > 0:
            couts_mana.append(float(mv))

    # Calculer statistiques
    # CMC moyen : basé uniquement sur les cartes à mana > 0
    if couts_mana:
        analyse['statistiques']['cmc_moyen'] = round(sum(couts_mana) / len(couts_mana), 2)
    else:
        analyse['statistiques']['cmc_moyen'] = 0.0
    
    # Vérifier conformité par catégorie
    prereq = pre_requis.get(bracket_level, {})
    
    # Game Changers
    max_gc = prereq.get('game_changers_max')
    gc_count = analyse['statistiques']['game_changers_count']
    if max_gc is None:
        analyse['conformite_par_categorie']['game_changers'] = {'conforme': True, 'detail': 'Illimité en bracket 4'}
    elif gc_count <= max_gc:
        analyse['conformite_par_categorie']['game_changers'] = {'conforme': True, 'detail': f'{gc_count}/{max_gc}'}
    else:
        analyse['conformite_par_categorie']['game_changers'] = {'conforme': False, 'detail': f'{gc_count}/{max_gc} - TROP'}
    
    # Tutors
    max_tutors = prereq.get('tutors_max')
    tutors_count = analyse['statistiques']['tutors_count']
    if max_tutors is None:
        analyse['conformite_par_categorie']['tutors'] = {'conforme': True, 'detail': 'Illimité en bracket 4'}
    elif tutors_count <= max_tutors:
        analyse['conformite_par_categorie']['tutors'] = {'conforme': True, 'detail': f'{tutors_count}/{max_tutors}'}
    else:
        analyse['conformite_par_categorie']['tutors'] = {'conforme': False, 'detail': f'{tutors_count}/{max_tutors} - TROP'}
    
    # Combos
    if prereq.get('combos_infinis', False):
        analyse['conformite_par_categorie']['combos'] = {'conforme': True, 'detail': 'Autorisés'}
    elif analyse['statistiques']['combos_count'] == 0:
        analyse['conformite_par_categorie']['combos'] = {'conforme': True, 'detail': 'Aucun détecté'}
    else:
        analyse['conformite_par_categorie']['combos'] = {'conforme': False, 'detail': f"{analyse['statistiques']['combos_count']} détectés (interdits)"}
    
    # CMC moyen
    cmc_max = prereq.get('cmc_moyen_max')
    cmc_actuel = analyse['statistiques']['cmc_moyen']
    if cmc_max is None:
        analyse['conformite_par_categorie']['cmc'] = {'conforme': True, 'detail': 'Aucune limite'}
    elif cmc_actuel <= cmc_max:
        analyse['conformite_par_categorie']['cmc'] = {'conforme': True, 'detail': f'{cmc_actuel} <= {cmc_max}'}
    else:
        analyse['conformite_par_categorie']['cmc'] = {'conforme': False, 'detail': f'{cmc_actuel} > {cmc_max} - TROP ÉLEVÉ'}
    
    return analyse


def analyser_doublons_bibliotheque(deck_cards, library_cards_used):
    """Analyse les cartes du deck qui sont déjà présentes dans d'autres decks.
    
    Retourne un dictionnaire avec:
    - 'total_doublons': nombre total de cartes en doublon
    - 'par_deck': dict {nom_deck: [liste de cartes]}
    - 'cartes_multi_decks': liste des cartes dans plusieurs decks
    EXCLUT les terrains de base (Plains, Island, Swamp, Mountain, Forest).
    """
    basic_land_names = {"plains", "island", "swamp", "mountain", "forest"}
    
    # Structure: {nom_deck: {carte_normalisee: carte_nom}}
    cartes_par_deck = {}
    # Structure: {carte_normalisee: {'nom': carte_nom, 'decks': [noms_decks]}}
    cartes_multi_decks = {}
    
    for carte_nom in deck_cards:
        carte_normalisee = normalize_card_name(carte_nom)
        
        # EXCLURE les terrains de base du contrôle des doublons
        if carte_normalisee in basic_land_names:
            continue
        
        if carte_normalisee in library_cards_used:
            origins = library_cards_used[carte_normalisee]
            
            # Ajouter à chaque deck concerné
            for deck_name in origins.keys():
                if deck_name not in cartes_par_deck:
                    cartes_par_deck[deck_name] = {}
                cartes_par_deck[deck_name][carte_normalisee] = carte_nom
            
            # Tracker les cartes dans plusieurs decks
            if len(origins) > 1:
                cartes_multi_decks[carte_normalisee] = {
                    'nom': carte_nom,
                    'decks': list(origins.keys())
                }
    
    return {
        'total_doublons': sum(len(cartes) for cartes in cartes_par_deck.values()),
        'par_deck': cartes_par_deck,
        'cartes_multi_decks': cartes_multi_decks,
        'nb_decks_touches': len(cartes_par_deck)
    }


def afficher_warning_doublons(analyse_doublons, check_enabled):
    """Affiche un warning sur les cartes en doublon avec les decks existants.
    
    Affiche les cartes regroupées par deck.
    """
    if not analyse_doublons['par_deck']:
        print("\n✅ AUCUNE CARTE EN COMMUN AVEC LES AUTRES DECKS")
        print("   Toutes les cartes de ce deck sont uniques !\n")
        return
    
    print("\n" + "=" * 60)
    if check_enabled:
        print("⚠️  CARTES DÉJÀ UTILISÉES DANS D'AUTRES DECKS")
    else:
        print("⚠️  WARNING : CARTES POTENTIELLEMENT DÉJÀ UTILISÉES")
        print("   (check_existing_decks: false dans config.yaml)")
    print("=" * 60)
    
    total = analyse_doublons['total_doublons']
    nb_decks = analyse_doublons['nb_decks_touches']
    print(f"\n   {total} carte(s) de ce deck sont déjà utilisées dans {nb_decks} autre(s) deck(s) :\n")
    
    # Afficher les cartes regroupées par deck
    for deck_name, cartes in sorted(analyse_doublons['par_deck'].items()):
        print(f"   📁 Dans le deck '{deck_name}' ({len(cartes)} cartes) :")
        
        # Trier les cartes par ordre alphabétique
        for i, carte_nom in enumerate(sorted(cartes.values()), 1):
            print(f"       {i:3}. {carte_nom}")
        print()
    
    # Afficher les cartes dans plusieurs decks (cross-deck overlap)
    if analyse_doublons['cartes_multi_decks']:
        print("   " + "-" * 50)
        print(f"   🔄 {len(analyse_doublons['cartes_multi_decks'])} carte(s) dans PLUSIEURS decks :")
        for carte_info in sorted(analyse_doublons['cartes_multi_decks'].values(), 
                                  key=lambda x: len(x['decks']), reverse=True)[:10]:
            decks_str = ", ".join(f"'{d}'" for d in carte_info['decks'])
            print(f"       • {carte_info['nom']} → {decks_str}")
        if len(analyse_doublons['cartes_multi_decks']) > 10:
            print(f"       ... et {len(analyse_doublons['cartes_multi_decks']) - 10} autres")
    
    print("\n" + "=" * 60 + "\n")


def afficher_pre_requis_bracket(analyse):
    """Affiche l'analyse détaillée des pré-requis par bracket."""
    print("\n" + "=" * 60)
    print("📋 ANALYSE DÉTAILLÉE DES PRÉ-REQUIS PAR BRACKET")
    print("=" * 60)
    
    prereq = analyse['pre_requis_bracket']
    bracket_names = {
        1: "Exhibition (Ultra-Casual)",
        2: "Core (Préconstruit)",
        3: "Upgraded (Amélioré)",
        4: "Optimized (Haute Puissance)"
    }
    
    print(f"\n🎯 BRACKET CIBLÉ : {analyse['bracket_cible']} - {prereq.get('nom', 'Inconnu')}")
    print(f"   Description : {prereq.get('description', '')}")
    print()
    
    print("📏 PRÉ-REQUIS OFFICIELS POUR CE BRACKET :")
    print("-" * 50)
    print(f"   • Game Changers max : {prereq.get('game_changers_max', '∞')}")
    print(f"   • Tutors max : {prereq.get('tutors_max', '∞')}")
    print(f"   • Combos infinis : {'Autorisés' if prereq.get('combos_infinis') else 'Interdits'}")
    print(f"   • Tours supplémentaires : {'Autorisés' if prereq.get('extra_turns') else 'Interdits'}")
    print(f"   • Destruction de terrain : {'Autorisée' if prereq.get('mass_land_destruction') else 'Interdite'}")
    if prereq.get('cmc_moyen_max'):
        print(f"   • Coût mana moyen max : {prereq['cmc_moyen_max']}")
    print()
    
    print("📊 STATISTIQUES DE TON DECK :")
    print("-" * 50)
    stats = analyse['statistiques']
    print(f"   • Total cartes : {stats['total_cartes']}")
    print(f"   • Coût mana moyen : {stats['cmc_moyen']}")
    print(f"   • Game Changers : {stats['game_changers_count']}")
    print(f"   • Tutors : {stats['tutors_count']}")
    print(f"   • Combos potentiels : {stats['combos_count']}")
    print()
    
    print("✅ CONFORMITÉ PAR CATÉGORIE :")
    print("-" * 50)
    for categorie, result in analyse['conformite_par_categorie'].items():
        status = "✓" if result['conforme'] else "✗"
        print(f"   {status} {categorie.capitalize()}: {result['detail']}")
    print()
    
    # Afficher les cartes par catégorie
    print("🃏 CARTES DÉTECTÉES PAR CATÉGORIE :")
    print("-" * 50)
    
    categories_affichage = [
        ('game_changers', 'Game Changers (interdites bracket 1-2)'),
        ('tutors', 'Tutors (recherche bibliothèque)'),
        ('combos', 'Combos infinis potentiels'),
        ('ramp', 'Ramp (accélération mana)'),
        ('draw', 'Pioche'),
        ('removal', 'Removal (élimination)'),
        ('wipes', 'Board Wipes')
    ]
    
    for cat_key, cat_nom in categories_affichage:
        cartes = analyse['cartes_par_categorie'].get(cat_key, [])
        if cartes:
            print(f"\n   {cat_nom} ({len(cartes)}):")
            for carte in cartes[:10]:  # limiter à 10 cartes
                print(f"      • {carte}")
            if len(cartes) > 10:
                print(f"      ... et {len(cartes) - 10} autres")
    
    # Vérifier si le deck correspond au bracket détecté par Manabox
    print("\n" + "=" * 60)
    print("🔍 COMPARAISON AVEC BRACKETS MANABOX")
    print("=" * 60)
    
    # Déterminer le bracket probable selon les cartes
    bracket_probable = 4
    if stats['game_changers_count'] == 0 and stats['combos_count'] == 0:
        bracket_probable = 2
    if stats['cmc_moyen'] <= 3.5 and stats['tutors_count'] <= 2:
        bracket_probable = 1
    elif stats['game_changers_count'] <= 3 and stats['cmc_moyen'] <= 4.2:
        bracket_probable = 3
    
    print(f"\n📊 Bracket ciblé : {analyse['bracket_cible']}")
    print(f"📊 Bracket estimé (selon cartes) : {bracket_probable}")
    print()
    
    if bracket_probable < analyse['bracket_cible']:
        print(f"⚠️  ATTENTION : Ton deck semble être un bracket {bracket_probable}")
        print(f"   Manabox risque de le détecter en bracket {bracket_probable} au lieu de {analyse['bracket_cible']}")
        print()
        print("💡 CONSEIL : Pour augmenter la puissance du deck :")
        if stats['game_changers_count'] == 0 and analyse['bracket_cible'] >= 2:
            print("   • Ajouter des Game Changers puissants (Sol Ring, Arcane Signet, etc.)")
        if stats['tutors_count'] < 4 and analyse['bracket_cible'] >= 2:
            print("   • Ajouter des tutors (Demonic Tutor, Vampiric Tutor, etc.)")
        if stats['cmc_moyen'] < 3.0:
            print("   • Ajouter des cartes plus puissantes (coût mana plus élevé)")
        if stats['combos_count'] == 0 and analyse['bracket_cible'] >= 3:
            print("   • Ajouter des cartes avec synergies fortes / combos")
    elif bracket_probable > analyse['bracket_cible']:
        print(f"⚠️  ATTENTION : Ton deck semble être un bracket {bracket_probable}")
        print(f"   Manabox risque de le détecter en bracket {bracket_probable} au lieu de {analyse['bracket_cible']}")
    else:
        print(f"✅ Bracket cohérent ! Manabox devrait détecter un bracket {bracket_probable}")
    
    print("\n" + "=" * 60 + "\n")


def generer_decklist_pour_export(deck_cards, commander_name, _filename_base):
    """Génère un fichier de decklist formaté pour import sur les sites d'analyse.
    
    Format compatible avec:
    - https://brackcheck.com/
    - https://manabox.app/
    - https://edhrec.com/
    """
    
    # Format standard pour Manabox, brackcheck, EDHREC
    export_dir = EXPORTS_DIR
    os.makedirs(export_dir, exist_ok=True)
    
    # Nom du fichier d'export
    safe_name = re.sub(r"[^A-Za-z0-9]+", "-", commander_name).strip("-")
    export_filename = os.path.join(export_dir, f"{safe_name}_decklist.txt")
    
    with open(export_filename, "w", encoding="utf-8") as f:
        f.write(f"Commander: {commander_name}\n")
        f.write("\n")
        
        # Compter les cartes
        counts = Counter(deck_cards)
        
        # Trier par type (terrain, créature, etc.)
        terrains = []
        creatures = []
        non_creatures = []
        
        for carte_nom, count in counts.items():
            match = collection[collection['name'].str.lower() == normalize_card_name(carte_nom)]
            if match.empty:
                continue
            
            carte_info = match.iloc[0]
            type_line = str(carte_info.get('type_line', '')).lower()
            
            if 'land' in type_line:
                terrains.append((carte_nom, count))
            elif 'creature' in type_line:
                creatures.append((carte_nom, count))
            else:
                non_creatures.append((carte_nom, count))
        
        # Écrire les cartes par catégorie
        f.write("--- CREATURES ---\n")
        for nom, cnt in sorted(creatures, key=lambda x: x[1], reverse=True):
            f.write(f"{cnt} {nom}\n")
        f.write("\n")
        
        f.write("--- SORTS ET ARTIFACTS ---\n")
        for nom, cnt in sorted(non_creatures, key=lambda x: x[1], reverse=True):
            f.write(f"{cnt} {nom}\n")
        f.write("\n")
        
        f.write("--- TERRAINS ---\n")
        for nom, cnt in sorted(terrains, key=lambda x: x[1], reverse=True):
            f.write(f"{cnt} {nom}\n")
    
    print(f"\n📁 Decklist exportée vers : '{export_filename}'")
    print(f"   → Copie-colle ce fichier sur https://brackcheck.com/ pour analyse")
    print(f"   → Ou importe sur https://manabox.app/ ou https://edhrec.com/")
    
    return export_filename


# exécuter l'analyse et afficher le rapport
rapport_bracket = analyser_conformite_bracket(final_deck, BRACKET_LEVEL, BRACKET_CONSTRAINTS)
afficher_rapport_bracket(rapport_bracket)

# analyser et afficher les pré-requis détaillés par bracket
pre_requis_analyse = analyser_pre_requis_bracket(final_deck, BRACKET_LEVEL)
afficher_pre_requis_bracket(pre_requis_analyse)

# analyser et afficher la cohérence du deck
coherence_deck = analyser_coherence_deck(final_deck, commander["name"])
afficher_coherence_deck(coherence_deck)

# analyser et afficher les doublons avec la bibliothèque
# IMPORTANT: On affiche les cartes du deck créé qui existent dans d'autres decks
print("\n" + "=" * 60)
print("📊 CARTES DU DECK DÉJÀ UTILISÉES DANS LA BIBLIOTHÈQUE")
print("=" * 60)

if library_check_done and library_cards_used:
    # Trouver les cartes du deck final qui sont dans d'autres decks
    cartes_en_commun = []
    
    for carte_nom in final_deck:
        carte_normalisee = normalize_card_name(carte_nom)
        
        # Exclure les terrains de base
        if carte_normalisee in basic_land_names:
            continue
        
        # Vérifier si la carte est dans d'autres decks
        if carte_normalisee in library_cards_used:
            decks_info = library_cards_used[carte_normalisee]
            cartes_en_commun.append({
                'carte': carte_nom,
                'decks': list(decks_info.keys()),
                'count': sum(decks_info.values())
            })
    
    # Afficher les résultats
    if cartes_en_commun:
        print(f"\n⚠️  {len(cartes_en_commun)} carte(s) de ce deck sont déjà utilisées ailleurs :\n")
        
        # Trier par nombre de decks (les plus partagées en premier)
        cartes_en_commun.sort(key=lambda x: (len(x['decks']), x['count']), reverse=True)
        
        for i, carte_info in enumerate(cartes_en_commun, 1):
            carte = carte_info['carte']
            decks = carte_info['decks']
            count = carte_info['count']
            
            # Formater la liste des decks
            decks_str = ", ".join(decks[:3])
            if len(decks) > 3:
                decks_str += f" (+{len(decks) - 3} autres)"
            
            print(f"   {i:3}. {carte}")
            print(f"        Déjà dans : {decks_str} ({count} exemplaire(s))")
        
        print()
    else:
        print("\n✅ AUCUNE CARTE EN COMMUN")
        print("   Toutes les cartes de ce deck sont uniques !\n")
else:
    print("\n⚠️  Bibliothèque non vérifiée")
    print("   L'analyse des doublons n'a pas pu être effectuée.")

# calculer et afficher le score de puissance
score_puissance = calculer_score_puissance(rapport_bracket)
print(f"💪 Score de puissance: {score_puissance}/10")
print()

# Afficher le résumé final
export_status = export_filename if "export_filename" in locals() else "N/A"
print(f"Deck exporté : {export_status}")
print(f"Cartes exclues (doublons) : {len(excluded_cards)}")
print()

# suggestions d'amélioration (TOUJOURS affichées)
print("💡 SUGGESTIONS D'AMÉLIORATION :")
print("-" * 30)

suggestions_affichees = False

if rapport_bracket['game_changers'] > 0:
    if BRACKET_CONSTRAINTS.get('max_game_changers') == 0:
        print("   • Retirer les cartes Game Changers (interdites dans ce bracket)")
        suggestions_affichees = True
    elif rapport_bracket['game_changers'] > (BRACKET_CONSTRAINTS.get('max_game_changers') or 999):
        print(f"   • Réduire les Game Changers: {rapport_bracket['game_changers']} détectés")
        suggestions_affichees = True

if rapport_bracket['tutors'] > 0 and BRACKET_CONSTRAINTS.get('max_tutors') == 0:
    print("   • Retirer les Tutors (interdits dans ce bracket)")
    suggestions_affichees = True
elif rapport_bracket['tutors'] > (BRACKET_CONSTRAINTS.get('max_tutors') or 999):
    print(f"   • Réduire le nombre de Tutors: {rapport_bracket['tutors']} détectés")
    suggestions_affichees = True

if rapport_bracket['combos_infinis'] > 0 and not BRACKET_CONSTRAINTS.get('allow_infinite_combos', False):
    print("   • Retirer les cartes permettant des combos infinis")
    suggestions_affichees = True

if rapport_bracket['destruction_terrain'] > 0 and not BRACKET_CONSTRAINTS.get('allow_mass_land_destruction', False):
    print("   • Retirer la destruction de terrain massive")
    suggestions_affichees = True

if rapport_bracket['tours_supplementaires'] > 0 and not BRACKET_CONSTRAINTS.get('allow_extra_turns', False):
    print("   • Retirer les tours supplémentaires")
    suggestions_affichees = True

if rapport_bracket['cout_mana_moyen'] > 3.5 and BRACKET_LEVEL <= 2:
    print(f"   • Coût mana moyen trop élevé ({rapport_bracket['cout_mana_moyen']}): ajouter des cartes moins chères")
    suggestions_affichees = True

# Suggestions de cohérence
if rapport_bracket['combos_infinis'] == 0 and BRACKET_LEVEL >= 3:
    print("   • Envisager d'ajouter des combos infinis pour bracket 3-4")
    suggestions_affichees = True

if rapport_bracket['tutors'] == 0 and BRACKET_LEVEL >= 2:
    print("   • Ajouter quelques tutors pour améliorer la consistance")
    suggestions_affichees = True

if not suggestions_affichees:
    print("   ✅ Aucune amélioration nécessaire - Deck optimisé !")

print()


# Finaliser et fermer le log
print("=" * 60)
print(f"Log complet sauvegardé : {log_filename}")

# Fermer le fichier de log et restaurer la sortie normale
log_file.close()
sys.stdout = sys.__stdout__  # Restaurer stdout original

# =============================
# 10. EXPORT POUR SITES D'ANALYSE
# =============================

# Générer un fichier de decklist formaté pour import sur les sites d'analyse
generer_decklist_pour_export(final_deck, commander["name"], filename)

# =============================
# 11. COPIE VERS DROPBOX (OPTIONNEL)
# =============================

# dossier Dropbox pour synchronisation des decks
DROPBOX_DECKS_DIR = r"C:\Users\mineh\Dropbox\decks"

if os.path.isdir(DROPBOX_DECKS_DIR):
    import shutil
    # copier le fichier du deck vers Dropbox
    dropbox_filename = os.path.join(DROPBOX_DECKS_DIR, os.path.basename(filename))
    try:
        shutil.copy2(filename, dropbox_filename)
        print(f"Deck copié vers Dropbox : '{dropbox_filename}'")
    except Exception as e:
        print(f"Erreur lors de la copie vers Dropbox : {e}")
else:
    print(f"Dossier Dropbox introuvable : {DROPBOX_DECKS_DIR}")
    print("La copie Dropbox a été ignorée.")
