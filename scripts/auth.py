#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MTG DeckGenPy - Module d'Authentification
"""

import hashlib
import yaml
from pathlib import Path

# ==========================================
# CONFIGURATION
# ==========================================
BASE_DIR = Path(__file__).parent.parent
USERS_FILE = BASE_DIR / "conf" / "users.yaml"

# ==========================================
# FONCTIONS
# ==========================================

def load_users():
    """Charge les utilisateurs depuis le fichier YAML."""
    if not USERS_FILE.exists():
        return {}
    
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        return data.get('users', {})

def hash_password(password):
    """Hache le mot de passe en SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate(username, password):
    """
    Authentifie un utilisateur.
    
    Args:
        username: Nom d'utilisateur
        password: Mot de passe (en clair)
    
    Returns:
        dict: {'username': str, 'role': str} ou None si échec
    """
    users = load_users()
    
    if username not in users:
        return None
    
    user_data = users[username]
    stored_password = user_data.get('password', '')
    
    # Vérifier mot de passe (en clair ou hashé)
    if password == stored_password or hash_password(password) == stored_password:
        return {
            'username': username,
            'role': user_data.get('role', 'user')
        }
    
    return None

def get_user_role(username):
    """Récupère le rôle d'un utilisateur."""
    users = load_users()
    if username in users:
        return users[username].get('role', 'user')
    return None

def user_exists(username):
    """Vérifie si un utilisateur existe."""
    users = load_users()
    return username in users

def create_user(username, password, role='user'):
    """
    Crée un nouvel utilisateur.
    
    Args:
        username: Nom d'utilisateur
        password: Mot de passe
        role: Rôle ('user' ou 'admin')
    
    Returns:
        bool: True si créé, False si existe déjà
    """
    users = load_users()
    
    if username in users:
        return False
    
    users[username] = {
        'password': hash_password(password),
        'role': role
    }
    
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        yaml.dump({'users': users}, f, default_flow_style=False)
    
    return True
