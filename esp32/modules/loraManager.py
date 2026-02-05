# modules/loraManager.py
import time

        
def log(message):
    """Affiche un message avec l'heure courante (HH:MM:SS)"""
    t = time.localtime()
    timestamp = "{:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5])
    print(f"[{timestamp}] {message}")

class LoRaManager:

        
    def __init__(self, lora, uid, rtc=None):
        self.lora = lora
        self.uid = uid
        self.rtc = rtc
    
    def construire_message(self, type_msg, datas=""):
        timestamp = self._get_timestamp()
        return f"B|{type_msg}|{timestamp}|{self.uid}|{datas}|E"
    
    def parser_message(self, msg):
        """Parse un message textuel"""
        # Nettoyage
        msg = msg.strip()
        
        # Vérification structure
        if not "B|" in msg or not "|E" in msg:
            print(f"⚠️ [PARSER] Rejeté (Format incorrect): {msg}")
            return None
        
        # Extraction propre
        try:
            debut = msg.index("B|")
            fin = msg.rindex("|E") + 2
            clean_content = msg[debut:fin] # On garde B|...|E
            
            # On enlève B| et |E pour le split
            inner = clean_content[2:-2]
            parts = inner.split("|")
            
            if len(parts) < 3:
                print("⚠️ [PARSER] Trop court")
                return None
            
            # Reconstruction datas (si pipes dedans)
            datas_reconstitue = "|".join(parts[3:]) if len(parts) > 3 else ""
            
            return {
                "type": parts[0],
                "timestamp": parts[1] if len(parts) > 1 else "",
                "uid": parts[2] if len(parts) > 2 else "",
                "datas": datas_reconstitue
            }
        except Exception as e:
            print(f"⚠️ [PARSER] Exception: {e}")
            return None
    
    def envoyer_rafale(self, message):
        """Envoie avec padding"""
        padded_message = "XXXX" + message
        payload = padded_message.encode('utf-8')
        for i in range(3):
            self.lora.send(payload)
            time.sleep(0.1)
        if len(message) < 100:
            print(f"Envoi Message: {message}")
    
    def ecouter(self, timeout_ms=3000):
        """Écoute robuste : Nettoie les octets AVANT le décodage"""
        
        log("Passage en mode écoute...")
        # Initialisation RX
        self.lora._write(0x01, 0x81)  
        self.lora._write(0x12, 0xFF)  
        self.lora.recv()  
        
        start = time.ticks_ms()
        
        while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
            irq = self.lora._read(0x12)
            
            if (irq & 0x40): # RxDone
                self.lora._write(0x12, 0xFF) # Clear IRQ
                
                try:
                    raw = self.lora._read_payload()
                    
                    if raw:
                        # --- ÉTAPE CLÉ : TRAVAIL SUR LES OCTETS DIRECTEMENT ---
                        # On cherche la séquence binaire "B|" (0x42, 0x7C)
                        # Cela évite de décoder les headers pourris (\xff\xff)
                        idx = raw.find(b'B|')
                        
                        if idx != -1:
                            # On garde uniquement la partie propre à partir de B|
                            clean_bytes = raw[idx:]
                            
                            try:
                                # MAINTENANT on peut décoder sans erreur
                                msg_str = clean_bytes.decode('utf-8', 'ignore').strip()
                                
                                parsed = self.parser_message(msg_str)
                                if parsed:
                                    
                                    # Si c'est pour moi, je le retourne et JE SORS de la boucle
                                    if parsed['uid'] == self.uid:
                                        return parsed
                                        
                            except Exception as e:
                                print(f"❌ Erreur décodage texte: {e}")
                        else:
                            print(f"⚠️ Reçu ignoré (Pas de 'B|'): {raw}")

                except Exception as e:
                    print(f"❌ Erreur lecture RX: {e}")
                
                # On relance l'écoute pour la suite du temps imparti
                self.lora.recv()
            
            time.sleep_ms(10)
        
        return None

    def _get_timestamp(self):
        """Génère un timestamp ISO 8601 (Force le format date)"""
        # 1. Essayer le module RTC externe (DS3231) si présent
        if self.rtc:
            try:
                dt = self.rtc.datetime()
                return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
                    dt[0], dt[1], dt[2], dt[4], dt[5], dt[6]
                )
            except:
                pass
        
        # 2. Sinon, utiliser l'horloge interne de l'ESP32 (time.localtime)
        # Cela donnera une date (ex: 2000-01-01) mais au bon format.
        try:
            t = time.localtime()
            return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
                t[0], t[1], t[2], t[3], t[4], t[5]
            )
        except:
            # 3. Vraiment si tout échoue (devrait jamais arriver)
            ms = time.ticks_ms() // 1000
            return f"BOOT+{ms}s"