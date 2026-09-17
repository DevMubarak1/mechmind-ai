/*
 * MechMind AI — ESP32 Sensor Node Firmware (mechmind_node.ino)
 * 
 * Hardware Setup (matches your exact purchased components):
 * - Microcontroller: ESP32 Development Board (USB Type-C, 38-pin)
 * - Vibration: GY-291 ADXL345 3-Axis Accelerometer (I2C: SDA=GPIO21, SCL=GPIO22)
 * - Temperature: Waterproof DS18B20 Digital Probe (OneWire: DATA=GPIO4, with 4.7kΩ pull-up)
 * - Sound: INMP441 I2S Omnidirectional MEMS Microphone (SCK=GPIO14, WS=GPIO15, SD=GPIO32)
 * - Power: 18650 Li-ion 3.7V Battery + TP4056 Boost Converter (5V to VIN)
 * - Mounting: Neodymium magnets (6×2mm) on enclosure bottom
 * 
 * Required Arduino Libraries (install via Library Manager):
 *   - Adafruit ADXL345
 *   - Adafruit Unified Sensor
 *   - OneWire
 *   - DallasTemperature
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_ADXL345_U.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <driver/i2s.h>
#include <math.h>

// ========================
// Configuration — CHANGE THESE!
// ========================
const char* WIFI_SSID = "YOUR_WIFI_OR_HOTSPOT_NAME";
const char* WIFI_PASS = "YOUR_WIFI_PASSWORD";

// Server endpoint — use your laptop's local IP (run ipconfig to find it)
const char* SERVER_URL = "http://192.168.1.100:8080/api/sensors/data";
const char* NODE_ID    = "NODE-001"; // Matches CAT 320 Excavator in DB

// ========================
// Pin Definitions
// ========================

// I2C Bus (shared by ADXL345)
#define I2C_SDA_PIN    21
#define I2C_SCL_PIN    22

// DS18B20 Waterproof Temperature Probe (OneWire)
#define DS18B20_PIN    4   // Data pin (needs 4.7kΩ pull-up to 3.3V)

// INMP441 I2S MEMS Microphone
#define I2S_WS_PIN     15  // Word Select (L/R clock)
#define I2S_SCK_PIN    14  // Serial Clock (BCLK)
#define I2S_SD_PIN     32  // Serial Data Out (DOUT)
#define I2S_PORT       I2S_NUM_0
#define I2S_BUFFER_LEN 512

// Status LED
#define STATUS_LED_PIN 2   // Built-in blue LED on ESP32

// ========================
// Sensor Instances
// ========================
Adafruit_ADXL345_Unified accel = Adafruit_ADXL345_Unified(12345);

OneWire oneWire(DS18B20_PIN);
DallasTemperature tempSensor(&oneWire);

// Telemetry interval (send data every 2 seconds)
unsigned long lastSendTime = 0;
const unsigned long SEND_INTERVAL_MS = 2000;

// ========================
// I2S Microphone Setup
// ========================
void setupI2S() {
  i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = 16000,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = i2s_comm_format_t(I2S_COMM_FORMAT_STAND_I2S),
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 4,
    .dma_buf_len = I2S_BUFFER_LEN,
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };

  i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_SCK_PIN,
    .ws_io_num = I2S_WS_PIN,
    .data_out_num = I2S_PIN_NO_CHANGE,
    .data_in_num = I2S_SD_PIN
  };

  i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
  i2s_set_pin(I2S_PORT, &pin_config);
  i2s_set_clk(I2S_PORT, 16000, I2S_BITS_PER_SAMPLE_32BIT, I2S_CHANNEL_MONO);
}

// ========================
// Read Sound Level (dB SPL approximation from INMP441 RMS)
// ========================
float readSoundLevelDb() {
  int32_t samples[I2S_BUFFER_LEN];
  size_t bytesRead = 0;
  
  esp_err_t result = i2s_read(I2S_PORT, (char*)samples, sizeof(samples), &bytesRead, portMAX_DELAY);
  if (result != ESP_OK || bytesRead == 0) {
    return 45.0; // Ambient fallback
  }

  int samplesRead = bytesRead / sizeof(int32_t);
  double sumSquares = 0;
  for (int i = 0; i < samplesRead; i++) {
    // INMP441 outputs 24-bit audio packed in 32-bit container (MSB-aligned)
    double val = (double)(samples[i] >> 8);
    sumSquares += (val * val);
  }

  double rms = sqrt(sumSquares / samplesRead);
  if (rms <= 0) return 40.0;

  // Convert RMS to approximate dB SPL
  // Calibration offset may need adjustment for your specific INMP441 board
  float db = 20.0 * log10(rms) - 40.0; 
  if (db < 35.0) db = 35.0;
  if (db > 130.0) db = 130.0;
  return db;
}

// ========================
// Read Temperature from Waterproof DS18B20 Probe
// ========================
float readTemperature() {
  tempSensor.requestTemperatures();
  float tempC = tempSensor.getTempCByIndex(0);
  
  // DS18B20 returns -127.0 on read error (disconnected probe)
  if (tempC == DEVICE_DISCONNECTED_C || tempC < -50.0 || tempC > 150.0) {
    Serial.println("  [!] DS18B20 read error — probe disconnected or faulty");
    return 25.0; // Safe fallback for demo
  }
  
  return tempC;
}

// ========================
// Setup
// ========================
void setup() {
  Serial.begin(115200);
  pinMode(STATUS_LED_PIN, OUTPUT);
  digitalWrite(STATUS_LED_PIN, LOW);

  Serial.println("======================================");
  Serial.println(" MechMind AI — ESP32 Sensor Node v2.0");
  Serial.println(" DS18B20 + ADXL345 + INMP441          ");
  Serial.println("======================================");

  // Initialize I2C for ADXL345 Accelerometer
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  if (!accel.begin()) {
    Serial.println("[-] ADXL345 accelerometer NOT found on I2C bus!");
    Serial.println("    Check wiring: VCC→3V3, GND→GND, SDA→GPIO21, SCL→GPIO22");
  } else {
    accel.setRange(ADXL345_RANGE_16_G); // ±16g for heavy industrial vibration
    Serial.println("[+] ADXL345 initialized (±16g range)");
  }

  // Initialize DS18B20 Waterproof Temperature Probe
  tempSensor.begin();
  int deviceCount = tempSensor.getDeviceCount();
  if (deviceCount == 0) {
    Serial.println("[-] DS18B20 NOT found on OneWire bus (GPIO4)!");
    Serial.println("    Check: DATA→GPIO4, 4.7kΩ pull-up between DATA and 3V3");
  } else {
    tempSensor.setResolution(12); // 12-bit = ±0.0625°C precision
    Serial.printf("[+] DS18B20 initialized (%d device(s) found, 12-bit resolution)\n", deviceCount);
  }

  // Initialize I2S INMP441 Microphone
  setupI2S();
  Serial.println("[+] INMP441 I2S microphone initialized (16kHz, 32-bit)");

  // Connect to WiFi
  Serial.printf("[*] Connecting to WiFi: %s", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 30) {
    delay(500);
    Serial.print(".");
    digitalWrite(STATUS_LED_PIN, !digitalRead(STATUS_LED_PIN)); // Blink while connecting
    retries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    digitalWrite(STATUS_LED_PIN, HIGH); // Solid = connected
    Serial.println("\n[+] WiFi Connected! IP: " + WiFi.localIP().toString());
  } else {
    Serial.println("\n[-] WiFi timeout. Will retry in main loop.");
  }
}

// ========================
// Main Loop
// ========================
void loop() {
  unsigned long now = millis();
  if (now - lastSendTime < SEND_INTERVAL_MS) {
    return;
  }
  lastSendTime = now;

  // 1. Read ADXL345 Accelerometer (convert m/s² → g)
  sensors_event_t event;
  float ax = 0.0, ay = 0.0, az = 0.0, mag = 0.0;
  if (accel.getEvent(&event)) {
    ax = event.acceleration.x / 9.80665;
    ay = event.acceleration.y / 9.80665;
    az = event.acceleration.z / 9.80665;
    mag = sqrt(ax * ax + ay * ay + az * az);
  } else {
    // Return 1g at rest if sensor disconnected (gravity only)
    mag = 1.0;
  }

  // 2. Read DS18B20 Temperature (°C)
  float temp = readTemperature();

  // 3. Read Sound Level (dB)
  float soundDb = readSoundLevelDb();

  // Print telemetry to Serial Monitor
  Serial.printf("[Telemetry] Node: %s | Temp: %.1f°C | Vib: %.2fg [X:%.2f Y:%.2f Z:%.2f] | Sound: %.1f dB\n",
                NODE_ID, temp, mag, ax, ay, az, soundDb);

  // 4. Send to FastAPI Backend via HTTP POST
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(5000); // 5 second timeout

    String jsonPayload = "{";
    jsonPayload += "\"node_id\":\"" + String(NODE_ID) + "\",";
    jsonPayload += "\"temperature\":" + String(temp, 2) + ",";
    jsonPayload += "\"vibration_x\":" + String(ax, 2) + ",";
    jsonPayload += "\"vibration_y\":" + String(ay, 2) + ",";
    jsonPayload += "\"vibration_z\":" + String(az, 2) + ",";
    jsonPayload += "\"vibration_magnitude\":" + String(mag, 2) + ",";
    jsonPayload += "\"sound_level_db\":" + String(soundDb, 1);
    jsonPayload += "}";

    int httpCode = http.POST(jsonPayload);
    if (httpCode > 0) {
      Serial.printf("[HTTP] POST → %d OK\n", httpCode);
    } else {
      Serial.printf("[HTTP] POST failed: %s\n", http.errorToString(httpCode).c_str());
    }
    http.end();
  } else {
    // Auto-reconnect
    Serial.println("[*] WiFi lost. Reconnecting...");
    WiFi.reconnect();
  }
}
