"""
Generate a realistic multi-page OEM Service Manual PDF for SANY SY215C Hydraulic Excavator
Includes:
- Hydraulic circuit specifications & pressure relief settings
- Cylinder head bolt torque tables with part numbers
- SAE J1939 Diagnostic Fault Code troubleshooting trees
"""

import os
import fitz  # PyMuPDF

def create_sample_manual():
    manuals_dir = os.path.dirname(os.path.abspath(__file__))
    out_pdf_path = os.path.join(manuals_dir, "sany_sy215c_service_manual.pdf")
    
    doc = fitz.open()

    # --- Page 1: Cover & General Specifications ---
    p1 = doc.new_page(width=595, height=842) # A4
    p1.insert_text((50, 80), "SANY HEAVY INDUSTRY CO., LTD.", fontsize=14, fontname="helv", color=(0.2, 0.2, 0.2))
    p1.insert_text((50, 120), "SHOP SERVICE MANUAL: SANY SY215C HYDRAULIC EXCAVATOR", fontsize=18, fontname="helv", color=(0, 0, 0))
    p1.insert_text((50, 150), "Document ID: SE-SY215C-HYD-2024 | Revision: 4.2", fontsize=11, fontname="helv", color=(0.3, 0.3, 0.3))
    
    body_p1 = """
CHAPTER 1: GENERAL MACHINE SPECIFICATIONS & SAFETY GUIDELINES

1.1 General Description
The SANY SY215C is a 21.5-metric-ton crawler excavator powered by a Cummins QSB6.7 inline-6 turbocharged diesel engine producing 128 kW (172 hp) at 2000 RPM. The machine features a positive flow hydraulic control system with Kawasaki tandem axial piston variable displacement pumps.

Operating Weight: 21,900 kg
Standard Bucket Capacity: 0.93 m3
Engine Model: Cummins QSB6.7-C170 (Tier 3 / Tier 4 interim)
Hydraulic System Operating Pressure: 34.3 MPa (343 bar)
Travel Speed (High/Low): 5.4 / 3.4 km/h
Swing Speed: 11.0 RPM
Fuel Tank Capacity: 340 Liters
Hydraulic Oil Tank Capacity: 240 Liters (Full System: 310 Liters)

SAFETY WARNING:
Before servicing any hydraulic lines or accumulator circuits, lower all work equipment to the ground, stop the engine, turn the starter key to ON, and cycle control levers in all directions to release residual hydraulic pilot pressure.
"""
    p1.insert_textbox(fitz.Rect(50, 180, 545, 780), body_p1, fontsize=10.5, fontname="helv")

    # --- Page 2: Hydraulic System & Relief Valve Specifications (With Table) ---
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text((50, 60), "SECTION 2: HYDRAULIC SYSTEM TROUBLESHOOTING & PRESSURE SETTINGS", fontsize=14, fontname="helv")
    
    body_p2_text = """
2.1 Main Pump & Pressure Relief Diagnostics
The hydraulic system uses twin variable displacement axial piston pumps (Pump 1 & Pump 2) providing a maximum rated flow of 2 x 222 L/min.

SYMPTOM: BOOM CYLINDER DRIFT OR WEAK DIGGING FORCE
When the boom cylinder drifts downward under static load exceeding 50 mm in 15 minutes, perform the following inspection sequence:
1. Connect a 0-600 bar calibrated digital pressure gauge to Pilot Check Port MP1.
2. Warm the hydraulic oil to 50C - 60C (ISO VG 46 high VI anti-wear oil).
3. Measure Main Relief Valve (MRV) cracking pressure at engine high idle (2000 RPM).
4. If pressure is below 31.5 MPa (315 bar), adjust pilot relief spring shim or replace valve cartridge P/N 60032918.
5. If MRV pressure is normal (34.3 MPa) but boom drifts, inspect boom holding valve spool for contamination or worn check seal P/N B210780000045.
"""
    p2.insert_textbox(fitz.Rect(50, 80, 545, 300), body_p2_text, fontsize=10, fontname="helv")
    
    # Insert Table on Page 2
    p2.insert_text((50, 310), "SPECIFICATION TABLE 2.1: HYDRAULIC PRESSURE & TORQUE RATINGS", fontsize=11, fontname="helv")
    
    # We draw an aligned table grid and text
    table_rect = fitz.Rect(50, 330, 545, 520)
    p2.draw_rect(table_rect, color=(0, 0, 0), width=1)
    
    # Headers
    p2.draw_line(fitz.Point(50, 360), fitz.Point(545, 360), color=(0,0,0), width=1)
    p2.insert_text((55, 350), "Component / Test Point", fontsize=9.5, fontname="helv")
    p2.insert_text((220, 350), "Standard Spec", fontsize=9.5, fontname="helv")
    p2.insert_text((340, 350), "Tolerance Limit", fontsize=9.5, fontname="helv")
    p2.insert_text((440, 350), "Part Number / Notes", fontsize=9.5, fontname="helv")
    
    rows = [
        ("Main Relief Valve (Normal)", "34.3 MPa (343 bar)", "33.5 - 35.0 MPa", "Valve Cartridge: 60032918"),
        ("Power Boost Pressure", "37.3 MPa (373 bar)", "36.5 - 38.0 MPa", "Active 8 sec duration"),
        ("Pilot System Pressure", "3.9 MPa (39 bar)", "3.7 - 4.2 MPa", "Pilot Relief: 60114920"),
        ("Boom Cylinder Holding Valve", "36.8 MPa (368 bar)", "35.5 - 37.5 MPa", "Seal Kit: B210780000045"),
        ("Swing Motor Relief Pressure", "27.5 MPa (275 bar)", "26.5 - 28.5 MPa", "Swing Brake Valve: 60081234"),
        ("Pump Flange Mounting Bolts", "240 Nm (177 lbf-ft)", "+/- 15 Nm", "M16 Class 10.9 (Torque Spec)"),
        ("Main Control Valve Tie Rods", "98 Nm (72 lbf-ft)", "+/- 5 Nm", "M12 Grade 8.8 (Torque Spec)"),
    ]
    
    y = 385
    for r in rows:
        p2.draw_line(fitz.Point(50, y + 5), fitz.Point(545, y + 5), color=(0.7,0.7,0.7), width=0.5)
        p2.insert_text((55, y), r[0], fontsize=8.5, fontname="helv")
        p2.insert_text((220, y), r[1], fontsize=8.5, fontname="helv")
        p2.insert_text((340, y), r[2], fontsize=8.5, fontname="helv")
        p2.insert_text((440, y), r[3], fontsize=8.5, fontname="helv")
        y += 22

    # --- Page 3: Diesel Powertrain & J1939 Diagnostic Trouble Codes ---
    p3 = doc.new_page(width=595, height=842)
    p3.insert_text((50, 60), "SECTION 3: ENGINE DIAGNOSTICS & SAE J1939 FAULT CODES", fontsize=14, fontname="helv")
    
    body_p3 = """
3.1 Electronic Engine Controller Diagnostics
The Cummins QSB6.7 ECM communicates with the machine display via SAE J1939 CAN bus network at 250 kbps baud rate.

SPN 110 FMI 0: ENGINE COOLANT TEMPERATURE CRITICALLY HIGH
- Threshold: Engine coolant temperature exceeds 108C (226F) for > 10 seconds.
- Probable Root Causes:
  1. Radiator cooling pack clogged with dust/debris.
  2. Thermostat stuck in closed position (P/N 5292712).
  3. Water pump impeller slippage or serpentine belt tensioner failure (P/N 3976831).
  4. Viscous fan clutch failure or low coolant level.
- Corrective Repair Steps:
  1. Clean radiator cooling fins using low-pressure compressed air (< 0.2 MPa).
  2. Inspect drive belt tension; ensure automatic belt tensioner pointer is within green zone.
  3. Replace thermostat assembly (cracking temp: 82C, full open: 95C).
  4. Tighten water pump housing bolts to 24 Nm.

SPN 100 FMI 1: ENGINE OIL PRESSURE CRITICALLY LOW
- Threshold: Engine oil pressure drops below 0.8 bar (12 PSI) at low idle or 2.1 bar at high idle.
- Probable Root Causes:
  1. Low engine oil level or incorrect viscosity grade (use CI-4 / CK-4 15W-40).
  2. Oil filter bypass valve jammed open (Filter P/N LF16015).
  3. Main crankshaft bearing excessive clearance.
- Corrective Repair Steps:
  1. Shut down engine immediately to prevent catastrophic crankshaft seizure.
  2. Inspect oil level on dipstick; check for fuel dilution (smell or elevated level).
  3. Replace lube oil filter element LF16015, torque to 35 Nm.

SPN 651 FMI 5: INJECTOR CYLINDER #1 CURRENT BELOW NORMAL / OPEN CIRCUIT
- Threshold: Open circuit detected on Common Rail Injector Cylinder #1 wiring harness.
- Corrective Repair Steps:
  1. Measure injector solenoid resistance with digital multimeter: specification is 0.2 to 0.5 ohms at 20C.
  2. Inspect engine wiring harness connector ECM pin J2-14 for moisture or pin corrosion.
  3. If injector resistance is > 1.0 ohm, replace common rail injector P/N 4988830.
"""
    p3.insert_textbox(fitz.Rect(50, 80, 545, 780), body_p3, fontsize=9.5, fontname="helv")

    # Save to disk
    doc.save(out_pdf_path)
    doc.close()
    print(f"Generated OEM Service Manual PDF: {out_pdf_path}")
    return out_pdf_path

if __name__ == "__main__":
    create_sample_manual()
