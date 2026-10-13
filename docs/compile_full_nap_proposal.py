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

def create_full_proposal():
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
        hrun = hp.add_run("National Automation Prize (NAP 2026) | Track 08: Made-in-Nigeria Affordable Automation")
        hrun.font.name = "Segoe UI"
        hrun.font.size = Pt(8)
        hrun.font.color.rgb = RGBColor(100, 116, 139)
        
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        frun = fp.add_run("MechMind AI — Non-Invasive Edge Condition Monitoring & Diagnostic Intelligence — Lagos State University")
        frun.font.name = "Segoe UI"
        frun.font.size = Pt(8)
        frun.font.color.rgb = RGBColor(148, 163, 184)

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
    trun.font.color.rgb = RGBColor(15, 23, 42)

    sub_p = doc.add_paragraph()
    sub_p.paragraph_format.space_after = Pt(8)
    srun = sub_p.add_run("Non-Invasive Edge Condition Monitoring and Diagnostic Intelligence for Legacy Industrial, Construction and Agricultural Machinery")
    srun.font.name = "Segoe UI"
    srun.font.size = Pt(11)
    srun.font.bold = True
    srun.font.color.rgb = RGBColor(234, 88, 12)

    # Metadata Box Table
    meta_table = doc.add_table(rows=4, cols=2)
    meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta_data = [
        ("Competition & Track", "National Automation Prize (NAP 2026)\nTrack 08: Made-in-Nigeria Affordable Automation & Industrial Machines"),
        ("Cross-Cutting Synergies", "Track 01: Smart Automation of Process Plants\nTrack 02: AI & Robotics for Agriculture & Food Security"),
        ("Institution & Commercial Vehicle", "Lagos State University (LASU), Lagos, Nigeria\nPullup Events (CAC Registration: BN-9846744)"),
        ("Engineering Core Team", "• Oni Mujeeb Ramadan — Product Operations & Field Lead\n• Mubarak Raji Babatunde — AI & Software Lead\n• Olawale Oladele — Hardware & Embedded Systems Lead")
    ]
    for row_idx, (k, v) in enumerate(meta_data):
        row = meta_table.rows[row_idx]
        cell_k, cell_v = row.cells[0], row.cells[1]
        cell_k.width = Inches(2.2)
        cell_v.width = Inches(4.47)
        set_cell_margins(cell_k, 50, 50, 80, 80)
        set_cell_margins(cell_v, 50, 50, 80, 80)
        set_cell_shading(cell_k, "F8FAFC")
        set_cell_shading(cell_v, "FFFFFF")
        
        kp = cell_k.paragraphs[0]
        kp.paragraph_format.space_after = Pt(0)
        krun = kp.add_run(k)
        krun.font.name = "Segoe UI"
        krun.font.bold = True
        krun.font.size = Pt(8.5)
        krun.font.color.rgb = RGBColor(71, 85, 105)
        
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
        run.font.color.rgb = RGBColor(15, 23, 42)
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
    add_body("Nigeria operates a large population of legacy construction, agricultural and industrial machines that were designed before modern low-cost condition-monitoring technologies became widely accessible. Many of these machines continue to operate without continuous vibration, temperature or acoustic monitoring, leaving operators dependent on periodic inspection, experience-based troubleshooting and, where available, expensive proprietary diagnostic systems.")
    add_body("MechMind AI is a locally developed, non-invasive machine-health monitoring and diagnostic intelligence platform designed to close this gap.")
    add_body("The system combines a compact edge sensor node with vibration, surface-temperature and acoustic sensing; local signal processing; low-bandwidth telemetry; a web-based machine-health dashboard; and a retrieval-augmented artificial intelligence diagnostic assistant accessible through WhatsApp.")
    add_body("The sensor node attaches externally to compatible machinery without cutting factory wiring or permanently modifying the machine. It collects machine-condition signals and extracts useful health indicators at the edge before transmitting compact telemetry. The diagnostic layer combines retrieved technical service information with a locally hosted language model to provide technicians with evidence-grounded troubleshooting guidance, inspection steps and safety considerations.")
    add_body("The current prototype has been physically assembled and tested on operating earthmoving equipment. In an internal 56-case blind diagnostic benchmark covering hydraulic, electrical, fuel-delivery and powertrain-related faults, the system correctly identified 42 cases, corresponding to 75.0% accuracy. The prototype also recorded a median local inference time of 65.1 seconds and an average end-to-end WhatsApp delivery turnaround of approximately 84.2 seconds.")
    add_body("These results represent an early engineering validation rather than a claim of production-grade diagnostic accuracy. The next development phase focuses on controlled fault testing, expanded machine coverage, improved sensor calibration, dedicated PCB fabrication, cellular connectivity and larger field datasets.")
    p_core = add_body("Make machine intelligence affordable enough for the machines Nigeria already owns.", "Core Engineering Principle: ")
    p_core.runs[1].font.italic = True

    # --- SECTION 2 ---
    add_sec_heading("2. Problem Statement")
    add_body("A significant portion of Nigeria’s construction, agricultural and industrial machinery consists of imported legacy equipment. Many such machines lack modern telematics, continuous condition monitoring or affordable access to advanced diagnostic infrastructure.")
    add_body("The consequence is a reactive maintenance cycle. A machine begins to develop abnormal vibration, excessive temperature, acoustic changes or other physical symptoms. If these changes are not detected early, the equipment may continue operating until the fault becomes severe enough to cause catastrophic downtime.")
    add_body("For contractors and machinery owners, an equipment failure results in: unexpected maintenance costs; idle equipment and stranded operators; project delays and milestone penalties; emergency repair surcharges; difficult spare parts procurement; and reduced equipment availability.")
    add_body("Existing OEM diagnostic systems (e.g. Caterpillar Electronic Technician, Komatsu Komtrax) provide machine-specific data but require proprietary hardware adapters (e.g., Cat Comm Adapter III, Komatsu Inline), expensive annual subscriptions, closed interfaces and specialist technicians. This creates an acute accessibility gap for small-to-medium contractors, independent workshops and agricultural machinery owners.")
    add_body("The engineering problem addressed by MechMind is therefore not simply the absence of artificial intelligence — it is the absence of an affordable, non-invasive and accessible machine-health intelligence layer for legacy equipment.")

    # --- SECTION 3 ---
    add_sec_heading("3. Engineering Objective")
    add_body("The objective of MechMind AI is to develop and validate an indigenous, low-cost system capable of:")
    add_bullet("capturing relevant machine-condition signals without cutting factory wiring or permanent modification;", "1. Non-Invasive Acquisition: ")
    add_bullet("processing and extracting useful health indicators locally at the edge controller;", "2. Edge Feature Extraction: ")
    add_bullet("transmitting machine-health telemetry using compact, bandwidth-efficient payloads;", "3. Efficient Telemetry: ")
    add_bullet("identifying abnormal operating conditions using signal-derived features and threshold rules;", "4. Anomaly Identification: ")
    add_bullet("providing evidence-grounded diagnostic support grounded in indexed technical service documentation;", "5. Grounded Diagnostics: ")
    add_bullet("delivering actionable guidance through an interface native to Nigerian technicians (WhatsApp);", "6. Zero-Friction Delivery: ")
    add_bullet("providing fleet-level visibility through a real-time web telemetry console; and", "7. Fleet-Level Monitoring: ")
    add_bullet("establishing a scalable architecture capable of local assembly and domestic manufacturing.", "8. Indigenous Scalability: ")

    # --- SECTION 4 ---
    add_sec_heading("4. Proposed Solution")
    add_body("MechMind AI is structured around a three-tier architecture:")
    add_sub_heading("Layer 1: Edge Sensing and Processing")
    add_body("A compact sensor node attaches externally to machine casings using a high-strength magnetic mount. The current physical prototype (NODE-001) integrates:")
    add_bullet("ESP32-WROOM-32D dual-core 32-bit microcontroller running FreeRTOS;");
    add_bullet("ADXL345 3-axis digital accelerometer (GY-291 module) configured at ±16g dynamic measurement range;");
    add_bullet("DS18B20 digital waterproof temperature probe (-55°C to +125°C, 12-bit resolution);");
    add_bullet("INMP441 omnidirectional MEMS microphone operating over an I2S digital audio bus at 16 kHz;");
    add_bullet("Rechargeable 18650 Li-ion 3.7V 2600 mAh cell with TP4056 linear charging, DW01A protection, and MT3608 boost conversion; and");
    add_bullet("Custom 3D-printed PETG enclosure embedded with four high-coercivity N52 neodymium magnets.");
    add_body("The node acquires machine-condition signals locally and extracts statistical features before transmission, eliminating reliance on continuous high-bandwidth cellular streaming.")

    add_sub_heading("Layer 2: Diagnostic Intelligence")
    add_body("The diagnostic layer combines retrieval-augmented generation (RAG) with a locally hosted language model. The system indexes official technical service documentation into a vector database (ChromaDB). When an anomaly occurs or a technician asks a question, relevant technical context is retrieved and provided to the model. The model is constrained to ground its recommendations strictly in retrieved engineering context and explicitly declare uncertainty when evidence is insufficient.")

    add_sub_heading("Layer 3: Technician and Fleet Interfaces")
    add_body("Field technicians interact with MechMind through WhatsApp (+234 701 029 9562) using text, voice notes (transcribed via faster-whisper), and damaged component photographs (analyzed via multimodal vision). Fleet managers access a real-time web dashboard (https://mechmind-ng.vercel.app) to review machine waveforms, thermal trends, and consolidated Machine Health Indices.")

    # --- SECTION 5 ---
    add_sec_heading("5. System Architecture")
    add_body("The complete end-to-end data pipeline separates physical sensing, signal processing, telemetry, diagnostic retrieval, and language generation to guarantee modularity and auditability:")
    add_body("Machine Surface → Multi-Modal Sensors (ADXL345, DS18B20, INMP441) → ESP32 Edge Controller → Local Feature Extraction (Resultant Magnitude, AC Dynamic RMS, Peak Acceleration, Crest Factor, 64-pt FFT, dT/dt, Acoustic RMS) → Compact JSON Telemetry (2.0s Interval) → FastAPI Backend & Time-Series DB → Real-Time Fleet Web Dashboard & Threshold Classifiers → Hybrid RAG Retrieval Engine (1,200+ Pages Indexed Service Context) → Quantized Local LLM (Llama 3.1 8B via Ollama) → Evidence-Grounded Troubleshooting Protocol → WhatsApp Field Gateway → Frontline Technician.")

    # --- SECTION 6 ---
    add_sec_heading("6. Hardware Engineering")
    add_body("6.1 Vibration Monitoring: An ADXL345 three-axis digital accelerometer (GY-291 module) captures machine vibration and transient acceleration across three orthogonal axes. The system uses acceleration measurements to derive machine-condition indicators, including time-domain features (dynamic RMS acceleration, peak acceleration, crest factor) and frequency-domain spectral characteristics. Dedicated industrial-grade accelerometers with extended bandwidth, hermetic environmental protection, and traceable calibration standards are planned for subsequent production phases.")
    add_body("6.2 Temperature Monitoring: A waterproof DS18B20 digital probe provides 12-bit surface temperature readings (0.0625°C resolution) across -55°C to +125°C, enabling early detection of hydraulic overheating, radiator clogging, and bearing dry-friction.")
    add_body("6.3 Acoustic Monitoring: The current prototype uses an INMP441 omnidirectional MEMS microphone module sampled at 16 kHz over I2S. On the edge node, the acoustic signal is processed into a time-domain RMS sound-level envelope to track overall operating sound pressure and capture transient mechanical clatter or severe pump distress. The current prototype does not perform on-device acoustic spectral decomposition; dedicated acoustic spectral classification (e.g., differentiating ultrasonic hydraulic cavitation signatures from background engine noise) is reserved for Phase 2 edge DSP implementation.")
    add_body("6.4 Power System: Powered by a single 3.7V 2600 mAh 18650 Li-ion cell with TP4056 linear charging, DW01A protection, and MT3608 boost regulation, providing ~18 hours continuous telemetry or up to 5 days under periodic duty-cycled sampling.")
    add_body("6.5 Mechanical Mounting: Housed in a custom 3D-printed PETG enclosure embedded with four high-coercivity N52 neodymium magnets, allowing rapid, tool-free attachment to metallic casings without drilling, welding, or tapping into factory harnesses.")

    # --- SECTION 7 ---
    add_sec_heading("7. Edge Signal Processing")
    add_body("To operate reliably across low-bandwidth African cellular environments, MechMind processes raw signals directly on the ESP32: High-rate sampling (200 Hz) → 128-point sliding window (640 ms) → Time-domain statistical feature extraction (Resultant acceleration, dynamic RMS, peak-to-peak, crest factor) + 64-point Radix-2 FFT (3.125 Hz bin resolution across 0–100 Hz Nyquist range) → Compact JSON telemetry burst (<380 bytes per frame every 2.0 seconds, average throughput ~190 bytes/s). This edge extraction yields rigorous bandwidth reductions against raw streaming baselines: (1) Compared to raw 200 Hz tri-axial vibration streaming (200 Hz × 3 axes × 2 bytes = 1,200 bytes/s, or 2,400 bytes per 2s window), transmitting ~190 bytes/s achieves an 84.2% bandwidth reduction; (2) Compared to continuous 16 kHz raw audio streaming (16,000 samples/s × 2 bytes = 32,000 bytes/s), it achieves a 99.4% reduction; (3) Compared to streaming combined raw multi-modal sensor channels (~33.2 kB/s), bandwidth consumption is cut by over 99.4%.")

    # --- SECTION 8 & 9 ---
    add_sec_heading("8. Diagnostic Intelligence Architecture")
    add_body("The diagnostic engine executes an 8-step retrieval-augmented workflow: (1) Query parsing and subsystem entity extraction; (2) Semantic retrieval of relevant technical service sections from indexed OEM manuals; (3) Context synthesis and prompt injection; (4) Grounded inference via locally hosted quantized Llama 3.1 8B; (5) Generation of structured root-cause probabilities; (6) Step-by-step physical inspection sequence; (7) Mandatory safety warnings and OEM torque/fluid specifications; (8) Explicit uncertainty reporting when symptoms are ambiguous.")

    add_sec_heading("9. Safety Architecture")
    add_body("Industrial diagnostics directly impact human life and machine survivability. Rather than assuming generative models are intrinsically safe, MechMind enforces an audited safety-first architecture: (1) Evidence Grounding: Recommendations must link strictly to indexed OEM service documentation; (2) Uncertainty Handling: Diagnostic suggestions are presented as ranked probabilistic hypotheses requiring technician verification; (3) Mandatory Safety Escalation: Suspected catastrophic failure modes (loss of oil pressure, brake failure, hydraulic leaks) immediately trigger emergency machine shutdown alerts; (4) Real-World Safety Iteration & Deterministic Hard-Pinning: The system was not assumed to be flawless from day one. During initial unconstrained testing on failure scenario TEST-001 (critical engine low oil pressure), the baseline LLM suggested routine electrical harness and sensor checks before machine shutdown—a potentially catastrophic real-world failure mode. In response, the engineering team introduced deterministic alphanumeric code pinning into the RAG pipeline: whenever critical STOP-level diagnostic trouble codes (e.g., SPN 100 FMI 1) or hazardous pressure drops are detected, emergency engine shutdown protocols are deterministically hard-pinned to Rank 1 of retrieved context, overriding probabilistic generation. Following this deterministic intervention, the system achieved zero safety-critical hallucinations (0.0% unsafe recommendations) across the complete 56-case verified benchmark.")

    # --- SECTION 10 ---
    add_sec_heading("10. Prototype Status & Experimental Validation")
    add_body("MechMind AI has advanced from concept to a physically assembled, field-validated working prototype. It has undergone bench calibration, installation on operating earthmoving equipment (SANY SY215C and Komatsu PC200-8), continuous telemetry streaming, and structured blind benchmarking across 56 documented failure scenarios.")
    add_body("The benchmark achieved 42 correct root-cause diagnoses out of 56 cases (75.0% accuracy). Local LLM inference recorded a median latency of 65.1 seconds on a workstation GPU, and the complete end-to-end WhatsApp turnaround (including speech transcription and network dispatch) averaged 84.2 seconds.")

    # Table 1: Performance
    perf_table = doc.add_table(rows=6, cols=2)
    perf_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    perf_rows = [
        ("Evaluated Metric / Parameter", "Measured Engineering Result"),
        ("Blind Diagnostic Benchmark (OEM Service Manuals)", "56 Scenarios (Hydraulics, Engine, Electrical, Powertrain)"),
        ("Correct Root-Cause Identifications", "42 Cases Verified Correct (75.0% Accuracy)"),
        ("Response Latency Profile", "Median Local LLM Inference: 65.1s | End-to-End WhatsApp: 84.2s"),
        ("Safety-Critical Hallucination Rate", "0.0% post-intervention (Resolved initial TEST-001 near-miss via deterministic code pinning)"),
        ("Hardware Bill of Materials (BOM)", "Prototype: ₦34,750 (~$22.00) | Indicative 500+ Batch: ₦21,500 (~$13.80)")
    ]
    for r_idx, (c0, c1) in enumerate(perf_rows):
        row = perf_table.rows[r_idx]
        set_cell_margins(row.cells[0], 45, 45, 70, 70)
        set_cell_margins(row.cells[1], 45, 45, 70, 70)
        if r_idx == 0:
            set_cell_shading(row.cells[0], "0F172A")
            set_cell_shading(row.cells[1], "0F172A")
            row.cells[0].paragraphs[0].add_run(c0).font.color.rgb = RGBColor(255, 255, 255)
            row.cells[1].paragraphs[0].add_run(c1).font.color.rgb = RGBColor(255, 255, 255)
            row.cells[0].paragraphs[0].runs[0].font.bold = True
            row.cells[1].paragraphs[0].runs[0].font.bold = True
        else:
            set_cell_shading(row.cells[0], "F8FAFC" if r_idx % 2 == 1 else "FFFFFF")
            set_cell_shading(row.cells[1], "F8FAFC" if r_idx % 2 == 1 else "FFFFFF")
            r0 = row.cells[0].paragraphs[0].add_run(c0)
            r1 = row.cells[1].paragraphs[0].add_run(c1)
            r0.font.bold = True
            r0.font.size = Pt(8.5)
            r1.font.size = Pt(8.5)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # --- SECTIONS 13 to 21 ---
    add_sec_heading("13. Local Content & Import Substitution")
    add_body("MechMind AI directly champions Nigerian industrial sovereignty. Imported diagnostic scan tools cost between ₦4,000,000 and ₦8,500,000 with mandatory annual licensing subscriptions exceeding $1,200/year. MechMind AI delivers an entirely locally developed alternative: local firmware, locally trained retrieval architecture, locally assembled hardware, and domestic supply chains for under ₦35,000. It directly democratizes the 'Right to Repair' for informal roadside mechanic clusters (Ladipo, Owode Onirin, Apo).")

    add_sec_heading("14. Commercialisation Model")
    add_body("The commercial architecture relies on three complementary revenue streams: (1) Hardware Unit Sales: MechMind Nodes sold at ₦50,000 to ₦75,000 per unit. With an indicative 500+ batch component BOM of ₦21,500 plus ₦4,500 local assembly and testing (total landed COGS of ~₦26,000), this pricing structure yields a sustainable 48%–56% gross margin across standalone units (₦50,000) and bundled packages (₦75,000); (2) Fleet Telemetry SaaS: Recurring cloud monitoring subscription at ₦15,000 to ₦25,000 per machine/month providing real-time fleet health dashboards and automated WhatsApp alert dispatch; (3) Spare Parts Transaction Commissions: 3%–5% transaction fee connecting diagnosed fault codes with verified local parts vendors in major industrial spare-parts markets (Ladipo, Owode Onirin).")

    add_sec_heading("15. Target Applications")
    add_body("• Heavy Construction: Excavators, wheel loaders, motor graders, bulldozers, and mobile cranes;\n• Commercial Agriculture: Tractors (Massey Ferguson, Steyr, John Deere), combine harvesters, irrigation pump sets;\n• Stationary Industrial Equipment: Diesel generator sets (Perkins, Cummins, FG Wilson), air compressors, process slurry pumps;\n• Equipment Rental Fleets: Telematics-enabled plant hire monitoring to prevent operator abuse and log utilization.")

    add_sec_heading("16. Scalability & Engineering Roadmap")
    add_body("The modular architecture enables progressive industrial scaling across five defined milestones:\n• Phase 1 (Months 1–3): Controlled fault bench validation and sensor repeatability characterization;\n• Phase 2 (Months 4–6): Industrialisation: Dedicated 2-layer PCB fabrication, IP65 enclosure, integrated 4G LTE-M / NB-IoT modem;\n• Phase 3 (Months 7–12): Multi-site field pilot across 50 machines with construction and agricultural partners in Lagos and Ogun State;\n• Phase 4 (Months 13–24): Commercial fleet deployments, workshop certifications, and parts marketplace rollout;\n• Phase 5 (Months 25+): Regional expansion across West African markets with identical legacy equipment dynamics (Ghana, Cote d'Ivoire).")

    add_sec_heading("17. Prototype Limitations")
    add_body("In keeping with rigorous engineering reporting, the current prototype has known boundaries: (1) The Wi-Fi telemetry module is suitable for worksites with hot-spot coverage; industrial cellular modems will replace this in Phase 2; (2) The 56-case benchmark evaluates diagnostic decision support and is not yet an exhaustive statistical sample of all rare failure modes; (3) MechMind serves strictly as an advisory diagnostic assistant and does not execute automated mechanical actuator intervention.")

    add_sec_heading("18. Engineering Team")
    add_body("• Oni Mujeeb Ramadan (Product Operations & Field Lead): Civil Engineering, Lagos State University. NUESA Engineering Scholar of the Year (2026), Man of Excellence Award (LASUSU), 1st Place ASCE Nigeria Student Technical Essay Competition. Directs site testing, technician workflows, and field operations.\n• Mubarak Raji Babatunde (AI & Software Lead): Civil Engineering, Lagos State University. 1st Place Winner Vibranium Valley x PowerTech Grand Challenge, DCP Digital Twin Engineering Challenge finalist. Directs AI RAG pipeline, FastAPI backend, and WhatsApp bot.\n• Olawale Oladele (Hardware & Embedded Systems Lead): Mechanical Engineering, Lagos State University. Certified SolidWorks Professional (CSWP) + 4 CSWPA Advanced Certifications, Ansys Mechanical & Fluent Associate. Directs node CAD, PCB schematic design, sensor firmware, and thermal-structural validation.")

    add_sec_heading("19. Expected National Impact")
    add_body("• Targeted 50%–60% Reduction in Unplanned Breakdown Downtime: Serves as the primary operational hypothesis for upcoming longitudinal fleet trials, shifting reactive repair cycles into condition-based preventative interventions before catastrophic component seizure occurs;\n• Foreign Exchange Conservation: Extends the operational lifespan of multi-million Naira imported machinery, mitigating premature capital flight from unnecessary total machine write-offs;\n• Dignified Engineering Employment: Trains and upskills informal roadside mechanics into certified digital diagnostics technicians capable of operating modern telematics workflows;\n• Food Security Infrastructure Support: Prevents seasonal tractor and harvester breakdowns during time-critical planting and harvesting windows across Nigerian agricultural belts.")

    add_sec_heading("20. Conclusion")
    add_body("MechMind AI proves that cutting-edge machine condition monitoring and generative diagnostic intelligence can be engineered locally at a price point accessible to every Nigerian contractor, farmer, and independent mechanic. By bringing non-invasive intelligence to the machines Nigeria already owns, MechMind provides a scalable, homegrown solution that drives productivity, preserves capital, and accelerates indigenous industrial automation.")

    # --- TECHNICAL APPENDIX ---
    add_sec_heading("TECHNICAL APPENDIX")

    # Appendix A
    add_sub_heading("A. Current Hardware Bill of Materials (BOM)")
    add_body("The current prototype was assembled using components sourced locally in Lagos through Ikeja Computer Village, Alaba International and local electronic-component suppliers. The following represents the current prototype configuration and indicative 500+ unit procurement estimates:")

    bom_table = doc.add_table(rows=10, cols=4)
    bom_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    bom_rows = [
        ("Subsystem", "Component & Specification", "Unit Prototype (NGN)", "500+ Batch (NGN)"),
        ("Microcontroller Unit", "ESP32-WROOM-32D, dual-core 32-bit LX6, up to 240 MHz, 4 MB Flash", "₦6,500", "₦4,200"),
        ("Tri-Axial Vibration Sensor", "ADXL345 3-axis digital accelerometer (GY-291), I²C, configured ±16 g range (13-bit)", "₦3,200", "₦1,850"),
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
                set_cell_shading(cell, "0F172A")
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
                set_cell_shading(cell, "F8FAFC" if r_idx % 2 == 1 else "FFFFFF")
                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                run = p.add_run(val)
                run.font.size = Pt(8)
                run.font.color.rgb = RGBColor(15, 23, 42)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    add_body("Prototype BOM: ₦34,750 per unit. Indicative 500+ unit component BOM: ₦21,500 per unit. Adding estimated local batch assembly, flashing, QA calibration testing, and protective packaging (₦4,500–₦5,500), total landed manufacturing COGS is projected at ~₦26,000–₦27,000 per unit. This forms the analytical basis for the ₦50,000–₦75,000 commercial pricing and 48%–56% gross margin. The batch figure is an indicative procurement estimate based on current component configurations and will be refined through formal vendor quotations and pilot-run production before commercial scale.")

    # Appendix B
    add_sub_heading("B. Verified Sensor Specifications")
    add_body("B.1 ESP32-WROOM-32D: Tensilica Xtensa dual-core 32-bit LX6 processor operating up to 240 MHz; 4 MB SPI flash; integrated 2.4 GHz 802.11 b/g/n Wi-Fi; Bluetooth 4.2 / BLE; I²C, SPI, UART peripherals; operating ambient range −40°C to +85°C. In the current prototype firmware (mechmind_node.ino), Wi-Fi networking executes on Core 0 managed by the ESP-IDF background RTOS, while sensor polling and telemetry run in the main loop on Core 1.")
    add_body("B.2 ADXL345 3-Axis Digital Accelerometer: The current MechMind Node uses the Analog Devices ADXL345 3-axis digital accelerometer, implemented on a GY-291 breakout module, as its primary vibration sensor. Relevant characteristics include: (1) Three-axis digital acceleration measurement across X, Y and Z; (2) Selectable full-scale ranges of ±2 g, ±4 g, ±8 g and ±16 g; (3) The current prototype configured at ±16 g to provide measurement headroom for transient machinery shocks; (4) Up to 13-bit resolution, with approximately 4 mg/LSB at the ±16 g range; (5) Selectable output data rates extending up to 3200 Hz; (6) I²C digital communication configured at address 0x53; (7) High mechanical shock survivability rated up to 10,000 g unpowered shock tolerance (distinct from its ±16 g measurement range); and (8) Low-power operation suitable for battery-powered sensing. The ADXL345 was selected for the prototype because its three-axis measurement, selectable ±16 g range and shock survivability provide an appropriate sensing foundation for monitoring vibration and transient acceleration on operating machinery. The measured acceleration is processed into time-domain features including resultant acceleration, dynamic RMS, peak acceleration and crest factor, while a 64-point FFT is applied to the vibration signal to identify dominant spectral components within the 0–100 Hz Nyquist range. The sensor is used as a machine-condition sensing input rather than a standalone diagnostic instrument.")
    add_body("B.3 DS18B20 Temperature Probe: 1-Wire digital bus protocol; operating range −55°C to +125°C; manufacturer-specified accuracy ±0.5°C over −10°C to +85°C; 12-bit configuration (0.0625°C nominal resolution). Tracks thermal trends and detects abnormal thermal rise rates (dT/dt).")
    add_body("B.4 INMP441 MEMS Microphone: Omnidirectional MEMS microphone operating over an I2S digital audio bus sampled at 16 kHz. The acoustic channel is used to derive an acoustic envelope/RMS feature for detecting macro changes in overall machine sound pressure level and intermittent mechanical clatter. The current implementation treats acoustic information as a supporting diagnostic signal rather than an on-device spectral fault classifier (dedicated acoustic spectral decomposition, e.g. for ultrasonic cavitation isolation, is planned for Phase 2).")
    add_body("B.5 Power Subsystem: Nominal 3.7 V, 2600 mAh 18650 Li-ion cell with TP4056 charging, DW01A protection, and MT3608 boost conversion. Achieves ~18 hours continuous active burst telemetry and up to 5 days under deep-sleep duty cycling.")

    # Appendix C
    add_sub_heading("C. Sampling and Signal-Processing Configuration")
    add_body("C.1 Vibration Acquisition: Sample rate = 200 Hz; acquisition window = 128 samples (duration: 128 / 200 = 0.64 seconds). Sliding acquisition window for local processing across X, Y, Z axes. Features extracted: Resultant vector magnitude |a| = sqrt(ax² + ay² + az²), dynamic AC RMS (subtracting static 1.0g gravity baseline), peak acceleration, and crest factor.")
    add_body("C.2 Frequency-Domain Transformation: 64-point Radix-2 on-device FFT. Bin spacing: Δf = 200 / 64 = 3.125 Hz across the 0–100 Hz Nyquist range. Spectral peaks provide supporting indicators for rotating component degradation.")
    add_body("C.3 Temperature Monitoring: Polled at 1 Hz; calculates moving-average temperature, temperature trend, and rate of rise (dT/dt).")
    add_body("C.4 Acoustic Processing: 16 kHz I2S digital audio acquisition reduced on-chip to a time-domain RMS sound pressure level envelope feature for detecting overall acoustic shifts and transient clatter, without on-device acoustic spectral decomposition.")
    add_body("C.5 Telemetry Framing: Compressed JSON telemetry frames emitted every ~2.0 seconds (payload size < 380 bytes per burst, ~190 bytes/s). Compared to raw 200 Hz tri-axial accelerometer streaming (1,200 bytes/s), edge extraction reduces bandwidth by 84.2%; compared to continuous 16 kHz raw audio streaming (32,000 bytes/s), reduction exceeds 99.4%, ensuring seamless operation over constrained 2G/3G cellular networks.")

    # Appendix D
    add_sub_heading("D. 56-Case Diagnostic Benchmark Results")
    add_body("Evaluated against 56 blind diagnostic scenarios constructed from documented fault conditions in Caterpillar, Komatsu, and XCMG official service manuals:")

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
                set_cell_shading(cell, "0F172A")
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
                set_cell_shading(cell, "F8FAFC" if r_idx % 2 == 1 else "FFFFFF")
                p = cell.paragraphs[0]
                p.paragraph_format.space_after = Pt(0)
                run = p.add_run(val)
                run.font.size = Pt(8)
                run.font.color.rgb = RGBColor(15, 23, 42)

    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    add_body("Safety Evaluation & Code Pinning: A senior human engineering audit identified an initial safety risk in automated generation where the model suggested electrical troubleshooting on a low oil pressure fault (TEST-001). To resolve this, deterministic alphanumeric code pinning was introduced in the RAG pipeline: critical stop fault codes (SPN 100 FMI 1) force emergency engine shutdown protocols to Rank 1 of retrieved context. Across the verified benchmark, zero responses recommended dangerous operational workarounds.")

    # Appendix E
    add_sub_heading("E. Validation Photographs & Media References")
    add_body("E.1 Assembled Sensor Node (NODE-001): 3D-printed PETG enclosure housing the ESP32, ADXL345 accelerometer, INMP441 MEMS microphone, DS18B20 probe, battery subsystem, and four N52 neodymium mounting magnets.")
    add_body("E.2 Magnetic Attachment Test: Successfully attached to the primary hydraulic pump housing and cylinder head area of operating excavators without drilling, wiring cuts, or machine modification.")
    add_body("E.3 Live Telemetry Dashboard: Publicly deployed at https://mechmind-ng.vercel.app with multi-asset selection, 3-axis kinematic waveforms, thermal trend logging, and Machine Health Index classification.")
    add_body("E.4 WhatsApp Diagnostic Interface: Deployed at +234 701 029 9562 accepting text queries, speech voice notes (faster-whisper), and broken component photographs.")

    # Appendix F
    add_sub_heading("F. System Architecture Flow")
    add_body("[MECHMIND EDGE NODE]\n• ADXL345 3-axis accelerometer\n• DS18B20 temperature probe\n• INMP441 MEMS microphone\n• ESP32-WROOM-32D\n• Battery + power management\n↓\n[EDGE SIGNAL PROCESSING]\nVibration: Resultant acceleration, Dynamic RMS, Peak acceleration, Crest factor, 64-point FFT (3.125 Hz bin spacing)\nTemperature: Temperature, Moving average, dT/dt\nAcoustic: 16 kHz I²S acquisition, RMS audio envelope, Sound-level indicator\n↓\n[COMPACT TELEMETRY] (JSON feature payload over Wi-Fi; Cellular/GSM modem planned for Phase 2)\n↓\n[FASTAPI BACKEND & POSTGRESQL DB]\n↓\n[REAL-TIME DASHBOARD (Next.js)]\n↓\n[HYBRID RAG DIAGNOSTIC PIPELINE] (ChromaDB, 1,200+ pages technical documentation, SPN/FMI fault information, Safety documentation)\n↓\n[DETERMINISTIC SAFETY PRIORITIZATION] (Critical fault-code detection, Emergency procedure prioritization)\n↓\n[LLAMA 3.1 8B] (Locally hosted, quantized model)\n↓\n[EVIDENCE-GROUNDED RESPONSE] (Likely causes, Inspection sequence, Technical evidence, Safety warnings, Uncertainty / escalation)\n↓\n[WHATSAPP GATEWAY (Baileys)] → Frontline Technician / Fleet Manager")

    # Appendix G
    add_sub_heading("G. Field-Test Evidence")
    add_body("• Equipment Monitored: SANY SY215C and Komatsu PC200-8 hydraulic excavators.\n• Location: Craneburg Construction active project jobsite, Alaro City / Epe axis, Lagos State, Nigeria.\n• Test Period: September 2026.\n• Sensor Attachment: Tandem variable-displacement hydraulic pump casing and engine valve cover.\n• Mechanical Results: Magnetic mount maintained secure contact during high-vibration trenching without physical slippage.\n• Logged Telemetry: Steady-state baseline vibration averaged ~0.32g dynamic RMS; transient shock spike of ~1.84g resultant magnitude recorded during hydraulic relief valve load events; surface temperature tracked smoothly from 31.2°C ambient to 78.6°C operating temperature over a 45-minute continuous cycle.")

    # Appendix H
    add_sub_heading("H. Commercial & Industrial Pilot Progress")
    add_body("• Technician Interviews: Field workflow validation conducted with 5 experienced heavy-equipment mechanics across informal workshops in the Epe and Ajah industrial corridors.\n• Corporate Engagement: Practical installation demonstration and feedback session conducted with equipment supervisory personnel at the Craneburg infrastructure project site.\n• Corporate Standing: Commercial vehicle registered under Pullup Events (Corporate Affairs Commission: BN-9846744) to execute pilot contracts, partnerships, and manufacturing activities.\n• Commercialization Pathway: Prototype → Controlled Validation → Industry Pilot → Dedicated PCB & IP65 Enclosure → Local Manufacturing → Fleet Deployment → Subscription Services.")

    # Technical Validation Statement
    add_sub_heading("Technical Validation Statement")
    add_body("The current MechMind prototype demonstrates an integrated engineering system combining physical sensing, edge processing, telemetry, technical-document retrieval and locally hosted AI-assisted diagnostic support. The reported results are intentionally separated into measured prototype results and future engineering targets. The 56-case benchmark, field measurements, prototype BOM, sensor architecture and live system interfaces represent the current development state. Larger controlled datasets, extended environmental testing, industrial-grade sensing, cellular connectivity, dedicated PCB fabrication and longitudinal fleet validation remain part of the engineering roadmap. This distinction is maintained to ensure that MechMind's competition claims remain reproducible, technically defensible and aligned with the actual maturity of the prototype.")

    # Save DOCX
    out_docx = os.path.join(r"c:\Users\XPS\Downloads\china", "MechMind_AI_Project_Synopsis_NAP2026.docx")
    doc.save(out_docx)
    print(f"Successfully generated DOCX: {out_docx}")

    # Convert to PDF using Word COM
    out_pdf = os.path.join(r"c:\Users\XPS\Downloads\china", "MechMind_AI_Project_Synopsis_NAP2026.pdf")
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
    create_full_proposal()
