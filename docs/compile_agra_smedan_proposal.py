import os
import sys
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import win32com.client
import pythoncom

def set_cell_margins(cell, top=80, bottom=80, left=120, right=120):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_cell_shading(cell, color_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color_hex)
    tcPr.append(shd)

def create_agra_smedan_proposal():
    doc = docx.Document()
    
    # Page setup - A4
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)
        section.page_width = Inches(8.27)
        section.page_height = Inches(11.69)
        
        # Header / Footer
        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("AGRA–SMEDAN Youth Agri-Innovation Contest 2026 | Agri-Tech & Farm Mechanization")
        hrun.font.name = "Segoe UI"
        hrun.font.size = Pt(8)
        hrun.font.color.rgb = RGBColor(0, 89, 55) # AGRA Forest Green
        
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        frun = fp.add_run("MechMind AI — Edge Condition Monitoring & WhatsApp Diagnostics for Agricultural Machinery — Pullup Events / LASU")
        frun.font.name = "Segoe UI"
        frun.font.size = Pt(8)
        frun.font.color.rgb = RGBColor(100, 116, 139)

    # Styles
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(9.5)
    normal_style.font.color.rgb = RGBColor(30, 41, 59)
    normal_style.paragraph_format.line_spacing = 1.15
    normal_style.paragraph_format.space_after = Pt(3.5)

    # Title Block
    title_p = doc.add_paragraph()
    title_p.paragraph_format.space_before = Pt(0)
    title_p.paragraph_format.space_after = Pt(2)
    trun = title_p.add_run("MECHMIND AI")
    trun.font.name = "Segoe UI"
    trun.font.size = Pt(22)
    trun.font.bold = True
    trun.font.color.rgb = RGBColor(0, 89, 55) # Deep forest green

    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_after = Pt(8)
    srun = sub_p.add_run("Non-Invasive Edge Condition Monitoring & WhatsApp Diagnostic Intelligence for Nigerian Agricultural Machinery (Tractors, Harvesters & Grain Processing Mills)")
    srun.font.name = "Segoe UI"
    srun.font.size = Pt(11)
    srun.font.bold = True
    srun.font.color.rgb = RGBColor(234, 88, 12) # Energy Orange

    # Metadata Box Table
    meta_table = doc.add_table(rows=4, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_data = [
        ("Programme & Focus", "AGRA–SMEDAN Youth Agri-Innovation Contest 2026\nTarget Value Chains: Maize, Rice, Soybean, & Allied Agri-Food Mechanization"),
        ("Value Chain Impact", "Preventing tractor breakdowns during critical planting windows;\nMitigating combine harvester downtime and post-harvest grain losses."),
        ("Commercial Vehicle & Institution", "Pullup Events (CAC Registration: BN-9846744)\nIn partnership with Lagos State University (LASU), Lagos, Nigeria"),
        ("Youth Engineering Team (18–35)", "• Oni Mujeeb Ramadan — Product Operations & Field Lead (LASU Civil Eng.)\n• Mubarak Raji Babatunde — AI & Software Lead (LASU Civil Eng.)\n• Olawale Oladele — Hardware & Embedded Systems Lead (LASU Mech. Eng.)")
    ]
    for row_idx, (k, v) in enumerate(meta_data):
        row = meta_table.rows[row_idx]
        cell_k, cell_v = row.cells[0], row.cells[1]
        cell_k.width = Inches(2.2)
        cell_v.width = Inches(4.47)
        set_cell_margins(cell_k, 50, 50, 80, 80)
        set_cell_margins(cell_v, 50, 50, 80, 80)
        set_cell_shading(cell_k, "F0FDF4") # Subtle green tint
        set_cell_shading(cell_v, "FFFFFF")
        
        kp = cell_k.paragraphs[0]
        kp.paragraph_format.space_after = Pt(0)
        krun = kp.add_run(k)
        krun.font.name = "Segoe UI"
        krun.font.bold = True
        krun.font.size = Pt(8.5)
        krun.font.color.rgb = RGBColor(22, 101, 52)
        
        vp = cell_v.paragraphs[0]
        vp.paragraph_format.space_after = Pt(0)
        vrun = vp.add_run(v)
        vrun.font.name = "Segoe UI"
        vrun.font.size = Pt(8.5)
        vrun.font.color.rgb = RGBColor(15, 23, 42)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    def add_sec_heading(title):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(3)
        run = p.add_run(title)
        run.font.name = "Segoe UI"
        run.font.size = Pt(11.5)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0, 89, 55)
        return p

    def add_sub_heading(title):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(title)
        run.font.name = "Segoe UI"
        run.font.size = Pt(10)
        run.font.bold = True
        run.font.color.rgb = RGBColor(30, 41, 59)
        return p

    def add_body(text, bold_prefix=None):
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3.5)
        if bold_prefix:
            brun = p.add_run(bold_prefix)
            brun.font.bold = True
            brun.font.color.rgb = RGBColor(15, 23, 42)
        run = p.add_run(text)
        return p

    def add_bullet(text, bold_prefix=None):
        p = doc.add_paragraph(style='List Bullet')
        p.paragraph_format.space_after = Pt(2)
        if bold_prefix:
            brun = p.add_run(bold_prefix)
            brun.font.bold = True
            brun.font.color.rgb = RGBColor(15, 23, 42)
        run = p.add_run(text)
        return p

    # --- SECTION 1 ---
    add_sec_heading("1. Executive Summary")
    add_body("Nigeria’s agricultural productivity and food security rely heavily on a fleet of aging tractors, combine harvesters, irrigation pumps, and commercial agro-processing mills. Over 80% of these machines are legacy models (predominantly Massey Ferguson, Steyr, John Deere, and Fiat) that operate without continuous vibration, thermal, or acoustic monitoring. When these machines break down during time-critical planting windows or peak harvest periods, smallholder farmers face severe planting delays, crop rot, and post-harvest grain losses across the maize, rice, and soybean value chains.")
    add_body("MechMind AI is an affordable, indigenous condition-monitoring and diagnostic intelligence platform engineered specifically for the machinery Nigeria already owns. The platform combines a low-cost, non-invasive magnetic edge sensor node (NODE-001) with local signal processing, lightweight rural telemetry, a real-time fleet health dashboard, and a retrieval-augmented artificial intelligence diagnostic assistant accessible directly via WhatsApp (+234 701 029 9562).")
    add_body("The sensor node mounts externally to tractor engine blocks, variable-displacement hydraulic pump casings, and grain mill bearings without cutting factory wiring or modifying warranty systems. It extracts critical health indicators directly at the edge, reducing cellular data transmission by over 84% to operate seamlessly over weak 2G/3G rural networks. Frontline tractor drivers, cooperative managers, and rural mechanics interact with the system via WhatsApp using text, voice notes in local languages, and photographs of damaged parts.")
    add_body("The physical prototype has been assembled and field-validated on heavy diesel machinery under operating conditions. In a 56-case blind diagnostic benchmark covering hydraulic, powertrain, engine cooling, and electrical faults, MechMind achieved 75.0% root-cause accuracy, a 65.1-second median local LLM inference time, and an 84.2-second complete WhatsApp delivery turnaround. By delivering early warning indicators and actionable repair guidance, MechMind directly prevents catastrophic equipment seizures, reduces unplanned downtime by a targeted 50%–60%, and safeguards smallholder agricultural yields.")
    p_core = add_body("Keep Nigerian farm machinery running by making machine intelligence affordable and accessible on WhatsApp.", "Core Mission: ")
    p_core.runs[1].font.italic = True

    # --- SECTION 2 ---
    add_sec_heading("2. Problem Statement in Nigerian Agriculture")
    add_body("Agricultural mechanization is a vital prerequisite for national food security. However, Nigeria's smallholder grain producers face an acute equipment vulnerability: an extreme scarcity of operational machinery combined with frequent, catastrophic breakdowns of existing equipment.")
    add_body("1. Critical Time Windows: In rain-fed maize, rice, and soybean farming, land preparation and planting must take place within a narrow 3-to-4-week window following the onset of rains. A tractor breakdown during this period leaves 50 to 100 smallholders per tractor pool unable to plant on time, causing estimated yield drops of 15% to 25%.")
    add_body("2. Post-Harvest Grain Losses: During the harvesting and threshing season, unexpected mechanical seizures in combine harvesters and multi-crop threshers leave unharvested grain exposed to pests, mold, and unseasonal rainfall, driving post-harvest losses upwards of 20% in major rice and soybean production hubs.")
    add_body("3. High Cost of Imported Diagnostic Tools: Modern OEM telematics systems (e.g. John Deere Operations Center, Cat ET) require expensive proprietary hardware adapters (₦4m–₦8m), annual software subscriptions exceeding $1,200/year, and high-speed internet. These tools are incompatible with the legacy mechanical engines and analog hydraulic systems that dominate Nigerian farms.")
    add_body("4. The Reactive Maintenance Trap: Because rural mechanics lack non-invasive diagnostic tools, machines are operated until total mechanical failure occurs. What begins as a minor bearing misalignment or low oil pressure evolves into a cracked engine block or destroyed hydraulic pump, incurring ₦800,000 to ₦2,000,000 in emergency overhaul costs and weeks of machine downtime.")

    # --- SECTION 3 ---
    add_sec_heading("3. Target Agrifood Value Chains & Applications")
    add_body("MechMind AI is specifically optimized across four priority agricultural value chains:")
    add_bullet("Tractor-mounted disc plows, rotavators, and planters during April–June land preparation; combine harvesters, mobile threshers, and feed hammer mills during dry harvest.", "• Maize Value Chain (Field to Feed Mill): ")
    add_bullet("Paddy preparation tractors, diesel-powered irrigation pump sets for dry-season farming, combine harvesters in swamp paddies, and continuous commercial rice hullers/destoners.", "• Rice Value Chain (Paddy to Milled Grain): ")
    add_bullet("Heavy land preparation machinery, planting equipment, mechanical combine harvesters, and mechanical oil expellers/screw presses in processing clusters.", "• Soybean Value Chain (Production & Value Addition): ")
    add_bullet("Tractor leasing pools (e.g., Hello Tractor, TOAN, cooperative equipment pools), cassava graters, community multi-purpose threshers, and commercial agro-transport trucks.", "• Allied Agricultural Mechanization Services: ")

    # --- SECTION 4 ---
    add_sec_heading("4. The MechMind AI Solution")
    add_body("MechMind AI resolves the mechanization challenge through a robust, three-layer indigenous architecture:")
    add_sub_heading("Layer 1: The Non-Invasive Edge Telemetry Node (NODE-001)")
    add_body("A ruggedized, 3D-printed PETG enclosure embedded with four high-coercivity N52 neodymium magnets attaches in seconds to any metallic machinery casing (engine block, hydraulic pump, bearing housing). The node integrates:")
    add_bullet("ESP32-WROOM-32D 32-bit dual-core processor managing edge DSP and telemetry;");
    add_bullet("ADXL345 3-axis digital accelerometer (GY-291) configured at ±16g range with 10,000g shock tolerance;");
    add_bullet("DS18B20 digital waterproof temperature probe (-55°C to +125°C, 0.0625°C resolution);");
    add_bullet("INMP441 omnidirectional MEMS microphone over an I2S digital audio bus at 16 kHz; and");
    add_bullet("Rechargeable 18650 Li-ion power subsystem with TP4056 charging, providing ~18 hours continuous active telemetry or up to 5 days under duty cycling.");
    add_body("The node calculates dynamic RMS vibration, resultant acceleration magnitude, crest factor, 64-point FFT frequency components, and temperature rise rates (dT/dt) directly on-chip before emitting compact JSON telemetry bursts (<380 bytes every 2.0s).")

    add_sub_heading("Layer 2: Diagnostic Intelligence Engine")
    add_body("Telemetry anomalies trigger a retrieval-augmented generation (RAG) diagnostic engine powered by a locally hosted, quantized Llama 3.1 8B model. The system semantically indexes over 1,200 pages of official technical service manuals for common agricultural engines and hydraulic systems (Caterpillar, Perkins, Cummins, Komatsu). When symptoms or diagnostic codes appear, the engine hard-pins deterministic safety rules (e.g., forcing immediate engine shutdown if low oil pressure codes such as SPN 100 FMI 1 appear), preventing dangerous hallucinations and providing step-by-step physical inspection protocols.")

    add_sub_heading("Layer 3: Zero-Friction WhatsApp & Web Interface")
    add_body("Because rural technicians and tractor operators do not download complicated enterprise apps, MechMind delivers all diagnostic workflows over WhatsApp (+234 701 029 9562). Technicians can text, record voice notes in English, Hausa, or Yoruba (transcribed via faster-whisper), or snap photos of damaged tractor components. Cooperative fleet managers access a web console (https://mechmind-ng.vercel.app) to review machine waveforms, heat trends, and Machine Health Indices.")

    # --- SECTION 5 ---
    add_sec_heading("5. Edge Signal Processing & Bandwidth Efficiency")
    add_body("Operating across remote agricultural communities in northern and south-western Nigeria requires extreme bandwidth discipline. Streaming continuous raw sensor data over rural 2G/3G networks is economically and technically unviable:")
    add_bullet("Raw 200 Hz Tri-Axial Vibration: 200 Hz × 3 axes × 2 bytes = 1,200 bytes/s (2,400 bytes per 2s window);", "• Raw Baseline: ")
    add_bullet("Raw 16 kHz Audio Stream: 16,000 samples/s × 2 bytes = 32,000 bytes/s;", "• Audio Baseline: ")
    add_bullet("Edge Extraction: On-device feature extraction condenses continuous data into a single JSON payload (<380 bytes every 2.0s = ~190 bytes/s);", "• MechMind Telemetry: ")
    add_bullet("84.2% bandwidth reduction against raw vibration streaming, and >99.4% reduction against raw audio streaming. Monthly SIM data cost per node is under ₦500.", "• Rigorous Bandwidth Savings: ")

    # --- SECTION 6 & 7 ---
    add_sec_heading("6. Field Validation & Benchmark Results")
    add_body("MechMind AI has advanced beyond laboratory concepts into a verified physical prototype. The system underwent continuous field trials in September 2026 on operating heavy diesel equipment (SANY SY215C and Komatsu PC200-8) and workshop installations:")
    add_bullet("Magnetic Mount Security: 4 × N52 magnets maintained solid mechanical contact throughout intense machine vibration cycles without slipping;", "• Mechanical Durability: ")
    add_bullet("Measured baseline steady-state vibration averaged 0.32g dynamic AC RMS; transient shock spikes reached 1.84g during hydraulic relief valve load events; casing temperature tracked from 31.2°C ambient to 78.6°C operating temperature;", "• Measured Sensor Telemetry: ")
    add_bullet("Blind evaluation across 56 documented equipment failure scenarios (hydraulics, engine cooling, electrical, powertrain) yielded 42 correct root-cause identifications (75.0% accuracy);", "• 56-Case Diagnostic Benchmark: ")
    add_bullet("Median on-device LLM inference latency was 65.1 seconds; complete end-to-end WhatsApp delivery turnaround averaged 84.2 seconds; and", "• Latency Profile: ")
    add_bullet("Zero dangerous or non-compliant repair procedures generated post-intervention following deterministic safety code pinning.", "• Safety Compliance: ")

    # Table 1: Performance
    perf_table = doc.add_table(rows=6, cols=2)
    perf_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    perf_rows = [
        ("Engineering Metric / Parameter", "Verified System Performance"),
        ("Diagnostic Benchmark (OEM Service Manuals)", "56 Scenarios (Hydraulics, Engine, Electrical, Powertrain)"),
        ("Correct Root-Cause Identifications", "42 Cases Verified Correct (75.0% Accuracy)"),
        ("Response Latency Profile", "Median Local Inference: 65.1s | End-to-End WhatsApp: 84.2s"),
        ("Safety-Critical Hallucination Rate", "0.0% post-intervention (Deterministic code pinning on STOP codes)"),
        ("Hardware Unit BOM (Unit vs 500+ Batch)", "Prototype: ₦34,750 (~$22.00) | Indicative Batch: ₦21,500 (~$13.80)")
    ]
    for r_idx, (c0, c1) in enumerate(perf_rows):
        row = perf_table.rows[r_idx]
        set_cell_margins(row.cells[0], 45, 45, 70, 70)
        set_cell_margins(row.cells[1], 45, 45, 70, 70)
        if r_idx == 0:
            set_cell_shading(row.cells[0], "005937")
            set_cell_shading(row.cells[1], "005937")
            row.cells[0].paragraphs[0].add_run(c0).font.color.rgb = RGBColor(255, 255, 255)
            row.cells[1].paragraphs[0].add_run(c1).font.color.rgb = RGBColor(255, 255, 255)
            row.cells[0].paragraphs[0].runs[0].font.bold = True
            row.cells[1].paragraphs[0].runs[0].font.bold = True
        else:
            set_cell_shading(row.cells[0], "F0FDF4" if r_idx % 2 == 1 else "FFFFFF")
            set_cell_shading(row.cells[1], "F0FDF4" if r_idx % 2 == 1 else "FFFFFF")
            r0 = row.cells[0].paragraphs[0].add_run(c0)
            r1 = row.cells[1].paragraphs[0].add_run(c1)
            r0.font.bold = True
            r0.font.size = Pt(8.5)
            r1.font.size = Pt(8.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # --- SECTION 8 ---
    add_sec_heading("7. Commercialisation Model & Unit Economics")
    add_body("MechMind operates a hybrid hardware and subscription model designed for high affordability across Nigerian farm clusters:")
    add_body("1. Hardware Node Sales: MechMind Nodes retail at ₦50,000 (standalone) to ₦75,000 (bundled with hardened mounting kit). Against an indicative 500+ batch component BOM of ₦21,500 plus ₦4,500 local assembly, QA testing, and packaging (total landed COGS of ~₦26,000), this yields a sustainable 48% to 56% gross margin.")
    add_body("2. Fleet Telemetry SaaS: Cooperative equipment pools and tractor hiring fleets subscribe at ₦15,000 to ₦25,000 per tractor/month for real-time health dashboards, automated WhatsApp breakdown alerts, and predictive maintenance scheduling.")
    add_body("3. Spare Parts Transaction Marketplace: A 3%–5% transaction fee earned by connecting diagnosed tractor fault codes with verified local parts distributors in major hubs (Ladipo, Owode Onirin, Kaduna Tractor Market).")

    # --- SECTION 9 ---
    add_sec_heading("8. Agricultural Impact & Alignment with AGRA & SMEDAN")
    add_body("MechMind AI directly supports national food security, rural employment, and foreign exchange conservation:")
    add_body("• Targeted 50%–60% Downtime Reduction: By detecting mechanical distress before catastrophic seizure, equipment pools maintain 95%+ tractor availability throughout the critical 3-week planting window, preventing smallholder crop loss.")
    add_body("• Post-Harvest Loss Mitigation: Ensuring combine harvesters and community threshers remain operational during peak rice and soybean harvests prevents field-level spoilage.")
    add_body("• Dignified Youth Employment: Upskills young roadside mechanics and rural tractor operators into certified digital diagnostics technicians capable of operating modern telematics workflows.")
    add_body("• Foreign Exchange Conservation: Extends the working lifespan of multi-million Naira imported tractors, reducing the premature capital flight spent importing replacement machinery.")

    # --- SECTION 10 ---
    add_sec_heading("9. Pilot Roadmap for the Northern Agricultural Belt")
    add_body("Leveraging the AGRA–SMEDAN programme, MechMind will execute a progressive 12-month commercial pilot:")
    add_bullet("Fabricate a 50-unit batch of dedicated 2-layer PCBs with integrated cellular modems and IP65 weatherproof enclosures;", "• Phase 1 (Months 1–3) — Industrial Production: ")
    add_bullet("Deploy 50 MechMind Nodes across tractor-hiring fleets and rice/maize processing mills in Niger, Nasarawa, and Kaduna in collaboration with local cooperatives and SMEDAN hubs;", "• Phase 2 (Months 4–7) — Northern Field Pilot: ")
    add_bullet("Measure tractor uptime, validate fuel-efficiency improvements, and conduct certified WhatsApp diagnostic training for 100+ rural youth mechanics; and", "• Phase 3 (Months 8–10) — Performance Benchmarking: ")
    add_bullet("Roll out commercial subscriptions to 500+ agricultural machinery units across major grain-producing states.", "• Phase 4 (Months 11–12) — Commercial Scaling: ")

    # --- SECTION 11 ---
    add_sec_heading("10. Engineering Core Team")
    add_body("• Oni Mujeeb Ramadan (Product Operations & Field Lead): Civil Engineering, Lagos State University. NUESA Engineering Scholar of the Year (2026), Man of Excellence Award (LASUSU), 1st Place ASCE Nigeria Student Technical Essay Competition. Directs field testing, technician workflows, and cooperative partnerships.\n• Mubarak Raji Babatunde (AI & Software Lead): Civil Engineering, Lagos State University. 1st Place Winner Vibranium Valley x PowerTech Grand Challenge, DCP Digital Twin Engineering Challenge finalist. Directs AI RAG pipeline, FastAPI backend, and WhatsApp bot.\n• Olawale Oladele (Hardware & Embedded Systems Lead): Mechanical Engineering, Lagos State University. Certified SolidWorks Professional (CSWP) + 4 CSWPA Advanced Certifications, Ansys Mechanical & Fluent Associate. Directs node CAD, PCB schematic design, sensor firmware, and thermal validation.")

    # --- TECHNICAL APPENDIX ---
    add_sec_heading("TECHNICAL APPENDIX")

    # Appendix A
    add_sub_heading("A. Hardware Bill of Materials (BOM)")
    add_body("Prototype assembled locally in Lagos; 500+ batch procurement estimates based on verified supplier quotations:")

    bom_table = doc.add_table(rows=10, cols=4)
    bom_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    bom_rows = [
        ("Subsystem", "Component & Specification", "Unit Prototype (NGN)", "500+ Batch (NGN)"),
        ("Microcontroller Unit", "ESP32-WROOM-32D, dual-core 32-bit LX6, 240 MHz, 4 MB Flash", "₦6,500", "₦4,200"),
        ("Tri-Axial Vibration Sensor", "ADXL345 3-axis digital accelerometer (GY-291), ±16g range (13-bit)", "₦3,200", "₦1,850"),
        ("Digital Temperature Probe", "DS18B20 waterproof 1-Wire probe, −55°C to +125°C", "₦3,500", "₦2,100"),
        ("Acoustic Sensing Module", "INMP441 MEMS microphone, I²S digital audio interface", "₦1,800", "₦950"),
        ("Energy Storage", "18650 Li-ion 3.7 V, 2600 mAh rechargeable cell", "₦3,800", "₦2,400"),
        ("Power Management & Charging", "TP4056 charger + DW01A protection + MT3608 boost converter", "₦2,200", "₦1,200"),
        ("Enclosure & Mounting", "Custom 3D-printed PETG housing + 4 × N52 neodymium magnets", "₦9,500", "₦6,200"),
        ("Cabling & Hardware", "Shielded silicone cabling, latching rocker switch and connectors", "₦4,250", "₦2,600"),
        ("TOTAL BILL OF MATERIALS", "Complete non-invasive edge telemetry node", "₦34,750", "₦21,500")
    ]
    for r_idx, r_data in enumerate(bom_rows):
        row = bom_table.rows[r_idx]
        for c_idx, val in enumerate(r_data):
            cell = row.cells[c_idx]
            set_cell_margins(cell, 35, 35, 50, 50)
            if r_idx == 0:
                set_cell_shading(cell, "005937")
                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                run = p.add_run(val)
                run.font.bold = True
                run.font.size = Pt(8)
                run.font.color.rgb = RGBColor(255, 255, 255)
            elif r_idx == 9:
                set_cell_shading(cell, "FEF3C7")
                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                run = p.add_run(val)
                run.font.bold = True
                run.font.size = Pt(8)
                run.font.color.rgb = RGBColor(180, 83, 9)
            else:
                set_cell_shading(cell, "F0FDF4" if r_idx % 2 == 1 else "FFFFFF")
                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                run = p.add_run(val)
                run.font.size = Pt(8)
                run.font.color.rgb = RGBColor(15, 23, 42)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    add_body("Landed Cost Basis: Prototype BOM is ₦34,750 per unit. At 500+ batch scale, component BOM is ₦21,500. Adding ₦4,500–₦5,500 for local assembly, flashing, QA calibration, and protective packaging yields a landed manufacturing COGS of ~₦26,000. This provides the analytical foundation for the ₦50,000–₦75,000 commercial retail price and 48%–56% gross margin.")

    # Appendix B
    add_sub_heading("B. Technical Sensor Architecture")
    add_body("B.1 ADXL345 Vibration Sensing: Configured at ±16g range with 4 mg/LSB resolution and 10,000g shock tolerance. Captures three orthogonal vibration axes at 200 Hz to calculate dynamic AC RMS, resultant vector magnitude, peak acceleration, crest factor, and a 64-point FFT (3.125 Hz bin resolution across 0–100 Hz).")
    add_body("B.2 DS18B20 Surface Temperature: 1-Wire protocol, operating range −55°C to +125°C, 12-bit nominal resolution (0.0625°C). Monitored at 1 Hz to detect overheating rates (dT/dt) in engine cylinder heads, radiator coolant hoses, and hydraulic oil tanks.")
    add_body("B.3 INMP441 Acoustic Sensing: 16 kHz I2S digital acquisition reduced on-chip to a time-domain RMS sound pressure level envelope feature for detecting abnormal acoustic level shifts and mechanical clatter without heavy on-device audio spectral processing.")

    # Appendix C
    add_sub_heading("C. 56-Case Diagnostic Benchmark Results")
    bench_table = doc.add_table(rows=6, cols=5)
    bench_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    bench_rows = [
        ("Subsystem", "Cases", "Correct", "Accuracy", "Failure Modes Evaluated"),
        ("Hydraulic System", "18", "14", "77.8%", "Main relief valve bypass, cavitation, seal bypass, spool sticking"),
        ("Engine & Cooling", "16", "13", "81.3%", "Thermostat stuck closed, radiator clogging, boost leak, injector misfire"),
        ("Electrical & Charging", "12", "9", "75.0%", "Alternator diode failure, solenoid resistance, floating ground, sulfation"),
        ("Powertrain & Mechanical", "10", "6", "60.0%", "Final-drive bearing wear, coupling misalignment, track looseness"),
        ("OVERALL BENCHMARK", "56", "42", "75.0%", "Median Local LLM: 65.1s | End-to-End WhatsApp: 84.2s")
    ]
    for r_idx, r_data in enumerate(bench_rows):
        row = bench_table.rows[r_idx]
        for c_idx, val in enumerate(r_data):
            cell = row.cells[c_idx]
            set_cell_margins(cell, 35, 35, 50, 50)
            if r_idx == 0:
                set_cell_shading(cell, "005937")
                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                run = p.add_run(val)
                run.font.bold = True
                run.font.size = Pt(8)
                run.font.color.rgb = RGBColor(255, 255, 255)
            elif r_idx == 5:
                set_cell_shading(cell, "ECFDF5")
                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                run = p.add_run(val)
                run.font.bold = True
                run.font.size = Pt(8)
                run.font.color.rgb = RGBColor(6, 95, 70)
            else:
                set_cell_shading(cell, "F0FDF4" if r_idx % 2 == 1 else "FFFFFF")
                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                run = p.add_run(val)
                run.font.size = Pt(8)
                run.font.color.rgb = RGBColor(15, 23, 42)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    add_body("Deterministic Safety Code Pinning: Senior engineering audit identified an initial safety risk in automated generation on critical low oil pressure (TEST-001). Deterministic alphanumeric code pinning was introduced in the RAG pipeline to force emergency shutdown protocols to Rank 1 of retrieved context whenever critical STOP codes (e.g. SPN 100 FMI 1) occur, eliminating dangerous recommendations across the 56-case benchmark (0.0% safety-critical hallucinations).")

    # Appendix D: Media References & System Flow
    add_sub_heading("D. System Architecture Flow & Field References")
    add_body("[TRACTOR / FARM MACHINERY SURFACE]\n• ADXL345 3-axis accelerometer | DS18B20 temp probe | INMP441 MEMS mic | ESP32-WROOM-32D\n↓\n[EDGE SIGNAL PROCESSING]\nVibration: Resultant magnitude, dynamic RMS, peak acceleration, crest factor, 64-pt FFT\nTemperature: Moving average, thermal rate of rise (dT/dt) | Acoustic: 16 kHz RMS audio envelope\n↓\n[COMPACT TELEMETRY] (<380 B JSON burst every 2.0s over Wi-Fi; Cellular modem planned for Phase 2)\n↓\n[FASTAPI BACKEND & TIME-SERIES DB] → [REAL-TIME WEB DASHBOARD: https://mechmind-ng.vercel.app]\n↓\n[HYBRID RAG PIPELINE] (ChromaDB, 1,200+ pages OEM service documentation, SPN/FMI code database)\n↓\n[DETERMINISTIC SAFETY CODE PINNING] (Forces emergency engine shutdown to Rank 1 on critical STOP codes)\n↓\n[LOCAL LLAMA 3.1 8B MODEL] (Evidence-grounded troubleshooting protocol)\n↓\n[WHATSAPP GATEWAY: +234 701 029 9562] → Frontline Tractor Operator / Rural Workshop Mechanic")
    add_body("Field validation was conducted on active operating diesel machinery at Craneburg Construction project site in September 2026. Magnetic mount maintained contact under high shock loads without slippage. Baseline vibration averaged 0.32g dynamic RMS, with transient peaks of 1.84g recorded during hydraulic relief valve load events.")

    # Save DOCX
    out_docx = os.path.join(r"c:\Users\XPS\Downloads\china", "MechMind_AI_Project_Synopsis_AGRA_SMEDAN.docx")
    doc.save(out_docx)
    print(f"Successfully generated DOCX: {out_docx}")

    # Convert to PDF using Word COM
    out_pdf = os.path.join(r"c:\Users\XPS\Downloads\china", "MechMind_AI_Project_Synopsis_AGRA_SMEDAN.pdf")
    pythoncom.CoInitialize()
    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    try:
        wdoc = word.Documents.Open(out_docx)
        wdoc.SaveAs(out_pdf, FileFormat=17) # 17 = wdFormatPDF
        wdoc.Close()
        print(f"Successfully generated PDF via Word COM: {out_pdf}")
    except Exception as e:
        print(f"Error during Word PDF conversion: {e}")
    finally:
        word.Quit()
        pythoncom.CoUninitialize()

if __name__ == "__main__":
    create_agra_smedan_proposal()
