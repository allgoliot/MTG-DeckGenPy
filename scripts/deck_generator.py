#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MTG DeckGenPy - Moteur de Génération de Decks
Module commun utilisé par CLI et GUI
"""

import pandas as pd
import os
import re
import ast
import yaml
from pathlib import Path
from collections import Counter

# ==========================================
# CONFIGURATION DES CHEMINS
# ==========================================
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR.parent / "conf" / "config.yaml"
COLLECTION_PATH = BASE_DIR.parent / "data" / "collection_enriched.csv"
BIBLIO_DIR = BASE_DIR.parent / "bibliotheque"
EXPORTS_DIR = BASE_DIR.parent / "exports"
LOGS_DIR = BASE_DIR.parent / "logs"

# ==========================================
# CONFIGURATION
# ==========================================
def load_config(path=CONFIG_PATH):
    """Charge la configuration YAML."""
    if not path.exists():
        raise FileNotFoundError(f"Configuration {path} introuvable.")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

config = load_config()

# Variables de configuration
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
BRACKET_PENALTIES = config.get("bracket_penalties", {1: 0.6, 2: 0.3, 3: 0.1, 4: 0.0})
ENABLE_TRIBE_SELECTION = config.get("enable_tribe_selection", True)
CHECK_EXISTING_DECKS = config.get("check_existing_decks", True)
BRACKET_CONSTRAINTS = config.get("bracket_constraints", {})
GAME_CHANGERS = set(config.get("game_changers", []))

# ==========================================
# CONSTANTES
# ==========================================
COLOR_SYMBOLS = {'W': '⚪', 'U': '🔵', 'B': '⚫', 'R': '🔴', 'G': '🟢', 'C': '⚪'}

COLOR_STRENGTHS = {
    'W': {'strong': ['tokens', 'lifegain', 'wipe', 'removal'], 'weak': ['draw', 'ramp']},
    'U': {'strong': ['draw', 'counters', 'spellslinger'], 'weak': ['removal', 'ramp']},
    'B': {'strong': ['removal', 'graveyard', 'tutors'], 'weak': ['wipe']},
    'R': {'strong': ['ramp', 'removal', 'spellslinger'], 'weak': ['draw', 'graveyard']},
    'G': {'strong': ['ramp', 'tokens', 'counters'], 'weak': ['removal', 'draw']}
}

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

# Mots-clés de détection
INFINITE_COMBO_KEYWORDS = [
    "infinite", "untap", "sacrifice a creature", "return from graveyard",
    "whenever you cast", "whenever a creature dies", "copy target",
    "exile target card from a graveyard", "you may cast it without paying"
]

LAND_DESTRUCTION_KEYWORDS = [
    "destroy all lands", "destroy each land", "sacrifice a land",
    "bury all lands", "exile all lands"
]

EXTRA_TURN_KEYWORDS = ["extra turn", "take another turn", "after this turn"]

TUTOR_KEYWORDS = ["search your library", "search your graveyard", "tutor"]

# ==========================================
# FONCTIONS UTILITAIRES
# ==========================================

def parse_colors(color_string):
    """Parse la chaîne de couleurs."""
    try:
        return set(ast.literal_eval(color_string))
    except Exception:
        return set()

def normalize_card_name(name: str) -> str:
    """Normalise le nom de la carte."""
    name = str(name).strip()
    if '//' in name:
        name = name.split('//')[0].strip()
    parts = name.split(maxsplit=1)
    if parts and parts[0].isdigit():
        name = parts[-1]
    name = re.sub(r'\s*\*[^*]*\*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*\([A-Za-z0-9]{2,5}\)', '', name)
    name = re.sub(r'\s+\d+\s*$', '', name)
    return ' '.join(name.split()).lower()

def format_colors(colors_set):
    """Formate les couleurs avec symboles."""
    if not colors_set:
        return '⚪'
    colored = [c for c in colors_set if c != 'C']
    if not colored:
        return ''
    return ''.join(COLOR_SYMBOLS.get(c, c) for c in sorted(colored))

def contains_any(text, keywords):
    """Vérifie si le texte contient un mot-clé."""
    text = str(text).lower()
    return any(word.lower() in text for word in keywords)

def extract_tribes(type_line):
    """Extrait les tribus du type_line."""
    tl = str(type_line).lower()
    if 'creature' not in tl:
        return []
    if '—' in tl:
        return [w.strip() for w in tl.split('—', 1)[1].split()]
    return []

# Détections spéciales
def detect_infinite_combo_potential(oracle_text):
    text = str(oracle_text).lower()
    return sum(1 for kw in INFINITE_COMBO_KEYWORDS if kw in text) >= 2

def detect_mass_land_destruction(oracle_text):
    text = str(oracle_text).lower()
    return any(kw in text for kw in LAND_DESTRUCTION_KEYWORDS)

def detect_extra_turn(oracle_text):
    text = str(oracle_text).lower()
    return any(kw in text for kw in EXTRA_TURN_KEYWORDS)

def detect_tutor(oracle_text):
    text = str(oracle_text).lower()
    return any(kw in text for kw in TUTOR_KEYWORDS)

# ==========================================
# SCORING INTELLIGENT
# ==========================================

def calculer_synergie_commandant(carte_row, commander_tribes, commander_themes):
    """Calcule la synergie avec le commandant."""
    synergie = 0
    texte = str(carte_row.get('oracle_text', '')).lower()
    type_line = str(carte_row.get('type_line', '')).lower()
    
    for tribu in commander_tribes:
        if tribu in type_line:
            synergie += 5
    
    for theme in commander_themes:
        keywords = COMMANDANT_SYNERGIES.get(theme, [])
        if any(kw in texte or kw in type_line for kw in keywords):
            synergie += 3
    
    return synergie

def score_card(row, commander_tribes=None, commander_themes=None, couleurs_commandant=None, detected_strategy="tokens"):
    """Calcule le score intelligent d'une carte."""
    score = 0
    texte = str(row["oracle_text"]).lower()
    mv = row["mana_value"]
    type_line = str(row["type_line"]).lower()
    
    # 1. Synergie avec le commandant
    if commander_tribes and commander_themes:
        score += calculer_synergie_commandant(row, commander_tribes, commander_themes) * 2
    
    # 2. Bonus/malus des couleurs
    for couleur in (couleurs_commandant or []):
        forces = COLOR_STRENGTHS.get(couleur, {}).get('strong', [])
        for force in forces:
            if force in COMMANDANT_SYNERGIES:
                if any(kw in texte for kw in COMMANDANT_SYNERGIES.get(force, [])):
                    score += 1
    
    # 3. Synergie avec la stratégie détectée
    if contains_any(texte, STRATEGY_KEYWORDS.get(detected_strategy, [])):
        score += 4
    
    # 4. Utilité générale
    if contains_any(texte, RAMP_WORDS):
        score += 3
    if contains_any(texte, DRAW_WORDS):
        score += 3
    if contains_any(texte, REMOVAL_WORDS):
        score += 2
    if contains_any(texte, WIPE_WORDS):
        score += 4
    
    # 5. Bonus pour les créatures
    if "creature" in type_line:
        score += 1.5
        if 'whenever' in texte or 'enter the battlefield' in texte:
            score += 1
    
    # 6. Bonus pour les artifacts utiles
    if "artifact" in type_line and "equipment" not in type_line:
        if contains_any(texte, RAMP_WORDS) or contains_any(texte, DRAW_WORDS):
            score += 2
    
    # 7. Pénalité progressive selon le coût en mana
    if mv >= 7:
        score -= 3
    elif mv >= 6:
        score -= 1.5
    elif mv >= 5:
        score -= 0.5
    
    # 8. Bonus pour les cartes à faible coût
    if mv <= 2:
        score += 1
    elif mv <= 3:
        score += 0.5
    
    # 9. Bonus pour les cartes légendaires
    if "legendary" in type_line:
        score += 1
    
    return score

# ==========================================
# CHARGEMENT DE LA COLLECTION
# ==========================================

def load_collection(collection_path=COLLECTION_PATH):
    """Charge et prépare la collection."""
    if not collection_path.exists():
        raise FileNotFoundError(
            f"Collection introuvable : {collection_path}\n"
            "Veuillez lancer scripts/enriching_collection.py d'abord."
        )
    
    collection = pd.read_csv(collection_path)
    collection.columns = (collection.columns
                          .str.strip()
                          .str.lower()
                          .str.replace(' ', '_', regex=False))
    collection["colors_parsed"] = collection["color_identity"].apply(parse_colors)
    return collection

# ==========================================
# CHARGEMENT BIBLIOTHÈQUE
# ==========================================

def load_library(biblio_dir=BIBLIO_DIR):
    """Charge les decks existants pour éviter doublons."""
    library_cards_used = {}
    
    if not biblio_dir.exists():
        return library_cards_used
    
    for fname in biblio_dir.iterdir():
        if not fname.is_file() or fname.suffix != '.txt':
            continue
        
        try:
            with open(fname, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('//'):
                        continue
                    lname = normalize_card_name(line)
                    if lname not in library_cards_used:
                        library_cards_used[lname] = {}
                    library_cards_used[lname][fname.name] = \
                        library_cards_used[lname].get(fname.name, 0) + 1
        except Exception:
            continue
    
    return library_cards_used

# ==========================================
# SÉLECTION DES CARTES
# ==========================================

def pick_unique(df, limit, used_names, bracket_level, library_cards_used=None, log_callback=None):
    """Sélectionne des cartes uniques en respectant les contraintes du bracket."""
    if library_cards_used is None:
        library_cards_used = {}
    
    picked = []
    available = df.copy()
    penalty = BRACKET_PENALTIES.get(bracket_level, 0.3)
    constraints = BRACKET_CONSTRAINTS.get(bracket_level, {})
    
    max_gc = constraints.get("max_game_changers")
    max_tutors = constraints.get("max_tutors")
    allow_infinite = constraints.get("allow_infinite_combos", False)
    allow_mld = constraints.get("allow_mass_land_destruction", False)
    allow_extra = constraints.get("allow_extra_turns", False)
    
    constraint_stats = {"game_changers": 0, "tutors": 0, "extra_turns": 0}
    
    while len(picked) < limit and not available.empty:
        # Filtrer les doublons
        mask = ~available["name"].str.lower().isin(used_names)
        if not mask.any():
            break
        available = available[mask]
        
        # Calculer le score ajusté
        def adj_score(row):
            base = row.get("score", 0) * (1 - penalty)
            return base
        
        available["adj_score"] = available.apply(adj_score, axis=1)
        best = available.sort_values("adj_score", ascending=False).iloc[0]
        
        name = best["name"]
        oracle = str(best.get("oracle_text", "")).lower()
        lname = normalize_card_name(name)
        
        # Vérifications bracket
        # Game Changers
        if max_gc == 0 and name in GAME_CHANGERS:
            available = available[available["name"] != name]
            continue
        elif max_gc and name in GAME_CHANGERS and constraint_stats["game_changers"] >= max_gc:
            available = available[available["name"] != name]
            continue
        
        # Tutors
        is_tutor = detect_tutor(oracle)
        if is_tutor:
            if max_tutors == 0 or (max_tutors and constraint_stats["tutors"] >= max_tutors):
                available = available[available["name"] != name]
                continue
        
        # Combos infinis
        if not allow_infinite and detect_infinite_combo_potential(oracle):
            available = available[available["name"] != name]
            continue
        
        # Mass Land Destruction
        if not allow_mld and detect_mass_land_destruction(oracle):
            available = available[available["name"] != name]
            continue
        
        # Extra Turns
        if not allow_extra and detect_extra_turn(oracle):
            available = available[available["name"] != name]
            continue
        
        # Vérification doublons bibliothèque
        is_basic = lname in ["plains", "island", "swamp", "mountain", "forest"]
        if CHECK_EXISTING_DECKS and lname in library_cards_used and not is_basic:
            origins = library_cards_used.get(lname, {})
            info = ", ".join(f"{fn}({cnt})" for fn, cnt in origins.items())
            if log_callback:
                log_callback(f"  ⚠️ {name} déjà dans {info}, exclue")
            available = available[available["name"] != name]
            continue
        
        # Ajouter la carte
        picked.append(name)
        used_names.add(lname)
        
        # Mettre à jour les compteurs
        if name in GAME_CHANGERS:
            constraint_stats["game_changers"] += 1
        if is_tutor:
            constraint_stats["tutors"] += 1
        if detect_extra_turn(oracle):
            constraint_stats["extra_turns"] += 1
        
        available = available[available["name"] != name]
    
    return picked, constraint_stats

# ==========================================
# GÉNÉRATION DU DECK
# ==========================================

def generate_deck(bracket_level, commander, collection, library_cards_used=None, tribes=None, log_callback=None):
    """
    Génère un deck Commander complet.
    
    Args:
        bracket_level: Niveau du bracket (1-4)
        commander: Dict du commandant avec keys: name, colors_parsed, type_line, oracle_text
        collection: DataFrame pandas de la collection
        library_cards_used: Dict des cartes déjà utilisées (optionnel)
        tribes: Liste des tribus à filtrer (optionnel)
        log_callback: Fonction de callback pour les logs (optionnel)
    
    Returns:
        dict: {
            'deck': liste des noms de cartes,
            'commander': nom du commandant,
            'bracket_level': niveau du bracket,
            'constraint_stats': stats des contraintes,
            'log': liste des messages de log
        }
    """
    if library_cards_used is None:
        library_cards_used = {}
    
    log = []
    
    def log_msg(msg):
        log.append(msg)
        if log_callback:
            log_callback(msg)
    
    commander_name = commander['name']
    commander_colors = commander.get('colors_parsed', set())
    commander_tribes = extract_tribes(commander.get('type_line', ''))
    
    log_msg(f"🎯 Commandant: {commander_name}")
    log_msg(f"📊 Bracket: {bracket_level}")
    log_msg(f"🎨 Couleurs: {format_colors(commander_colors)}")
    
    if commander_tribes:
        log_msg(f"🏷️ Tribus: {', '.join(commander_tribes)}")
    
    # Filtrer cartes légales
    legal_cards = collection[
        collection["colors_parsed"].apply(lambda c: c.issubset(commander_colors))
    ].copy()
    legal_cards = legal_cards[legal_cards["name"] != commander_name]
    
    # Filtre tribu optionnel (créatures uniquement)
    if tribes:
        def apply_tribe_filter(row):
            tl = str(row["type_line"]).lower()
            if 'creature' in tl:
                return any(tr.lower() in tl for tr in tribes)
            return True
        
        mask = legal_cards.apply(apply_tribe_filter, axis=1)
        legal_cards = legal_cards[mask]
        log_msg(f"🏷️ Filtre tribu appliqué: {', '.join(tribes)} (créatures uniquement)")
    
    # Score intelligent
    legal_cards["score"] = legal_cards.apply(
        lambda row: score_card(row, commander_tribes, [], commander_colors),
        axis=1
    )
    legal_cards = legal_cards.sort_values("score", ascending=False)
    
    used_names = set()
    deck = []
    constraint_stats = {"game_changers": 0, "tutors": 0, "extra_turns": 0}
    
    # === TERRAINS DE BASE ===
    color_to_basic = {"W": "Plains", "U": "Island", "B": "Swamp", "R": "Mountain", "G": "Forest"}
    allowed_basics = [color_to_basic[c] for c in commander_colors if c in color_to_basic]
    
    if not allowed_basics:
        allowed_basics = ["Plains"]
    
    nb_couleurs = len(allowed_basics)
    par_couleur = BASIC_LAND_COUNT // nb_couleurs
    reste = BASIC_LAND_COUNT % nb_couleurs
    
    log_msg(f"\n🏔️ Mana Base ({nb_couleurs} couleurs)")
    for i, basic in enumerate(allowed_basics):
        count = par_couleur + (1 if i < reste else 0)
        for _ in range(count):
            deck.append(basic)
        log_msg(f"   {basic}: {count}")
    
    # === TERRAINS SPÉCIAUX ===
    special_lands = legal_cards[
        (legal_cards["type_line"].str.contains("Land", na=False)) &
        ~legal_cards["name"].str.lower().isin(["plains", "island", "swamp", "mountain", "forest"])
    ].copy()
    
    if not special_lands.empty:
        log_msg(f"\n🏔️ Terrains spéciaux ({TOTAL_LANDS - BASIC_LAND_COUNT})")
        lands_picked, lands_stats = pick_unique(
            special_lands, TOTAL_LANDS - BASIC_LAND_COUNT, used_names, 
            bracket_level, library_cards_used, log_msg
        )
        deck += lands_picked
        for key in constraint_stats:
            constraint_stats[key] += lands_stats[key]
    
    # Marquer les bases comme utilisées
    for bl in allowed_basics:
        used_names.add(bl.lower())
    
    # === CARTES NON-TERRAINS ===
    nonlands = legal_cards[~legal_cards["type_line"].str.contains("Land", na=False)]
    
    # Ramp
    ramp_cards = nonlands[nonlands["oracle_text"].str.contains('|'.join(RAMP_WORDS), na=False)].copy()
    if not ramp_cards.empty:
        ramp_cards = ramp_cards.sort_values("score", ascending=False)
        log_msg(f"\n⚡ Ramp ({RAMP_TARGET}) - Top score")
        ramp_picked, ramp_stats = pick_unique(ramp_cards, RAMP_TARGET, used_names, bracket_level, library_cards_used, log_msg)
        deck += ramp_picked
        for key in constraint_stats:
            constraint_stats[key] += ramp_stats[key]
    
    # Draw
    draw_cards = nonlands[nonlands["oracle_text"].str.contains('|'.join(DRAW_WORDS), na=False)].copy()
    if not draw_cards.empty:
        draw_cards = draw_cards.sort_values("score", ascending=False)
        log_msg(f"\n📚 Draw ({DRAW_TARGET}) - Top score")
        draw_picked, draw_stats = pick_unique(draw_cards, DRAW_TARGET, used_names, bracket_level, library_cards_used, log_msg)
        deck += draw_picked
        for key in constraint_stats:
            constraint_stats[key] += draw_stats[key]
    
    # Removal
    removal_cards = nonlands[nonlands["oracle_text"].str.contains('|'.join(REMOVAL_WORDS), na=False)].copy()
    if not removal_cards.empty:
        removal_cards = removal_cards.sort_values("score", ascending=False)
        log_msg(f"\n⚔️ Removal ({REMOVAL_TARGET}) - Top score")
        removal_picked, removal_stats = pick_unique(removal_cards, REMOVAL_TARGET, used_names, bracket_level, library_cards_used, log_msg)
        deck += removal_picked
        for key in constraint_stats:
            constraint_stats[key] += removal_stats[key]
    
    # Wipes
    wipe_cards = nonlands[nonlands["oracle_text"].str.contains('|'.join(WIPE_WORDS), na=False)].copy()
    if not wipe_cards.empty:
        wipe_cards = wipe_cards.sort_values("score", ascending=False)
        log_msg(f"\n💥 Wipes ({WIPE_TARGET}) - Top score")
        wipe_picked, wipe_stats = pick_unique(wipe_cards, WIPE_TARGET, used_names, bracket_level, library_cards_used, log_msg)
        deck += wipe_picked
        for key in constraint_stats:
            constraint_stats[key] += wipe_stats[key]
    
    # Complément
    remaining = TOTAL_CARDS - len(deck)
    if remaining > 0:
        others = nonlands[~nonlands["name"].str.lower().isin(used_names)].copy()
        if not others.empty:
            others = others.sort_values("score", ascending=False)
            log_msg(f"\n🎴 Complément ({remaining}) - Meilleures cartes restantes")
            others_picked, others_stats = pick_unique(others, remaining, used_names, bracket_level, library_cards_used, log_msg)
            deck += others_picked
            for key in constraint_stats:
                constraint_stats[key] += others_stats[key]
    
    log_msg(f"\n✅ Deck complété : {len(deck)} cartes")
    
    return {
        'deck': deck,
        'commander': commander_name,
        'bracket_level': bracket_level,
        'constraint_stats': constraint_stats,
        'log': log
    }

# ==========================================
# SAUVEGARDE ET EXPORT
# ==========================================

def save_deck(deck, commander_name, bracket_level, constraint_stats, collection=None, biblio_dir=BIBLIO_DIR, exports_dir=EXPORTS_DIR):
    """
    Sauvegarde le deck dans bibliotheque/ et exports/ avec statistiques.
    
    Args:
        deck: Liste des noms de cartes
        commander_name: Nom du commandant
        bracket_level: Niveau du bracket
        constraint_stats: Stats des contraintes
        collection: DataFrame pandas de la collection (pour stats par type)
        biblio_dir: Dossier de sauvegarde
        exports_dir: Dossier d'export
    
    Returns:
        tuple: (biblio_file_path, export_file_path)
    """
    safe_name = re.sub(r"[^A-Za-z0-9]+", "-", commander_name).strip("-")
    
    bracket_names = {
        1: "Exhibition (Ultra-Casual)",
        2: "Core (Préconstruit)",
        3: "Upgraded (Amélioré)",
        4: "Optimized (Haute Puissance)"
    }
    
    # Calculer les statistiques par type de carte
    type_counts = {
        'Creature': 0,
        'Artifact': 0,
        'Enchantment': 0,
        'Sorcery': 0,
        'Instant': 0,
        'Planeswalker': 0,
        'Land': 0,
        'Other': 0
    }
    
    if collection is not None:
        for card_name in deck:
            norm = normalize_card_name(card_name)
            match = collection[collection['name'].str.lower() == norm]
            if not match.empty:
                tl = str(match.iloc[0].get('type_line', '')).lower()
                if 'land' in tl:
                    type_counts['Land'] += 1
                elif 'creature' in tl:
                    type_counts['Creature'] += 1
                elif 'artifact' in tl:
                    type_counts['Artifact'] += 1
                elif 'enchantment' in tl:
                    type_counts['Enchantment'] += 1
                elif 'sorcery' in tl:
                    type_counts['Sorcery'] += 1
                elif 'instant' in tl:
                    type_counts['Instant'] += 1
                elif 'planeswalker' in tl:
                    type_counts['Planeswalker'] += 1
                else:
                    type_counts['Other'] += 1
            else:
                type_counts['Other'] += 1
    
    # Fichier bibliothèque
    biblio_file = biblio_dir / f"{safe_name}.txt"
    
    with open(biblio_file, "w", encoding="utf-8") as f:
        f.write(f"// COMMANDER\n{commander_name}\n")
        f.write(f"// EDH Bracket: {bracket_names.get(bracket_level, 'Unknown')}\n")
        f.write(f"// niveau de bracket: {bracket_level}\n")
        
        max_gc_str = str(BRACKET_CONSTRAINTS.get(bracket_level, {}).get('max_game_changers')) or "illimité"
        max_tutors_str = str(BRACKET_CONSTRAINTS.get(bracket_level, {}).get('max_tutors')) or "illimité"
        
        f.write(f"// game_changers utilisés: {constraint_stats['game_changers']}/{max_gc_str}\n")
        f.write(f"// tutors utilisés: {constraint_stats['tutors']}/{max_tutors_str}\n\n")
        
        # Statistiques par type
        f.write(f"// === STATISTIQUES PAR TYPE ===\n")
        f.write(f"// Créatures: {type_counts['Creature']}\n")
        f.write(f"// Artifacts: {type_counts['Artifact']}\n")
        f.write(f"// Enchantements: {type_counts['Enchantment']}\n")
        f.write(f"// Rituals: {type_counts['Sorcery']}\n")
        f.write(f"// Éphémères: {type_counts['Instant']}\n")
        f.write(f"// Arpenteurs: {type_counts['Planeswalker']}\n")
        f.write(f"// Terrains: {type_counts['Land']}\n")
        f.write(f"// Autres: {type_counts['Other']}\n")
        f.write(f"// Total: {len(deck)} cartes\n\n")
        
        counts = Counter(deck)
        for name, cnt in counts.items():
            f.write(f"{cnt} {name}\n")
    
    # Fichier export
    export_file = exports_dir / f"{safe_name}_decklist.txt"
    
    with open(export_file, "w", encoding="utf-8") as f:
        f.write(f"Commander: {commander_name}\n\n")
        f.write("--- CARTE DU DECK ---\n")
        for name, cnt in counts.items():
            f.write(f"{cnt} {name}\n")
    
    return biblio_file, export_file
