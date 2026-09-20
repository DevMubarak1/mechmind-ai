# MechMind AI — Complete Technical System Documentation

**System Version**: 2.0 (Industrial Edge Edition)  
**Author**: MechMind AI Engineering Team  
**Last Updated**: September 2026  

---

## 1. Executive Summary & Purpose

**MechMind AI** is an end-to-end, edge-enabled predictive maintenance, real-time telemetry, and intelligent diagnostic platform designed specifically for heavy construction, mining, and earthmoving machinery (e.g., excavators, wheel loaders, tower cranes, bulldozers, haulers).

The platform bridges physical workshop realities and advanced AI reasoning:
- **Physical Edge Layer**: Ruggedized IoT sensor node with an ESP32 powered by an 18650 Li-ion battery, streaming vibration, thermal, and acoustic metrics over WiFi/cellular.
- **Data & Ingestion Layer**: High-throughput FastAPI backend backed by PostgreSQL 15, persisting real-time telemetry and triggering automated threshold alerts.
- **Cognitive Diagnostic Layer**: Hybrid RAG (Retrieval-Augmented Generation) pipeline powered by ChromaDB vector collections and local quantized LLMs (`llama3.1:8b` via Ollama with CUDA acceleration), grounded strictly in OEM workshop service manuals (Caterpillar, Komatsu, SANY, XCMG, and SAE J1939 specifications).
- **Technician Interfaces**:
  1. **Minimalist Monochrome Web Dashboard**: Real-time 3-axis kinematic waveforms, acoustic pressure meters, live thermal gauges, and multi-asset fleet switching.
  2. **Field-Grade WhatsApp AI Assistant**: Low-bandwidth, mobile-first conversational diagnostic copilot supporting natural text, voice notes (Whisper transcription), and component damage photos (vision models).

---

## 2. Hardware Architecture & Edge Sensor Node

### 2.1 Microcontroller & Sensors
The physical telemetry node (`NODE-001`) is built upon the **ESP32-WROOM-32** dual-core microcontroller:

| Component | Sensor IC / Part | Interface | Pin Assignment | Measurement Range & Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **MCU** | ESP32-WROOM-32D | SPI / I2C / UART | — | Dual-core 240MHz, 2.4GHz WiFi 802.11 b/g/n |
| **Temperature** | DS18B20 Digital Probe | 1-Wire (4.7kΩ pullup) | `GPIO 4` | -55°C to +125°C (±0.5°C), hydraulic oil & engine block |
| **Vibration / Motion** | MPU6050 6-DOF IMU | I2C (Address `0x68`) | `SDA: GPIO 21`, `SCL: GPIO 22` | ±16g accelerometer, 3-axis RMS vibration & gravity |
| **Acoustic Noise** | Analog Sound Microphone | ADC (Attenuation 11dB) | `GPIO 34` (ADC1_CH6) | 35 dB to 120 dB acoustic pressure level |
| **Status Indicator** | Surface-mount LED | Digital Output | `GPIO 2` | Heartbeat & WiFi link status |

### 2.2 Power Subsystem (Battery & Pass-Through Charging)
The node operates completely untethered on battery power:
- **Battery Cell**: Single 3.7V 18650 Lithium-Ion cell (2600 mAh).
- **Protection & Charging Module**: TP4056 board with integrated DW01A battery protection circuit and dual 8205A MOSFETs (protects against over-discharge `< 2.5V` and over-charge `> 4.2V`).
- **Voltage Booster**: MT3608 DC-DC step-up converter stepping 3.7V nominal battery voltage to stable 5.0V output delivered to the ESP32 `VIN` pin.
- **Pass-Through Charging**: Allows USB Type-C 5V charging while simultaneously powering the running ESP32 without brownout or reset.
- **Power Control**: Inline micro-rocker switch between battery `B+` and booster input `VIN+`.

### 2.3 Firmware Pipeline (`firmware/mechmind_node.ino`)
- **Sampling Cadence**: 2,000 milliseconds (~0.5 Hz telemetry packet stream).
- **Telemetry Vector**:
  ```json
  {
    "node_id": "NODE-001",
    "temperature": 28.12,
    "vibration_x": 0.00,
    "vibration_y": -0.06,
    "vibration_z": -1.19,
    "vibration_magnitude": 1.19,
    "sound_level_db": 41.5,
    "vibration_fft": null
  }
  ```
- **Fail-safe Logic**: Automatic non-blocking WiFi reconnect loop, I2C sensor bus hang recovery, and local LED status pulsing.

---

## 3. Database Architecture (PostgreSQL 15)

The database runs on port `5433` under database name `mechmind_db`:

### 3.1 Key Tables Schema

#### `equipment`
Stores all tracked fleet machinery assets across construction, mining, and earthmoving categories:
- `id` (SERIAL PRIMARY KEY)
- `name` (VARCHAR): Display asset name (e.g., `Excavator CAT 320`, `Hauler Volvo A40G`)
- `type` (VARCHAR): Machine category (`excavator`, `loader`, `crane`, `bulldozer`, `grader`, `dump_truck`)
- `model` (VARCHAR): OEM designation (e.g., `CAT 320GC`, `Komatsu PC200-8`, `SANY SY215C`)
- `location` (VARCHAR): Jobsite assignment (e.g., `Lagos Site A`, `Abuja Site B`)
- `status` (VARCHAR): `active`, `maintenance`, `idle`
- `node_id` (VARCHAR UNIQUE): Hardware binding (e.g., `NODE-001`)

#### `sensor_readings`
High-frequency time-series table logging every telemetry packet:
- `id` (BIGSERIAL PRIMARY KEY)
- `equipment_id` (INT REFERENCES equipment(id))
- `node_id` (VARCHAR)
- `temperature` (FLOAT): In Celsius
- `vibration_x`, `vibration_y`, `vibration_z` (FLOAT): 3-Axis acceleration in g
- `vibration_magnitude` (FLOAT): $\sqrt{X^2 + Y^2 + Z^2}$
- `sound_level_db` (FLOAT): Acoustic level in dB
- `vibration_fft` (TEXT / JSON): Optional frequency spectrum
- `timestamp` (TIMESTAMP WITH TIME ZONE DEFAULT NOW())

#### `alerts`
Automated system threshold violations triggered during ingestion:
- `id` (SERIAL PRIMARY KEY)
- `equipment_id` (INT REFERENCES equipment(id))
- `alert_type` (VARCHAR): `temperature`, `vibration`, `sound`
- `severity` (VARCHAR): `warning`, `critical`
- `message` (TEXT): Diagnostic warning description
- `sensor_value` (FLOAT)
- `acknowledged` (BOOLEAN DEFAULT FALSE)
- `created_at` (TIMESTAMP DEFAULT NOW())

#### `alert_thresholds`
Configurable operating limits per machinery type:
- Temperature warning: `85.0°C`, critical: `105.0°C`
- Vibration warning: `2.5g`, critical: `4.5g`
- Sound warning: `85.0 dB`, critical: `105.0 dB`

---

## 4. Backend Architecture (FastAPI & Python 3.11)

The backend (`backend/main.py`) provides REST APIs and coordinates ingestion, RAG, and WebSocket/polling feeds:

### 4.1 Core Endpoints
- `POST /api/sensors/data`: Receives raw telemetry packets from ESP32 nodes, inserts into `sensor_readings`, evaluates threshold violations, and triggers alerts.
- `POST /api/diagnose`: Main diagnostic endpoint accepting `{phone_number, message, equipment_id}`. Enriches user queries with live sensor data and routes to the RAG engine.
- `POST /api/diagnose/voice`: Ingests audio files (`.ogg`, `.mp3`), transcribes using Whisper, and executes diagnostic reasoning.
- `POST /api/diagnose/image`: Multimodal vision triage for component photos (cracks, leaks, wear patterns).
- `GET /api/equipment`: Returns all registered machinery in the fleet.
- `GET /api/equipment/{id}/readings`: Returns recent chronological readings for charts, with fallback to the active fleet stream if an asset has no dedicated sensor yet.
- `GET /api/dashboard/stats`: Returns fleet counts, total ingested points today, active 24h alerts, and diagnostic session counts.
- `GET /health`: Comprehensive subsystem check verifying PostgreSQL connection, Ollama daemon, and active models.

---

## 5. AI Reasoning & RAG Engine Architecture

### 5.1 Local Hardware Inference Stack
- **Engine**: Ollama 0.34+ serving `llama3.1:8b-instruct-q4_K_M`.
- **Compute Offload**: Hardware-accelerated with CUDA 13.1 on NVIDIA GeForce GTX 1650 (4GB VRAM). 13 transformer layers offloaded to GPU VRAM (`~1923 MiB`), with remaining 20 layers executed on the Intel Core i7 host CPU (`~2761 MiB`).
- **Embedding Model**: `nomic-embed-text` generating 768-dimensional dense vector embeddings.
- **Vector Database**: ChromaDB storing chunked OEM service manuals and standard fault code tables.

### 5.2 Dual-Path Dispatch Architecture

To balance sub-millisecond responsiveness for critical codes with deep diagnostic reasoning for complex issues, MechMind AI implements a dual-path routing system:

```
                  Incoming User Query
                           |
             +-------------+-------------+
             |                           |
             v                           v
     Fast-Path Check              RAG Reasoning Path
 (Regex & In-Memory Map)       (ChromaDB + llama3.1:8b)
             |                           |
    Matched Standard Codes?              v
    (e.g., SPN 100, 110, 102,     1. Embed query with nomic-embed-text
     or "status", "hi", "help")   2. Retrieve top-k manual excerpts
             |                    3. Inject live hardware telemetry
             |                    4. Enforce strict anti-fabrication prompt
             |                    5. Generate grounded response with Llama 3.1
             v                           |
    Instant Resolution                   v
       (< 1 ms latency)          Comprehensive Diagnostic Answer
                                     (15 - 35s latency)
```

1. **Sub-Millisecond Fast Path (`fast_diagnostics.js`)**:
   - Matches standard SAE J1939 fault codes (SPN 100, 110, 102, 157, 190, 639, etc.) and quick commands (`status`, `hi`, `help`).
   - Resolves instantly from structured in-memory dictionaries in `< 1ms` with deterministic, standard workshop actions.
2. **Deep RAG Engine Path (`rag_engine.py`)**:
   - Invoked for all natural language questions, symptom descriptions, and cross-equipment comparisons.
   - Embeds query and retrieves contextual passages from the ChromaDB manual collections.
   - Injects the active hardware sensor telemetry directly into the prompt so the LLM knows the machine's live temperature, vibration, and acoustic levels.
   - **Anti-Fabrication Guardrail**: Explicitly instructs the model to refuse and state lack of documentation rather than invent fake cause codes or torque specifications for out-of-scope queries (e.g., proprietary CAT error 105 or unknown bolt specs).

---

## 6. WhatsApp Bot Architecture (`whatsapp-bot/index.js`)

- **Socket Layer**: Powered by `@whiskeysockets/baileys` using multi-file auth credentials stored in `auth_info/`.
- **Client Independence**: Runs as a standing Windows service daemon. Message reception, processing, and delivery happen on the server. If the user minimizes WhatsApp, locks their phone, or closes the chat window, background processing continues uninterrupted.
- **Typing Indicator Heartbeat**: Uses WhatsApp's native `sendPresenceUpdate('composing', sender)` with a 6-second heartbeat timer. This keeps the native animated "typing..." status active on the user's phone throughout LLM generation, completely eliminating cluttered intermediate text messages.
- **Local Control API**: Express server running on port `3001` providing:
  - `POST /api/send-message`: Direct dispatch to any WhatsApp JID or phone number.
  - `POST /api/send-alert`: Dispatches real-time threshold alerts from backend sensors to registered technician numbers.
  - `GET /api/qr` & `POST /api/pairing-code`: Integrates directly with the web dashboard for phone pairing.

---

## 7. Web Dashboard Architecture (`dashboard/`)

- **Aesthetic**: Minimalist Monochrome Dark Theme conforming to modern industrial standards (pure blacks, subtle zinc borders, JetBrains Mono data readouts).
- **Instruments Grid**:
  - `01 / THERMAL`: Live hydraulic reservoir temperature (°C) with dynamic fill meter and warning thresholds.
  - `02 / KINEMATIC`: 3-axis vibration RMS (g) with live vector readout (`X: 0.0 · Y: -0.1 · Z: -1.2`).
  - `03 / ACOUSTIC`: Sound pressure level (dB) tracking noise from INMP441 MEMS sensor.
  - `04 / INGESTION`: Stream synchronization and hardware node status (`NODE-001`).
- **Waveform Canvas**: High-precision multi-line Chart.js charts rendering 30-sample rolling windows.
- **Categorized Asset Selector**: Categorized dropdown allowing technicians to monitor any construction machine across the jobsite:
  - Earthmoving & Excavators (CAT 320 [Live IoT], Komatsu PC200-8, SANY SY215C)
  - Dozers, Hauling & Grading (CAT D6T Dozer, Volvo A40G Hauler, CAT 140K Grader)
  - Loading & Lifting (XCMG LW500 Wheel Loader, Zoomlion TC6013A Crane)
- **AI Diagnostic Copilot**: Chat interface equipped with photo upload previews, prompt chips, and a 3-dot animated bouncing typing indicator.

---

## 8. Directory & File Structure

```
mechmind-ai/
├── backend/
│   ├── main.py                     # Primary FastAPI application & API endpoints
│   ├── rag_engine.py               # ChromaDB retrieval & Ollama LLM integration
│   ├── init.sql                    # PostgreSQL schema definition
│   ├── requirements.txt            # Python dependencies
│   ├── ingestion/                  # Manual chunking & ingestion scripts
│   ├── manuals/                    # OEM technical documentation files
│   └── knowledge/                  # Structured failure modes & J1939 fault definitions
├── dashboard/
│   ├── index.html                  # Dashboard HTML structure & modal dialogs
│   ├── style.css                   # Monochrome industrial design system
│   └── app.js                      # Chart rendering, telemetry polling & chat handlers
├── firmware/
│   ├── mechmind_node.ino           # ESP32 Arduino C++ firmware
│   └── WIRING_GUIDE.md             # Complete physical wiring & battery guide
├── whatsapp-bot/
│   ├── index.js                    # Baileys WhatsApp bot & Express control server
│   ├── fast_diagnostics.js         # Sub-millisecond SAE J1939 lookup engine
│   └── package.json                # Node.js dependencies
└── docs/
    └── SYSTEM_ARCHITECTURE.md      # This comprehensive architectural specification
```

---

## 9. Verification & Operational Summary

All core systems have been verified under live operation:
- **Hardware**: ESP32 streaming physical sensor data while battery powered.
- **Database**: PostgreSQL 15 logging live rows every 2 seconds with timestamps.
- **AI Copilot**: Llama 3.1:8b running locally with CUDA acceleration and verified anti-fabrication controls.
- **WhatsApp**: Responsive to casual queries, grounded fault diagnostics, and live sensor awareness.
