#!/usr/bin/env python3

import time
import board
import busio
import digitalio

print("Testing SPI and GPIO pins for LoRa module...")

# Test different CS pin options
cs_pins = [board.D17, board.D27, board.D22, board.D7, board.D8]
reset_pins = [board.D25, board.D24, board.D23]

print(f"\nAvailable SPI settings:")
print(f"SCK: {board.SCK}")
print(f"MOSI: {board.MOSI}")
print(f"MISO: {board.MISO}")

# Try to initialize SPI
try:
    spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
    print("\n✓ SPI bus initialized successfully")

    # Test CS pins
    print("\nTesting CS pins:")
    for cs_pin in cs_pins:
        try:
            cs = digitalio.DigitalInOut(cs_pin)
            cs.direction = digitalio.Direction.OUTPUT
            print(f"  ✓ {cs_pin} works")
            cs.deinit()
        except Exception as e:
            print(f"  ✗ {cs_pin} failed: {e}")

    # Test Reset pins
    print("\nTesting Reset pins:")
    for reset_pin in reset_pins:
        try:
            reset = digitalio.DigitalInOut(reset_pin)
            reset.direction = digitalio.Direction.OUTPUT
            print(f"  ✓ {reset_pin} works")
            reset.deinit()
        except Exception as e:
            print(f"  ✗ {reset_pin} failed: {e}")

    spi.deinit()

except Exception as e:
    print(f"\n✗ Failed to initialize SPI: {e}")

print("\n" + "="*50)
print("Now testing RFM9x initialization with working pins...")

# Try the most common working combination
try:
    import adafruit_rfm9x

    spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)
    cs = digitalio.DigitalInOut(board.D17)
    reset = digitalio.DigitalInOut(board.D25)

    print("\nAttempting to initialize RFM9x...")
    print("CS: D17, Reset: D25")

    # Try with reset sequence
    reset.direction = digitalio.Direction.OUTPUT
    reset.value = False
    time.sleep(0.01)
    reset.value = True
    time.sleep(0.01)

    rfm9x = adafruit_rfm9x.RFM9x(spi, cs, reset, frequency=915.0)
    print("✓ RFM9x module detected and initialized!")
    print(f"  Frequency: {rfm9x.frequency_mhz} MHz")

except ImportError:
    print("✗ adafruit_rfm9x module not installed")
except Exception as e:
    print(f"✗ RFM9x initialization failed: {e}")
    print("\nPossible issues:")
    print("1. Check physical wiring:")
    print("   - VCC to 3.3V (NOT 5V)")
    print("   - GND to GND")
    print("   - SCK to GPIO11 (SPI0 SCK)")
    print("   - MOSI to GPIO10 (SPI0 MOSI)")
    print("   - MISO to GPIO9 (SPI0 MISO)")
    print("   - CS to GPIO17")
    print("   - Reset to GPIO25")
    print("2. Ensure SPI is enabled: sudo raspi-config > Interface Options > SPI")
    print("3. Check that no other process is using SPI")