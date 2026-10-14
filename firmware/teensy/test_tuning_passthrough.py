from pathlib import Path


source_path = Path(__file__).with_name("teensy_coinft_serial_interface.cpp")
source = source_path.read_text(encoding="utf-8")

assert "uint8_t tuningCommand[5]" in source
assert "Serial.readBytes(" in source
assert "tuningCommand + 1" in source
assert "CFT1.write(tuningCommand, 5)" in source

print("PASS: Teensy forwards the complete five-byte CoinFT tuning command")
