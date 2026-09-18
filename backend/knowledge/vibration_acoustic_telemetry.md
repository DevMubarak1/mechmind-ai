# Telemetry Vibration and Acoustic Diagnostic Signatures
## Sensors: ADXL345 3-Axis Accelerometer & INMP441 MEMS Digital Microphone

### 1. Vibration Analysis Thresholds (ADXL345 Calibration)
Vibration magnitude is calculated from tri-axial acceleration vectors:
$$\text{Magnitude } g = \sqrt{X^2 + Y^2 + Z^2}$$

- **Operational Health Bands**:
  - **Normal Operating Range (< 0.45g RMS)**: Typical baseline for well-balanced hydraulic pumps, diesel engines on vibration dampers, and smooth swing reduction gearboxes.
  - **Elevated Warning Band (0.45g to 1.10g RMS)**: Indicates developing mechanical anomaly:
    * Loose structural mounting bolts or worn engine/pump elastomeric shock mounts.
    * Minor hydraulic flow pulsation or early stage bearing surface wear.
    * Inspect torque on all bracket fasteners, drive coupling rubbers, and cooling fan blades.
  - **Severe / Critical Alert (> 1.20g RMS)**: Imminent mechanical failure:
    * Hydraulic pump piston shoe separation or valve plate seizure.
    * Severe gear tooth spalling or chipped gear in swing/travel final drive reduction.
    * Broken engine mounting bracket or catastrophic unbalance in cooling fan rotor.
    * Action: Immediate de-rate or shutdown to prevent total structural disintegration.

---

### 2. Frequency Spectral Patterns (FFT Peak Analysis)
- **1X RPM (Rotational Fundamental Frequency)**:
  - *Indication*: Dynamic mass unbalance (e.g. mud caked on radiator fan blade, bent drive shaft).
- **2X RPM**:
  - *Indication*: Shaft angular or parallel misalignment between engine flywheel and hydraulic main pump drive coupling.
- **High Frequency Broadband Noise (> 1500 Hz)**:
  - *Indication*: Bearing race micro-spalling (Ball Pass Frequency Outer Race BPFO / Inner Race BPFI) or active pump cavitation bubbles collapsing against casing walls.

---

### 3. Acoustic Diagnostic Signatures (INMP441 Sound Sensor)
- **Baseline Ambient Construction Site Noise**: 65 dB to 78 dB SPL.
- **Normal Machine Operating Sound**: 80 dB to 86 dB SPL at operator station.
- **Acoustic Warning Thresholds**:
  - **Acoustic Level > 92 dB SPL Continuous**: Indicates structural resonance, exhaust manifold blow-by, or dry gear mesh.
  - **Acoustic Level > 98 dB SPL Peak**: Indicates severe hydraulic cavitation, high-pressure relief valve chattering, or turbocharger compressor surge.
- **Acoustic Signature Classification**:
  1. *High-Pitched Whine / Shrill Tone*:
     - Characteristic of hydraulic pump cavitation or alternator diode ripple / bearing seizure.
  2. *Low-Frequency Heavy Rhythmic Thump*:
     - Characteristic of crankshaft main or connecting rod bearing knock (frequency matches engine speed / 2 on 4-stroke diesels).
  3. *Hissing Sound*:
     - Charge air cooler boost leak, pneumatic brake line fitting leak, or hydraulic pilot check valve bypass leak.
  4. *Intermittent Clicking / Ticking*:
     - Excessive valve lash clearance (tappet noise), or injector solenoid mechanical sticking.
