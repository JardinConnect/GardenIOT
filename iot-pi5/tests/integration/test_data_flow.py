"""
Tests d'intégration pour le flux de données complet
Simule le flux depuis les cellules enfants jusqu'au broker MQTT
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Ajouter le chemin du projet au Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from models.messages import (
    LoRaMessage, 
    MessageType, 
    SensorData, 
    AlertConfig, 
    AlertTrigger
)
from core.message_router import MessageRouter


class TestDataFlowIntegration(unittest.TestCase):
    """Tests d'intégration pour le flux de données complet"""
    
    def setUp(self):
        """Configuration des tests"""
        # Créer un mock du gateway
        self.mock_gateway = Mock()
        self.mock_gateway.child_repo = Mock()
        self.mock_gateway.mqtt_comm = Mock()
        self.mock_gateway.lora_comm = Mock()
        
        # Configurer les comportements par défaut
        self.mock_gateway.child_repo.is_child_authorized.return_value = True
        self.mock_gateway.child_repo.get_parent_id.return_value = "PI5_TEST"
        self.mock_gateway.mqtt_comm.publish.return_value = True
        self.mock_gateway.lora_comm.send.return_value = True
        
        # Créer le router
        self.router = MessageRouter(self.mock_gateway)
        
        # Stocker les messages publiés pour vérification
        self.published_messages = []
        
        # Remplacer la méthode publish pour capturer les messages
        def capture_publish(topic, payload, qos=1):
            self.published_messages.append({
                'topic': topic,
                'payload': payload,
                'qos': qos
            })
            return True
        
        self.mock_gateway.mqtt_comm.publish = capture_publish
    
    def test_sensor_data_flow(self):
        """Test complet du flux de données capteurs"""
        print("\n=== Test: Flux de données capteurs ===")
        
        # 1. Simuler la réception d'un message LoRa depuis une cellule (format avec index)
        lora_raw = "B|D|2023-01-01T12:00:00|ESP32_001|1TA:25;1HA:60;1TS:23;1L:1000;1B:85|E"
        print(f"1. Message LoRa reçu: {lora_raw}")
        
        # 2. Parser le message LoRa
        lora_msg = LoRaMessage.from_lora_format(lora_raw)
        self.assertIsNotNone(lora_msg)
        print(f"2. Message parsé: {lora_msg.message_type.name} de {lora_msg.uid}")
        
        # 3. Router le message
        self.router.route_from_lora(lora_msg)
        print("3. Message routé vers MQTT")
        
        # 4. Vérifier que le message a été publié sur MQTT
        self.assertEqual(len(self.published_messages), 1)
        
        published = self.published_messages[0]
        print(f"4. Message publié sur {published['topic']}")
        
        # 5. Vérifier le contenu du message publié
        self.assertEqual(published['topic'], "garden/sensors/ESP32_001")
        self.assertEqual(published['qos'], 1)
        
        payload = published['payload']
        self.assertIn('uid', payload)
        self.assertIn('timestamp', payload)
        self.assertIn('raw_data', payload)
        self.assertIn('parsed', payload)
        
        self.assertEqual(payload['uid'], "ESP32_001")
        self.assertEqual(payload['raw_data'], "1TA:25;1HA:60;1TS:23;1L:1000;1B:85")
        self.assertEqual(payload['parsed'], {
            "TA:1": 25.0,
            "HA:1": 60.0,
            "TS:1": 23.0,
            "L:1": 1000.0,
            "B:1": 85.0
        })
        
        print(f"5. Payload MQTT validé: {payload}")
        print("✅ Test réussi: Données capteurs correctement routées")
    
    def test_alert_config_flow(self):
        """Test complet du flux de configuration d'alerte"""
        print("\n=== Test: Flux de configuration d'alerte ===")
        
        # 1. Simuler la réception d'une configuration d'alerte depuis MQTT
        mqtt_payload = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "title": "Température trop élevée",
            "is_active": True,
            "warning_enabled": False,
            "cell_ids": ["ESP32_001", "ESP32_002"],
            "sensors": [
                {
                    "type": "TA",
                    "index": 0,
                    "criticalRange": [30, 100],
                    "warningRange": [25, 30]
                }
            ]
        }
        print(f"1. Configuration MQTT reçue: {mqtt_payload['title']}")
        
        # 2. Router le message MQTT
        self.router.route_from_mqtt("garden/alerts/config", mqtt_payload)
        print("2. Configuration routée vers LoRa")
        
        # 3. Vérifier que les messages LoRa ont été envoyés aux cellules
        # Le mock lora_comm.send a été appelé 2 fois (une par cellule)
        self.assertEqual(self.mock_gateway.lora_comm.send.call_count, 2)
        print("3. Messages LoRa envoyés à 2 cellules")
        
        # 4. Vérifier le contenu des messages LoRa
        calls = self.mock_gateway.lora_comm.send.call_args_list
        
        for i, call in enumerate(calls):
            lora_message = call[0][0]
            print(f"4.{i+1}. Message LoRa pour cellule {i+1}: {lora_message[:50]}...")
            
            # Vérifier que le message contient les informations attendues
            self.assertIn("550e8400-e29b-41d4-a716-446655440000", lora_message)
            self.assertIn("Température trop élevée", lora_message)
            self.assertIn("TA:0:30:100:25:30", lora_message)
            
            # Vérifier que le message est au bon format
            self.assertTrue(lora_message.startswith("B|A|"))
            self.assertTrue(lora_message.endswith("|E"))
        
        print("✅ Test réussi: Configuration d'alerte correctement routée")
    
    def test_alert_trigger_flow(self):
        """Test complet du flux d'alerte déclenchée"""
        print("\n=== Test: Flux d'alerte déclenchée ===")
        
        # 1. Simuler la réception d'une alerte déclenchée depuis LoRa
        lora_raw = "B|T|2023-01-01T12:05:00|ESP32_001|550e8400...|ESP32_001|TA|0|32.5|critical|2023-01-01T12:05:00|E"
        print(f"1. Alerte LoRa reçue: {lora_raw}")
        
        # 2. Parser le message LoRa
        lora_msg = LoRaMessage.from_lora_format(lora_raw)
        self.assertIsNotNone(lora_msg)
        print(f"2. Message parsé: Alerte {lora_msg.message_type.name} de {lora_msg.uid}")
        
        # 3. Router le message
        self.router.route_from_lora(lora_msg)
        print("3. Alerte routée vers MQTT")
        
        # 4. Vérifier que l'alerte a été publiée sur MQTT
        self.assertEqual(len(self.published_messages), 1)
        
        published = self.published_messages[0]
        print(f"4. Alerte publiée sur {published['topic']}")
        
        # 5. Vérifier le contenu de l'alerte publiée
        self.assertEqual(published['topic'], "garden/alerts/trigger/ESP32_001")
        self.assertEqual(published['qos'], 1)
        
        payload = published['payload']
        self.assertIn('alert_id', payload)
        self.assertIn('cell_uid', payload)
        self.assertIn('sensor_type', payload)
        self.assertIn('value', payload)
        self.assertIn('trigger_type', payload)
        self.assertIn('timestamp', payload)
        
        self.assertEqual(payload['alert_id'], "550e8400...")
        self.assertEqual(payload['cell_uid'], "ESP32_001")
        self.assertEqual(payload['sensor_type'], "TA")
        self.assertEqual(payload['value'], 32.5)
        self.assertEqual(payload['trigger_type'], "critical")
        
        print(f"5. Payload MQTT validé: {payload}")
        print("✅ Test réussi: Alerte déclenchée correctement routée")
    
    def test_pairing_flow(self):
        """Test complet du flux de pairing"""
        print("\n=== Test: Flux de pairing ===")
        
        # 1. Configurer le mock pour le mode pairing
        mock_state = Mock()
        mock_state.__class__.__name__ = "PairingState"
        self.mock_gateway.current_state = mock_state
        
        # 2. Simuler la réception d'une demande de pairing
        lora_raw = "B|P|2023-01-01T12:00:00|ESP32_NEW||E"
        print(f"1. Demande de pairing reçue: {lora_raw}")
        
        # 3. Parser le message
        lora_msg = LoRaMessage.from_lora_format(lora_raw)
        self.assertIsNotNone(lora_msg)
        print(f"2. Message parsé: {lora_msg.message_type.name} de {lora_msg.uid}")
        
        # 4. Router le message
        self.router.route_from_lora(lora_msg)
        print("3. Demande de pairing routée")
        
        # 5. Vérifier que l'enfant a été ajouté
        self.mock_gateway.child_repo.add_child.assert_called_once_with("ESP32_NEW")
        print("4. Enfant ajouté au repository")
        
        # 6. Vérifier que l'ACK a été envoyé via LoRa
        self.mock_gateway.lora_comm.send.assert_called_once()
        
        ack_message = self.mock_gateway.lora_comm.send.call_args[0][0]
        print(f"5. ACK LoRa envoyé: {ack_message}")
        
        # Vérifier le format de l'ACK
        self.assertTrue(ack_message.startswith("B|PA|"))
        self.assertTrue(ack_message.endswith("|E"))
        self.assertIn("PI5_TEST", ack_message)
        self.assertIn("ESP32_NEW", ack_message)
        
        # 7. Vérifier que la notification MQTT a été envoyée
        self.assertEqual(len(self.published_messages), 1)
        
        published = self.published_messages[0]
        print(f"6. Notification MQTT publiée sur {published['topic']}")
        
        self.assertEqual(published['topic'], "garden/pairing/success/ESP32_NEW")
        
        payload = published['payload']
        self.assertEqual(payload['uid'], "ESP32_NEW")
        self.assertEqual(payload['parent_id'], "PI5_TEST")
        
        print(f"7. Payload MQTT validé: {payload}")
        print("✅ Test réussi: Pairing correctement effectué")
    
    def test_unauthorized_cell_data(self):
        """Test flux avec une cellule non autorisée"""
        print("\n=== Test: Cellule non autorisée ===")
        
        # 1. Configurer le mock pour retourner False
        self.mock_gateway.child_repo.is_child_authorized.return_value = False
        
        # 2. Simuler la réception d'un message
        lora_raw = "B|D|2023-01-01T12:00:00|ESP32_UNKNOWN|1TA25;1HA60|E"
        print(f"1. Message reçu de cellule non autorisée: {lora_raw}")
        
        # 3. Parser et router
        lora_msg = LoRaMessage.from_lora_format(lora_raw)
        self.router.route_from_lora(lora_msg)
        print("2. Message routé (devrait être ignoré)")
        
        # 4. Vérifier que rien n'a été publié
        self.assertEqual(len(self.published_messages), 0)
        print("3. Aucun message publié sur MQTT")
        
        print("✅ Test réussi: Cellule non autorisée correctement ignorée")


if __name__ == '__main__':
    # Exécuter les tests avec une sortie plus lisible
    unittest.main(verbosity=2)
