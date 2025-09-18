#!/usr/bin/env python3
"""
Pi5 LoRa Listener with ACK - Version Simplifiée
Sans reset manuel pour éviter les conflits de pins
"""
import time
import board
import busio
import digitalio
import adafruit_rfm9x

# Configuration LoRa
RADIO_FREQ_MHZ = 433.0

# Mode debug
DEBUG = True

def init_lora():
    """Initialise le module LoRa"""
    try:
        # Pins pour le module
        CS = digitalio.DigitalInOut(board.D5)
        RESET = digitalio.DigitalInOut(board.D25)
        spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
        
        # Créer l'objet RFM9x
        rfm9x = adafruit_rfm9x.RFM9x(spi, CS, RESET, RADIO_FREQ_MHZ)
        
        # Configuration identique au Nano
        rfm9x.tx_power = 14
        rfm9x.spreading_factor = 7
        rfm9x.signal_bandwidth = 125000
        rfm9x.coding_rate = 5
        rfm9x.preamble_length = 8
        
        print(f"✅ Pi5 LoRa Listener - Fréquence: {RADIO_FREQ_MHZ} MHz")
        print(f"Configuration: SF={rfm9x.spreading_factor}, BW={rfm9x.signal_bandwidth}, CR={rfm9x.coding_rate}")
        print("En attente des mesures du Nano...\n")
        
        return rfm9x
        
    except Exception as e:
        print(f"❌ Erreur initialisation LoRa: {e}")
        return None

def send_ack(rfm9x, message_id):
    """Envoie un ACK au Nano avec gestion du mode TX/RX"""
    try:
        # Préparer le message ACK (sans préfixe XXXX)
        ack_msg = f"ACK_{message_id}"
        
        if DEBUG:
            print(f"  → Envoi ACK: {ack_msg}")
        
        # IMPORTANT: Attendre que le Nano passe en mode RX
        time.sleep(0.5)  # 500ms pour laisser le temps au Nano
        
        # Envoyer l'ACK
        rfm9x.send(bytes(ack_msg, "utf-8"))
        
        # Attendre que l'envoi soit complet
        time.sleep(0.2)
        
        return True
        
    except Exception as e:
        print(f"  ❌ Erreur envoi ACK: {e}")
        return False

def process_message(packet, rssi):
    """Traite le message reçu"""
    try:
        # Décoder le message
        message = packet.decode('utf-8', errors='ignore')
        
        if DEBUG and len(packet) < 100:  # Afficher seulement pour les petits paquets
            print(f"\nDEBUG - Bytes hex: {packet.hex()}")
        
        # Retirer le préfixe XXXX
        if message.startswith("XXXX"):
            message = message[4:]
        
        print(f"\n📡 Reçu: {message}")
        print(f"   RSSI: {rssi} dBm")
        
        # Extraire l'ID du message
        if "Nano #" in message:
            try:
                message_id = message.split("Nano #")[1].split()[0]
                return message_id
            except:
                print("  ⚠️  Impossible d'extraire l'ID")
                return "unknown"
        else:
            print("  ⚠️  Format non reconnu")
            return None
            
    except Exception as e:
        print(f"  ❌ Erreur décodage: {e}")
        return None

def main():
    print("=== DÉMARRAGE PI5 LORA LISTENER ===\n")
    
    # Initialiser le module
    rfm9x = init_lora()
    if not rfm9x:
        print("Impossible d'initialiser le module LoRa!")
        return
    
    print("📡 Mode écoute activé")
    print("Ctrl+C pour arrêter\n")
    
    # Statistiques
    messages_received = 0
    acks_sent = 0
    errors = 0
    
    # Boucle principale
    while True:
        try:
            # Recevoir un paquet (timeout de 1 seconde)
            packet = rfm9x.receive(timeout=1.0)
            
            if packet is not None:
                messages_received += 1
                rssi = rfm9x.last_rssi
                
                # Traiter le message
                message_id = process_message(packet, rssi)
                
                if message_id:
                    # Envoyer l'ACK
                    if send_ack(rfm9x, message_id):
                        acks_sent += 1
                        print(f"  ✅ ACK envoyé pour message #{message_id}")
                    else:
                        errors += 1
                        print(f"  ❌ Échec envoi ACK")
                    
                    # Afficher les stats
                    print(f"  📊 Stats: {messages_received} reçus, {acks_sent} ACKs envoyés")
                
                # Petit délai pour stabilité
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print(f"\n\n🛑 Arrêt du listener")
            print(f"📊 Statistiques finales:")
            print(f"   Messages reçus: {messages_received}")
            print(f"   ACKs envoyés: {acks_sent}")
            print(f"   Erreurs: {errors}")
            break
            
        except Exception as e:
            errors += 1
            print(f"\n⚠️  Erreur inattendue: {e}")
            print("Reprise dans 2 secondes...")
            time.sleep(2)
            
            # Essayer de réinitialiser si trop d'erreurs
            if errors > 5:
                print("\n🔄 Trop d'erreurs, réinitialisation...")
                rfm9x = init_lora()
                if rfm9x:
                    print("✅ Module réinitialisé")
                    errors = 0
                else:
                    print("❌ Échec réinitialisation")
                    break

if __name__ == "__main__":
    main()