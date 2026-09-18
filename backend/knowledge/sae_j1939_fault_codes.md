# SAE J1939 Diagnostic Trouble Codes (DTC) Reference Guide
## Heavy Construction Machinery & Commercial Diesel Powertrains

### Overview of J1939 Format
SAE J1939 DTCs consist of:
- **SPN (Suspect Parameter Number)**: Indicates the subsystem or component.
- **FMI (Failure Mode Identifier)**: Identifies the type of failure.
  - FMI 0: Data valid but above normal operational range (most severe level)
  - FMI 1: Data valid but below normal operational range (most severe level)
  - FMI 2: Data erratic, intermittent, or incorrect
  - FMI 3: Voltage above normal or shorted to high source
  - FMI 4: Voltage below normal or shorted to low source
  - FMI 5: Current below normal or open circuit
  - FMI 6: Current above normal or grounded circuit
  - FMI 7: Mechanical system not responding or out of adjustment
  - FMI 8: Abnormal frequency or pulse width or period
  - FMI 9: Abnormal update rate
  - FMI 10: Abnormal rate of change
  - FMI 11: Root cause not known
  - FMI 12: Bad intelligent device or component
  - FMI 13: Out of calibration
  - FMI 14: Special instructions
  - FMI 15: Data valid but above normal operating range (least severe level)
  - FMI 16: Data valid but above normal operating range (moderately severe level)
  - FMI 17: Data valid but below normal operating range (least severe level)
  - FMI 18: Data valid but below normal operating range (moderately severe level)
  - FMI 19: Received network data in error

---

### Critical Fault Codes and Field Procedures

#### SPN 100: Engine Oil Pressure
- **SPN 100 FMI 1 / FMI 18 (Engine Oil Pressure Extremely Low)**:
  - *Symptom*: Engine oil pressure gauge drops below 100 kPa (14.5 psi) at rated speed or below 60 kPa at idle.
  - *Probable Causes*: Low engine oil sump level, worn oil pump gerotor gears, stuck-open pressure relief valve in oil pump, severe oil dilution from diesel fuel leaking past injector O-rings, blocked suction oil pickup strainer.
  - *Immediate Action*: Shut down engine immediately. Check oil dipstick for level and smell of diesel fuel. If oil is milky, coolant has breached head gasket or oil cooler. Do not restart until root cause is identified to avoid crankshaft bearing seizure.

#### SPN 110: Engine Coolant Temperature
- **SPN 110 FMI 0 / FMI 16 (Engine Coolant Overheating)**:
  - *Symptom*: Coolant temperature exceeds 103°C (warning) or 108°C (critical de-rate / shutdown).
  - *Probable Causes*: Radiator core clogged with construction dust/mud, viscous fan clutch slipping or hydraulic fan drive motor low flow, thermostat stuck closed, water pump belt slipping or impeller eroded, low coolant level from external hose leak.
  - *Immediate Action*: Reduce engine speed to low idle. Do not shut off immediately if boiling (allow fan to cool engine to prevent cylinder head warpage). Spray radiator with low-pressure air or water from clean side. Never remove radiator cap while system is under pressure.

#### SPN 102: Engine Turbocharger Boost Pressure
- **SPN 102 FMI 18 (Low Boost Pressure / Underboost)**:
  - *Symptom*: Heavy black smoke under load, sluggish acceleration, lack of hydraulic digging power.
  - *Probable Causes*: Charge air cooler (CAC) hose split or clamp loose, wastegate actuator stuck open, turbocharger compressor wheel damaged by debris, exhaust manifold gasket blowing.
  - *Inspection*: Check all CAC silicone boots between turbo, intercooler, and intake manifold with soapy water while engine is revved. Inspect turbo shaft for radial and axial play.

#### SPN 157: Engine Fuel Rail 1 Pressure
- **SPN 157 FMI 0 (Fuel Rail Over-Pressure)**:
  - *Symptom*: Engine knock, high-pitched combustion sound, limp-home mode.
  - *Probable Causes*: Faulty fuel metering unit / Suction Control Valve (SCV) on high-pressure pump, clogged fuel return line back to tank.
- **SPN 157 FMI 1 / FMI 18 (Fuel Rail Pressure Below Target)**:
  - *Symptom*: Engine cranks but will not start, or cuts out during heavy bucket breakout load.
  - *Probable Causes*: Primary/secondary fuel filter plugged with wax or asphaltines, air ingress in low-pressure suction line, excessive fuel back-leak from worn common rail injectors, pressure relief valve leaking to return.
  - *Inspection*: Perform injector fuel leak-off test. Verify rail pressure reaches minimum 250-300 bar during cranking.

#### SPN 639: J1939 CAN Network Communication Failure
- **SPN 639 FMI 2 (CAN Bus Off / Data Intermittent)**:
  - *Symptom*: Instrument cluster gauges flicker, throttle dial unresponsive, machine locked in limp mode.
  - *Probable Causes*: CAN_H and CAN_L terminating resistors damaged (normal resistance across pin C and D of Deutsch connector is 60 ohms with battery isolated, 120 ohms if one resistor failed), harness rubbed through to chassis ground, water ingress in ECM connector.
  - *Inspection*: Measure resistance between CAN-High (yellow) and CAN-Low (green) with battery disconnect switch OPEN. Expected: 60 ohms (+/- 3 ohms).
