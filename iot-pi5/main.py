"""
Point d'entrée principal du système Gateway Pi5
"""
import time
import digitalio
import board
from core.gateway_core import GatewayCore
from core.message_router import MessageRouter
from communications.lora_communication import LoRaCommunication
from communications.mqtt_communication import MqttCommunication
from repositories.child_repository import ChildRepository
from config import load_config


def main():
    """Fonction principale"""
    print("🌱 Garden IoT Gateway - Démarrage...")
    
    # Initialiser les composants
    CONFIG = load_config()
    gateway_core = GatewayCore(CONFIG)
    
    # Créer les instances des composants
    lora_comm = LoRaCommunication(CONFIG["lora"])
    mqtt_comm = MqttCommunication(CONFIG["mqtt"])
    child_repo = ChildRepository(CONFIG["repository"])
    message_router = MessageRouter(gateway_core)
    
    # Initialiser le cœur avec les composants
    gateway_core.initialize_components(lora_comm, mqtt_comm, child_repo, message_router)
    
    # Configurer le bouton physique
    setup_button(gateway_core)
    
    # Démarrer le système
    gateway_core.start()


def setup_button(gateway_core: GatewayCore):
    """Configure le bouton physique pour le pairing"""
    try:
        btn = digitalio.DigitalInOut(CONFIG["system"]["button_pin"])
        btn.direction = digitalio.Direction.INPUT
        btn.pull = digitalio.Pull.UP
        
        print(f"🔘 Bouton configuré sur {CONFIG['system']['button_pin']}")
        
        # Lancer un thread pour surveiller le bouton
        import _thread
        _thread.start_new_thread(button_monitor, (gateway_core, btn))
        
    except Exception as e:
        print(f"⚠️ Impossible de configurer le bouton: {e}")


def button_monitor(gateway_core: GatewayCore, btn):
    """Surveille l'état du bouton"""
    while True:
        if not btn.value:
            # Bouton enfoncé
            start_time = time.time()
            
            # Attendre que le bouton soit relâché
            while not btn.value:
                time.sleep(0.1)
            
            press_duration = time.time() - start_time
            
            # Gérer l'appui
            gateway_core.handle_button_press(press_duration)
        
        time.sleep(0.1)


if __name__ == "__main__":
    main()
