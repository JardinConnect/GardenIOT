import time

class LoRaManager:
    def __init__(self, lora, uid, rtc=None):
        self.lora = lora
        self.uid = uid
        self.rtc = rtc
    
    def construire_message(self, type_msg, datas=""):
        timestamp = self._get_timestamp()
        return f"B|{type_msg}|{timestamp}|{self.uid}|{datas}|E"
    
    def parser_message(self, msg):
        """Parse un message reçu"""
        if not msg.startswith("B|") or not msg.endswith("|E"):
            return None
        
        parts = msg[2:-2].split("|")
        if len(parts) < 4:
            return None
        
        return {
            "type": parts[0],
            "timestamp": parts[1],
            "uid": parts[2],
            "datas": parts[3] if len(parts) > 3 else ""
        }
    
    def envoyer_rafale(self, message):
        """Envoie un message en rafale"""
        padded_message = "XXXX" + message
        payload = padded_message.encode('utf-8')
        
        for i in range(3):
            self.lora.send(payload)
            time.sleep(0.1)
        if len(message) < 100:
            print(f"Envoi Message: {message}")
    
    def ecouter(self, timeout_ms=3000):
        """
        Écoute un message pendant timeout_ms
        Retourne: dict parsé ou None
        """
        
        # Mode RX
        self.lora._write(0x01, 0x81)  
        time.sleep(0.01)
        self.lora._write(0x12, 0xFF)  
        self.lora.recv()  
        
        start = time.ticks_ms()
        
        while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
            if (self.lora._read(0x12) & 0x40):
                self.lora._write(0x12, 0xFF)
                
                try:
                    raw = self.lora._read_payload()
                    msg_str = raw.decode('utf-8', 'ignore').strip()
                    parsed = self.parser_message(msg_str)
                    
                    if parsed:
                        print(f" Reçu: {parsed['type']}")
                        return parsed
                except Exception as e:
                    print(f" Erreur: {e}")
                
                self.lora.recv()
            
            time.sleep_ms(10)
        
        return None
    
    def _get_timestamp(self):
        """Génère un timestamp ISO 8601"""
        if self.rtc:
            try:
                dt = self.rtc.datetime()
                return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
                    dt[0],
                    dt[1],  
                    dt[2],  
                    dt[4],  
                    dt[5],  
                    dt[6]   
                )
            except Exception as e:
                print(f"RTC erreur: {e}")
        
        t = time.ticks_ms() // 1000
        return f"BOOT+{t}s"
