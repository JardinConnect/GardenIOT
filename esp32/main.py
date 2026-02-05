import sys
import time
sys.path.append('/modules')
sys.path.append('/config')
sys.path.append('/sensors')

from loraManager import LoRaManager
from pairing import PairingManager
from SensorManager import SensorManager
from pins import init_hardware, UID

# Init matériel
lora, capteurs, btn, rtc = init_hardware()

# Init modules
lora_manager = LoRaManager(lora, UID, rtc)
pairing_mgr = PairingManager(lora, UID) 
sensor_mgr = SensorManager(**capteurs)

# Charge config
parent_id = pairing_mgr._charger

while True:
    if parent_id:
        # Mode connecté à son parent
        datas = sensor_mgr.lire_all_capteurs()
        msg = lora_manager.construire_message("D", datas)
        lora_manager.envoyer_rafale(msg)  
        
        ordre = lora_manager.ecouter(timeout_ms=3000)
        if ordre and ordre['type'] == 'U':
            parent_id = None
            pairing_mgr.lancer_unpairing()
        
        time.sleep(15)
    else:
        # Mode sans parent
        if btn.value() == 0:
            parent_id = pairing_mgr.lancer_pairing()