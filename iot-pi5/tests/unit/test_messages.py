"""
Tests unitaires pour les modèles de messages
"""
import unittest
from datetime import datetime
import sys
import os

# Ajouter le chemin du projet au Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from models.messages import (
    LoRaMessage, 
    MqttMessage, 
    MessageType, 
    SensorData, 
    AlertConfig, 
    AlertTrigger
)


class TestLoRaMessage(unittest.TestCase):
    """Tests pour LoRaMessage"""
    
    def test_from_lora_format_valid(self):
        """Test parsing d'un message LoRa valide"""
        raw = "B|D|2023-01-01T12:00:00|ESP32_001|1TA25;1HA60|E"
        msg = LoRaMessage.from_lora_format(raw)
        
        self.assertIsNotNone(msg)
        self.assertEqual(msg.message_type, MessageType.DATA)
        self.assertEqual(msg.timestamp, "2023-01-01T12:00:00")
        self.assertEqual(msg.uid, "ESP32_001")
        self.assertEqual(msg.data, "1TA25;1HA60")
        self.assertEqual(msg.raw, raw)
    
    def test_from_lora_format_invalid(self):
        """Test parsing d'un message LoRa invalide"""
        invalid_messages = [
            "Invalid message",
            "B|D|2023-01-01T12:00:00|ESP32_001|1TA25;1HA60",  # Pas de |E
            "D|2023-01-01T12:00:00|ESP32_001|1TA25;1HA60|E",  # Pas de B|
            "B||E",  # Message vide
        ]
        
        for invalid_msg in invalid_messages:
            with self.subTest(msg=invalid_msg):
                result = LoRaMessage.from_lora_format(invalid_msg)
                self.assertIsNone(result)
    
    def test_to_lora_format(self):
        """Test conversion en format LoRa"""
        msg = LoRaMessage(
            message_type=MessageType.PAIRING,
            timestamp="2023-01-01T12:00:00",
            uid="ESP32_NEW",
            data=""
        )
        
        formatted = msg.to_lora_format()
        expected = "B|P|2023-01-01T12:00:00|ESP32_NEW||E"
        self.assertEqual(formatted, expected)


class TestMqttMessage(unittest.TestCase):
    """Tests pour MqttMessage"""
    
    def test_from_mqtt_valid_json(self):
        """Test parsing d'un message MQTT avec JSON valide"""
        topic = "garden/sensors/ESP32_001"
        payload = '{"temperature": 25, "humidity": 60}'
        
        msg = MqttMessage.from_mqtt(topic, payload)
        
        self.assertEqual(msg.topic, topic)
        self.assertEqual(msg.payload, {"temperature": 25, "humidity": 60})
        self.assertEqual(msg.qos, 1)
    
    def test_from_mqtt_invalid_json(self):
        """Test parsing d'un message MQTT avec JSON invalide"""
        topic = "garden/sensors/ESP32_001"
        payload = "Not a JSON string"
        
        msg = MqttMessage.from_mqtt(topic, payload)
        
        self.assertEqual(msg.topic, topic)
        self.assertEqual(msg.payload, {"raw": "Not a JSON string"})
        self.assertEqual(msg.qos, 1)
    
    def test_to_json(self):
        """Test conversion en JSON"""
        msg = MqttMessage(
            topic="garden/alerts",
            payload={"alert_id": "123", "type": "temperature"},
            qos=1
        )
        
        json_str = msg.to_json()
        expected = '{"alert_id": "123", "type": "temperature"}'
        self.assertEqual(json_str, expected)


class TestSensorData(unittest.TestCase):
    """Tests pour SensorData"""
    
    def test_from_lora_data_with_index(self):
        """Test parsing des données capteurs avec index (format 1TA:25)"""
        data_str = "1TA:25;1HA:60;1TS:23;1L:1000;1B:85"
        sensor_data = SensorData.from_lora_data(data_str)
        
        self.assertEqual(sensor_data.raw_data, data_str)
        self.assertEqual(sensor_data.parsed_values, {
            "TA:1": 25.0,
            "HA:1": 60.0,
            "TS:1": 23.0,
            "L:1": 1000.0,
            "B:1": 85.0
        })
    
    def test_from_lora_data_multiple_indexes(self):
        """Test parsing avec plusieurs index pour le même type"""
        data_str = "1TA:25;2TA:26;1HA:60;2HA:65"
        sensor_data = SensorData.from_lora_data(data_str)
        
        self.assertEqual(sensor_data.raw_data, data_str)
        self.assertEqual(sensor_data.parsed_values, {
            "TA:1": 25.0,
            "TA:2": 26.0,
            "HA:1": 60.0,
            "HA:2": 65.0
        })
    
    def test_from_lora_data_long_code(self):
        """Test parsing avec des codes longs (4+ caractères)"""
        data_str = "1TEMPERATURE:23.5;1HUMIDITY:60.0;1LIGHT:1000"
        sensor_data = SensorData.from_lora_data(data_str)
        
        self.assertEqual(sensor_data.raw_data, data_str)
        self.assertEqual(sensor_data.parsed_values, {
            "TEMPERATURE:1": 23.5,
            "HUMIDITY:1": 60.0,
            "LIGHT:1": 1000.0
        })
    
    def test_from_lora_data_invalid_format(self):
        """Test parsing avec format invalide (sans :)"""
        data_str = "1TA25;1HA60"
        sensor_data = SensorData.from_lora_data(data_str)
        
        # Doit ignorer les formats sans :
        self.assertEqual(sensor_data.raw_data, data_str)
        self.assertEqual(sensor_data.parsed_values, {})
    
    def test_from_lora_data_with_invalid_items(self):
        """Test parsing avec des items invalides"""
        data_str = "1TA25;INVALID;1HA60;1TSabc"
        sensor_data = SensorData.from_lora_data(data_str)
        
        self.assertEqual(sensor_data.raw_data, data_str)
        self.assertEqual(sensor_data.parsed_values, {
            "TA": 25.0,
            "HA": 60.0
        })
    
    def test_to_dict(self):
        """Test conversion en dictionnaire"""
        data_str = "1TA25;1HA60"
        sensor_data = SensorData.from_lora_data(data_str)
        result = sensor_data.to_dict()
        
        self.assertIn("raw_data", result)
        self.assertIn("sensors", result)
        self.assertIn("timestamp", result)
        self.assertEqual(result["sensors"], {"TA": 25.0, "HA": 60.0})


class TestAlertConfig(unittest.TestCase):
    """Tests pour AlertConfig"""
    
    def test_from_mqtt_payload(self):
        """Test création depuis un payload MQTT"""
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
        
        alert = AlertConfig.from_mqtt_payload(payload)
        
        self.assertEqual(alert.alert_id, "550e8400-e29b-41d4-a716-446655440000")
        self.assertEqual(alert.title, "Température trop élevée")
        self.assertTrue(alert.is_active)
        self.assertFalse(alert.warning_enabled)
        self.assertEqual(alert.cell_ids, ["ESP32_001", "ESP32_002"])
        self.assertEqual(len(alert.sensors), 1)
        self.assertEqual(alert.sensors[0]["type"], "TA")
    
    def test_to_lora_data(self):
        """Test conversion en format LoRa"""
        alert = AlertConfig(
            alert_id="550e8400-e29b-41d4-a716-446655440000",
            title="Test Alert",
            is_active=True,
            warning_enabled=False,
            cell_ids=["ESP32_001"],
            sensors=[
                {
                    "type": "TA",
                    "index": 0,
                    "criticalRange": [30, 100],
                    "warningRange": [25, 30]
                }
            ]
        )
        
        lora_data = alert.to_lora_data()
        expected = "550e8400-e29b-41d4-a716-446655440000|Test Alert|1|0|ESP32_001|TA:0:30:100:25:30"
        self.assertEqual(lora_data, expected)


class TestAlertTrigger(unittest.TestCase):
    """Tests pour AlertTrigger"""
    
    def test_from_lora_data(self):
        """Test parsing depuis format LoRa"""
        data_str = "550e8400...|ESP32_001|TA|0|32.5|critical|2023-01-01T12:00:00"
        alert = AlertTrigger.from_lora_data(data_str)
        
        self.assertEqual(alert.alert_id, "550e8400...")
        self.assertEqual(alert.cell_uid, "ESP32_001")
        self.assertEqual(alert.sensor_type, "TA")
        self.assertEqual(alert.sensor_index, 0)
        self.assertEqual(alert.value, 32.5)
        self.assertEqual(alert.trigger_type, "critical")
        self.assertEqual(alert.timestamp, "2023-01-01T12:00:00")
    
    def test_from_lora_data_invalid(self):
        """Test parsing avec données incomplètes"""
        data_str = "550e8400...|ESP32_001"
        alert = AlertTrigger.from_lora_data(data_str)
        
        self.assertEqual(alert.alert_id, "")
        self.assertEqual(alert.cell_uid, "")
    
    def test_to_dict(self):
        """Test conversion en dictionnaire"""
        alert = AlertTrigger(
            alert_id="550e8400-e29b-41d4-a716-446655440000",
            cell_uid="ESP32_001",
            sensor_type="TA",
            sensor_index=0,
            value=32.5,
            trigger_type="critical",
            timestamp="2023-01-01T12:00:00"
        )
        
        result = alert.to_dict()
        
        self.assertEqual(result["alert_id"], "550e8400-e29b-41d4-a716-446655440000")
        self.assertEqual(result["cell_uid"], "ESP32_001")
        self.assertEqual(result["sensor_type"], "TA")
        self.assertEqual(result["value"], 32.5)
        self.assertEqual(result["trigger_type"], "critical")
        self.assertEqual(result["timestamp"], "2023-01-01T12:00:00")


if __name__ == '__main__':
    unittest.main()
