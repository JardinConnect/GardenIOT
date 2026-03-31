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
        msg = msg.strip()
        
        if not "B|" in msg or not "|E" in msg:
            print(f"[PARSER] Rejeté (Format incorrect): {msg}")
            return None
        
        try:
            debut = msg.index("B|")
            fin = msg.rindex("|E") + 2
            clean_content = msg[debut:fin] 
            
            inner = clean_content[2:-2]
            parts = inner.split("|")
            
            if len(parts) < 3:
                print("[PARSER] Trop court")
                return None
            
            datas_reconstitue = "|".join(parts[3:]) if len(parts) > 3 else ""
            
            return {
                "type": parts[0],
                "timestamp": parts[1] if len(parts) > 1 else "",
                "uid": parts[2] if len(parts) > 2 else "",
                "datas": datas_reconstitue
            }
        except Exception as e:
            print(f"[PARSER] Exception: {e}")
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
        
        self.lora._write(0x01, 0x81)  
        self.lora._write(0x12, 0xFF)  
        self.lora.recv()  
        
        start = time.ticks_ms()
        
        while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
            irq = self.lora._read(0x12)
            if (irq & 0x40):
                self.lora._write(0x12, 0xFF)
                try:
                    raw = self.lora._read_payload()
                    
                    if raw:

                        idx = raw.find(b'B|')
                        
                        if idx != -1:
                            clean_bytes = raw[idx:]
                        
                            try:
                                msg_str = clean_bytes.decode('utf-8', 'ignore').strip()
                                
                                parsed = self.parser_message(msg_str)
                                if parsed:
                                    
                                    if parsed['uid'] == self.uid:
                                        return parsed
                                        
                            except Exception as e:
                                print(f"Erreur décodage texte: {e}")
                        else:
                            print(f"Reçu ignoré (Pas de 'B|'): {raw}")

                except Exception as e:
                    print(f"Erreur lecture RX: {e}")
                
                # On relance l'écoute pour la suite du temps imparti
                self.lora.recv()
            
            time.sleep_ms(10)
        
        return None

    def _get_timestamp(self):
        """Génère un timestamp ISO 8601 (Force le format date)"""
        if self.rtc:
            try:
                dt = self.rtc.datetime()
                return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
                    dt[0], dt[1], dt[2], dt[4], dt[5], dt[6]
                )
            except:
                pass
        
        try:
            t = time.localtime()
            return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
                t[0], t[1], t[2], t[3], t[4], t[5]
            )
        except:
            ms = time.ticks_ms() // 1000
            return f"BOOT+{ms}s"