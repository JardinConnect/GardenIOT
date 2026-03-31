# Fichier: gest_noeud.py
import json
import os
from datetime import datetime
import uuid

FILE_JSON = "child.json"

def init():
    """Initialise le fichier JSON avec la structure correcte"""
    if not os.path.exists(FILE_JSON):
        data = {
            "parent_id": get_parent_id(),
            "children": []
        }
        with open(FILE_JSON, 'w') as f:
            json.dump(data, f, indent=4)

def all_child():
    """Retourne la structure complète du fichier"""
    try:
        with open(FILE_JSON, 'r') as f:
            data = json.load(f)
            if isinstance(data, list):
                new_data = {
                    "parent_id": get_parent_id(),
                    "children": data
                }
                save_nodes(new_data)
                return new_data
            return data
    except:
        return {
            "parent_id": get_parent_id(),
            "children": []
        }

def save_nodes(data):
    """Écrit les données dans le fichier JSON"""
    with open(FILE_JSON, "w") as f:
        json.dump(data, f, indent=4)

def add_child(idChild):
    """Ajoute un enfant à la liste"""
    data = all_child()
    
    # Verifier si il existe deja
    for child in data["children"]:
        if isinstance(child, dict) and child.get('id') == idChild:
            print(f"{idChild} déjà connu")
            return False
        elif isinstance(child, str) and child == idChild:
            print(f"{idChild} déjà connu")
            return False
    
    # Ajout d'un nouvel enfant
    newChild = {
        "id": idChild,
        "date": str(datetime.now())
    }
    data["children"].append(newChild)
    
    save_nodes(data)
    print(f"[DB] {idChild} ajouté")
    return True

def get_parent_id():
    """Récupère l'ID unique du Raspberry Pi"""
    try:
        with open(FILE_JSON, 'r') as f:
            data = json.load(f)
            if isinstance(data, dict) and "parent_id" in data:
                return data["parent_id"]
    except:
        pass
    
    # Si l'id n'est pas présent on genere un nouvel id basé sur l'adresse MAC
    cpuserial = "0000000000000000"

    if cpuserial == "0000000000000000" or cpuserial == "UNKNOWN":
        cpuserial = hex(uuid.getnode())[2:]
        
    return cpuserial.strip()

def remove_child(child_uid):
    """Supprime un enfant de la liste"""
    data = all_child()
    
    # Cherche l'enfant dans la liste
    for i, child in enumerate(data["children"]):
        child_id = child.get('id') if isinstance(child, dict) else child
        
        if child_id == child_uid:
            data["children"].pop(i)
            save_nodes(data)
            print(f"[DB] {child_uid} supprimé")
            return True
    
    print(f"{child_uid} introuvable")
    return False

def remove_all_children():
    """Supprime tous les enfants"""
    data = all_child()
    count = len(data["children"])
    
    data["children"] = []
    save_nodes(data)
    
    print(f"{count} enfants supprimés")
    return True

def est_autorise(child_uid):
    """Vérifie si un enfant est autorisé"""
    data = all_child()
    
    for child in data["children"]:
        child_id = child.get('id') if isinstance(child, dict) else child
        
        if child_id == child_uid:
            return True
    
    return False
