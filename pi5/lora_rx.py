import time
import board
import busio
import digitalio
import adafruit_rfm9x
import json
import gest_noeud 
import datetime
from services.message_service import MessageService

# ============================================
# CONFIGURATION
# ============================================
btn = digitalio.DigitalInOut(board.D22)
btn.direction = digitalio.Direction.INPUT
btn.pull = digitalio.Pull.UP

CS = digitalio.DigitalInOut(board.D5)
RESET = digitalio.DigitalInOut(board.D25)
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, 433.1)
rfm9x.signal_bandwidth = 500000
rfm9x.spreading_factor = 10
rfm9x.coding_rate = 5
rfm9x.preamble_length = 8
rfm9x.enable_crc = False
rfm9x._write_u8(0x39, 0x12)

gest_noeud.init()
MY_PARENT_ID = gest_noeud.get_parent_id()

print(f"\n--- RASPBERRY PRÊT ---")

# ============================================
# PARSING DES MESSAGES
# ============================================
def parser_message(msg):
    """
    Parse format: B|TYPE|TIMESTAMP|UID|DATAS|E
    
    """
    if not msg.startswith("B|") or not msg.endswith("|E"):
        return None
    
    content = msg[2:-2]
    parts = content.split("|")
    
    if len(parts) < 3:
        return None
    
    parsed = {
        "type": parts[0],
        "timestamp": parts[1] if len(parts) > 1 else "",
        "uid": parts[2] if len(parts) > 2 else "",
        "datas": parts[3] if len(parts) > 3 else ""
    }
    
    if parsed["type"] == "D" and parsed["datas"]:
        parsed["sensors"] = MessageService._parse_sensor_data(parsed["datas"])
    
    return parsed

def construire_ack_pairing(uid):
    """Construit un ACK de pairing"""
    return f"B|PA|{MY_PARENT_ID}|{uid}||E"

# ============================================
# VARIABLES
# ============================================
memoire_msg = ""
memoire_temps = 0
mode_pairing = False
fin_pairing = 0

DUREE_PAIRING_SEC = 30.0
DUREE_RESET_SEC = 15.0

print("\nPassage en mode ÉCOUTE...")
rfm9x.idle() 
time.sleep(0.01)
rfm9x.listen() 
time.sleep(0.01)


while True:
    now = time.time()

    # Gestion du bouton
    if not btn.value:
        start_p = now
        reset_triggered = False
        
        while not btn.value:
            duree_appui = time.time() - start_p
            
            if duree_appui >= DUREE_RESET_SEC:
                print(f"\n Reset total des enfants ({DUREE_RESET_SEC}s dépassées)")
                gest_noeud.remove_all_children()
                reset_triggered = True
                while not btn.value: 
                    time.sleep(0.1)
                break
            
            time.sleep(0.1)
        
        duree_relache = time.time() - start_p
        
        if reset_triggered:
            continue
            
        elif duree_relache >= 3.0:
            if not mode_pairing:
                print(f"\nMODE PAIRING activé ({DUREE_PAIRING_SEC}s)")
                mode_pairing = True
                fin_pairing = time.time() + DUREE_PAIRING_SEC

    # Désactivation automatique du mode pairing
    if mode_pairing and now > fin_pairing:
        print("Fin de la fenêtre de Pairing")
        mode_pairing = False

    # Reception des messages
    try:
        timeout_rx = 0.5 if mode_pairing else 0.1
        packet = rfm9x.receive(timeout=timeout_rx)
    except Exception as e:
        print(f"Erreur Radio: {e}")
        packet = None

    if packet:
        try:
            msg = str(packet, 'utf-8', 'ignore').strip()
            
            # Anti-doublon
            if msg == memoire_msg and (time.time() - memoire_temps) < 1.0:
                continue
            
            memoire_msg = msg
            memoire_temps = time.time()
            
            # Parser le message
            parsed = parser_message(msg)
            
            if parsed:
                print(f"Parsé: Type={parsed['type']}, UID={parsed['uid']}")
            else:
                print(f"Échec du parsing")
            
            if not parsed or not parsed.get("uid"):
                print(f"Message invalide ou UID manquant")
                continue
            
            mtype = parsed["type"]
            uid = parsed["uid"]
            timestamp = parsed.get("timestamp", "")
            
            # Pairing
            if mtype == "P" and mode_pairing:
                print(f"\nDEMANDE PAIRING de {uid}")
                
                try:
                    success = gest_noeud.add_child(uid)
                    
                    ack_payload = construire_ack_pairing(uid).encode('utf-8')
                    
                    if success:
                        print(f"Nouvel enfant ajouté: {uid}")
                    else:
                        print(f"ESP32 déjà connu: {uid}")
                    
                    print(f"Envoi réponse PAIRING à {uid}...", end="")
                    
                    # Rafale étendue
                    start_send = time.time()
                    count = 0
                    while time.time() - start_send < 2.0:
                        rfm9x.send(ack_payload)
                        time.sleep(0.15)
                        count += 1
                        if count % 3 == 0:
                            print(".", end="")
                        
                except Exception as e:
                    print(f"Erreur pairing: {e}")
                    import traceback
                    traceback.print_exc()

            elif mtype == "P" and not mode_pairing:
                print(f"PAIRING REFUSÉ: {uid}")

            # Gestion données
            elif mtype == "D":
                is_known = gest_noeud.est_autorise(uid)
                statut = "OK" if is_known else ""
                print(f"\n{statut} [DATA] {uid}: {parsed['datas']}")

            # -------------------- UNPAIR --------------------
            elif mtype == "U":
                print(f"\nUnpair: {uid}")
                gest_noeud.remove_child(uid)

        except Exception as e:
            print(f"Erreur traitement: {e}")
            import traceback
            traceback.print_exc()