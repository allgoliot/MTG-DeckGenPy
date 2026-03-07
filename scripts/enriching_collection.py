#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MTG DeckGenPy - Script d'Enrichissement de Collection
Analyse collection.csv et ajoute les cartes manquantes depuis Scryfall
"""

import pandas as pd
import requests
import time
import os
from pathlib import Path

# ==========================================
# CONFIGURATION DES CHEMINS
# ==========================================
BASE_DIR = Path(__file__).parent.parent
COLLECTION_PATH = BASE_DIR / "data" / "collection.csv"
ENRICHED_PATH = BASE_DIR / "data" / "collection_enriched.csv"

# ==========================================
# CONFIGURATION
# ==========================================
SCRYFALL_API = "https://api.scryfall.com/cards/search"
REQUEST_DELAY = 0.1  # Délai entre les requêtes (100ms)

# ==========================================
# FONCTIONS UTILITAIRES
# ==========================================

def load_collection():
    """Charge la collection depuis collection.csv."""
    if not COLLECTION_PATH.exists():
        raise FileNotFoundError(f"Collection introuvable : {COLLECTION_PATH}")
    
    collection = pd.read_csv(COLLECTION_PATH)
    
    # Normaliser les noms de colonnes
    collection.columns = (collection.columns
                          .str.strip()
                          .str.lower()
                          .str.replace(' ', '_', regex=False))
    
    return collection

def load_enriched():
    """Charge la collection enrichie existante (si elle existe)."""
    if not ENRICHED_PATH.exists():
        return pd.DataFrame()
    
    enriched = pd.read_csv(ENRICHED_PATH)
    enriched.columns = (enriched.columns
                        .str.strip()
                        .str.lower()
                        .str.replace(' ', '_', regex=False))
    
    return enriched

def normalize_card_name(name):
    """Normalise le nom d'une carte pour comparaison."""
    name = str(name).strip().lower()
    # Supprimer les caractères spéciaux
    name = ''.join(c for c in name if c.isalnum() or c.isspace())
    return ' '.join(name.split())

def search_scryfall(card_name):
    """Recherche une carte sur Scryfall par nom."""
    try:
        params = {'q': f'!"{card_name}"'}
        response = requests.get(SCRYFALL_API, params=params, timeout=10)
        
        if response.status_code != 200:
            print(f"  ⚠️ Erreur API: {response.status_code}")
            return None
        
        data = response.json()
        
        if data.get('object') == 'error':
            print(f"  ❌ {data.get('details', 'Erreur inconnue')}")
            return None
        
        if data.get('total_cards', 0) == 0:
            return None
        
        # Retourner la première carte (la plus pertinente)
        return data['data'][0]
    
    except Exception as e:
        print(f"  ❌ Erreur: {e}")
        return None

def extract_card_data(scryfall_data):
    """Extrait les données pertinentes depuis Scryfall."""
    if not scryfall_data:
        return None
    
    return {
        'name': scryfall_data.get('name', ''),
        'type_line': scryfall_data.get('type_line', ''),
        'oracle_text': scryfall_data.get('oracle_text', ''),
        'mana_value': scryfall_data.get('cmc', 0),
        'color_identity': str(scryfall_data.get('color_identity', [])),
        'colors': str(scryfall_data.get('colors', [])),
        'rarity': scryfall_data.get('rarity', ''),
        'set_code': scryfall_data.get('set', ''),
        'artist': scryfall_data.get('artist', ''),
        'image_uris': str(scryfall_data.get('image_uris', {}))
    }

def card_exists_in_enriched(card_name, enriched_collection):
    """Vérifie si une carte existe déjà dans la collection enrichie."""
    normalized_name = normalize_card_name(card_name)
    
    if enriched_collection.empty:
        return False
    
    # Vérifier si le nom normalisé existe déjà
    existing_names = enriched_collection['name'].apply(normalize_card_name)
    return normalized_name in existing_names.values

# ==========================================
# FONCTION PRINCIPALE
# ==========================================

def main():
    """Fonction principale d'enrichissement."""
    print("=" * 60)
    print("  MTG DeckGenPy - Enrichissement de Collection")
    print("=" * 60)
    print()
    
    # 1. Charger la collection
    print("📥 Chargement de collection.csv...")
    try:
        collection = load_collection()
        print(f"   ✅ {len(collection)} cartes chargées")
    except FileNotFoundError as e:
        print(f"   ❌ {e}")
        return
    
    # 2. Charger la collection enrichie existante
    print("\n📥 Chargement de collection_enriched.csv (si existe)...")
    enriched = load_enriched()
    if enriched.empty:
        print("   ℹ️ Aucun fichier enrichi existant, création d'un nouveau")
        enriched_columns = ['name', 'type_line', 'oracle_text', 'mana_value', 
                           'color_identity', 'colors', 'rarity', 'set_code', 
                           'artist', 'image_uris', 'quantity']
        enriched = pd.DataFrame(columns=enriched_columns)
    else:
        print(f"   ✅ {len(enriched)} cartes déjà enrichies")
    
    # 3. Identifier les cartes manquantes
    print("\n🔍 Analyse des cartes manquantes...")
    missing_cards = []
    
    for idx, row in collection.iterrows():
        card_name = row.get('name', '')
        quantity = row.get('quantity', 1)
        
        # Vérifier si la carte existe déjà
        if not card_exists_in_enriched(card_name, enriched):
            missing_cards.append({
                'name': card_name,
                'quantity': quantity
            })
    
    print(f"   📊 {len(missing_cards)} cartes à enrichir")
    
    if not missing_cards:
        print("\n✅ Toutes les cartes sont déjà enrichies !")
        print(f"   Collection enrichie: {len(enriched)} cartes")
        return
    
    # 4. Enrichir les cartes manquantes
    print("\n🌐 Enrichissement depuis Scryfall...")
    print("-" * 60)
    
    new_cards = []
    
    for i, card in enumerate(missing_cards, start=1):
        card_name = card['name']
        quantity = card['quantity']
        
        print(f"[{i}/{len(missing_cards)}] {card_name} (x{quantity})")
        
        # Rechercher sur Scryfall
        scryfall_data = search_scryfall(card_name)
        
        if scryfall_data:
            card_data = extract_card_data(scryfall_data)
            if card_data:
                card_data['quantity'] = quantity
                new_cards.append(card_data)
                print(f"   ✅ {card_data['name']} - {card_data['type_line']}")
        else:
            print(f"   ❌ Carte non trouvée")
        
        # Délai pour éviter de spam l'API
        time.sleep(REQUEST_DELAY)
    
    # 5. Fusionner avec la collection enrichie
    print("\n" + "=" * 60)
    print("💾 Sauvegarde de la collection enrichie...")
    
    if new_cards:
        new_cards_df = pd.DataFrame(new_cards)
        enriched = pd.concat([enriched, new_cards_df], ignore_index=True)
        print(f"   ✅ {len(new_cards)} nouvelles cartes ajoutées")
    
    # Réorganiser les colonnes
    column_order = ['name', 'type_line', 'oracle_text', 'mana_value', 
                    'color_identity', 'colors', 'rarity', 'set_code', 
                    'artist', 'image_uris', 'quantity']
    enriched = enriched[column_order]
    
    # Sauvegarder
    enriched.to_csv(ENRICHED_PATH, index=False, encoding='utf-8')
    print(f"   ✅ Sauvegardé dans : {ENRICHED_PATH}")
    
    # 6. Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ")
    print("=" * 60)
    print(f"   Collection initiale: {len(collection)} cartes")
    print(f"   Cartes enrichies: {len(enriched)} cartes")
    print(f"   Nouvelles cartes: {len(new_cards)}")
    print(f"   Cartes déjà présentes: {len(missing_cards) - len(new_cards)}")
    print()
    print("✅ Enrichissement terminé !")
    print()

# ==========================================
# LANCEMENT
# ==========================================
if __name__ == "__main__":
    main()
