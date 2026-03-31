# main.py
import sys
import time

sys.path.append('/modules')
sys.path.append('/config')
sys.path.append('/sensors')

from loraManager import LoRaManager
from pairing import PairingManager
from SensorManager import SensorManager
from alertManager import AlertManager
from pins import init_hardware, UID

# ============================================
# INITIALISATION
# ============================================

# Init matériel
lora, capteurs, btn, rtc = init_hardware()

# Init modules
lora_manager = LoRaManager(lora, UID, rtc)
pairing_mgr = PairingManager(lora, UID) 
sensor_mgr = SensorManager(**capteurs)
alert_mgr = AlertManager(lora_manager)

# Charge parent ID
parent_id = pairing_mgr._charger()

SEND_INTERVAL_SEC = 60
LISTEN_INTERVAL_MS = 5000

def log(message):
    t = time.localtime()
    timestamp = "{:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5])
    print(f"[{timestamp}] {message}")
    
print("="*40)
log(f"UID: {UID}")
print("="*40)


# ============================================
# BOUCLE PRINCIPALE
# ============================================

last_send_time = 0

while True:
    if parent_id:
        
        now = time.time()
        time_since_last_send = now - last_send_time
        

        if alert_mgr.should_check():
            datas = sensor_mgr.lire_all_capteurs()
            alert_mgr.check_and_send_alerts(datas)
        

        if time_since_last_send >= SEND_INTERVAL_SEC:
            

            datas = sensor_mgr.lire_all_capteurs()
            

            msg = lora_manager.construire_message("D", datas)
            lora_manager.envoyer_rafale(msg)
            
            last_send_time = now
        

        ordre = lora_manager.ecouter(timeout_ms=LISTEN_INTERVAL_MS)
        
        
        if ordre:
            type_ordre = ordre.get('type')

            if type_ordre == 'U':
                log("Demande Unpair reçu")
                parent_id = None
                pairing_mgr.lancer_unpairing()
            
            elif type_ordre == 'A':
                sensor = alert_mgr.traiter_config_lora(ordre)
                
                if sensor:

                    msg_ack = lora_manager.construire_message("AC", sensor)
                    
                    lora_manager.envoyer_rafale(msg_ack)
                else:
                    log("Échec de la configuration dans alert_mgr")

            elif type_ordre == 'AS':
                log("Tentative de suppression d'alerte...")
                sensor = ordre.get('datas', '')
                if sensor:
                    sensor = sensor.strip()
                    datas = alert_mgr.remove_alert_and_build_ad_datas(sensor)
                    msg_ack = lora_manager.construire_message("AD", datas)
                    lora_manager.envoyer_rafale(msg_ack)

        time.sleep(0.1)
    
    else:
        
        if btn.value() == 0:
            log("Bouton pressé - Lancement pairing")
            parent_id = pairing_mgr.lancer_pairing()
            
            if parent_id:
                log(f"Pairé avec: {parent_id}")
                last_send_time = 0
        
        time.sleep(0.5)