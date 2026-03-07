#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MTG DeckGenPy - Interface Graphique
Générateur de Decks Commander avec interface NiceGUI

Réutilise la logique de commander_generator3_0.py
"""

import pandas as pd
import os
import sys
import re
import ast
from datetime import datetime
from collections import Counter
from pathlib import Path

from nicegui import ui, app

# ==========================================
# CONFIGURATION DES CHEMINS
# ==========================================
BASE_DIR = Path(__file__).parent.parent
CONFIG_PATH = BASE_DIR / "conf" / "config.yaml"
COLLECTION_PATH = BASE_DIR / "data" / "collection_enriched.csv"
BIBLIO_DIR = BASE_DIR / "bibliotheque"
EXPORTS_DIR = BASE_DIR / "exports"
LOGS_DIR = BASE_DIR / "logs"

# Créer les dossiers
for d in [BIBLIO_DIR, EXPORTS_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ==========================================
# IMPORT CONFIGURATION
# ==========================================
import yaml

def load_config(path=CONFIG_PATH):
    """Charge la configuration YAML."""
    if not path.exists():
        raise FileNotFoundError(f"Fichier de configuration {path} introuvable.")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

config = load_config()

# Variables de configuration (MÊMES VARIABLES QUE commander_generator3_0.py)
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
# ÉTAT GLOBAL DE L'APPLICATION
# ==========================================
class AppState:
    def __init__(self):
        self.collection = None
        self.legal_cards = None
        self.commander = None
        self.commander_colors = set()
        self.commander_tribes = []
        self.commander_themes = []
        self.bracket_level = 2
        self.selected_tribes = []
        self.deck = []
        self.generation_log = []
        self.library_cards_used = {}
        self.constraint_stats = {"game_changers": 0, "tutors": 0, "extra_turns": 0}
        
    def reset(self):
        self.__init__()

state = AppState()

# ==========================================
# FONCTIONS UTILITAIRES (COPIES DE commander_generator3_0.py)
# ==========================================
COLOR_SYMBOLS = {
    'W': '⚪', 'U': '🔵', 'B': '⚫', 'R': '🔴', 'G': '🟢', 'C': '⚪'
}

def parse_colors(color_string):
    """Parse la chaîne de couleurs."""
    try:
        return set(ast.literal_eval(color_string))
    except Exception:
        return set()

def normalize_card_name(name: str) -> str:
    """Normalise le nom de la carte (SUPPRIME set code et numéro)."""
    name = str(name).strip()
    if '//' in name:
        name = name.split('//')[0].strip()
    parts = name.split(maxsplit=1)
    if parts and parts[0].isdigit():
        name = parts[-1]
    name = re.sub(r'\s*\*[^*]*\*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*\([A-Za-z0-9]{2,5}\)', '', name)  # Supprime (XXX)
    name = re.sub(r'\s+\d+\s*$', '', name)  # Supprime numéro fin
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

# Détection des cartes spéciales (MÊMES MOTS-CLÉS QUE commander_generator3_0.py)
INFINITE_COMBO_KEYWORDS = [
    "infinite", "untap", "sacrifice a creature", "return from graveyard",
    "whenever you cast", "whenever a creature dies", "copy target",
    "exile target card from a graveyard", "you may cast it without paying",
    "whenever this creature deals combat damage", "deathtouch", "first strike",
    "double strike", "haste", "vigilance", "trample", "lifelink",
    "whenever you gain life", "whenever a token enters", "populate"
]

LAND_DESTRUCTION_KEYWORDS = [
    "destroy all lands", "destroy each land", "sacrifice a land",
    "bury all lands", "exile all lands", "destroy all nonbasic lands"
]

EXTRA_TURN_KEYWORDS = ["extra turn", "take another turn", "after this turn"]

TUTOR_KEYWORDS = ["search your library", "search your graveyard",
                  "put a card from your library", "tutor"]

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
# SCORING INTELLIGENT (MÊME LOGIQUE QUE commander_generator3_0.py)
# ==========================================
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

def score_card(row, commander_tribes=None, commander_themes=None, couleurs_commandant=None):
    """Calcule le score intelligent d'une carte (MÊME LOGIQUE QUE commander_generator3_0.py)."""
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
    detected_strategy = "tokens"  # Simplifié pour GUI
    if contains_any(texte, STRATEGY_KEYWORDS.get(detected_strategy, [])):
        score += 4
    
    # 4. Utilité générale (ramp, draw, removal, wipe)
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
def load_collection():
    """Charge et prépare la collection."""
    if not COLLECTION_PATH.exists():
        raise FileNotFoundError(
            f"Collection introuvable : {COLLECTION_PATH}\n"
            "Veuillez lancer scripts/enriching_collection.py d'abord."
        )
    
    collection = pd.read_csv(COLLECTION_PATH)
    collection.columns = (collection.columns
                          .str.strip()
                          .str.lower()
                          .str.replace(' ', '_', regex=False))
    collection["colors_parsed"] = collection["color_identity"].apply(parse_colors)
    return collection

# ==========================================
# SÉLECTION DES CARTES (MÊME LOGIQUE QUE commander_generator3_0.py)
# ==========================================
def pick_unique(df, limit, used_names, bracket_level, log_callback=None):
    """Sélectionne des cartes uniques en respectant les contraintes du bracket."""
    picked = []
    available = df.copy()
    penalty = BRACKET_PENALTIES.get(bracket_level, 0.3)
    constraints = BRACKET_CONSTRAINTS.get(bracket_level, {})
    
    max_gc = constraints.get("max_game_changers")
    max_tutors = constraints.get("max_tutors")
    allow_infinite = constraints.get("allow_infinite_combos", False)
    allow_mld = constraints.get("allow_mass_land_destruction", False)
    allow_extra = constraints.get("allow_extra_turns", False)
    
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
        
        # Vérifications bracket (MÊMES RÈGLES QUE commander_generator3_0.py)
        # Game Changers
        if max_gc == 0 and name in GAME_CHANGERS:
            available = available[available["name"] != name]
            continue
        elif max_gc and name in GAME_CHANGERS and state.constraint_stats["game_changers"] >= max_gc:
            available = available[available["name"] != name]
            continue
        
        # Tutors
        is_tutor = detect_tutor(oracle)
        if is_tutor:
            if max_tutors == 0 or (max_tutors and state.constraint_stats["tutors"] >= max_tutors):
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
        if CHECK_EXISTING_DECKS and lname in state.library_cards_used and not is_basic:
            origins = state.library_cards_used.get(lname, {})
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
            state.constraint_stats["game_changers"] += 1
        if is_tutor:
            state.constraint_stats["tutors"] += 1
        if detect_extra_turn(oracle):
            state.constraint_stats["extra_turns"] += 1
        
        available = available[available["name"] != name]
    
    return picked

# ==========================================
# GÉNÉRATION DU DECK (MÊME LOGIQUE QUE commander_generator3_0.py)
# ==========================================
def generate_deck(bracket_level, commander, tribes=None, log_callback=None):
    """Génère un deck complet."""
    state.bracket_level = bracket_level
    state.commander = commander
    state.commander_colors = commander["colors_parsed"]
    state.commander_tribes = extract_tribes(commander["type_line"])
    state.deck = []
    state.generation_log = []
    state.constraint_stats = {"game_changers": 0, "tutors": 0, "extra_turns": 0}
    
    def log(msg):
        state.generation_log.append(msg)
        if log_callback:
            log_callback(msg)
    
    log(f"🎯 Commandant: {commander['name']}")
    log(f"📊 Bracket: {bracket_level}")
    log(f"🎨 Couleurs: {format_colors(state.commander_colors)}")
    
    if state.commander_tribes:
        log(f"🏷️ Tribus: {', '.join(state.commander_tribes)}")
    
    # Filtrer cartes légales
    legal_cards = state.collection[
        state.collection["colors_parsed"].apply(lambda c: c.issubset(state.commander_colors))
    ].copy()
    legal_cards = legal_cards[legal_cards["name"] != commander["name"]]
    
    # Filtre tribu optionnel
    if tribes:
        mask = legal_cards["type_line"].str.lower().apply(
            lambda tl: any(tr.lower() in tl for tr in tribes)
        )
        legal_cards = legal_cards[mask]
        log(f"🏷️ Filtre tribu appliqué: {', '.join(tribes)}")
    
    # Score intelligent
    legal_cards["score"] = legal_cards.apply(
        lambda row: score_card(row, state.commander_tribes, [], state.commander_colors),
        axis=1
    )
    legal_cards = legal_cards.sort_values("score", ascending=False)
    
    used_names = set()
    
    # === TERRAINS DE BASE ===
    color_to_basic = {"W": "Plains", "U": "Island", "B": "Swamp", "R": "Mountain", "G": "Forest"}
    allowed_basics = [color_to_basic[c] for c in state.commander_colors if c in color_to_basic]
    
    if not allowed_basics:
        allowed_basics = ["Plains"]  # Fallback
    
    nb_couleurs = len(allowed_basics)
    par_couleur = BASIC_LAND_COUNT // nb_couleurs
    reste = BASIC_LAND_COUNT % nb_couleurs
    
    log(f"\n🏔️ Mana Base ({nb_couleurs} couleurs)")
    for i, basic in enumerate(allowed_basics):
        count = par_couleur + (1 if i < reste else 0)
        for _ in range(count):
            state.deck.append(basic)
        log(f"   {basic}: {count}")
    
    # === TERRAINS SPÉCIAUX ===
    special_lands = legal_cards[
        (legal_cards["type_line"].str.contains("Land", na=False)) &
        ~legal_cards["name"].str.lower().isin(["plains", "island", "swamp", "mountain", "forest"])
    ].copy()
    
    if not special_lands.empty:
        log(f"\n🏔️ Terrains spéciaux ({TOTAL_LANDS - BASIC_LAND_COUNT})")
        state.deck += pick_unique(special_lands, TOTAL_LANDS - BASIC_LAND_COUNT, used_names, bracket_level, log)
    
    # Marquer les bases comme utilisées
    for bl in allowed_basics:
        used_names.add(bl.lower())
    
    # === CARTES NON-TERRAINS ===
    nonlands = legal_cards[~legal_cards["type_line"].str.contains("Land", na=False)]
    
    # Ramp
    ramp_cards = nonlands[nonlands["oracle_text"].str.contains('|'.join(RAMP_WORDS), na=False)].copy()
    if not ramp_cards.empty:
        ramp_cards = ramp_cards.sort_values("score", ascending=False)
        log(f"\n⚡ Ramp ({RAMP_TARGET}) - Top score")
        state.deck += pick_unique(ramp_cards, RAMP_TARGET, used_names, bracket_level, log)
    
    # Draw
    draw_cards = nonlands[nonlands["oracle_text"].str.contains('|'.join(DRAW_WORDS), na=False)].copy()
    if not draw_cards.empty:
        draw_cards = draw_cards.sort_values("score", ascending=False)
        log(f"\n📚 Draw ({DRAW_TARGET}) - Top score")
        state.deck += pick_unique(draw_cards, DRAW_TARGET, used_names, bracket_level, log)
    
    # Removal
    removal_cards = nonlands[nonlands["oracle_text"].str.contains('|'.join(REMOVAL_WORDS), na=False)].copy()
    if not removal_cards.empty:
        removal_cards = removal_cards.sort_values("score", ascending=False)
        log(f"\n⚔️ Removal ({REMOVAL_TARGET}) - Top score")
        state.deck += pick_unique(removal_cards, REMOVAL_TARGET, used_names, bracket_level, log)
    
    # Wipes
    wipe_cards = nonlands[nonlands["oracle_text"].str.contains('|'.join(WIPE_WORDS), na=False)].copy()
    if not wipe_cards.empty:
        wipe_cards = wipe_cards.sort_values("score", ascending=False)
        log(f"\n💥 Wipes ({WIPE_TARGET}) - Top score")
        state.deck += pick_unique(wipe_cards, WIPE_TARGET, used_names, bracket_level, log)
    
    # Complément
    remaining = TOTAL_CARDS - len(state.deck)
    if remaining > 0:
        others = nonlands[~nonlands["name"].str.lower().isin(used_names)].copy()
        if not others.empty:
            others = others.sort_values("score", ascending=False)
            log(f"\n🎴 Complément ({remaining}) - Meilleures cartes restantes")
            state.deck += pick_unique(others, remaining, used_names, bracket_level, log)
    
    log(f"\n✅ Deck complété : {len(state.deck)} cartes")
    
    return state.deck

# ==========================================
# SAUVEGARDE ET EXPORT
# ==========================================
def save_deck():
    """Sauvegarde le deck dans bibliotheque/ et exports/."""
    if not state.deck or not state.commander:
        return None, None
    
    commander_name = state.commander["name"]
    safe_name = re.sub(r"[^A-Za-z0-9]+", "-", commander_name).strip("-")
    
    bracket_names = {
        1: "Exhibition (Ultra-Casual)",
        2: "Core (Préconstruit)",
        3: "Upgraded (Amélioré)",
        4: "Optimized (Haute Puissance)"
    }
    
    # Fichier bibliothèque
    filename = BIBLIO_DIR / f"{safe_name}.txt"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"// COMMANDER\n{commander_name}\n")
        f.write(f"// EDH Bracket: {bracket_names.get(state.bracket_level, 'Unknown')}\n")
        f.write(f"// niveau de bracket: {state.bracket_level}\n")
        
        max_gc_str = str(BRACKET_CONSTRAINTS.get(state.bracket_level, {}).get('max_game_changers')) or "illimité"
        max_tutors_str = str(BRACKET_CONSTRAINTS.get(state.bracket_level, {}).get('max_tutors')) or "illimité"
        
        f.write(f"// game_changers utilisés: {state.constraint_stats['game_changers']}/{max_gc_str}\n")
        f.write(f"// tutors utilisés: {state.constraint_stats['tutors']}/{max_tutors_str}\n\n")
        
        counts = Counter(state.deck)
        for name, cnt in counts.items():
            f.write(f"{cnt} {name}\n")
    
    # Fichier export
    export_filename = EXPORTS_DIR / f"{safe_name}_decklist.txt"
    
    with open(export_filename, "w", encoding="utf-8") as f:
        f.write(f"Commander: {commander_name}\n\n")
        
        creatures = []
        spells = []
        lands = []
        
        for card_name in state.deck:
            match = state.collection[state.collection['name'].str.lower() == normalize_card_name(card_name)]
            if match.empty:
                continue
            card = match.iloc[0]
            tl = str(card.get('type_line', '')).lower()
            
            if 'land' in tl:
                lands.append(card_name)
            elif 'creature' in tl:
                creatures.append(card_name)
            else:
                spells.append(card_name)
        
        f.write("--- CREATURES ---\n")
        for name in sorted(creatures):
            f.write(f"1 {name}\n")
        
        f.write("\n--- SORTS ET ARTIFACTS ---\n")
        for name in sorted(spells):
            f.write(f"1 {name}\n")
        
        f.write("\n--- TERRAINS ---\n")
        for name in sorted(lands):
            f.write(f"1 {name}\n")
    
    return filename, export_filename

# ==========================================
# CHARGEMENT BIBLIOTHÈQUE
# ==========================================
def load_library():
    """Charge les decks existants pour éviter doublons."""
    state.library_cards_used = {}
    
    if not BIBLIO_DIR.exists():
        return
    
    for fname in BIBLIO_DIR.iterdir():
        if not fname.is_file() or fname.suffix != '.txt':
            continue
        
        try:
            with open(fname, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('//'):
                        continue
                    lname = normalize_card_name(line)
                    if lname not in state.library_cards_used:
                        state.library_cards_used[lname] = {}
                    state.library_cards_used[lname][fname.name] = \
                        state.library_cards_used[lname].get(fname.name, 0) + 1
        except Exception:
            continue

# ==========================================
# INTERFACE GRAPHIQUE
# ==========================================

@ui.page('/')
def main_page():
    """Page principale de l'application."""
    
    # En-tête
    with ui.header().classes('bg-gradient-to-r from-purple-600 to-blue-600'):
        ui.label('🎴 MTG DeckGenPy').classes('text-2xl font-bold')
        ui.label('Générateur de Decks Commander').classes('text-sm opacity-80')
    
    # Contenu principal
    with ui.column().classes('w-full max-w-4xl mx-auto p-6 gap-6'):
        
        # Titre
        ui.label('Générateur de Deck Commander').classes('text-3xl font-bold text-center w-full')
        
        # Étape 1: Sélection du Bracket
        with ui.card().classes('w-full'):
            ui.label('1️⃣ Sélectionnez le Bracket EDH').classes('text-xl font-semibold mb-4')
            
            bracket_options = {
                1: '🎪 Exhibition (Ultra-Casual) - 0 GC, 2 Tutors max',
                2: '📦 Core (Préconstruit) - 0 GC, 4 Tutors max',
                3: '⚡ Upgraded (Amélioré) - 3 GC, 6 Tutors max',
                4: '🏆 Optimized (Haute Puissance) - Illimité'
            }
            
            bracket_select = ui.radio(
                options=bracket_options,
                value=2
            ).classes('w-full')
        
        # Étape 2: Chargement et sélection du commandant
        with ui.card().classes('w-full'):
            ui.label('2️⃣ Choisissez votre Commandant').classes('text-xl font-semibold mb-4')
            
            # Barre de recherche
            with ui.row().classes('w-full gap-2'):
                search_input = ui.input(
                    placeholder='Rechercher un commandant...'
                ).classes('flex-grow')
                
                def do_filter():
                    filter_commanders(search_input.value)
                
                search_input.on('keydown.enter', do_filter)
                ui.button('🔍', on_click=do_filter).props('round')
            
            # Liste des commandants
            commander_container = ui.column().classes('w-full max-h-96 overflow-y-auto')
            
            commanders_data = []
            selected_commander_index = None  # Track which commander is selected
            
            def load_commanders():
                """Charge et affiche les commandants."""
                nonlocal commanders_data, selected_commander_index
                
                if state.collection is None:
                    try:
                        state.collection = load_collection()
                        load_library()
                        ui.notify('Collection chargée avec succès', type='positive')
                    except FileNotFoundError as e:
                        ui.notify(str(e), type='negative', timeout=8000)
                        return
                
                # Filtrer commandants
                commanders = state.collection[
                    (state.collection["type_line"].str.contains("Legendary Creature", na=False)) &
                    (state.collection["quantity"] > 0)
                ].copy()
                
                if commanders.empty:
                    ui.notify('Aucun commandant trouvé dans la collection', type='warning')
                    return
                
                # Calculer score de force
                def commander_strength(row):
                    text = str(row.get("oracle_text", "")).lower()
                    mv = row.get("mana_value", 0)
                    score = 0
                    if contains_any(text, RAMP_WORDS): score += 1
                    if contains_any(text, DRAW_WORDS): score += 1
                    if contains_any(text, REMOVAL_WORDS): score += 1
                    if contains_any(text, WIPE_WORDS): score += 1
                    if "creature" in str(row.get("type_line", "")).lower(): score += 1
                    score -= mv * 0.1
                    return score
                
                commanders["strength_score"] = commanders.apply(commander_strength, axis=1)
                commanders["tribes"] = commanders["type_line"].apply(extract_tribes)
                commanders = commanders.sort_values("strength_score")
                
                # Assigner bracket groups
                n = len(commanders)
                group_size = max(1, n // 4)
                commanders["bracket_group"] = [min(4, i // group_size + 1) for i in range(n)]
                
                # Filtrer par bracket sélectionné
                selected_bracket = bracket_select.value
                commanders_filtered = commanders[commanders["bracket_group"] == selected_bracket].copy()
                
                # Supprimer doublons
                commanders_filtered = commanders_filtered.drop_duplicates(subset=['name'], keep='first')
                commanders_data = commanders_filtered.reset_index(drop=True).to_dict('records')
                
                # Trouver l'index du commandant sélectionné (s'il est dans la nouvelle liste)
                selected_commander_index = None
                if state.commander:
                    for idx, cmd in enumerate(commanders_data):
                        if cmd['name'] == state.commander['name']:
                            selected_commander_index = idx
                            break
                
                display_commanders(commanders_data, commander_container)
            
            def display_commanders(data, container):
                """Affiche la liste des commandants."""
                try:
                    with container:
                        container.clear()
                        with container:
                            if not data:
                                ui.label('Aucun commandant trouvé pour ce bracket').classes('text-gray-500 italic p-4')
                                return
                            
                            for idx, cmd in enumerate(data):
                                tribes_str = f" [{', '.join(cmd['tribes'])}]" if cmd.get('tribes') else ""
                                colors = format_colors(cmd['colors_parsed'])
                                
                                # Déterminer si ce commandant est sélectionné
                                is_selected = (selected_commander_index == idx)
                                
                                # Style différent si sélectionné
                                row_classes = 'w-full items-center gap-2 p-2 rounded cursor-pointer '
                                if is_selected:
                                    row_classes += 'bg-purple-200 border-2 border-purple-500'
                                else:
                                    row_classes += 'hover:bg-gray-100'
                                
                                with ui.row().classes(row_classes):
                                    ui.label(f"{cmd['name']}{tribes_str}").classes('flex-grow')
                                    ui.label(f"B{cmd['bracket_group']}").classes(
                                        'bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded'
                                    )
                                    ui.label(colors).classes('text-lg')

                                    def select_cmd(c=cmd, i=idx):
                                        nonlocal selected_commander_index
                                        selected_commander_index = i
                                        state.commander = c
                                        state.commander_colors = c["colors_parsed"]
                                        state.commander_tribes = c.get("tribes", [])
                                        ui.notify(f"✅ {c['name']} sélectionné", type='positive')

                                        # Afficher détails AVANT de recharger l'affichage
                                        with ui.dialog() as dlg, ui.card().classes('w-[500px]'):
                                            ui.label(f"🎯 {c['name']}").classes('text-xl font-bold')
                                            ui.label(f"🎨 {format_colors(c['colors_parsed'])}")
                                            if c.get('tribes'):
                                                ui.label(f"🏷️ Tribus: {', '.join(c['tribes'])}")
                                            ui.separator()
                                            ui.label("Oracle Text:").classes('font-semibold')
                                            ui.label(c.get('oracle_text', '(aucun)')).classes('text-sm italic')
                                            ui.button('Fermer', on_click=dlg.close).classes('mt-4')
                                        dlg.open()

                                        # Recharger l'affichage pour montrer la sélection (après le dialog)
                                        display_commanders(data, container)

                                        # Charger automatiquement les tribus
                                        load_tribes()

                                    ui.button('Sélectionner', on_click=select_cmd).props('flat dense')
                except RuntimeError as e:
                    # Le container a été supprimé, ignorer
                    pass
            
            def filter_commanders(search_term):
                """Filtre les commandants par recherche."""
                if not commanders_data:
                    return
                
                search_term = search_term.lower()
                filtered = [c for c in commanders_data if search_term in c['name'].lower()]
                display_commanders(filtered, commander_container)
            
            # Mise à jour automatique quand le bracket change
            def on_bracket_change(e):
                """Recharge les commandants quand le bracket change."""
                load_commanders()
            
            bracket_select.on('update:model-value', on_bracket_change)
            
            # Bouton charger
            ui.button('🔄 Charger les commandants', on_click=load_commanders).classes('mt-4')
        
        # Étape 3: Sélection de tribu (optionnel)
        with ui.card().classes('w-full'):
            ui.label('3️⃣ Filtre par Tribu (optionnel)').classes('text-xl font-semibold mb-4')
            
            tribe_container = ui.column().classes('w-full')
            selected_tribes = []
            
            def load_tribes():
                """Charge les tribus disponibles."""
                nonlocal selected_tribes
                selected_tribes = []

                if state.collection is None:
                    ui.notify('⚠️ Collection non chargée. Cliquez sur "🔄 Charger les commandants" d\'abord.', type='warning')
                    return

                # Extraire tribus de TOUTES les cartes (pas seulement légales en couleur)
                # pour avoir un maximum d'options
                all_cards = state.collection

                # Méthode 1: Extraire depuis type_line (après le tiret —)
                tribes_set = set()

                # Parcourir toutes les cartes pour extraire les tribus
                type_lines = all_cards["type_line"].dropna().unique()

                for tl in type_lines:
                    tl_str = str(tl).lower()

                    # Les créatures ont des tribus après le tiret "—"
                    if 'creature' in tl_str and '—' in tl_str:
                        # Partie après "Creature —"
                        parts = tl_str.split('—', 1)
                        if len(parts) > 1:
                            tribe_part = parts[1]

                            # Extraire chaque mot (tribe) séparé par des espaces
                            for word in re.split(r'[\s\-]+', tribe_part):
                                word = word.strip()
                                # Inclure les tribus de 2+ lettres (pour inclure "Elf", "Cat", etc.)
                                if word and len(word) >= 2 and word not in ['legendary', 'artifact', 'enchantment', 'sorcery', 'instant', 'land']:
                                    tribes_set.add(word)

                    # Méthode 2: Chercher les mots-clés de tribus connus dans oracle_text
                    # pour les cartes qui n'ont pas de type_line clair
                    known_tribes = [
                        'human', 'elf', 'dwarf', 'goblin', 'orc', 'vampire', 'zombie',
                        'skeleton', 'spirit', 'angel', 'demon', 'dragon', 'wizard',
                        'cleric', 'knight', 'rogue', 'warrior', 'berserker', 'peasant',
                        'soldier', 'archer', 'assassin', 'mutant', 'insect', 'spider',
                        'beast', 'bird', 'cat', 'dog', 'wolf', 'fox', 'bear', 'boar',
                        'elephant', 'rhino', 'hippo', 'dinosaur', 'saurian', 'hydra',
                        'giant', 'titan', 'golem', 'construct', 'myr', 'thrull',
                        'sliver', 'changeling', 'shapeshifter', 'mimic', 'illusion',
                        'horror', 'eldrazi', 'alien', 'robot', 'vehicle', 'germ',
                        'wall', 'tentacle', 'eye', 'brain', 'hand', 'skull',
                        'rat', 'bat', 'crab', 'lobster', 'squid', 'octopus', 'jellyfish',
                        'snake', 'lizard', 'turtle', 'frog', 'toad', 'crocodile',
                        'mouse', 'otter', 'beaver', 'unicorn', 'pegasus', 'hippogriff',
                        'griffin', 'manticore', 'chimera', 'basilisk', 'cockatrice',
                        'gorgon', 'harpy', 'medusa', 'naga', 'merfolk', 'siren',
                        'leviathan', 'kraken', 'serpent', 'worm', 'dragon', 'drake',
                        'wyvern', 'hellion', 'horrors', 'avatars', 'gods', 'nobles',
                        'advisors', 'citizens', 'monks', 'samurai', 'ninjas', 'shamans',
                        'scouts', 'pirates', 'cowboys', 'detectives', 'citizens',
                        'goblins', 'elves', 'wizards', 'knights', 'angels', 'demons',
                        'dragons', 'vampires', 'zombies', 'skeletons', 'spirits',
                        'faeries', 'dryads', 'treants', 'elementals', 'giants',
                        'ogres', 'trolls', 'cyclops', 'minotaurs', 'satyrs', 'centaurs'
                    ]

                    for tribe in known_tribes:
                        if tribe in tl_str:
                            tribes_set.add(tribe)

                # Ajouter les tribus du commandant sélectionné (si existe)
                if state.commander and state.commander_tribes:
                    for tribe in state.commander_tribes:
                        if tribe:
                            tribes_set.add(tribe.lower())

                # Trier par ordre alphabétique
                tribes_list = sorted(tribes_set)

                # Afficher toutes les tribus (pas de limite)
                try:
                    with tribe_container:
                        tribe_container.clear()
                        with tribe_container:
                            ui.label(f"Sélectionnez une ou plusieurs tribus ({len(tribes_list)} disponibles):").classes('font-semibold mb-2')

                            # Barre de recherche de tribu
                            tribe_search = ui.input(
                                placeholder='Filtrer les tribus...'
                            ).classes('w-full mb-2')

                            # Conteneur pour les checkboxes
                            tribe_grid = ui.grid().classes('grid-cols-4 gap-2 max-h-64 overflow-y-auto')

                            checkboxes = {}  # tribe -> checkbox reference

                            def update_tribe_display():
                                """Met à jour l'affichage des tribus selon le filtre."""
                                try:
                                    search_term = tribe_search.value.lower()
                                    with tribe_grid:
                                        tribe_grid.clear()
                                        with tribe_grid:
                                            for tribe in tribes_list:
                                                if search_term in tribe:
                                                    cb = ui.checkbox(tribe.capitalize(), value=False)
                                                    checkboxes[tribe] = cb
                                                    def on_change(is_checked, tribe_name=tribe):
                                                        if is_checked and tribe_name not in selected_tribes:
                                                            selected_tribes.append(tribe_name)
                                                        elif not is_checked and tribe_name in selected_tribes:
                                                            selected_tribes.remove(tribe_name)
                                                    cb.on('update:model-value', on_change)
                                except RuntimeError:
                                    pass

                            # Afficher initialement
                            update_tribe_display()

                            # Mettre à jour au filtrage
                            tribe_search.on('keydown.enter', update_tribe_display)

                            # Boutons utilitaires
                            with ui.row().classes('mt-2 gap-2'):
                                def select_all():
                                    """Sélectionne toutes les tribus visibles."""
                                    search_term = tribe_search.value.lower()
                                    for tribe in tribes_list:
                                        if search_term in tribe:
                                            if tribe in checkboxes and checkboxes[tribe].value:
                                                if tribe not in selected_tribes:
                                                    selected_tribes.append(tribe)
                                    ui.notify(f'✅ {len(selected_tribes)} tribus sélectionnées', type='positive')

                                def deselect_all():
                                    """Désélectionne toutes les tribus."""
                                    selected_tribes.clear()
                                    try:
                                        for cb in checkboxes.values():
                                            cb.value = False
                                    except:
                                        pass
                                    ui.notify('Aucune tribu sélectionnée', type='info')

                                ui.button('📋 Tout', on_click=select_all).props('flat dense')
                                ui.button('❌ Aucun', on_click=deselect_all).props('flat dense')
                
                except RuntimeError:
                    # Container supprimé, ignorer
                    pass
            
            def apply_tribes():
                state.selected_tribes = selected_tribes.copy()
                if selected_tribes:
                    ui.notify(f'🏷️ Filtre appliqué: {", ".join(selected_tribes)}', type='positive')
                else:
                    ui.notify('Aucun filtre de tribu', type='info')
            
            with ui.row():
                ui.button('🏷️ Charger les tribus', on_click=load_tribes)
                ui.button('✅ Appliquer', on_click=apply_tribes).props('color=primary')
        
        # Étape 4: Génération
        with ui.card().classes('w-full'):
            ui.label('4️⃣ Générer le Deck').classes('text-xl font-semibold mb-4')
            
            progress_log = ui.log().classes('w-full h-64 font-mono text-sm')
            
            def log_to_ui(msg):
                progress_log.push(msg)
            
            def generate():
                """Lance la génération du deck."""
                if not state.commander:
                    ui.notify('⚠️ Veuillez sélectionner un commandant', type='warning')
                    return
                
                try:
                    progress_log.clear()
                    log_to_ui("🚀 Démarrage de la génération...")
                    
                    deck = generate_deck(
                        bracket_select.value,
                        state.commander,
                        state.selected_tribes,
                        log_to_ui
                    )
                    
                    # Sauvegarder
                    biblio_file, export_file = save_deck()
                    
                    log_to_ui(f"\n✅ Deck sauvegardé: {biblio_file.name}")
                    log_to_ui(f"📤 Export: {export_file.name}")
                    
                    # Afficher résultats
                    show_results(biblio_file, export_file)
                    
                except Exception as e:
                    import traceback
                    error_msg = f"❌ Erreur: {str(e)}"
                    ui.notify(error_msg, type='negative', timeout=10000)
                    log_to_ui(error_msg)
                    log_to_ui(traceback.format_exc())
            
            ui.button('⚡ Générer le Deck', on_click=generate).classes('w-full text-lg py-2')
        
        # Résultats
        def show_results(biblio_file, export_file):
            """Affiche les résultats."""
            with ui.dialog() as dlg, ui.card().classes('w-[600px]'):
                ui.label('✅ Deck Généré avec Succès!').classes('text-2xl font-bold text-green-600')
                ui.separator()
                
                ui.label(f"📁 Bibliothèque: {biblio_file.name}").classes('text-sm')
                ui.label(f"📤 Export: {export_file.name}").classes('text-sm')
                
                ui.separator()
                
                ui.label('📊 Statistiques').classes('font-semibold')
                ui.label(f"• Total cartes: {len(state.deck)}")
                ui.label(f"• Bracket: {state.bracket_level}")
                ui.label(f"• Game Changers: {state.constraint_stats['game_changers']}")
                ui.label(f"• Tutors: {state.constraint_stats['tutors']}")
                
                ui.separator()
                
                ui.label('📝 Journal de génération').classes('font-semibold')
                with ui.scroll_area().classes('h-64'):
                    for msg in state.generation_log:
                        ui.label(msg).classes('text-sm font-mono')
                
                with ui.row().classes('mt-4'):
                    def open_biblio():
                        os.startfile(str(biblio_file))
                    
                    def open_export():
                        os.startfile(str(export_file))
                    
                    ui.button('📂 Ouvrir Bibliothèque', on_click=open_biblio)
                    ui.button('📤 Ouvrir Export', on_click=open_export)
                    ui.button('Fermer', on_click=dlg.close).props('flat')
            
            dlg.open()
        
        # Pied de page
        with ui.row().classes('w-full justify-center mt-8'):
            ui.label('MTG DeckGenPy v3.0 - Interface NiceGUI').classes('text-sm text-gray-500')


# ==========================================
# LANCEMENT
# ==========================================
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title='MTG DeckGenPy - Générateur Commander',
        port=8080,
        reload=False,
        show=False  # N'ouvre pas automatiquement le navigateur
    )
