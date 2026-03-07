#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MTG DeckGenPy - Script Principal de Génération (CLI)
Utilise le module deck_generator.py pour la logique commune
"""

import sys
import os
from datetime import datetime

# Import du moteur commun
import deck_generator as engine

# ==========================================
# CLASSE POUR LOGGING (EFFET TEE)
# ==========================================
class TeeHandler:
    """Redirige la sortie vers la console ET un fichier de log."""
    def __init__(self, *streams):
        self.streams = streams

    def write(self, text):
        for stream in self.streams:
            stream.write(text)
            stream.flush()

    def flush(self):
        for stream in self.streams:
            stream.flush()

# ==========================================
# FONCTION PRINCIPALE
# ==========================================
def main():
    """Fonction principale du script CLI."""
    
    # ==========================================
    # 1. CHARGER LA COLLECTION
    # ==========================================
    print(f"Chargement de la collection depuis : {engine.COLLECTION_PATH}")
    collection = engine.load_collection()
    
    # ==========================================
    # 2. DIFFICULTÉ (bracket officiel EDH)
    # ==========================================
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
    
    # ==========================================
    # 3. TROUVER LES COMMANDANTS
    # ==========================================
    commanders = collection[
        (collection["type_line"].str.contains("Legendary Creature", na=False)) &
        (collection["quantity"] > 0)
    ].copy()
    
    if not commanders.empty:
        def extract_tribes(tl):
            tl = str(tl).lower()
            if 'creature' not in tl:
                return []
            if '—' in tl:
                return [w.strip() for w in tl.split('—', 1)[1].split()]
            return []
        
        def commander_strength(row):
            text = str(row.get("oracle_text", "")).lower()
            mv = row.get("mana_value", 0)
            score = 0
            if engine.contains_any(text, engine.RAMP_WORDS): score += 1
            if engine.contains_any(text, engine.DRAW_WORDS): score += 1
            if engine.contains_any(text, engine.REMOVAL_WORDS): score += 1
            if engine.contains_any(text, engine.WIPE_WORDS): score += 1
            if "creature" in str(row.get("type_line", "")).lower(): score += 1
            score -= mv * 0.1
            return score
        
        commanders["tribes"] = commanders["type_line"].apply(extract_tribes)
        commanders["strength_score"] = commanders.apply(commander_strength, axis=1)
        commanders = commanders.sort_values("strength_score")
        
        n = len(commanders)
        group_size = max(1, n // 4)
        commanders["bracket_group"] = [min(4, i // group_size + 1) for i in range(n)]
        
        if BRACKET_LEVEL in [1, 4]:
            commanders = commanders[commanders["bracket_group"] == BRACKET_LEVEL]
        else:
            commanders = commanders[commanders["bracket_group"] == BRACKET_LEVEL]
    
    commanders = commanders.drop_duplicates(subset=['name'], keep='first')
    print(f"\n🎯 {len(commanders)} commandants uniques disponibles pour le bracket {BRACKET_LEVEL}\n")
    
    # ==========================================
    # 4. SÉLECTION DU COMMANDANT
    # ==========================================
    commander = None
    while commander is None:
        print("Commandants disponibles :")
        for idx, row in commanders.reset_index(drop=True).iterrows():
            colors = row.get('colors_parsed', set())
            bracket_grp = row.get('bracket_group', '?')
            tribes = row.get('tribes', [])
            tribe_str = f" [{' '.join(tribes)}]" if tribes else ""
            color_symbols = engine.format_colors(colors)
            print(f"{idx+1}. {row['name']}{tribe_str} [bracket {bracket_grp}] {color_symbols}")
        
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
        print(candidate.get('oracle_text', '(aucun)'))
        confirm = input("Confirmer ce commandant ? (o/n) : ").strip().lower()
        if confirm.startswith('o'):
            commander = candidate
            commander_colors = commander["colors_parsed"]
            print("Commandant choisi :", commander["name"])
        else:
            print("Choix annulé, veuillez sélectionner un autre commandant.\n")
    
    # ==========================================
    # 5. FILTRE DE TRIBU (OPTIONNEL)
    # ==========================================
    selected_tribes = []
    if engine.ENABLE_TRIBE_SELECTION:
        all_types = collection["type_line"].dropna().str.lower().unique()
        tribe_set = set()
        
        for tl in all_types:
            parts = tl.split('—')
            if len(parts) > 1:
                for word in __import__('re').split(r"[^a-z]+", parts[1]):
                    if word and len(word) > 2:
                        tribe_set.add(word)
        
        tribes_list = sorted(tribe_set)
        if tribes_list:
            print("Tribus disponibles :")
            for idx, tr in enumerate(tribes_list, start=1):
                print(f"{idx}. {tr}")
            sel = input("Sélectionnez un ou plusieurs numéros (ex. 1-3,5) ou laissez vide : ").strip()
            if sel:
                chosen = set()
                for part in sel.split(','):
                    if '-' in part:
                        a, b = part.split('-', 1)
                        try:
                            for i in range(int(a), int(b)+1):
                                if 1 <= i <= len(tribes_list):
                                    chosen.add(tribes_list[i-1])
                        except ValueError:
                            continue
                    else:
                        try:
                            i = int(part)
                            if 1 <= i <= len(tribes_list):
                                chosen.add(tribes_list[i-1])
                        except ValueError:
                            continue
                selected_tribes = list(chosen)
    
    # ==========================================
    # 6. CHARGER BIBLIOTHÈQUE (DOUBLONS)
    # ==========================================
    print("\n📚 VÉRIFICATION DES DECKS EXISTANTS...")
    library_cards_used = engine.load_library()
    nb_decks = len([f for f in engine.BIBLIO_DIR.iterdir() if f.suffix == '.txt'])
    nb_cartes = len(library_cards_used)
    print(f"   📊 Total: {nb_decks} deck(s), {nb_cartes} cartes uniques déjà utilisées")
    
    # ==========================================
    # 7. GÉNÉRER LE DECK
    # ==========================================
    print("\n🚀 GÉNÉRATION DU DECK EN COURS...")
    
    # Configuration du logging
    safe_name = __import__('re').sub(r"[^A-Za-z0-9]+", "-", commander["name"]).strip("-")
    log_filename = engine.LOGS_DIR / f"{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    log_file = open(log_filename, "w", encoding="utf-8")
    tee = TeeHandler(sys.stdout, log_file)
    sys.stdout = tee
    
    # Générer le deck en utilisant le moteur commun
    result = engine.generate_deck(
        bracket_level=BRACKET_LEVEL,
        commander=commander.to_dict(),
        collection=collection,
        library_cards_used=library_cards_used,
        tribes=selected_tribes if selected_tribes else None,
        log_callback=lambda msg: print(msg)
    )
    
    # ==========================================
    # 8. SAUVEGARDER LE DECK
    # ==========================================
    biblio_file, export_file = engine.save_deck(
        deck=result['deck'],
        commander_name=result['commander'],
        bracket_level=result['bracket_level'],
        constraint_stats=result['constraint_stats'],
        collection=collection  # Passer la collection pour les stats
    )
    
    print(f"\n✅ Deck généré et sauvegardé : {biblio_file.name}")
    print(f"📤 Export : {export_file.name}")
    print("=" * 60)
    
    # Fermer le log
    log_file.close()
    sys.stdout = sys.__stdout__
    
    print(f"\n📝 Log sauvegardé : {log_filename.name}")
    print("\n=== GÉNÉRATION TERMINÉE ===")

# ==========================================
# LANCEMENT
# ==========================================
if __name__ == "__main__":
    main()
