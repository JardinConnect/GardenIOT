# Testing LoRa Communication between ESP32 and Pi5

This document explains how to test the LoRa communication with ACK response between the ESP32 device and Pi5 gateway.

## Test Overview

Two test scripts have been created:

1. **ESP32 Test**: `iot esp32/src/test_lora.py` - Sends a test message and waits for ACK from Pi5
2. **Pi5 Test**: `iot-pi5/tests/test_lora_communication.py` - Waits for test message and sends ACK response

## Prerequisites

### Hardware Setup
- ESP32 device with LoRa module connected
- Raspberry Pi 5 with LoRa module connected
- Both devices configured with matching LoRa parameters (frequency, spreading factor, etc.)
- Physical connection between devices (same LoRa network)

### Configuration Files

#### ESP32 Configuration
File: `iot esp32/src/config/config.json`

Key LoRa parameters:
```json
"lora": {
  "frequency": 433.0,
  "spreading_factor": 7,
  "bandwidth": 125000,
  "coding_rate": 5,
  "tx_power": 14,
  "preamble_length": 8,
  "crc": false,
  "ack_enabled": true,
  "ack_timeout_ms": 5000,
  "max_retries": 5,
  "listen_timeout_ms": 5000
}
```

#### Pi5 Configuration
File: `iot-pi5/config.py`

Key LoRa parameters:
```python
"lora": {
    "frequency": 433.0,
    "bandwidth": 125000,
    "spreading_factor": 7,
    "coding_rate": 5,
    "sync_word": 0x12,
    "preamble_length": 8,
    "crc": False,
    "listen_timeout": 2.0,
    "cs_pin": board.D5,
    "reset_pin": board.D25
}
```

**Important**: Ensure both devices use the same frequency, spreading factor, bandwidth, and other LoRa parameters.

## Running the Tests

### ESP32 Test

1. **Upload the test to ESP32**:
   ```bash
   # From the iot esp32 directory
   cd "iot esp32"
   pio run -t upload -e esp32dev
   ```

2. **Run the test**:
   ```bash
   # Connect to ESP32 serial monitor
   pio device monitor
   
   # Then run the test (or upload test_lora.py as main.py)
   ```

### Pi5 Test

1. **Navigate to Pi5 directory**:
   ```bash
   cd "iot-pi5"
   ```

2. **Run the test**:
   ```bash
   python -m tests.test_lora_communication
   ```

## Test Execution Flow

### Expected Sequence

1. **ESP32** sends test message: `B|TEST|timestamp|ESP32_UID|TO:GATEWAY_PI|E`
2. **Pi5** receives the test message
3. **Pi5** sends ACK response: `B|ACK|timestamp|GATEWAY_PI|TO:ESP32_UID|E`
4. **ESP32** receives the ACK and marks test as passed

### Test Messages

- **ESP32 Test Message**:
  ```
  {
    'type': 'TEST',
    'datas': 'TO:GATEWAY_PI'
  }
  ```
  This gets formatted as: `B|TEST|timestamp|ESP32_UID|TO:GATEWAY_PI|E`

- **Pi5 ACK Message**:
  ```
  B|ACK|timestamp|GATEWAY_PI|TO:ESP32_UID|E
  ```

## Troubleshooting

### Common Issues

1. **No messages received**:
   - Check LoRa frequency matches on both devices
   - Verify antenna connections
   - Check spreading factor and bandwidth settings
   - Ensure devices are within range

2. **ACK not received**:
   - Check that `ack_enabled` is `true` in ESP32 config
   - Verify `ack_timeout_ms` is sufficient for your environment
   - Check Pi5 is actually sending the ACK (debug logs)

3. **Import errors**:
   - For Pi5: Run from project root or ensure Python path includes parent directory
   - For ESP32: Ensure all required libraries are in the `lib` directory

### Debugging Tips

- **ESP32**: Use serial monitor to see debug output
- **Pi5**: Run with `python -u tests/test_lora_communication.py` for unbuffered output
- Check LoRa module LEDs for activity
- Verify power supply to both devices

## Test Results

### Success Criteria

- ✅ **ESP32 Test**: Receives ACK from Pi5 within timeout period
- ✅ **Pi5 Test**: Receives test message and successfully sends ACK

### Exit Codes

- `0`: Test passed successfully
- `1`: Test failed (no ACK received or other error)

## Notes

- Tests are designed to run independently but work best when both are running simultaneously
- The ESP32 test has a 10-second timeout for ACK response
- The Pi5 test has a 15-second timeout for receiving test message
- Both tests will exit with appropriate status codes
