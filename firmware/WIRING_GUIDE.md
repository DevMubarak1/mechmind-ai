# MechMind AI — ESP32 Hardware Wiring Guide 🛠️🔌

This guide matches the **exact components** in your pictures (`components-pictures/`).

---

## 📦 Component Checklist

| Component | Function | Interface / Pins |
|---|---|---|
| **ESP32 Dev Board (Type-C)** | Brain / IoT Gateway / WiFi | 30 or 38 pin GPIO |
| **GY-291 ADXL345** | 3-Axis Vibration & Shock | I2C (`SDA`, `SCL`) |
| **Digital Temp Module (KY-028/NTC)** | Engine / Hydraulic Temp | Analog Out (`AO`), VCC, GND |
| **INMP441 MEMS Mic** | Industrial Acoustic / Sound (dB) | I2S (`SCK`, `WS`, `SD`, `L/R`) |
| **18650 Battery + Holder + TP4056** | Autonomous Portable Power | 5V Out to `VIN` & `GND` |
| **Neodymium Magnets** | Magnetic Machine Mount | Adhered to bottom of box |

---

## 🔌 Pin-by-Pin Wiring Diagram

### 1. GY-291 ADXL345 (Vibration Sensor) -> ESP32
*Connects using standard I2C bus:*
- **VCC / 3V3**  ➡️  ESP32 **3V3**
- **GND**      ➡️  ESP32 **GND**
- **SDA**      ➡️  ESP32 **GPIO 21**
- **SCL**      ➡️  ESP32 **GPIO 22**
- **CS**       ➡️  ESP32 **3V3** (High selects I2C mode)
- **SDO**      ➡️  ESP32 **GND** (Sets I2C address to `0x53`)

---

### 2. Digital Temperature Sensor Module -> ESP32
*Connects to 3.3V and an ADC pin:*
- **VCC (+)**  ➡️  ESP32 **3V3**
- **GND (-)**  ➡️  ESP32 **GND**
- **AO (Analog Out)** ➡️  ESP32 **GPIO 34** *(Reads analog engine heat)*
- **DO (Digital Out)** ➡️  ESP32 **GPIO 4** *(Optional emergency overheat hardware trip)*

---

### 3. INMP441 I2S Omnidirectional Microphone -> ESP32
*High-precision digital microphone:*
- **VDD**      ➡️  ESP32 **3V3**
- **GND**      ➡️  ESP32 **GND**
- **L/R**      ➡️  ESP32 **GND** *(Selects Left Channel)*
- **SCK / BCLK** ➡️  ESP32 **GPIO 14** *(Serial Clock)*
- **WS / LRCK**  ➡️  ESP32 **GPIO 15** *(Word Select)*
- **SD / DOUT**  ➡️  ESP32 **GPIO 32** *(Serial Audio Data)*

---

### 4. Power & Battery (TP4056 + 18650) -> ESP32
- **18650 Holder (+ / Red)** ➡️ TP4056 **B+**
- **18650 Holder (- / Black)** ➡️ TP4056 **B-**
- TP4056 **OUT+ (5V Boost)** ➡️ ESP32 **VIN / 5V**
- TP4056 **OUT- (GND)** ➡️ ESP32 **GND**
- *Note:* While testing on your desk, you can simply plug the USB Type-C cable directly from your laptop into the ESP32!

---

## 🧲 How MechMind Mounts onto Heavy Machinery

```
+-------------------------------------------------------------+
|               CAT 320 / XCMG Loader Engine Bay             |
|                                                             |
|   [ Heavy Cast-Iron Engine Block / Hydraulic Pump Body ]    |
|   =======================================================   |
|         ▲                     ▲                    ▲        |
|         │                     │                    │        |
|    [Strong Neodymium]   [Strong Neodymium]   [Strong Neodymium]|
|   =======================================================   |
|               Bottom of MechMind Rugged Enclosure           |
|                                                             |
|   - ADXL345 firmly pressed against base (vibration probe)   |
|   - NTC Thermistor tip touching metal casing (temp probe)   |
|   - INMP441 pointing toward engine chamber (acoustic probe) |
|   - ESP32 transmitting WiFi / Cellular telemetry to backend |
+-------------------------------------------------------------+
```

### Why Magnets?
Heavy machinery (excavators, loaders, tower cranes) have thick steel and cast-iron frames. Neodymium magnets (grade N52) provide over 5-10kg of pull force, allowing Mubarak to snap MechMind onto the engine or hydraulic pump in **5 seconds** without drilling holes or voiding machine warranties!
