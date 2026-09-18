"""
========================================================================================
MechMind AI - SAE J1939 Fault Code Dictionary & ChromaDB Ingestion Adapter
========================================================================================

PURPOSE:
--------
Provides a comprehensive dictionary of SAE J1939 Suspect Parameter Numbers (SPNs) and
Failure Mode Identifiers (FMIs) tailored for heavy construction machinery (excavators,
wheel loaders, bulldozers - SANY, XCMG, Shantui, Caterpillar, Komatsu).

NOTE ON ARCHITECTURE:
---------------------
THIS DATASET IS INGESTED DIRECTLY INTO CHROMADB VECTOR STORE FOR THE RAG ENGINE.
When a mechanic or operator messages MechMind AI via WhatsApp with any fault code
(e.g., "SPN 110 FMI 0" or "engine code 100 1"), this dictionary allows ChromaDB vector
similarity search to immediately resolve the code into:
  1. Plain-English component identity
  2. Failure severity and operational impact (derate / immediate shutdown)
  3. Likely root causes (mechanical, hydraulic, electrical)
  4. Step-by-step diagnostic and remediation checklist
========================================================================================
"""

import sys
import os
from typing import Dict, List, Any, Optional

# Add parent directory to path so we can import ingestion modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ingestion.chroma_storage import ChromaStorage

# ======================================================================================
# 1. SAE J1939 Standard Failure Mode Identifiers (FMI 0 - 31)
# ======================================================================================
J1939_FMI_DEFINITIONS: Dict[int, Dict[str, str]] = {
    0: {
        "name": "Data Valid Above Normal Operational Range (Most Severe Level)",
        "meaning": "The sensor reading is valid but has exceeded the maximum critical safety threshold. Imminent damage or shutdown required."
    },
    1: {
        "name": "Data Valid Below Normal Operational Range (Most Severe Level)",
        "meaning": "The sensor reading is valid but has fallen below the minimum critical safety threshold. Risk of mechanical starvation or seizure."
    },
    2: {
        "name": "Data Erratic, Intermittent, or Incorrect",
        "meaning": "The signal fluctuates wildly or conflicts with other redundant sensors. Often caused by loose connectors, damaged harness, or sensor drift."
    },
    3: {
        "name": "Voltage Above Normal or Shorted to High Source",
        "meaning": "Sensor signal wire is shorted to battery positive (+12V/+24V) or open circuit with internal pull-up."
    },
    4: {
        "name": "Voltage Below Normal or Shorted to Low Source",
        "meaning": "Sensor signal wire is shorted to chassis ground or broken circuit."
    },
    5: {
        "name": "Current Below Normal or Open Circuit",
        "meaning": "Actuator or solenoid circuit is broken, disconnected, or high resistance."
    },
    6: {
        "name": "Current Above Normal or Grounded Circuit",
        "meaning": "Actuator or solenoid coil has shorted turns or short to ground."
    },
    7: {
        "name": "Mechanical System Not Responding or Out of Adjustment",
        "meaning": "ECU issued an actuation command (e.g. spool shift, wastegate, EGR), but position feedback did not change."
    },
    8: {
        "name": "Abnormal Frequency, Pulse Width, or Period",
        "meaning": "PWM or frequency signal (speed sensor, hall effect) is outside allowable time limits."
    },
    9: {
        "name": "Abnormal Update Rate",
        "meaning": "CAN bus communication timeout. Expected periodic CAN message stopped arriving from another controller."
    },
    10: {
        "name": "Abnormal Rate of Change",
        "meaning": "Physical parameter changed faster than physically possible (e.g. temp jumping 40°C in 10ms, indicating intermittent wire contact)."
    },
    11: {
        "name": "Root Cause Not Known",
        "meaning": "Failure mode cannot be isolated by ECU onboard diagnostics."
    },
    12: {
        "name": "Bad Intelligent Device or Component",
        "meaning": "Internal microprocessor, EEPROM, or internal RAM fault inside the smart sensor or module."
    },
    13: {
        "name": "Out of Calibration",
        "meaning": "Sensor requires zero-point re-calibration or mechanical end-stop relearn."
    },
    14: {
        "name": "Special Instructions",
        "meaning": "Manufacturer-specific fault condition requiring OEM service tool."
    },
    15: {
        "name": "Data Valid Above Normal Range (Least Severe / Warning Level)",
        "meaning": "Parameter is moderately elevated above normal working range. Operator warning issued; performance not yet cut."
    },
    16: {
        "name": "Data Valid Above Normal Range (Moderately Severe Level)",
        "meaning": "Parameter high. Automatic engine derate or hydraulic flow cut active."
    },
    17: {
        "name": "Data Valid Below Normal Range (Least Severe / Warning Level)",
        "meaning": "Parameter moderately below normal range."
    },
    18: {
        "name": "Data Valid Below Normal Range (Moderately Severe Level)",
        "meaning": "Parameter low. System operating in degraded protection mode."
    },
    19: {
        "name": "Received Network Data in Error",
        "meaning": "Data received over J1939 CAN contains error flag or corrupted payload."
    },
    31: {
        "name": "Condition Exists",
        "meaning": "State-based event or non-numerical fault flag active."
    }
}

# ======================================================================================
# 2. Critical Heavy Machinery SPN Definitions
# ======================================================================================
J1939_SPN_DEFINITIONS: Dict[int, Dict[str, Any]] = {
    # --- Diesel Engine & Powertrain ---
    100: {
        "name": "Engine Oil Pressure",
        "system": "Powertrain / Lubrication",
        "normal_range": "2.5 to 5.5 bar (36 to 80 PSI) at working RPM; min 1.0 bar at low idle",
        "unit": "bar / PSI",
        "fmi_details": {
            1: {
                "symptom": "CRITICAL: Engine oil pressure dropped below minimum safety threshold (e.g., < 0.8 bar at idle, < 2.0 bar under load). Red STOP lamp on instrument cluster.",
                "derate": "Immediate automatic engine protection shutdown or severe 50% derate.",
                "root_causes": [
                    "Critically low engine oil level or severe oil sump leak",
                    "Oil pump pressure relief valve stuck open or pump drive gear sheared",
                    "Severely worn main/rod crankshaft bearings allowing excessive oil bleed-off",
                    "Severe oil dilution with diesel fuel (failed injector seal) dropping oil viscosity",
                    "Clogged oil pickup tube strainer screen in oil pan"
                ],
                "action": "1. SHUT DOWN ENGINE IMMEDIATELY. Do not restart.\n2. Check oil dipstick level and check for fuel/coolant odor on dipstick.\n3. Inspect oil filter housing and drain plug for external leakage.\n4. Connect manual mechanical pressure gauge to oil gallery test port to rule out faulty pressure sensor.\n5. If manual gauge confirms < 1.0 bar, drop oil pan and inspect pickup screen and rod bearings."
            },
            3: {
                "symptom": "Oil pressure gauge reads pegged at maximum scale (10 bar / 145 PSI) regardless of engine speed.",
                "derate": "None, but warning amber lamp illuminated.",
                "root_causes": ["Pressure sensor signal wire shorted to +5V or +24V harness", "Failed pressure sensor internal transducer"],
                "action": "1. Disconnect oil pressure sensor 3-pin connector.\n2. Measure voltage on harness signal pin; if 5V/24V present with sensor unplugged, trace harness for short.\n3. Verify 5V reference and ground integrity."
            },
            4: {
                "symptom": "Oil pressure gauge reads 0 bar continuously even when engine runs normally.",
                "derate": "Warning amber lamp, ECU may limit load.",
                "root_causes": ["Sensor signal wire shorted to ground or broken wire", "Defective oil pressure sender"],
                "action": "Check harness continuity between sensor Pin B and ECU Pin 42; inspect for pinch points near bell housing."
            }
        }
    },
    110: {
        "name": "Engine Coolant Temperature",
        "system": "Powertrain / Cooling",
        "normal_range": "82°C to 96°C (180°F to 205°F)",
        "unit": "°C / °F",
        "fmi_details": {
            0: {
                "symptom": "CRITICAL: Engine coolant temperature exceeds critical maximum threshold (> 108°C / 226°F). Steam escaping expansion tank, warning buzzer sounding.",
                "derate": "ECU applies 30% to 50% torque derate; auto-shutdown after 30 seconds if temperature continues to climb.",
                "root_causes": [
                    "Radiator core heavily plugged with dust, dirt, mud, or chaff",
                    "Coolant level low due to hose rupture, water pump weep hole leak, or cylinder head gasket failure",
                    "Thermostat stuck in closed position",
                    "Hydraulic radiator cooling fan motor failure or loose fan drive belt",
                    "Water pump impeller damaged or slipping on shaft"
                ],
                "action": "1. Throttle down to low idle immediately. DO NOT shut off engine instantly if coolant is circulating (idle helps cool down heads).\n2. CAUTION: DO NOT OPEN RADIATOR CAP WHILE HOT.\n3. Inspect radiator fins with flashlight; use compressed air or low-pressure water to blow out dust from inside out.\n4. Verify cooling fan is spinning at maximum commanded RPM.\n5. If upper radiator hose is boiling hot but lower hose is cold, replace thermostat."
            },
            15: {
                "symptom": "Coolant temperature moderately high (98°C - 105°C) during heavy trenching or uphill climb.",
                "derate": "Warning message on cluster; no torque derate yet.",
                "root_causes": ["Partial fin obstruction", "High ambient temperature combined with maximum continuous hydraulic relief load"],
                "action": "Reduce machine duty cycle; clean radiator and hydraulic oil cooler packs at next shift."
            },
            3: {
                "symptom": "Coolant temperature reading jumps to -40°C or +140°C intermittently.",
                "derate": "ECU defaults cooling fan to 100% full speed (fail-safe).",
                "root_causes": ["Sensor wiring open circuit or shorted to power", "Corroded sensor pins"],
                "action": "Inspect 2-pin coolant temp sensor connector on thermostat housing; measure thermistor resistance."
            }
        }
    },
    190: {
        "name": "Engine Speed (Crankshaft Position RPM)",
        "system": "Powertrain / Electrical",
        "normal_range": "800 RPM (low idle) to 2150 RPM (high idle / working)",
        "unit": "RPM",
        "fmi_details": {
            0: {
                "symptom": "CRITICAL: Engine overspeed detected (> 2450 RPM). Severe risk of valvetrain float, piston-to-valve collision.",
                "derate": "ECU cuts all fuel injection immediately.",
                "root_causes": [
                    "Operating down steep quarry slope in high gear without service brakes",
                    "Turbocharger oil seal failure allowing engine to run away on crankcase oil vapor",
                    "Stuck governor / fuel metering actuator"
                ],
                "action": "1. If engine is running away on oil vapor, choke air intake immediately with a flat board or CO2 extinguisher.\n2. Check turbocharger compressor housing for oil pooling.\n3. Inspect valvetrain and pushrods for bending."
            },
            2: {
                "symptom": "Engine cranks prolonged before starting, rough idle, sudden stalling under load.",
                "derate": "Engine running in backup mode using camshaft sensor only; torque restricted.",
                "root_causes": [
                    "Crankshaft position sensor magnetic tip fouled with metal shavings",
                    "Air gap between sensor face and flywheel tone wheel out of spec (> 1.2mm)",
                    "Loose sensor mounting bolt"
                ],
                "action": "1. Remove crankshaft speed sensor from flywheel housing.\n2. Clean ferrous debris from magnetic tip.\n3. Inspect tone wheel teeth for damage through mounting hole.\n4. Reinstall and torque mounting bolt to 10 Nm with threadlocker."
            }
        }
    },
    102: {
        "name": "Engine Turbocharger Boost Pressure",
        "system": "Powertrain / Air Intake",
        "normal_range": "1.2 to 2.4 bar (17 to 35 PSI) boost at full engine load",
        "unit": "bar / PSI",
        "fmi_details": {
            18: {
                "symptom": "Engine sluggish under digging load, black smoke from exhaust stack, inability to reach full hydraulic pump pressure.",
                "derate": "Torque reduced 20-30% due to smoke limitation map.",
                "root_causes": [
                    "Charge air cooler (CAC / intercooler) hose split or clamp blown off",
                    "Intercooler core cracked from machine vibration",
                    "Turbocharger wastegate stuck open or VGT actuator linkage binding",
                    "Heavy carbon buildup on variable geometry turbo vanes",
                    "Air filter primary and secondary elements choked with dust"
                ],
                "action": "1. Inspect all 3-inch rubber charge air hoses between turbo, intercooler, and intake manifold for splits or loose T-bolt clamps.\n2. Perform smoke pressure test on intercooler system at 1.5 bar.\n3. Inspect air filter differential pressure restriction indicator.\n4. Check wastegate actuator rod movement with hand vacuum/pressure pump."
            }
        }
    },
    157: {
        "name": "Engine Common Rail Fuel Pressure",
        "system": "Powertrain / Fuel Injection",
        "normal_range": "350 bar (idle) to 1800-2200 bar (full load)",
        "unit": "bar",
        "fmi_details": {
            1: {
                "symptom": "Engine stalls under digging load, hard starting, severe lack of power, rail pressure cannot reach target.",
                "derate": "Severe 40% torque derate; max RPM capped at 1500 RPM.",
                "root_causes": [
                    "Primary or secondary fuel filters plugged with paraffin, sediment, or water",
                    "High pressure fuel pump (HPFP) inlet metering valve (IMV/FCA) sticking",
                    "High-pressure rail pressure relief valve leaking fuel back to return line",
                    "One or more injectors has excessive high-pressure back-leakage",
                    "Low pressure lift pump supply pressure < 3.5 bar"
                ],
                "action": "1. Drain water separator bowl and replace primary (10 micron) and secondary (3 micron) fuel filters.\n2. Measure low-pressure supply to HPFP (must be >= 4.0 bar).\n3. Perform injector injector back-leakage quantity test (return flow must not exceed 25 ml/min per injector at idle).\n4. Check temperature of mechanical rail relief valve with infrared thermometer; if hot, valve is leaking."
            },
            0: {
                "symptom": "Engine knocks heavily, rail pressure spikes above 2000 bar at low loads.",
                "derate": "ECU trips fuel shutoff to prevent rail burst.",
                "root_causes": ["Fuel rail pressure sensor calibration drifted", "Inlet metering valve stuck wide open"],
                "action": "Replace rail pressure sensor; inspect IMV connector for water ingress."
            }
        }
    },
    3251: {
        "name": "Aftertreatment DPF Differential Pressure",
        "system": "Emissions / Aftertreatment",
        "normal_range": "0.5 to 4.5 kPa at idle; < 15 kPa at full exhaust flow",
        "unit": "kPa",
        "fmi_details": {
            0: {
                "symptom": "CRITICAL: Diesel Particulate Filter (DPF) soot loading exceeds 140%. DPF lamp flashing, exhaust backpressure high.",
                "derate": "Level 3 severe engine derate (50% power loss); park regeneration disabled for safety to prevent thermal runaway / fire.",
                "root_causes": [
                    "DPF substrate heavily loaded with soot due to frequent low-idle duty cycles without regeneration",
                    "Soot sensor / delta-P pressure sensor sensing pipes cracked or clogged with soot",
                    "Defective fuel doser / hydrocarbon injector failing to initiate active regeneration",
                    "Excessive oil ash accumulation from using non-CJ-4/CK-4 engine oil"
                ],
                "action": "1. DO NOT force stationary regen if delta-P is extreme (fire hazard).\n2. Remove DPF filter canister and send to thermal cleaning kiln / air pulse facility.\n3. Inspect delta-P steel lines for blockages with a soft wire.\n4. Verify DEF/AdBlue dosing system functionality."
            },
            2: {
                "symptom": "DPF delta-P reads zero or erratic regardless of throttle position.",
                "derate": "Warning lamp on.",
                "root_causes": ["Delta-P silicone hose melted, disconnected, or kinked"],
                "action": "Inspect high and low pressure sampling lines between exhaust pipe and differential sensor."
            }
        }
    },
    4364: {
        "name": "Aftertreatment 1 SCR Catalyst Conversion Efficiency",
        "system": "Emissions / SCR",
        "normal_range": "> 85% NOx reduction efficiency",
        "unit": "%",
        "fmi_details": {
            18: {
                "symptom": "NOx emissions high, SCR efficiency below allowable emissions standard. 4-hour countdown timer to 5 MPH crawl derate on operator display.",
                "derate": "Inducement derate: 25% torque cut initially, then maximum engine speed restricted to 1200 RPM after countdown.",
                "root_causes": [
                    "Poor quality or diluted DEF/AdBlue fluid (DEF concentration < 32.5% urea)",
                    "DEF dosing injector tip encrusted with white urea crystal deposits",
                    "Upstream or downstream NOx sensor reading out of calibration",
                    "Exhaust gas temperature too low for catalytic conversion (< 220°C)"
                ],
                "action": "1. Test DEF fluid with optical refractometer (must read exactly 32.5% +/- 0.7%).\n2. Remove DEF dosing unit from decomposition tube; clean urea crystallization with warm demineralized water (DO NOT use carb cleaner).\n3. Compare upstream and downstream NOx sensor PPM readings with service tool."
            }
        }
    },
    1761: {
        "name": "Aftertreatment 1 Diesel Exhaust Fluid (DEF) Tank Level",
        "system": "Emissions / DEF",
        "normal_range": "10% to 100% capacity",
        "unit": "%",
        "fmi_details": {
            1: {
                "symptom": "DEF tank empty (< 2%). DEF gauge flashes red, warning chime sounds.",
                "derate": "Operator inducement derate initiated within 30 minutes.",
                "root_causes": ["DEF tank depleted by operation", "Ultrasonic level sensor stuck or failed"],
                "action": "Refill DEF tank with clean ISO 22241 standard AdBlue / DEF. Cycle ignition key 3 times to clear inducement lock."
            }
        }
    },
    639: {
        "name": "J1939 Network #1 Primary CAN Bus Communication",
        "system": "Electrical / CAN Bus",
        "normal_range": "60 Ohms termination resistance across CAN-H and CAN-L",
        "unit": "Ohms / Baud",
        "fmi_details": {
            9: {
                "symptom": "CRITICAL: Multiple controllers offline. Instrument panel gauges frozen, excavator hydraulic pilot lock will not disengage, error code cascade.",
                "derate": "Machine placed in default limp-home mode; electro-hydraulic controls unresponsive.",
                "root_causes": [
                    "Can bus termination resistor failed (open circuit or missing 120 Ohm resistor at backbone end)",
                    "CAN-High (Yellow) or CAN-Low (Green) twisted pair wire pinched or rubbed through against chassis frame",
                    "Water intrusion into main bulkhead connector behind cab",
                    "One faulty node (e.g. GPS telematics unit or secondary controller) dragging CAN bus down"
                ],
                "action": "1. Turn key OFF and disconnect battery master disconnect switch.\n2. Connect multimeter to diagnostic 9-pin port Pins C (CAN-H) and D (CAN-L).\n3. Measure resistance: It MUST read 60 Ohms (+/- 3 Ohms). If it reads 120 Ohms, one terminating resistor is disconnected. If it reads 0-5 Ohms, CAN-H is shorted to CAN-L.\n4. Unplug modules one by one while monitoring resistance to isolate offending controller."
            }
        }
    },
    168: {
        "name": "Battery Potential / Power Input 1",
        "system": "Electrical / Charging",
        "normal_range": "24.0V to 28.4V (24V system) or 12.6V to 14.4V (12V system)",
        "unit": "Volts",
        "fmi_details": {
            1: {
                "symptom": "Engine cranks very slowly or clicks; electrical relays chatter; display resets during starting.",
                "derate": "ECU may disable high-amperage hydraulic solenoids.",
                "root_causes": [
                    "Alternator internal regulator failed or alternator drive belt loose",
                    "Batteries discharged, sulfated, or internal cell short",
                    "Severe corrosion on battery terminals or chassis ground strap"
                ],
                "action": "1. Measure battery voltage with engine running (must be 27.5V to 28.5V on 24V machines).\n2. Clean battery posts and clamp bolts with wire brush; apply dielectric grease.\n3. Inspect ground connection from battery negative to machine main frame."
            },
            0: {
                "symptom": "Battery voltage > 31.0V. Bulbs blowing, ECU overvoltage warning.",
                "derate": "ECU enters overvoltage protection.",
                "root_causes": ["Alternator internal voltage regulator blown / shorted"],
                "action": "Replace alternator immediately to prevent frying ECU and display electronics."
            }
        }
    },
    # --- Heavy Equipment Hydraulic System SPNs (OEM Proprietary mapped to J1939) ---
    520200: {
        "name": "Hydraulic Main Pump 1 Discharge Pressure",
        "system": "Hydraulics / Main Circuit",
        "normal_range": "30 to 45 bar (standby) / 320 to 350 bar (main relief under heavy digging)",
        "unit": "bar",
        "fmi_details": {
            1: {
                "symptom": "Boom and arm movements extremely slow and weak. Cannot lift loaded bucket or break tough clay.",
                "derate": "Hydraulic output restricted.",
                "root_causes": [
                    "Main relief valve pressure set too low or relief valve pilot poppet worn/cracked",
                    "Hydraulic pump regulator negative flow control (NFC) or positive flow control (PFC) pilot pressure stuck high",
                    "Main variable displacement axial piston pump barrel and valve plate severely scored",
                    "Suction strainer in hydraulic tank clogged with debris/sludge starving pump"
                ],
                "action": "1. Install 600 bar mechanical pressure gauge on Pump 1 test tap (M1 port).\n2. Stall boom up cylinder over relief and read gauge (should be 343 bar on SY215C / CAT 320).\n3. If pressure is low (< 250 bar), adjust main relief valve clockwise 1/4 turn. If pressure does not increase, inspect relief valve seat for metal debris.\n4. Take hydraulic oil sample and inspect for bronze/steel flake from pump piston slipper failure."
            }
        }
    },
    520202: {
        "name": "Hydraulic Oil Temperature",
        "system": "Hydraulics / Cooling",
        "normal_range": "50°C to 75°C (122°F to 167°F); max allowable 85°C",
        "unit": "°C",
        "fmi_details": {
            0: {
                "symptom": "CRITICAL: Hydraulic oil temperature exceeds 90°C (194°F). Hydraulic hoses softening, cylinder speed slow, seals deteriorating rapidly.",
                "derate": "Auto-derate on hydraulic pump flow to reduce heat generation.",
                "root_causes": [
                    "Hydraulic oil cooler radiator core packed with dirt/chaff",
                    "Oil cooler bypass check valve stuck open (oil bypassing cooler radiator)",
                    "Continuous high-pressure fluid relief caused by stuck auxiliary spool or cracked relief valve seat",
                    "Hydraulic oil level below sight glass minimum"
                ],
                "action": "1. Park machine on level ground with arm and bucket cylinders fully extended and lower boom to ground.\n2. Check oil level in sight glass.\n3. Wash hydraulic oil cooler matrix with low-pressure water.\n4. Use infrared thermal gun on cooler inlet vs outlet lines (temperature drop must be at least 8-12°C across cooler)."
            }
        }
    },
    520204: {
        "name": "Hydraulic Swing Parking Brake Solenoid Circuit",
        "system": "Hydraulics / Swing Drive",
        "normal_range": "18 to 24 Ohms coil resistance; releases brake at > 35 bar pilot pressure",
        "unit": "Ohms / bar",
        "fmi_details": {
            7: {
                "symptom": "Upper structure swing movement will not engage or groans loudly when swing joystick moved.",
                "derate": "Swing lock active.",
                "root_causes": [
                    "Swing brake mechanical friction discs seized or worn to metal",
                    "Swing brake release solenoid valve coil burned out or pilot line pressure low (< 25 bar)",
                    "Swing drive reduction gearbox dry / seized"
                ],
                "action": "1. Check swing lock switch in cabin.\n2. Measure pilot pressure to swing brake release port with 100 bar gauge (must be > 35 bar when swing pilot is commanded).\n3. Measure solenoid coil resistance (18-24 Ohms). Replace solenoid if open circuit."
            }
        }
    }
}

# ======================================================================================
# 3. Document Chunk Generator for ChromaDB Ingestion
# ======================================================================================
def generate_j1939_knowledge_chunks() -> List[Dict[str, Any]]:
    """
    Synthesizes each SPN and FMI into an authoritative diagnostic knowledge chunk
    formatted for dense semantic vector retrieval in ChromaDB.
    """
    chunks = []
    
    for spn, spn_data in J1939_SPN_DEFINITIONS.items():
        spn_name = spn_data["name"]
        system = spn_data["system"]
        normal_range = spn_data.get("normal_range", "Standard OEM range")
        
        # Build individual chunks for each specific SPN-FMI pair
        for fmi, fmi_data in spn_data.get("fmi_details", {}).items():
            fmi_meta = J1939_FMI_DEFINITIONS.get(fmi, {"name": f"FMI {fmi}", "meaning": "Standard failure mode"})
            fmi_name = fmi_meta["name"]
            fmi_meaning = fmi_meta["meaning"]
            
            chunk_title = f"SAE J1939 Fault Code: SPN {spn} FMI {fmi} - {spn_name} ({fmi_name})"
            
            root_causes_str = "\n".join([f"  - {rc}" for rc in fmi_data.get("root_causes", ["Component failure"])])
            
            content = f"""# {chunk_title}
**Standard**: SAE J1939 Heavy-Duty Diagnostics
**Suspect Parameter (SPN)**: {spn} - {spn_name}
**Failure Mode Identifier (FMI)**: {fmi} - {fmi_name}
**Machinery Subsystem**: {system}
**Normal Operating Range**: {normal_range}

## Failure Mode Description
{fmi_meaning}

## Symptoms & Operational Impact
{fmi_data.get("symptom", "Fault code active on machine cluster.")}
**Derate / Protection Mode**: {fmi_data.get("derate", "Standard ECU protection.")}

## Probable Root Causes
{root_causes_str}

## Step-by-Step Diagnostic & Mechanic Remediation
{fmi_data.get("action", "Follow OEM workshop service procedures.")}

## Common Keyword Triggers
SPN {spn} FMI {fmi}, Fault Code {spn}-{fmi}, DTC {spn}:{fmi}, {spn_name}, {system}, Heavy Equipment Troubleshooting.
"""
            chunk = {
                "id": f"j1939_spn_{spn}_fmi_{fmi}",
                "title": chunk_title,
                "text": content.strip(),
                "metadata": {
                    "source": "SAE J1939 Standard Code Dictionary",
                    "equipment_model": "Universal Heavy Equipment (SANY, XCMG, Shantui, CAT)",
                    "section_title": f"DTC Diagnostics: SPN {spn} FMI {fmi}",
                    "system": system,
                    "spn": int(spn),
                    "fmi": int(fmi),
                    "page_number": 1,
                    "dataset_type": "j1939_fault_code_dictionary"
                }
            }
            chunks.append(chunk)
            
    return chunks

# ======================================================================================
# 4. Ingestion & Retrieval API
# ======================================================================================
class J1939Adapter:
    """
    Adapter that indexes the J1939 dictionary into ChromaDB and provides
    fast plain-English code resolution.
    """
    def __init__(self):
        self.chroma = ChromaStorage()
        
    def ingest_to_chromadb(self) -> int:
        """
        Embeds and stores all J1939 codes into the ChromaDB knowledge collection.
        Returns the number of chunks ingested.
        """
        chunks = generate_j1939_knowledge_chunks()
        print(f"[*] Generated {len(chunks)} J1939 diagnostic code chunks.")
        
        print(f"[*] Upserting {len(chunks)} J1939 chunks into ChromaDB '{self.chroma.collection_name}'...")
        count = self.chroma.upsert_chunks(chunks=chunks)
        print(f"[+] Successfully indexed {count} SAE J1939 fault code entries into ChromaDB.")
        return count

    def lookup_code(self, spn: int, fmi: int) -> Optional[Dict[str, Any]]:
        """
        Direct memory lookup for exact SPN and FMI pairs without vector search.
        """
        spn_data = J1939_SPN_DEFINITIONS.get(spn)
        if not spn_data:
            return None
        fmi_data = spn_data.get("fmi_details", {}).get(fmi)
        fmi_meta = J1939_FMI_DEFINITIONS.get(fmi, {"name": f"FMI {fmi}", "meaning": "Unknown"})
        
        return {
            "spn": spn,
            "spn_name": spn_data["name"],
            "system": spn_data["system"],
            "normal_range": spn_data.get("normal_range"),
            "fmi": fmi,
            "fmi_name": fmi_meta["name"],
            "fmi_meaning": fmi_meta["meaning"],
            "symptom": fmi_data.get("symptom") if fmi_data else "No specific symptom text",
            "derate": fmi_data.get("derate") if fmi_data else "Unknown",
            "root_causes": fmi_data.get("root_causes") if fmi_data else [],
            "action": fmi_data.get("action") if fmi_data else "Refer to service manual"
        }

    def vector_search_code(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Runs vector similarity search against ChromaDB for a natural language query
        like 'SPN 110 FMI 0' or 'overheating coolant code'.
        """
        return self.chroma.query(query, top_k=n_results)

# ======================================================================================
# 5. CLI Execution
# ======================================================================================
if __name__ == "__main__":
    adapter = J1939Adapter()
    print("=================================================================")
    print(" MechMind AI - SAE J1939 Code Dictionary Adapter")
    print("=================================================================")
    
    # 1. Ingest all codes into ChromaDB
    ingested = adapter.ingest_to_chromadb()
    
    # 2. Test direct lookup
    test_spn, test_fmi = 110, 0
    print(f"\n[Test 1] Direct Memory Lookup: SPN {test_spn} FMI {test_fmi}")
    res = adapter.lookup_code(test_spn, test_fmi)
    if res:
        print(f"  Component: {res['spn_name']}")
        print(f"  Failure:   {res['fmi_name']}")
        print(f"  Derate:    {res['derate']}")
    
    # 3. Test vector retrieval from ChromaDB
    test_query = "What causes SPN 100 FMI 1 oil pressure fault?"
    print(f"\n[Test 2] Vector Retrieval: '{test_query}'")
    results = adapter.vector_search_code(test_query, n_results=1)
    for r in results:
        print(f"  Retrieved Chunk ID: {r['id']}")
        print(f"  Distance: {r.get('distance', 'N/A')}")
        print(f"  Title: {r['metadata'].get('section_title')}")
        snippet = r['text'][:200].replace('\n', ' ')
        print(f"  Snippet: {snippet}...")
    print("\n[+] SAE J1939 Adapter test completed successfully.")
