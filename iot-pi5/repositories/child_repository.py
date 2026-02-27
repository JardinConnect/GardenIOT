"""
Child Repository - Gestion persistante des enfants appairés
"""
import json
import os
from typing import List, Dict, Any
from datetime import datetime
import uuid


class ChildRepository:
    """
    Gère la persistence des enfants appairés
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.file_path = config.get("file_path", "child.json")
        self.parent_id = None
    
    def initialize(self):
        """Initialise le repository"""
        self.parent_id = self._get_parent_id()
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """S'assure que le fichier existe avec la structure correcte"""
        if not os.path.exists(self.file_path):
            data = {
                "parent_id": self.parent_id,
                "children": []
            }
            self._save_data(data)
    
    def _load_data(self) -> Dict[str, Any]:
        """Charge les données depuis le fichier"""
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
                
                # Migration si ancien format (liste)
                if isinstance(data, list):
                    data = {
                        "parent_id": self.parent_id,
                        "children": data
                    }
                    self._save_data(data)
                
                return data
        except (json.JSONDecodeError, FileNotFoundError):
            return {
                "parent_id": self.parent_id,
                "children": []
            }
    
    def _save_data(self, data: Dict[str, Any]):
        """Sauvegarde les données dans le fichier"""
        with open(self.file_path, 'w') as f:
            json.dump(data, f, indent=4)
    
    def _get_parent_id(self) -> str:
        """Génère ou récupère l'ID du parent"""
        try:
            data = self._load_data()
            if "parent_id" in data and data["parent_id"]:
                return data["parent_id"]
        except:
            pass
        
        # Générer un nouvel ID basé sur l'adresse MAC ou UUID
        try:
            mac_address = hex(uuid.getnode())[2:]
            return mac_address.strip()
        except:
            return str(uuid.uuid4()).replace("-", "")[:12]
    
    def get_parent_id(self) -> str:
        """Retourne l'ID du parent"""
        return self.parent_id
    
    def get_all_children(self) -> List[Dict[str, Any]]:
        """Retourne tous les enfants"""
        data = self._load_data()
        return data.get("children", [])
    
    def add_child(self, child_uid: str) -> bool:
        """Ajoute un enfant"""
        data = self._load_data()
        
        # Vérifier si l'enfant existe déjà
        for child in data["children"]:
            child_id = child.get('id') if isinstance(child, dict) else child
            if child_id == child_uid:
                print(f"ℹ️ {child_uid} déjà connu")
                return False
        
        # Ajouter le nouvel enfant
        new_child = {
            "id": child_uid,
            "date": datetime.now().isoformat()
        }
        data["children"].append(new_child)
        
        self._save_data(data)
        print(f"✅ {child_uid} ajouté")
        return True
    
    def remove_child(self, child_uid: str) -> bool:
        """Supprime un enfant"""
        data = self._load_data()
        
        for i, child in enumerate(data["children"]):
            child_id = child.get('id') if isinstance(child, dict) else child
            
            if child_id == child_uid:
                data["children"].pop(i)
                self._save_data(data)
                print(f"🗑️ {child_uid} supprimé")
                return True
        
        print(f"⚠️ {child_uid} introuvable")
        return False
    
    def remove_all_children(self) -> int:
        """Supprime tous les enfants"""
        data = self._load_data()
        count = len(data["children"])
        
        data["children"] = []
        self._save_data(data)
        
        print(f"🧹 {count} enfants supprimés")
        return count
    
    def is_child_authorized(self, child_uid: str) -> bool:
        """Vérifie si un enfant est autorisé"""
        data = self._load_data()
        
        for child in data["children"]:
            child_id = child.get('id') if isinstance(child, dict) else child
            if child_id == child_uid:
                return True
        
        return False
    
    def get_child_count(self) -> int:
        """Retourne le nombre d'enfants appairés"""
        data = self._load_data()
        return len(data.get("children", []))
