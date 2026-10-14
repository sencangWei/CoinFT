#include <Arduino.h>

#ifdef USB_DUAL_SERIAL
#include <stdio.h>
static uint32_t diagLoopCount, diagUartBytes, diagDataReads, diagPayloadBytes;
static uint32_t diagEndMarkers, diagEndTimeouts, diagStarts, diagStops;
static volatile uint32_t diagTimerTicks, diagUsbAttempts, diagUsbAccepted;
static uint32_t diagLastReport, diagSequence;

static int diagReadUart() {
  int value = Serial2.read();
  if (value >= 0) ++diagUartBytes;
  return value;
}

static void diagCountAccepted(size_t actual, size_t requested) {
  if (actual <= requested) diagUsbAccepted += actual;
}

static void diagHeartbeat() {
  const uint32_t now = millis();
  if (uint32_t(now - diagLastReport) < 500) return;
  diagLastReport = now;
  ++diagSequence;
  if (!SerialUSB1) return;
  uint32_t mask;
#ifdef __arm__
  __asm__ volatile("mrs %0, primask" : "=r" (mask) :: "memory");
#else
  mask = __get_PRIMASK();
#endif
  __disable_irq();
  const uint32_t ticks = diagTimerTicks;
  const uint32_t attempts = diagUsbAttempts;
  const uint32_t accepted = diagUsbAccepted;
#ifdef __arm__
  __asm__ volatile("msr primask, %0" :: "r" (mask) : "memory");
#else
  __set_PRIMASK(mask);
#endif
  char line[192];
  const int length = snprintf(line, sizeof(line),
      "CFD1,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu,%lu\n",
      (unsigned long)diagSequence, (unsigned long)now, (unsigned long)diagLoopCount,
      (unsigned long)diagUartBytes, (unsigned long)diagDataReads,
      (unsigned long)diagPayloadBytes, (unsigned long)diagEndMarkers,
      (unsigned long)diagEndTimeouts, (unsigned long)ticks, (unsigned long)attempts,
      (unsigned long)accepted, (unsigned long)diagStarts, (unsigned long)diagStops);
  if (length <= 0 || size_t(length) >= sizeof(line)) return;
  if (SerialUSB1.availableForWrite() < length) return;
  SerialUSB1.write(reinterpret_cast<const uint8_t *>(line), size_t(length));
}
#endif

// ==========================================
// USER CONFIGURATION
// ==========================================
#define NUM_COINFTS  1   // Currently supports 1 or 2. You can easily extend to more CoinFTs by modifying the code.

// Current CoinFT final tuning table {Resolution, Ref, Compensation}, accepted 2026-09-07.
// CoinFT tuning lives in volatile runtime memory, so resend on every power-up.
// Any additional CoinFT needs its own table (per-sensor capacitance baseline differs).
const uint8_t TUNING[12][3] = {
  {12, 50, 50}, {12, 30, 72}, {12, 30, 81}, {12, 30, 82},
  {12, 30, 83}, {12, 30, 85}, {12, 30, 76}, {12, 30, 75},
  {12, 100, 17}, {12, 100, 26}, {12, 80, 58}, {12, 80, 42},
};
// ==========================================

// Use built-in IntervalTimer for Teensy 4.0
IntervalTimer myTimer;

// Hardware Serial Definitions
#define CFT1  Serial2
#if NUM_COINFTS == 2
  #define CFT2  Serial3
#endif

// Variables
byte data1[24] = { 0 };
volatile bool newData1 = false;

#if NUM_COINFTS == 2
  byte data2[24] = { 0 };
  volatile bool newData2 = false;
#endif

// Function Prototypes
void transmitData(void);

void setup() {
  CFT1.begin(1000000);
  #if NUM_COINFTS == 2
    CFT2.begin(1000000);
  #endif

  Serial.begin(115200);

  // Wait for hardware serials to be ready
  while (!CFT1 && millis() < 2000);
  #if NUM_COINFTS == 2
    while (!CFT2 && millis() < 2000);
  #endif

  // Let the CoinFT finish booting, then push the tuning table (volatile on
  // the sensor side, so it must be resent after every power cycle).
  delay(500);
  CFT1.write('i');
  #if NUM_COINFTS == 2
    CFT2.write('i');
  #endif
  delay(50);
  for (uint8_t ch = 0; ch < 12; ch++) {
    uint8_t cmd[5] = { 't', ch, TUNING[ch][0], TUNING[ch][1], TUNING[ch][2] };
    CFT1.write(cmd, 5);
    #if NUM_COINFTS == 2
      CFT2.write(cmd, 5);
    #endif
    delay(50);
  }
}

void loop() {
#ifdef USB_DUAL_SERIAL
  ++diagLoopCount;
#endif
  // 1. Listen for PC Commands
  if (Serial.available()) {
    char readChar = Serial.read();

    if (readChar == 'i') {
#ifdef USB_DUAL_SERIAL
      ++diagStops;
#endif
      // Idle Command
      CFT1.write('i');
      #if NUM_COINFTS == 2
        CFT2.write('i');
      #endif
      myTimer.end(); // Stop the checker
      
      // Reset flags
      newData1 = false;
      #if NUM_COINFTS == 2
        newData2 = false;
      #endif
    }
    else if (readChar == 's') {
#ifdef USB_DUAL_SERIAL
      ++diagStarts;
#endif
      // Start Command
      CFT1.write('s');
      #if NUM_COINFTS == 2
        CFT2.write('s');
      #endif
      
      // Check for data every 1ms (1000 Hz)
      myTimer.begin(transmitData, 1000); 
    }
    else if (readChar == 't') {
      // Tuning Command: 't' + channel + resolution + ref + compensation
      uint8_t tuningCommand[5] = { 't', 0, 0, 0, 0 };
      if (Serial.readBytes(reinterpret_cast<char *>(tuningCommand + 1), 4) == 4) {
        CFT1.write(tuningCommand, 5);
        #if NUM_COINFTS == 2
          CFT2.write(tuningCommand, 5);
        #endif
      }
    }
  }

  // 2. Listen for Sensor 1 Data
  if (CFT1.available() > 25) {
#ifdef USB_DUAL_SERIAL
    if (diagReadUart() == 0x02) { // Start Byte
      ++diagDataReads;
      const size_t payloadBytes = CFT1.readBytes(data1, 24);
      diagPayloadBytes += payloadBytes;
      diagUartBytes += payloadBytes;
#else
    if (CFT1.read() == 0x02) { // Start Byte
      CFT1.readBytes(data1, 24);
#endif
      newData1 = true;
      
      // Flush until End Byte
      unsigned long startWait = micros();
#ifdef USB_DUAL_SERIAL
      int endByte;
      while ((endByte = diagReadUart()) != 0x03 && (micros() - startWait < 1000));
      if (endByte == 0x03) ++diagEndMarkers;
      else ++diagEndTimeouts;
#else
      while (CFT1.read() != 0x03 && (micros() - startWait < 1000)); 
#endif
    }
  }

  // 3. Listen for Sensor 2 Data (Only if enabled)
  #if NUM_COINFTS == 2
    if (CFT2.available() > 25) {
       if (CFT2.read() == 0x02) { // Start Byte
         CFT2.readBytes(data2, 24);
         newData2 = true;
         
         // Flush until End Byte
         unsigned long startWait = micros();
         while (CFT2.read() != 0x03 && (micros() - startWait < 1000));
       }
    }
  #endif
#ifdef USB_DUAL_SERIAL
  diagHeartbeat();
#endif
}

// Interrupt Service Routine (Runs every 1ms)
void transmitData(void) {
#ifdef USB_DUAL_SERIAL
  ++diagTimerTicks;
#endif
  
  #if NUM_COINFTS == 1
    // --- SINGLE SENSOR MODE ---
    if (newData1) {
#ifdef USB_DUAL_SERIAL
      ++diagUsbAttempts;
      diagCountAccepted(Serial.write(0x00), 1); // Header
      diagCountAccepted(Serial.write(0x00), 1);
      diagCountAccepted(Serial.write(data1, 24), 24);
#else
      Serial.write(0x00); // Header
      Serial.write(0x00);
      Serial.write(data1, 24);
#endif
      
      newData1 = false;
    }

  #elif NUM_COINFTS == 2
    // --- DUAL SENSOR MODE (Synchronized) ---
    // Only send if BOTH sensors have reported in
    if (newData1 && newData2) {
      Serial.write(0x00); // Header
      Serial.write(0x00);
      Serial.write(data1, 24);
      Serial.write(data2, 24);

      newData1 = false;
      newData2 = false;
    }
  #endif
}
