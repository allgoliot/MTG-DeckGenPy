#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MTG DeckGenPy - Interface Graphique
Générateur de Decks Commander avec interface NiceGUI

Utilise le module deck_generator.py pour la logique commune (MÊME LOGIQUE QUE CLI)
"""

import os
import sys
import re
import asyncio
import requests
import urllib.parse
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from collections import Counter

from nicegui import ui, app

# Import du moteur commun (MÊME LOGIQUE QUE CLI)
import deck_generator as engine

# Import du module d'authentification
import auth

# ==========================================
# CONFIGURATION
# ==========================================
BASE_DIR = Path(__file__).parent.parent
BIBLIO_DIR = engine.BIBLIO_DIR
EXPORTS_DIR = engine.EXPORTS_DIR
LOGS_DIR = engine.LOGS_DIR

# ==========================================
# CRÉATION DES DOSSIERS NÉCESSAIRES
# ==========================================
def create_required_directories():
    """Crée les dossiers nécessaires pour l'application."""
    required_dirs = [
        BASE_DIR / "bibliotheque",
        BASE_DIR / "exports",
        BASE_DIR / "logs",
        BASE_DIR / "__pycache__",
        BASE_DIR / "conf",
        BASE_DIR / "data",
    ]
    
    for dir_path in required_dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"[OK] Dossier verifie : {dir_path.name}")

# Créer les dossiers au démarrage
create_required_directories()

# ==========================================
# CONFIGURATION DU LOGGING
# ==========================================
# Logger pour les interactions GUI
gui_logger = logging.getLogger('MTGDeckGenPy_GUI')
gui_logger.setLevel(logging.INFO)

# Handler fichier
log_file = LOGS_DIR / f"gui_interactions_{datetime.now().strftime('%Y%m%d')}.log"
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.INFO)

# Format du log
log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(log_format)

# Ajouter le handler au logger
if not gui_logger.handlers:
    gui_logger.addHandler(file_handler)

# ==========================================
# FONCTION DE LOGGING DES INTERACTIONS
# ==========================================
def log_interaction(action: str, details: str = "", ip: str = "unknown"):
    """
    Log une interaction utilisateur.
    
    Args:
        action: Type d'action (LOGIN, GENERATE, LIBRARY, etc.)
        details: Détails de l'action
        ip: Adresse IP du client
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{ip}] {action}: {details}"
    gui_logger.info(log_msg)
    print(f"[LOG {timestamp}] {log_msg}")

# ==========================================
# ÉTAT GLOBAL
# ==========================================
class AppState:
    def __init__(self):
        self.collection = None
        self.commander = None
        self.commander_colors = set()
        self.commander_tribes = []
        self.bracket_level = 2
        self.selected_tribes = []
        self.deck = []
        self.generation_log = []
        self.library_cards_used = {}
        self.constraint_stats = {}
        self.current_user = None  # Utilisateur connecté

state = AppState()

# ==========================================
# PAGE DE CONNEXION
# ==========================================
@ui.page('/')
def login_page():
    """Page de connexion."""
    
    def try_login():
        """Tente de connecter l'utilisateur."""
        # Récupérer l'IP du client
        ip = ui.context.client.ip if hasattr(ui.context.client, 'ip') else 'unknown'
        
        username = username_input.value.strip()
        password = password_input.value
        
        if not username or not password:
            ui.notify('⚠️ Veuillez remplir tous les champs', type='warning')
            log_interaction('LOGIN_FAILED', 'Champs vides', ip)
            return
        
        user = auth.authenticate(username, password)
        
        if user:
            state.current_user = user
            app.storage.user['username'] = username
            app.storage.user['role'] = user['role']
            ui.notify(f'✅ Bienvenue {user["username"]} !', type='positive')
            log_interaction('LOGIN_SUCCESS', f'User: {username}, Role: {user["role"]}', ip)
            ui.navigate.to('/home')
        else:
            ui.notify('❌ Identifiants incorrects', type='negative')
            log_interaction('LOGIN_FAILED', f'User: {username}', ip)
    
    with ui.column().classes('w-full h-screen items-center justify-center bg-gradient-to-br from-purple-900 to-blue-900'):
        with ui.card().classes('w-[400px] p-8'):
            ui.label('🎴 MTG DeckGenPy').classes('text-3xl font-bold text-center w-full mb-2')
            ui.label('Générateur de Decks Commander').classes('text-lg text-center w-full mb-6 text-gray-400')
            
            ui.separator()
            
            username_input = ui.input('Nom d\'utilisateur').classes('w-full')
            password_input = ui.input('Mot de passe', password=True, password_toggle_button=True).classes('w-full')
            
            ui.button('🔐 Se connecter', on_click=try_login).classes('w-full mt-4').props('color=primary')

# ==========================================
# PAGE D'ACCUEIL (après connexion)
# ==========================================
@ui.page('/home')
def home_page():
    """Page d'accueil - Générateur de decks."""
    
    # Vérifier la connexion
    if state.current_user is None and 'username' not in app.storage.user:
        ui.navigate.to('/')
        return
    
    # Restaurer l'utilisateur depuis le storage
    if state.current_user is None and 'username' in app.storage.user:
        username = app.storage.user['username']
        users = auth.load_users()
        if username in users:
            state.current_user = {
                'username': username,
                'role': users[username].get('role', 'user')
            }
    
    def logout():
        """Déconnecte l'utilisateur."""
        state.current_user = None
        app.storage.user.clear()
        ui.notify('👋 Déconnecté', type='positive')
        ui.navigate.to('/')
    
    # En-tête avec menu
    with ui.header().classes('bg-gradient-to-r from-purple-600 to-blue-600'):
        with ui.row().classes('w-full justify-between items-center'):
            with ui.row().classes('items-center gap-2'):
                ui.button('🎴 MTG DeckGenPy', on_click=lambda: ui.navigate.to('/home')).props('flat color=white').classes('text-xl font-bold')
                ui.label('Générateur de Decks Commander').classes('text-sm opacity-80')

            with ui.row().classes('items-center gap-4'):
                # Infos utilisateur
                if state.current_user:
                    role_badge = '👑' if state.current_user['role'] == 'admin' else '👤'
                    ui.label(f'{role_badge} {state.current_user["username"]}').classes('text-sm')
                
                # Boutons
                ui.button('📚 Bibliothèque', on_click=lambda: ui.navigate.to('/library')).props('flat color=white')
                ui.button('🚪 Déconnexion', on_click=logout).props('flat color=white')

    # Rendu du contenu
    render_home_content()

# ==========================================
# FONCTION SPÉCIFIQUE GUI (IMAGE SCRYFALL)
# ==========================================
def get_card_image_url(card_name):
    """Récupère l'URL de l'image d'une carte depuis Scryfall."""
    try:
        encoded_name = urllib.parse.quote(card_name)
        url = f"https://api.scryfall.com/cards/named?fuzzy={encoded_name}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get('image_uris', {}).get('large', '')
    except Exception:
        pass
    return ''

# ==========================================
# FONCTION D'OUVERTURE DE FICHIER (CROSS-PLATFORM)
# ==========================================
def open_file(filepath):
    """Ouvre un fichier avec l'application par défaut (Windows, Linux, Mac)."""
    filepath = str(filepath)
    try:
        if sys.platform == 'win32':
            os.startfile(filepath)
        elif sys.platform == 'darwin':  # macOS
            subprocess.run(['open', filepath])
        else:  # Linux
            subprocess.run(['xdg-open', filepath])
    except Exception as e:
        print(f"Erreur ouverture fichier: {e}")
        ui.notify(f"Erreur: Impossible d'ouvrir le fichier ({e})", type='negative')

# ==========================================
# CONTENU DE LA PAGE D'ACCUEIL (Générateur)
# ==========================================
def render_home_content():
    """Rend le contenu de la page d'accueil (générateur de decks)."""
    
    # Contenu principal
    with ui.column().classes('w-full max-w-7xl mx-auto p-6 gap-6'):

        # Titre
        ui.label('Générateur de Deck Commander').classes('text-3xl font-bold text-center w-full')

        # Étape 1: Bracket
        with ui.card().classes('w-full'):
            ui.label('1️⃣ Sélectionnez le Bracket EDH').classes('text-xl font-semibold mb-4')

            bracket_options = {
                1: '1 : Exhibition (Ultra-Casual) - 0 GC, 2 Tutors max',
                2: '2 : Core (Préconstruit) - 0 GC, 4 Tutors max',
                3: '3 : Upgraded (Amélioré) - 3 GC, 6 Tutors max',
                4: '4 : Optimized (Haute Puissance) - Illimité'
            }

            bracket_select = ui.radio(options=bracket_options, value=2).classes('w-full')

        # Étape 2: Commandant
        with ui.card().classes('w-full'):
            # Responsive : une colonne sur mobile, deux sur desktop
            with ui.column().classes('w-full gap-6 md:grid md:grid-cols-2'):
                # Colonne gauche : Liste
                with ui.column().classes('w-full'):
                    ui.label('2️⃣ Choisissez votre Commandant').classes('text-xl font-semibold mb-4')

                    with ui.row().classes('w-full gap-2 mb-4 flex-wrap'):
                        search_input = ui.input(placeholder='Rechercher un commandant...').classes('flex-grow min-w-[200px]')

                        def do_filter():
                            filter_commanders(search_input.value)

                        search_input.on('keydown.enter', do_filter)
                        ui.button('🔍', on_click=do_filter).props('round')

                    # Liste adaptable mobile
                    commander_container = ui.column().classes('w-full max-h-[300px] md:max-h-[400px] overflow-y-auto')
                    commanders_data = []
                    selected_commander_index = None

                    def load_commanders():
                        """Charge et affiche les commandants."""
                        nonlocal commanders_data, selected_commander_index
                        
                        if state.collection is None:
                            try:
                                state.collection = engine.load_collection()
                                state.library_cards_used = engine.load_library()
                                ui.notify('Collection chargée avec succès', type='positive')
                            except FileNotFoundError as e:
                                ui.notify(str(e), type='negative', timeout=8000)
                                return

                        commanders = state.collection[
                            (state.collection["type_line"].str.contains("Legendary Creature", na=False)) &
                            (state.collection["quantity"] > 0)
                        ].copy()

                        if commanders.empty:
                            ui.notify('Aucun commandant trouvé', type='warning')
                            return

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

                        commanders["tribes"] = commanders["type_line"].apply(engine.extract_tribes)
                        commanders["strength_score"] = commanders.apply(commander_strength, axis=1)
                        commanders = commanders.sort_values("strength_score")

                        n = len(commanders)
                        group_size = max(1, n // 4)
                        commanders["bracket_group"] = [min(4, i // group_size + 1) for i in range(n)]

                        selected_bracket = bracket_select.value
                        commanders_filtered = commanders[commanders["bracket_group"] == selected_bracket].copy()
                        commanders_filtered = commanders_filtered.drop_duplicates(subset=['name'], keep='first')
                        commanders_data = commanders_filtered.reset_index(drop=True).to_dict('records')

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
                                        ui.label('Aucun commandant trouvé').classes('text-gray-500 italic p-4')
                                        return

                                    for idx, cmd in enumerate(data):
                                        tribes_str = f" [{', '.join(cmd['tribes'])}]" if cmd.get('tribes') else ""
                                        colors = engine.format_colors(cmd['colors_parsed'])
                                        is_selected = (selected_commander_index == idx)

                                        row_classes = 'w-full items-center gap-2 p-2 rounded cursor-pointer '
                                        if is_selected:
                                            row_classes += 'bg-purple-200 border-2 border-purple-500'
                                        else:
                                            row_classes += 'hover:bg-gray-100'

                                        def select_cmd(c=cmd, i=idx):
                                            nonlocal selected_commander_index
                                            selected_commander_index = i
                                            state.commander = c
                                            state.commander_colors = c["colors_parsed"]
                                            state.commander_tribes = c.get("tribes", [])
                                            ui.notify(f"✅ {c['name']} sélectionné", type='positive')
                                            update_commander_preview(c)
                                            display_commanders(data, container)
                                            load_tribes()

                                        with ui.row().classes(row_classes + ' flex-nowrap overflow-hidden').on('click', select_cmd):
                                            # Nom du commandant - texte tronqué si trop long
                                            ui.label(f"{cmd['name']}{tribes_str}").classes('flex-grow text-sm md:text-base truncate min-w-[120px]')
                                            # Badge bracket - petite taille
                                            ui.label(f"B{cmd['bracket_group']}").classes('bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded flex-shrink-0')
                                            # Couleurs - ne pas réduire
                                            ui.label(colors).classes('text-lg flex-shrink-0')
                        except RuntimeError:
                            pass

                    def filter_commanders(search_term):
                        """Filtre les commandants par recherche (nom, oracle, tribu)."""
                        if not commanders_data:
                            return
                        search_term = search_term.lower()
                        filtered = [
                            c for c in commanders_data
                            if (
                                search_term in c['name'].lower() or
                                search_term in str(c.get('oracle_text', '')).lower() or
                                any(search_term in tribe.lower() for tribe in c.get('tribes', []))
                            )
                        ]
                        display_commanders(filtered, commander_container)

                    def on_bracket_change(e):
                        load_commanders()

                    bracket_select.on('update:model-value', on_bracket_change)
                    ui.button('🔄 Charger les commandants', on_click=load_commanders)

                # Colonne droite : Aperçu
                with ui.column().classes('w-[350px]'):
                    ui.label('Aperçu du Commandant').classes('text-xl font-semibold mb-4')
                    preview_container = ui.column().classes('w-full')

                    with preview_container:
                        with ui.column().classes('w-full items-center'):
                            with ui.card().classes('w-full h-[500px] flex items-center justify-center bg-gray-100'):
                                ui.label('Sélectionnez un commandant').classes('text-gray-500 mt-2 text-center')

                    def update_commander_preview(cmd):
                        try:
                            with preview_container:
                                preview_container.clear()
                                with preview_container:
                                    image_url = get_card_image_url(cmd['name'])

                                    with ui.column().classes('w-full items-center gap-3'):
                                        if image_url:
                                            ui.image(image_url).classes('w-full max-h-[500px] object-contain rounded-lg shadow-lg')
                                        else:
                                            with ui.card().classes('w-full h-[500px] flex items-center justify-center bg-gray-200'):
                                                ui.label('Image non disponible').classes('text-sm text-gray-500')

                        except RuntimeError:
                            pass

        # Étape 3: Tribus
        with ui.card().classes('w-full'):
            ui.label('3️⃣ Filtre par Tribu (optionnel)').classes('text-xl font-semibold mb-4')
            tribe_container = ui.column().classes('w-full max-w-full')
            selected_tribes = []

            def load_tribes():
                """Charge les tribus disponibles."""
                nonlocal selected_tribes
                selected_tribes = []

                if state.collection is None:
                    ui.notify('⚠️ Collection non chargée', type='warning')
                    return

                creatures = state.collection[
                    state.collection["type_line"].str.contains("Creature", na=False, case=False)
                ].copy()

                if creatures.empty:
                    ui.notify('⚠️ Aucune créature trouvée', type='warning')
                    return

                tribes_set = set()
                tribe_counts = {}
                type_lines = creatures["type_line"].dropna().unique()

                for tl in type_lines:
                    tl_str = str(tl).lower()
                    if '—' in tl_str:
                        parts = tl_str.split('—', 1)
                        if len(parts) > 1:
                            for word in re.split(r'[\s\-]+', parts[1]):
                                word = word.strip()
                                if word and len(word) >= 2 and word not in ['legendary', 'artifact', 'enchantment', 'sorcery', 'instant', 'land']:
                                    tribes_set.add(word)

                for _, creature in creatures.iterrows():
                    tl_str = str(creature["type_line"]).lower()
                    if '—' in tl_str:
                        parts = tl_str.split('—', 1)
                        if len(parts) > 1:
                            for word in re.split(r'[\s\-]+', parts[1]):
                                word = word.strip()
                                if word and len(word) >= 2 and word not in ['legendary', 'artifact', 'enchantment', 'sorcery', 'instant', 'land']:
                                    tribe_counts[word] = tribe_counts.get(word, 0) + 1

                if state.commander and state.commander_tribes:
                    for tribe in state.commander_tribes:
                        if tribe:
                            tribes_set.add(tribe.lower())

                tribes_list = sorted(tribes_set)

                try:
                    with tribe_container:
                        tribe_container.clear()
                        with tribe_container:
                            ui.label(f"Filtre par Tribu de créatures ({len(tribes_list)} tribus, {len(creatures)} créatures):").classes('font-semibold mb-2')

                            tribe_search = ui.input(placeholder='Filtrer les tribus...').classes('w-full mb-2')
                            tribe_grid = ui.grid().classes('grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2 max-h-64 overflow-y-auto w-full')
                            checkboxes = {}

                            def update_tribe_display():
                                try:
                                    search_term = tribe_search.value.lower()
                                    with tribe_grid:
                                        tribe_grid.clear()
                                        with tribe_grid:
                                            for tribe in tribes_list:
                                                if search_term in tribe:
                                                    count = tribe_counts.get(tribe, 0)
                                                    label = f"{tribe.capitalize()} ({count})"
                                                    cb = ui.checkbox(label, value=False)
                                                    checkboxes[tribe] = cb
                                                    def on_change(is_checked, tribe_name=tribe):
                                                        if is_checked and tribe_name not in selected_tribes:
                                                            selected_tribes.append(tribe_name)
                                                        elif not is_checked and tribe_name in selected_tribes:
                                                            selected_tribes.remove(tribe_name)
                                                    cb.on('update:model-value', on_change)
                                except RuntimeError:
                                    pass

                            update_tribe_display()
                            tribe_search.on('keydown.enter', update_tribe_display)

                            with ui.row().classes('mt-2 gap-2'):
                                def select_all():
                                    search_term = tribe_search.value.lower()
                                    for tribe in tribes_list:
                                        if search_term in tribe:
                                            if tribe in checkboxes and checkboxes[tribe].value:
                                                if tribe not in selected_tribes:
                                                    selected_tribes.append(tribe)
                                    ui.notify(f'✅ {len(selected_tribes)} tribus sélectionnées', type='positive')

                                def deselect_all():
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
                    pass

            def apply_tribes():
                state.selected_tribes = selected_tribes.copy()
                if selected_tribes:
                    ui.notify(f'🏷️ Filtre appliqué: {", ".join(selected_tribes)}', type='positive')
                else:
                    ui.notify('Aucun filtre de tribu', type='info')

            ui.button('✅ Appliquer le filtre de tribu', on_click=apply_tribes).classes('mt-2').props('color=primary')

        # Étape 4: Génération
        with ui.card().classes('w-full'):
            ui.label('4️⃣ Générer le Deck').classes('text-xl font-semibold mb-4')
            progress_log = ui.log().classes('w-full h-64 font-mono text-sm')
            
            # Stocker la référence au dialog pour éviter les erreurs de contexte
            results_dialog = None

            def log_to_ui(msg):
                progress_log.push(msg)

            def generate():
                """Génère le deck en utilisant le moteur commun."""
                # Récupérer IP pour logging
                ip = ui.context.client.ip if hasattr(ui.context.client, 'ip') else 'unknown'
                
                if not state.commander:
                    ui.notify('⚠️ Veuillez sélectionner un commandant', type='warning')
                    return

                try:
                    progress_log.clear()
                    log_to_ui("🚀 Démarrage de la génération...")
                    
                    # Log la demande de génération
                    log_interaction('GENERATE_DECK', f'Bracket: {bracket_select.value}, Commander: {state.commander["name"]}', ip)

                    # Utiliser le moteur commun (MÊME LOGIQUE QUE CLI)
                    result = engine.generate_deck(
                        bracket_level=bracket_select.value,
                        commander=state.commander,
                        collection=state.collection,
                        library_cards_used=state.library_cards_used,
                        tribes=state.selected_tribes if state.selected_tribes else None,
                        log_callback=log_to_ui
                    )

                    state.deck = result['deck']
                    state.constraint_stats = result['constraint_stats']

                    # Sauvegarder
                    biblio_file, export_file = engine.save_deck(
                        deck=result['deck'],
                        commander_name=result['commander'],
                        bracket_level=result['bracket_level'],
                        constraint_stats=result['constraint_stats'],
                        collection=state.collection  # Passer la collection pour les stats
                    )

                    log_to_ui(f"\n✅ Deck sauvegardé: {biblio_file.name}")
                    log_to_ui(f"📤 Export: {export_file.name}")
                    
                    # Log la génération réussie
                    log_interaction('DECK_GENERATED', f'Commander: {result["commander"]}, Cards: {len(result["deck"])}', ip)

                    # Afficher les résultats
                    show_results(biblio_file, export_file)

                except Exception as e:
                    import traceback
                    error_msg = f"❌ Erreur: {str(e)}"
                    log_to_ui(error_msg)
                    log_to_ui(traceback.format_exc())
                    ui.notify(error_msg, type='negative', timeout=10000)

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
                    ui.label(f"• Game Changers: {state.constraint_stats.get('game_changers', 0)}")
                    ui.label(f"• Tutors: {state.constraint_stats.get('tutors', 0)}")

                    ui.separator()

                    ui.label('📝 Journal de génération').classes('font-semibold')
                    with ui.scroll_area().classes('h-64'):
                        for msg in state.generation_log:
                            ui.label(msg).classes('text-sm font-mono')

                    with ui.row().classes('mt-4'):
                        def open_biblio():
                            open_file(str(biblio_file))

                        def open_export():
                            open_file(str(export_file))

                        ui.button('📂 Ouvrir Bibliothèque', on_click=open_biblio)
                        ui.button('📤 Ouvrir Export', on_click=open_export)
                        ui.button('Fermer', on_click=dlg.close).props('flat')

                dlg.open()

            ui.button('⚡ Générer le Deck', on_click=generate).classes('w-full text-lg py-2')

        # Pied de page
        with ui.row().classes('w-full justify-center mt-8'):
            ui.label('MTG DeckGenPy v3.0 - Interface NiceGUI').classes('text-sm text-gray-500')


# ==========================================
# PAGE BIBLIOTHÈQUE
# ==========================================
@ui.page('/library')
def library_page():
    """Page de la bibliothèque des decks."""
    
    # Récupérer IP pour logging
    ip = ui.context.client.ip if hasattr(ui.context.client, 'ip') else 'unknown'
    
    # Log l'accès à la bibliothèque
    log_interaction('PAGE_LIBRARY', 'Accès page bibliothèque', ip)

    # Vérifier la connexion
    if state.current_user is None and 'username' not in app.storage.user:
        ui.navigate.to('/')
        return

    # Restaurer l'utilisateur depuis le storage
    if state.current_user is None and 'username' in app.storage.user:
        username = app.storage.user['username']
        users = auth.load_users()
        if username in users:
            state.current_user = {
                'username': username,
                'role': users[username].get('role', 'user')
            }

    def logout():
        """Déconnecte l'utilisateur."""
        ip_logout = ui.context.client.ip if hasattr(ui.context.client, 'ip') else 'unknown'
        username = state.current_user['username'] if state.current_user else 'unknown'
        log_interaction('LOGOUT', f'User: {username}', ip_logout)
        state.current_user = None
        app.storage.user.clear()
        ui.notify('👋 Déconnecté', type='positive')
        ui.navigate.to('/')
    
    # En-tête avec menu
    with ui.header().classes('bg-gradient-to-r from-purple-600 to-blue-600'):
        with ui.row().classes('w-full justify-between items-center'):
            with ui.row().classes('items-center gap-2'):
                ui.button('🎴 MTG DeckGenPy', on_click=lambda: ui.navigate.to('/home')).props('flat color=white').classes('text-xl font-bold')
                ui.label('Bibliothèque').classes('text-2xl font-bold')

            with ui.row().classes('items-center gap-4'):
                # Infos utilisateur
                if state.current_user:
                    role_badge = '👑' if state.current_user['role'] == 'admin' else '👤'
                    ui.label(f'{role_badge} {state.current_user["username"]}').classes('text-sm')
                
                # Boutons
                ui.button('🏠 Accueil', on_click=lambda: ui.navigate.to('/home')).props('flat color=white')
                ui.button('🚪 Déconnexion', on_click=logout).props('flat color=white')

    with ui.column().classes('w-full max-w-7xl mx-auto p-6 gap-6'):
        ui.label('Decks Stockés dans la Bibliothèque').classes('text-3xl font-bold text-center w-full')

        # Menu de chargement (reste TOUJOURS en haut de page)
        loading_card = ui.card().classes('w-full items-center justify-center p-8')
        with loading_card:
            ui.spinner(color='primary', size='xl').classes('mb-4')
            ui.label('Chargement de la bibliothèque...').classes('text-xl font-bold mb-4')
            # Barre de progression (0% → 100% sans affichage numérique)
            progress_bar = ui.linear_progress(value=0, show_value=False).classes('w-full max-w-md')

        # Grille des decks (se remplit progressivement en dessous)
        deck_grid = ui.grid().classes('grid-cols-3 gap-6 w-full')

        def load_library_sync():
            """Charge la bibliothèque de manière synchrone."""
            try:
                if not engine.BIBLIO_DIR.exists():
                    with loading_card:
                        loading_card.clear()
                        with loading_card:
                            ui.label('Aucun deck dans la bibliothèque').classes('text-gray-500 italic')
                    return

                decks = [f for f in engine.BIBLIO_DIR.iterdir() if f.suffix == '.txt']

                if not decks:
                    with loading_card:
                        loading_card.clear()
                        with loading_card:
                            ui.label('Aucun deck dans la bibliothèque').classes('text-gray-500 italic')
                    return

                total_decks = len(decks)

                # Initialiser la barre à 0
                progress_bar.value = 0

                # Charger les decks - progression directe
                for idx, deck_file in enumerate(sorted(decks), start=1):
                    # Mettre à jour la progression (0 → 100)
                    progress = (idx / total_decks) * 100
                    progress_bar.value = progress

                    with deck_grid:
                        with ui.card().classes('w-full cursor-pointer hover:shadow-lg transition-shadow').on('click', lambda f=deck_file: show_deck_details(f)):
                            commander_name = deck_file.stem.replace('-', ' ')
                            bracket_info = ""

                            try:
                                with open(deck_file, 'r', encoding='utf-8') as f:
                                    for line in f:
                                        line = line.strip()
                                        if line.startswith('// EDH Bracket:'):
                                            bracket_info = line.replace('// EDH Bracket:', '').strip()
                                            break
                                        if line.startswith('// COMMANDER'):
                                            continue
                                        if not line.startswith('//'):
                                            break
                            except:
                                pass

                            image_url = get_card_image_url(commander_name)

                            with ui.column().classes('w-full items-center p-4'):
                                if image_url:
                                    # Image non tronquée - hauteur suffisante pour voir la carte entière
                                    ui.image(image_url).classes('w-full max-h-[500px] object-contain rounded-lg shadow-lg')
                                else:
                                    with ui.card().classes('w-full h-64 flex items-center justify-center bg-gray-200'):
                                        ui.label('🎴').classes('text-6xl')

                                ui.label(commander_name).classes('text-lg font-bold text-center mt-2')

                                if bracket_info:
                                    ui.badge(bracket_info).classes('bg-blue-100 text-blue-800 mt-1')

                                try:
                                    with open(deck_file, 'r', encoding='utf-8') as f:
                                        card_count = sum(1 for line in f if line.strip() and not line.startswith('//'))
                                    ui.label(f'{card_count} cartes').classes('text-sm text-gray-500 mt-1')
                                except:
                                    pass

                # Modifier le menu de chargement (reste en haut) une fois terminé
                with loading_card:
                    loading_card.clear()
                    with loading_card:
                        ui.label('✅ Bibliothèque chargée').classes('text-xl font-bold text-green-600')
                        ui.button('🔄 Actualiser', on_click=load_library_sync).classes('mt-2')

            except Exception as e:
                print(f"Erreur chargement bibliothèque: {e}")
                return

        # Charger la bibliothèque directement (pas de timer pour éviter erreurs async)
        load_library_sync()

        def show_deck_details(deck_file):
            """Affiche les détails d'un deck."""
            with ui.dialog() as dlg, ui.card().classes('w-[1200px] h-[750px] flex flex-col'):
                ui.label('📄 Détails du Deck').classes('text-2xl font-bold mb-4')

                commander_name = deck_file.stem.replace('-', ' ')

                with ui.row().classes('w-full gap-6 flex-1 overflow-hidden'):
                    with ui.column().classes('w-1/4 items-center'):
                        ui.label('Commandant').classes('font-semibold mb-2')

                        image_url = get_card_image_url(commander_name)
                        if image_url:
                            # Image non tronquée - hauteur suffisante pour voir la carte entière
                            ui.image(image_url).classes('w-full max-h-[500px] object-contain rounded-lg shadow-lg')
                        else:
                            with ui.card().classes('w-full h-64 flex items-center justify-center bg-gray-200'):
                                ui.label('🎴').classes('text-6xl')

                        ui.label(commander_name).classes('text-lg font-bold text-center mt-2')

                        ui.separator()
                        ui.label('Statistiques').classes('font-semibold mb-2')

                        # Lire les statistiques depuis le fichier
                        creatures = 0
                        non_creatures = 0
                        lands = 0
                        artifacts = 0
                        enchantments = 0
                        sorceries = 0
                        instants = 0
                        planeswalkers = 0
                        others = 0
                        
                        try:
                            with open(deck_file, 'r', encoding='utf-8') as f:
                                for line in f:
                                    line = line.strip()
                                    if not line or line.startswith('//'):
                                        # Lire les stats depuis les commentaires
                                        if line.startswith('// Créatures:'):
                                            creatures = int(line.split(':')[1].strip())
                                        elif line.startswith('// Artifacts:'):
                                            artifacts = int(line.split(':')[1].strip())
                                        elif line.startswith('// Enchantements:'):
                                            enchantments = int(line.split(':')[1].strip())
                                        elif line.startswith('// Rituals:'):
                                            sorceries = int(line.split(':')[1].strip())
                                        elif line.startswith('// Éphémères:'):
                                            instants = int(line.split(':')[1].strip())
                                        elif line.startswith('// Arpenteurs:'):
                                            planeswalkers = int(line.split(':')[1].strip())
                                        elif line.startswith('// Terrains:'):
                                            lands = int(line.split(':')[1].strip())
                                        elif line.startswith('// Autres:'):
                                            others = int(line.split(':')[1].strip())
                                        continue
                                    
                                    # Si pas de stats dans les commentaires, calculer depuis la collection
                                    if state.collection is not None and creatures == 0:
                                        parts = line.split(maxsplit=1)
                                        name = parts[1] if len(parts) == 2 else parts[0]
                                        norm = engine.normalize_card_name(name)
                                        match = state.collection[state.collection['name'].str.lower() == norm]
                                        if not match.empty:
                                            tl = str(match.iloc[0].get('type_line', '')).lower()
                                            if 'land' in tl:
                                                lands += 1
                                            elif 'creature' in tl:
                                                creatures += 1
                                            elif 'artifact' in tl:
                                                artifacts += 1
                                            elif 'enchantment' in tl:
                                                enchantments += 1
                                            elif 'sorcery' in tl:
                                                sorceries += 1
                                            elif 'instant' in tl:
                                                instants += 1
                                            elif 'planeswalker' in tl:
                                                planeswalkers += 1
                                            else:
                                                others += 1
                                        else:
                                            others += 1
                                    
                                    non_creatures = artifacts + enchantments + sorceries + instants + planeswalkers + others

                            with ui.column().classes('w-full gap-1'):
                                ui.label(f'⚔️ Créatures: {creatures}').classes('text-sm')
                                ui.label(f'🔧 Artifacts: {artifacts}').classes('text-sm')
                                ui.label(f'✨ Enchantements: {enchantments}').classes('text-sm')
                                ui.label(f'📜 Rituals: {sorceries}').classes('text-sm')
                                ui.label(f'⚡ Éphémères: {instants}').classes('text-sm')
                                ui.label(f'🎭 Arpenteurs: {planeswalkers}').classes('text-sm')
                                ui.label(f'🏔️ Terrains: {lands}').classes('text-sm')
                                ui.label(f'📦 Autres: {others}').classes('text-sm')
                                ui.separator()
                                total = creatures + non_creatures + lands
                                ui.label(f'📊 Total: {total} cartes').classes('text-sm font-bold')
                        except Exception as e:
                            ui.label(f'Erreur de lecture: {e}').classes('text-red-500')

                    with ui.column().classes('w-3/4'):
                        with ui.row().classes('w-full justify-between items-center mb-2'):
                            ui.label('Decklist Complète').classes('font-semibold text-lg')

                            def copy_decklist():
                                try:
                                    with open(deck_file, 'r', encoding='utf-8') as f:
                                        content = f.read()
                                    ui.clipboard.write(content)
                                    ui.notify('Decklist copiée !', type='positive', timeout=2000)
                                except Exception as e:
                                    ui.notify(f'Erreur: {e}', type='negative')

                            ui.button('📋 Copier', on_click=copy_decklist).props('flat dense')

                        try:
                            with open(deck_file, 'r', encoding='utf-8') as f:
                                decklist_content = f.read()
                        except:
                            decklist_content = 'Erreur'

                        ui.textarea(value=decklist_content).classes('w-full flex-1 font-mono text-sm').props('readonly outlined')

                        with ui.row().classes('w-full gap-2 mt-4'):
                            def open_deck_file():
                                open_file(str(deck_file))

                            def export_deck():
                                export_file = engine.EXPORTS_DIR / f"{deck_file.stem}_decklist.txt"
                                import shutil
                                shutil.copy(deck_file, export_file)
                                ui.notify(f'Deck exporté vers {export_file.name}', type='positive')
                                log_interaction('DECK_EXPORT', f'Deck: {deck_file.name}', ip)

                            def delete_deck():
                                deck_file.unlink()
                                ui.notify(f'Deck {deck_file.name} supprimé', type='positive')
                                log_interaction('DECK_DELETE', f'Deck: {deck_file.name}', ip)
                                dlg.close()
                                # Recharger la bibliothèque après suppression
                                ui.timer(0.1, load_library_sync, once=True)

                            ui.button('📂 Ouvrir', on_click=open_deck_file)
                            ui.button('📤 Exporter', on_click=export_deck)
                            ui.button('❌ Supprimer', on_click=delete_deck, color='negative')

                with ui.row().classes('w-full justify-end mt-4'):
                    ui.button('Fermer', on_click=dlg.close).props('color=primary')

            dlg.open()


# ==========================================
# LANCEMENT
# ==========================================
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title='MTG DeckGenPy - Générateur Commander',
        port=8080,
        reload=False,
        show=False,
        storage_secret='mtg-deckgenpy-secret-key-2024'  # Clé de chiffrement pour les sessions
    )
