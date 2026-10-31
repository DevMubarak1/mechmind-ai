# MechMind AI 🚜⚡🧠

> **Edge-Enabled Industrial Telemetry & Generative Diagnostic Copilot for Heavy Machinery, Construction Equipment, and Agricultural Fleets**  
> *Built for the MLH Hacktoberfest Hack Day 2026*

[![MLH Hack Day 2026](https://img.shields.io/badge/MLH_Hacktoberfest-Hack_Day_2026-FF6B4A?style=for-the-badge&logo=majorleaguehacking)](https://mlh.io)
[![Track: Best Use of Gemma](https://img.shields.io/badge/Track-Best_Use_of_Gemma-4285F4?style=for-the-badge&logo=google)](https://ai.google.dev/gemma)
[![Track: Best Open-Source AI](https://img.shields.io/badge/Track-Best_Open--Source_AI-10B981?style=for-the-badge&logo=opensourceinitiative)](LICENSE)

[![Status](https://img.shields.io/badge/Hardware_Status-Physical_Node_Operational-success.svg)](#prototype-device-and-hardware-architecture)
[![AI Engine](https://img.shields.io/badge/AI_Engine-Google_Gemma_2_%2B_ChromaDB_RAG-blue.svg)](#how-google-gemma-powers-mechmind-diagnostics)
[![Dashboard](https://img.shields.io/badge/Live_Dashboard-mechmind--ng.vercel.app-blue.svg)](https://mechmind-ng.vercel.app)
[![Hardware](https://img.shields.io/badge/Hardware-ESP32_%2B_ADXL345_%2B_DS18B20-orange.svg)](#edge-sensor-node-specifications)
[![Field Interface](https://img.shields.io/badge/Field_Interface-WhatsApp_Copilot-25D366.svg)](#field-interfaces-and-technician-access)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🏆 MLH Hack Day 2026 Focus Tracks

1. **Best Use of Gemma**: MechMind AI leverages **Google Gemma 2 (`gemma2:2b` / `gemma2:9b`)** via local Ollama inference coupled with ChromaDB vector search and deterministic safety hard-pinning. Gemma 2 digests high-frequency vibration, thermal rate-of-rise (dT/dt), and acoustic pressure levels, grounding every diagnostic recommendation in official OEM service manuals (Caterpillar, Komatsu, Perkins, SANY).
2. **Best Open-Source AI Project Overall**: MechMind bridges the physical-digital divide by marrying custom ESP32 IoT hardware with an end-to-end open-source AI software stack—100% open-weight model, open-source vector DB, open-source WhatsApp gateway, and MIT-licensed codebase.

---

## 📑 Table of Contents

- [Executive Overview](#executive-overview)
- [The Problem: The Diagnostic Divide in Emerging Fleets](#the-problem-the-diagnostic-divide-in-emerging-fleets)
- [System Architecture](#system-architecture)
- [How Google Gemma Powers MechMind Diagnostics](#how-google-gemma-powers-mechmind-diagnostics)
- [Prototype Device & Hardware Architecture](#prototype-device--hardware-architecture)
  - [Verified Hardware Specifications](#verified-hardware-specifications)
  - [Edge Signal Processing & Bandwidth Efficiency](#edge-signal-processing--bandwidth-efficiency)
- [Field Interfaces: Zero-Friction Delivery](#field-interfaces-zero-friction-delivery)
  - [1. WhatsApp Mobile Diagnostic Copilot](#1-whatsapp-mobile-diagnostic-copilot)
  - [2. Live Fleet Telemetry Console](#2-live-fleet-telemetry-console)
- [56-Case Blind Diagnostic Benchmark](#56-case-blind-diagnostic-benchmark)
- [Repository Structure](#repository-structure)
- [Quickstart: Running with Google Gemma](#quickstart-running-with-google-gemma)
- [Engineering Team](#engineering-team)
- [License](#license)

---

## Executive Overview

**MechMind AI** is an indigenous condition-monitoring and diagnostic intelligence ecosystem developed to eliminate catastrophic mechanical breakdowns in heavy industrial, construction, and agricultural equipment. 

By coupling an untethered, non-invasive magnetic edge sensor node with **Google Gemma 2** through a Retrieval-Augmented Generation (RAG) pipeline, MechMind captures real-time vibration harmonics, thermal anomalies, and acoustic distress signatures from operating machinery.

When mechanical distress occurs, MechMind translates raw sensor telemetry into evidence-grounded repair protocols delivered directly to technicians over **WhatsApp** (+234 701 029 9562) and an interactive **Live Fleet Web Dashboard**.

```
[ Heavy Machinery: Tractor / Excavator / Industrial Generator ]
                            |
           (Non-Invasive Magnetic Mount - 4x N52)
                            v
   +-------------------------------------------------------+
   |        MechMind Edge Sensor Node (NODE-001)           |
   |   • ADXL345 3-Axis Digital Accelerometer (±16g range) |
   |   • DS18B20 Waterproof Probe (-55°C to +125°C)        |
   |   • INMP441 I2S MEMS Microphone (16 kHz Audio Bus)    |
   |   • ESP32 Dual-Core (Edge FFT & Statistical Envelope) |
   |   • 18650 Li-Ion + TP4056 + MT3608 Boost Power Rail   |
   +-------------------------------------------------------+
                            |
           (Edge JSON Telemetry Burst every 2.0s)
                            v
   +-------------------------------------------------------+
   |                 FastAPI Backend Engine                |
   |   • Real-Time Telemetry Ingestion & In-Memory Stream  |
   |   • Dynamic ISO 10816 Severity Threshold Evaluation   |
   |   • Server-Sent Events (SSE) Live Broadcast           |
   +-------------------------------------------------------+
            |                                       |
            v                                       v
   +------------------+                   +--------------------+
   |  PostgreSQL 16   |                   |  ChromaDB Vector   |
   |  Time-Series DB  |                   |  1,200+ Pages OEM  |
   +------------------+                   |  Service Manuals   |
            |                             +--------------------+
            +-------------------+-------------------+
                                v
   +-------------------------------------------------------+
   |          Google Gemma 2 RAG Cognitive Engine          |
   |   • Model: Google Gemma 2 (gemma2:2b / gemma2:9b)     |
   |   • Semantic Context Synthesis via ChromaDB Embeddings|
   |   • Deterministic Safety Pinning (SPN 100 Emergency)  |
   |   • Structured Cause-Probability & Inspection Sequence|
   +-------------------------------------------------------+
            |                                       |
            v                                       v
   +--------------------+                 +--------------------+
   | Live Web Dashboard |                 | WhatsApp AI Bot    |
   | (Next.js / Vercel) |                 | (Baileys + Whisper)|
   | Real-time Waveforms|                 | Voice, Text, Photos|
   +--------------------+                 +--------------------+
```

---

## The Problem: The Diagnostic Divide in Emerging Fleets

1. **Legacy Machinery Populations**: Over 80% of earthmoving equipment and agricultural tractors operating in Nigeria and Sub-Saharan Africa are imported second-hand and lack onboard telematics.
2. **Proprietary Vendor Lock-in**: OEM diagnostic scan tools (e.g. Caterpillar ET, Komatsu Inline) cost between ₦4,000,000 and ₦8,500,000 with mandatory annual licensing subscriptions exceeding $1,200/year.
3. **The Reactive Breakdown Trap**: Without real-time telemetry, minor bearing misalignment, radiator clogging, or oil starvation goes unnoticed until total catastrophic seizure occurs, incurring millions of Naira in emergency overhaul costs and weeks of stranded downtime during critical planting or construction windows.

---

## How Google Gemma Powers MechMind Diagnostics

MechMind utilizes **Google Gemma 2** as its primary diagnostic brain:

* **High Parameter Efficiency**: Using `gemma2:2b` allows the entire diagnostic system to run locally on standard developer laptops and edge workstations without requiring expensive cloud GPUs or internet connectivity. For high-throughput servers, `gemma2:9b` delivers near-human expert reasoning.
* **Telemetry Grounding via RAG**: Instead of relying on general LLM memory, Gemma 2 is provided with indexed service documentation (Caterpillar, Komatsu, Perkins, Cummins) retrieved from ChromaDB based on real-time sensor anomalies.
* **Deterministic Safety Code Pinning**: To prevent AI hallucinations on dangerous equipment faults (e.g. loss of oil pressure or hydraulic failure), our pipeline deterministically hard-pins emergency shutdown protocols to **Rank 1** of Gemma’s retrieved context whenever critical SAE J1939 fault codes appear (such as SPN 100 FMI 1).
* **Multi-Modal Technician Input**: Field mechanics can send WhatsApp voice notes (transcribed via `faster-whisper`), text queries, or component photos; Gemma 2 generates step-by-step physical inspection checklists, torque specifications, and safety precautions.

---

## Prototype Device & Hardware Architecture

### Verified Hardware Specifications

The physical edge telemetry node (**NODE-001**) is assembled from locally accessible components packaged in a custom 3D-printed PETG enclosure embedded with four high-coercivity N52 neodymium magnets for tool-free attachment to engine blocks and pump casings:

| Subsystem | Component & Specification | Role in MechMind |
| :--- | :--- | :--- |
| **Microcontroller** | ESP32-WROOM-32D, Dual-Core 240 MHz, 4 MB Flash | On-chip edge signal processing & Wi-Fi telemetry |
| **Vibration Sensor** | ADXL345 3-Axis Digital Accelerometer (GY-291) | ±16g measurement range, 13-bit (4 mg/LSB), 10,000g shock tolerance |
| **Temperature Sensor**| DS18B20 Waterproof 1-Wire Digital Probe | -55°C to +125°C, 12-bit (0.0625°C resolution) |
| **Acoustic Sensor** | INMP441 Omnidirectional MEMS Microphone | 16 kHz I2S digital audio bus, RMS sound-level envelope |
| **Energy Storage** | 18650 Li-ion 3.7V 2600 mAh Rechargeable Cell | ~18 hours continuous active burst, up to 5 days duty-cycled |
| **Power Management** | TP4056 Linear Charger + DW01A Protection + MT3608 Boost | Regulated 5V rail to ESP32 VIN |
| **Enclosure** | 3D-Printed PETG + 4 × N52 Neodymium Magnets | Rapid, non-invasive mounting with zero machine drilling |

### Edge Signal Processing & Bandwidth Efficiency

To operate reliably over weak rural 2G/3G networks, MechMind extracts statistical indicators directly on the ESP32 before transmission:
* **Raw 200 Hz Tri-Axial Vibration**: $200\text{ Hz} \times 3\text{ axes} \times 2\text{ bytes} = 1,200\text{ bytes/s}$ ($2,400\text{ B}$ per 2s window).
* **Raw 16 kHz Audio**: $16,000\text{ samples/s} \times 2\text{ bytes} = 32,000\text{ bytes/s}$.
* **MechMind Telemetry Burst**: Compact JSON feature payload ($<380\text{ bytes}$ every 2.0s = $\sim 190\text{ bytes/s}$).
* **Net Bandwidth Reduction**: **84.2% reduction** against raw vibration streaming, and **>99.4% reduction** against raw audio streaming.

---

## Field Interfaces: Zero-Friction Delivery

### 1. WhatsApp Mobile Diagnostic Copilot
* **Demonstration Line**: `+234 701 029 9562`
* **Technologies**: Baileys WebSockets WhatsApp Framework + faster-whisper local STT + Google Gemma 2.
* **Why WhatsApp?**: In African industrial environments, WhatsApp is universal. Technicians wearing greasy gloves can send voice notes in English, Hausa, or Yoruba, ask questions, and receive actionable repair steps with torque specifications.

### 2. Live Fleet Telemetry Console
* **Public Dashboard**: [https://mechmind-ng.vercel.app](https://mechmind-ng.vercel.app)
* **Local Dashboard**: `http://localhost:8080`
* **Features**:
  * Real-time 3-axis kinematic vibration tracking (X, Y, Z acceleration waveforms).
  * Acoustic decibel pressure meter and thermal rate-of-rise trend monitoring.
  * Multi-asset switching (CAT Excavators, SANY Excavators, Farm Tractors, Diesel Generators).
  * Dynamic Machine Health Score index (0% - 100%) with automated status flags (Normal, Caution, Critical).

---

## 56-Case Blind Diagnostic Benchmark

Evaluated across 56 documented equipment failure scenarios constructed from official Caterpillar, Komatsu, and XCMG service manuals:

| Subsystem | Cases | Correct | Accuracy | Failure Modes Evaluated |
| :--- | :---: | :---: | :---: | :--- |
| **Hydraulic System** | 18 | 14 | 77.8% | Main relief valve bypass, cavitation, cylinder seal bypass, spool sticking |
| **Engine & Cooling** | 16 | 13 | 81.3% | Thermostat stuck closed, radiator clogging, boost leak, injector misfire |
| **Electrical & Charging** | 12 | 9 | 75.0% | Alternator diode failure, solenoid resistance, floating ground, sulfation |
| **Powertrain & Mechanical**| 10 | 6 | 60.0% | Final-drive bearing wear, coupling misalignment, track looseness |
| **OVERALL BENCHMARK** | **56** | **42** | **75.0%** | **Median Inference: 65.1s \| End-to-End WhatsApp: 84.2s** |

*Post-intervention Safety Compliance: **0.0% safety-critical hallucinations** across all 56 verified cases following deterministic code pinning.*

---

## Repository Structure

```
mechmind-ai/
├── backend/                        # FastAPI REST & Ingestion Backend
│   ├── main.py                     # API entrypoint, SSE streaming, route definitions
│   ├── rag_engine.py               # Google Gemma 2 RAG engine & ChromaDB interface
│   ├── requirements.txt            # Python dependencies (FastAPI, Ollama, ChromaDB, etc.)
│   ├── datasets/                   # AI4I 2020 & C-MAPSS dataset loaders
│   ├── eval/                       # 56-case diagnostic benchmarking harness & test sets
│   ├── manuals/                    # OEM service manual extractors & knowledge parsers
│   └── knowledge/                  # Indexed technical service chunks
│
├── firmware/                       # ESP32 Physical Edge Node Firmware
│   └── mechmind_node/
│       └── mechmind_node.ino       # FreeRTOS tasks, ADXL345 I2C, DS18B20, INMP441 I2S
│
├── dashboard/                      # Next.js / Static Live Telemetry Web Console
│   ├── index.html                  # Standalone live telemetry dashboard
│   ├── app.js                      # Real-time Chart.js kinematic waveform visualizer
│   └── style.css                   # Industrial dashboard theme
│
├── whatsapp-bot/                   # WhatsApp Field Assistant Gateway
│   ├── index.js                    # Baileys WhatsApp client & message dispatcher
│   └── package.json                # Node.js dependencies
│
├── docs/                           # Official Technical Dossiers & Proposals
│   ├── MechMind_AI_Project_Synopsis_AGRA_SMEDAN.pdf # AGRA-SMEDAN Agri-Tech Dossier
│   ├── MechMind_AI_Project_Synopsis_NAP2026.pdf     # National Automation Prize Dossier
│   ├── MechMind_AI_Pitch_Deck.pdf  # Executive & Competition Pitch Deck
│   ├── MechMind_AI_Prototype.jpg   # Physical prototype photograph
│   └── Sensor_Node_Assembly_Diagram.jpg # Complete wiring & electrical schematic
│
├── docker-compose.yml              # PostgreSQL 16 & ChromaDB container orchestration
├── LICENSE                         # Open-source MIT License
└── README.md                       # Master project overview & MLH Hack Day guide
```

---

## Quickstart: Running with Google Gemma

### 1. Prerequisites
- Python 3.10 or 3.11
- [Ollama](https://ollama.com/) installed on your machine
- Node.js 18+ (optional, for WhatsApp bot)

### 2. Pull Google Gemma 2
```bash
ollama pull gemma2:2b
# Or for higher reasoning capacity on GPU:
# ollama pull gemma2:9b
```

### 3. Launch Backend & Dashboard
```bash
cd backend
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8080
```
Open **`http://localhost:8080`** in your browser to interact with the live dashboard!

### 4. Optional: Run WhatsApp Field Bot
```bash
cd ../whatsapp-bot
npm install
node index.js
```
Scan the terminal QR code with WhatsApp to link the diagnostic assistant.

---

## Engineering Team

* **Oni Mujeeb Ramadan** — Product Operations & Field Lead (Lagos State University, Civil Engineering)  
  *Directs field test validation, technician workflow integration, and agricultural mechanization outreach.*
* **Mubarak Raji Babatunde** — AI & Software Lead (Lagos State University, Civil Engineering)  
  *Directs Google Gemma 2 RAG architecture, FastAPI backend, SSE stream, and WhatsApp gateway.*
* **Olawale Oladele** — Hardware & Embedded Systems Lead (Lagos State University, Mechanical Engineering)  
  *Directs ESP32 firmware, ADXL345/INMP441 sensor integration, PCB design, and 3D CAD enclosure.*

---

## License

This project is licensed under the open-source **MIT License** — see the [LICENSE](LICENSE) file for details. Built with ❤️ for the **MLH Hacktoberfest Hack Day 2026**.
