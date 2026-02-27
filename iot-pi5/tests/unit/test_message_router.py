"""
Tests unitaires pour le MessageRouter
"""
import unittest
from unittest.mock import Mock, MagicMock
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


class TestMessageRouter(unittest.TestCase):
    """Tests pour MessageRouter"""
    
    def setUp(self):
        """Configuration des tests"""
        self.mock_gateway = Mock()
        self.mock_gateway.child_repo = Mock()
        self.mock_gateway.mqtt_comm = Mock()
        self.mock_gateway.lora_comm = Mock()
        
        self.router = MessageRouter(self.mock_gateway)
        
        # Configurer les comportements par défaut
        self.mock_gateway.child_repo.is_child_authorized.return_value = True
        self.mock_gateway.mqtt_comm.publish.return_value = True
        self.mock_gateway.lora_comm.send.return_value = True
    
    def test_route_from_lora_data(self):
        """Test routing d'un message de données capteurs"""
        # Créer un message LoRa de données
        lora_msg = LoRaMessage(
            message_type=MessageType.DATA,
            timestamp="2023-01-01T12:00:00",
            uid="ESP32_001",
            data="1TA25;1HA60;1TS23"
        )
        
        # Appeler le router
        self.router.route_from_lora(lora_msg)
        
        # Vérifier que le message a été publié sur MQTT
        self.mock_gateway.mqtt_comm.publish.assert_called_once()
        
        # Vérifier les arguments de l'appel
        call_args = self.mock_gateway.mqtt_comm.publish.call_args
        topic = call_args[0][0]
        payload = call_args[0][1]
        qos = call_args[0][2]
        
        self.assertEqual(topic, "garden/sensors/ESP32_001")
        self.assertEqual(qos, 1)
        self.assertIn("uid", payload)
        self.assertIn("timestamp", payload)
        self.assertIn("raw_data", payload)
        self.assertIn("parsed", payload)
        self.assertEqual(payload["uid"], "ESP32_001")
    
    def test_route_from_lora_data_unauthorized(self):
        """Test routing d'un message de données d'une cellule non autorisée"""
        # Configurer le mock pour retourner False
        self.mock_gateway.child_repo.is_child_authorized.return_value = False
        
        lora_msg = LoRaMessage(
            message_type=MessageType.DATA,
            timestamp="2023-01-01T12:00:00",
            uid="ESP32_UNKNOWN",
            data="1TA25;1HA60"
        )
        
        # Appeler le router
        self.router.route_from_lora(lora_msg)
        
        # Vérifier que rien n'a été publié
        self.mock_gateway.mqtt_comm.publish.assert_not_called()
    
    def test_route_from_lora_pairing(self):
        """Test routing d'un message de pairing"""
        # Configurer le mock pour le mode pairing
        mock_state = Mock()
        mock_state.__class__.__name__ = "PairingState"
        self.mock_gateway.current_state = mock_state
        self.mock_gateway.child_repo.get_parent_id.return_value = "PI5_001"
        
        lora_msg = LoRaMessage(
            message_type=MessageType.PAIRING,
            timestamp="2023-01-01T12:00:00",
            uid="ESP32_NEW",
            data=""
        )
        
        # Appeler le router
        self.router.route_from_lora(lora_msg)
        
        # Vérifier que l'enfant a été ajouté
        self.mock_gateway.child_repo.add_child.assert_called_once_with("ESP32_NEW")
        
        # Vérifier que l'ACK a été envoyé via LoRa
        self.mock_gateway.lora_comm.send.assert_called_once()
        
        # Vérifier que la notification MQTT a été envoyée
        self.mock_gateway.mqtt_comm.publish.assert_called_once()
    
    def test_route_from_lora_pairing_not_in_pairing_mode(self):
        """Test routing d'un message de pairing hors mode pairing"""
        # Configurer le mock pour le mode normal
        mock_state = Mock()
        mock_state.__class__.__name__ = "NormalState"
        self.mock_gateway.current_state = mock_state
        
        lora_msg = LoRaMessage(
            message_type=MessageType.PAIRING,
            timestamp="2023-01-01T12:00:00",
            uid="ESP32_NEW",
            data=""
        )
        
        # Appeler le router
        self.router.route_from_lora(lora_msg)
        
        # Vérifier que rien n'a été fait
        self.mock_gateway.child_repo.add_child.assert_not_called()
        self.mock_gateway.lora_comm.send.assert_not_called()
        self.mock_gateway.mqtt_comm.publish.assert_not_called()
    
    def test_route_from_lora_alert_trigger(self):
        """Test routing d'un message d'alerte déclenchée"""
        lora_msg = LoRaMessage(
            message_type=MessageType.ALERT_TRIGGER,
            timestamp="2023-01-01T12:00:00",
            uid="ESP32_001",
            data="550e8400...|ESP32_001|TA|0|32.5|critical|2023-01-01T12:00:00"
        )
        
        # Appeler le router
        self.router.route_from_lora(lora_msg)
        
        # Vérifier que l'alerte a été publiée sur MQTT
        self.mock_gateway.mqtt_comm.publish.assert_called_once()
        
        # Vérifier les arguments
        call_args = self.mock_gateway.mqtt_comm.publish.call_args
        topic = call_args[0][0]
        payload = call_args[0][1]
        
        self.assertEqual(topic, "garden/alerts/trigger/ESP32_001")
        self.assertEqual(payload["alert_id"], "550e8400...")
        self.assertEqual(payload["cell_uid"], "ESP32_001")
        self.assertEqual(payload["sensor_type"], "TA")
        self.assertEqual(payload["value"], 32.5)
    
    def test_route_from_mqtt_alert_config(self):
        """Test routing d'une configuration d'alerte depuis MQTT"""
        payload = {
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
        
        # Appeler le router
        self.router.route_from_mqtt("garden/alerts/config", payload)
        
        # Vérifier que la configuration a été envoyée à chaque cellule
        self.assertEqual(self.mock_gateway.lora_comm.send.call_count, 2)
        
        # Vérifier les appels
        calls = self.mock_gateway.lora_comm.send.call_args_list
        
        # Premier appel pour ESP32_001
        first_call = calls[0]
        first_msg = first_call[0][0]
        self.assertTrue("ESP32_001" in first_msg)
        
        # Deuxième appel pour ESP32_002
        second_call = calls[1]
        second_msg = second_call[0][0]
        self.assertTrue("ESP32_002" in second_msg)
    
    def test_route_from_mqtt_alert_config_invalid_cells(self):
        """Test routing d'une configuration d'alerte avec cellules invalides"""
        # Configurer le mock pour retourner False pour toutes les cellules
        self.mock_gateway.child_repo.is_child_authorized.return_value = False
        
        payload = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "title": "Test Alert",
            "is_active": True,
            "cell_ids": ["ESP32_UNKNOWN"],
            "sensors": []
        }
        
        # Appeler le router
        self.router.route_from_mqtt("garden/alerts/config", payload)
        
        # Vérifier que rien n'a été envoyé
        self.mock_gateway.lora_comm.send.assert_not_called()
    
    def test_extract_uid_from_topic(self):
        """Test extraction d'UID depuis un topic MQTT"""
        # Test avec UID dans le topic
        uid = self.router._extract_uid_from_topic("garden/alerts/config/ESP32_001")
        self.assertEqual(uid, "ESP32_001")
        
        # Test avec UID au format uid-XXX
        uid = self.router._extract_uid_from_topic("garden/alerts/config/uid-ESP32_001")
        self.assertEqual(uid, "ESP32_001")
        
        # Test sans UID
        uid = self.router._extract_uid_from_topic("garden/alerts/config")
        self.assertIsNone(uid)


if __name__ == '__main__':
    unittest.main()
