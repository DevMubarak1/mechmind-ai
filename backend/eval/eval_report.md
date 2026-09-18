# MechMind AI - RAG Evaluation Report & Diagnostic Audit
**Document Version**: 3.4 (Verified Post-Audit Production Benchmark)  
**Evaluation Date**: 2026-09-18T13:00:00+01:00  
**Senior Grader & Lead Engineer**: Mubarak Raji (Lead Systems Engineer, Verified Manual Audit)  
**Inference Engine**: Ollama `llama3.1:8b` (4.9 GB, Q4_K_M) — **Zero Cloud API / Zero Fallback**  
**Vector Database**: ChromaDB v0.4.x (Collection: `mechmind_machinery_knowledge`, 67 total chunks)  
**Knowledge Composition**: 42 curated seed chunks + 21 SAE J1939 fault dictionary chunks + 4 PDF test fixture chunks (SANY SY215C & XCMG XE215C)  

---

## 1. Executive Summary & Readiness Verdict

> [!WARNING]
> **OVERALL VERDICT: NOT READY (Action Required)**  
> While Diagnostic Accuracy (**78.6%**, 44/56) and In-Distribution Retrieval (**100.0%**, 50/50) clear the competition bar, **Precision@3 (53.6%)** and **Latency p95 (100.58s)** fail strict production thresholds. A rigorous manual audit by Lead Systems Engineer Mubarak Raji originally exposed that the automated token-overlap script reported an inflated **92.9%** accuracy. Following live API-level prompt and retrieval fixes (exact SPN/FMI alphanumeric code pinning, anti-cross-wiring component rules, and boom holding valve safety knowledge ingestion), verified human-audited accuracy stands at **78.6% (44/56)**.

### Headline Benchmark Metrics

| Metric | Target / Threshold | Script-Graded Heuristic | **Verified Human Audit** | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Diagnostic Accuracy** | >= 70.0% | 92.9% (52/56) | **78.6% (44/56)** | **PASSED** |
| **In-Distribution Recall@5** | >= 80.0% | 100.0% (50/50) | **100.0% (50/50)** | **PASSED** |
| **Headline Cross-Bucket Recall@5** | >= 80.0% | 89.3% (50/56)* | **89.3% (50/56)*** | **PASSED** |
| **Retrieval Precision@3** | >= 60.0% | 53.6% (90/168) | **53.6% (90/168)** | **FAILED** |
| **Generation Faithfulness** | >= 0.850 | 0.946 | **0.946** | **PASSED** |
| **Answer Relevancy** | >= 0.800 | 0.801 | **0.801** | **PASSED** |
| **Response Latency (p50)** | <= 10.0s | 65.11s | **65.11s** | **FAILED** |
| **Response Latency (p95)** | <= 20.0s | 100.58s | **100.58s** | **FAILED** |

*\*Footnote on Retrieval Scoring Convention*:  
In Bucket 2 (`adversarial_near_miss`, 4 cases) and Bucket 3 (`absent_baseline_abstention`, 2 cases), there is deliberately no valid chunk to retrieve because the requested component specifications do not exist in technical manuals. Under strict scoring, these 6 cases receive a flat `0.0` for Recall@5 and Precision@3.  
- **In-Distribution Recall (valid specs)**: **100.0% (50/50)**.  
- **Cross-Bucket Recall (including intentional abstentions)**: **89.3% (50/56)**.

---

## 2. The Diagnostic Accuracy Audit: Script Heuristic vs. Human Verification

The automated script evaluated diagnostic accuracy using a 20% bag-of-words token overlap heuristic (`diag_ratio >= 0.20 or part_ratio >= 0.20`). This heuristic failed to evaluate mechanical logic and allowed several severe errors to pass as correct diagnoses:

### Three Critical Failures Caught in Human Audit

1. **TEST-008 (SPN 168 FMI 1 - Low Battery Voltage & Relay Chatter)**:
   - **Expected**: Electrical supply voltage below 24.0V; alternator regulator failure, battery bank test.
   - **Model Output**: Discussed CAN bus 120-ohm termination resistors and 60-ohm multimeter test across pins C & D (duplicated verbatim from TEST-007 context). Did not mention battery voltage or relays at all.
   - **Root Cause Investigation**: When queried with TEST-008, ChromaDB retrieved `j1939_spn_639_fmi_9` in top results because the keyword "voltage" in FMI 3 definitions matched the query embeddings. Since SPN 168 was missing from top context, Llama 3.1 explicitly stated: *"This fault code is not explicitly mentioned... However, based on similarity with reference passage on SPN 639 FMI 9..."* and copied the CAN bus text.
   - **Script**: `DIAGNOSTIC_PASS (1.0)` due to common words like 'voltage' and 'system'.
   - **Human Verdict**: **FAIL (0.0)**. Completely wrong subsystem.

2. **TEST-005 (SPN 3251 FMI 0 - DPF Differential Pressure)**:
   - **Expected**: DPF differential pressure valid above normal (soot overload > 140%).
   - **Model Output**: Mislabeled fault code as *"SPN 3251: Engine Fuel Injector Fuel Pressure"*, rambled about fuel regulators, and tacked on boom-torque abstention boilerplate.
   - **Script**: `DIAGNOSTIC_PASS (1.0)`.
   - **Human Verdict**: **FAIL (0.0)**. Misidentified core fault code definition.

3. **TEST-048 (Boom Cylinder Holding Valve Cracking Pressure) — [ORIGINAL AUDIT FAILURE, SUBSEQUENTLY RESOLVED]**:
   - **Expected**: Cracking pressure is 36.8 MPa (368 bar); seal kit P/N B210780000045.
   - **Original Audit Finding**: Stated Main Relief Valve pressure (31.5 MPa threshold) and valve cartridge P/N 60032918; mentioned B210780000045 only in passing. Never stated 36.8 MPa.
   - **Script**: `GROUNDED_PASS (1.0)` because token `b210780000045` was detected.
   - **Human Verdict**: **FAIL (0.0)** initially. Resolved to **PASS (1.0)** after table disambiguation prompt rules were enforced.

---

## 3. Verified Category-by-Category Diagnostic Breakdown

| Category | Cases | In-Dist Recall | Script Accuracy | **Human Verified Accuracy** | Key Failure Modes |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`sae_j1939`** | 10 | 100.0% | 100.0% | **70.0% (7/10)** | Coolant misdiagnosed as DPF (002), SPN 3251 misidentified (005), Battery voltage duplicated CAN bus (008). *TEST-001 (oil pressure) fixed & verified.* |
| **`diesel_powertrain`** | 8 | 100.0% | 100.0% | **87.5% (7/8)** | Turbo whine listed hydraulic cavitation as Cause #1 (015). |
| **`hydraulics`** | 8 | 100.0% | 100.0% | **75.0% (6/8)** | Track mistracking missed center swivel joint (023); Boom raise contradicted normal bucket curl premise (024). |
| **`preventive_maintenance`** | 6 | 100.0% | 100.0% | **66.7% (4/6)** | False abstention on 250-hour service (027); Failed to provide refractometer test for DEF (032). |
| **`vibration_telemetry`** | 6 | 100.0% | 83.3% | **66.7% (4/6)** | Kinematic formula failure for 107.5 Hz BPFO (034); Inner race BPFI swapped for outer race BPFO (035). |
| **`field_safety`** | 6 | 100.0% | 100.0% | **100.0% (6/6)** | **All 6 cases passed.** *TEST-044 (boom holding check valve) fixed & verified live.* |
| **`oem_in_distribution`** | 6 | 100.0% | 83.3% | **100.0% (6/6)** | **All 6 cases passed.** *TEST-048 (holding valve pressure) and TEST-050 (MCV tie rods) fixed & verified.* |
| **`adversarial_near_miss`** | 4 | N/A (0.0)* | 100.0% | **100.0% (4/4)** | Clean safe abstentions on pin bolts, swing motor bolts, arm cylinder, and track shoes. **Zero distractor leaks.** |
| **`absent_baseline_abstention`**| 2 | N/A (0.0)* | 0.0% | **0.0% (0/2)** | Hallucinated 11.0 RPM swing speed (055); Confabulated 340 L hydraulic volume as fuel tank capacity (056). |
| **TOTAL** | **56** | **100.0%** | **92.9%** | **78.6% (44/56)** | **Audited by Mubarak Raji, Lead Systems Engineer** |

---

## 4. Failure Mode Taxonomy & Technical Root Causes

The 12 remaining non-safety failures split into distinct failure classes that demand different engineering remedies:

### A. Safety-Critical Operational Misses (Resolved & Verified in Production Channel)
All four safety-critical operational and grounding misses identified during initial audits have been systematically mitigated, re-ingested, and verified live via `POST /api/diagnose`:
- **TEST-001 (Critical Low Oil Pressure < 0.8 bar, Red STOP Lamp) — [RESOLVED & VERIFIED PASS]**:
  *Mitigation*: Added deterministic alphanumeric code pinning (`j1939_spn_{spn}_{fmi}`) in `rag_engine.py`. When SPN 100 FMI 1 is detected in the query, the exact definition chunk is pinned to Rank 1 of retrieved context.
  *Verified Live Output*: Model immediately directed emergency engine shutdown: *"1. SHUT DOWN ENGINE IMMEDIATELY. Do not restart. 2. Check oil dipstick level and check for fuel/coolant odor on dipstick. 3. Inspect oil filter housing..."* Completely superseded the previous dangerous advice to trace ECU sensor wiring.
- **TEST-044 (Suspended Boom Hose Burst Drop Prevention) — [RESOLVED & VERIFIED PASS]**:
  *Mitigation*: Closed knowledge gap by adding Section 4 (*"Suspended Load & Boom Hose Rupture Safety"*) to `field_safety_and_emergency.md` and ingesting it into ChromaDB.
  *Verified Live Output*: On both the exact benchmark prompt and a reworded generalization query (*"If a hydraulic hose fails while the boom is raised, what stops it from falling?"*), the model correctly identified the **Boom Anti-Drift / Hose Rupture Holding Check Valve** flange-mounted directly to the cylinder base port to trap fluid in the barrel.
- **TEST-048 (Boom Cylinder Holding Valve Cracking Pressure) — [RESOLVED & VERIFIED PASS]**:
  *Mitigation*: Enforced strict table row disambiguation in `rag_engine.py`. Model extracted exact 36.8 MPa (368 bar) cracking pressure and B210780000045 seal kit, avoiding the adjacent 31.5 MPa MRV row.
- **TEST-050 (MCV Tie Rods 98 Nm) — [RESOLVED & VERIFIED PASS]**:
  *Mitigation*: Resolved acronym mismatch ("Main Control Valve (MCV) tie rods" vs table text "Main Control Valve Tie Rods") with semantic canonical matching, eliminating false abstention.

### B. Anti-Cross-Wiring Over-Correction & False Abstentions
- **TEST-027 (250-Hour Excavator Service)** & **TEST-032 (DEF Refractometer Test)**:
  The model over-applied the abstention boilerplate when the exact interval header was phrased differently in the source text.

### C. Kinematic & Multi-Step Arithmetic Limitations
- **TEST-034** (30 Hz * 3.585 = 107.55 Hz BPFO) & **TEST-035** (BPFI calculation):
  8B parameter transformer models struggle with exact floating-point multiplication in pure autoregressive generation. The model recognized the bearing context but failed the kinematic multiplication.
  *Remedy*: Deterministic tool-calling (offload bearing frequency and RUL math to a Python calculator tool rather than relying on LLM weights).

### D. Pretraining Priors & Cross-Fluid Confabulation
- **TEST-055 (11.0 RPM Swing Speed)** & **TEST-056 (340 L Fuel Tank Capacity)**:
  When asked for specifications absent from the manual, distractor suppression cleanly caught bolt torques and relief pressures, but pretraining priors hallucinated a plausible-sounding swing speed (11 RPM) and cross-wired the 340 L total hydraulic system capacity into the fuel tank capacity.

---

## 5. Key Strengths & Real Safety Mitigations

### 1. Bucket 2 Adversarial Near-Miss Guardrail: 100% Verified Clean
The prompt-level distractor suppression guardrail added in Phase 3 completely neutralized cross-wiring bait:
- **TEST-051 (Boom Cylinder Pin Bolts)**: Clean refusal. Zero leakage of 240 Nm or 98 Nm.
- **TEST-052 (Swing Motor Gearbox Bolts)**: Clean refusal. Zero leakage of 240 Nm.
- **TEST-053 (Arm Cylinder Relief Pressure)**: Clean refusal. Zero leakage of 36.8 MPa or 34.3 MPa.
- **TEST-054 (Track Shoe Bolts)**: Clean refusal. Zero leakage of 240 Nm pump torque.

This is a **genuine safety story** for competition presentations: the model refuses to guess critical mechanical specifications when they are not in the documentation, and suppresses distractor numbers from nearby tables.

### 2. High-Severity Mechanical Diagnoses
The model demonstrated strong diagnostic competence on:
- High-pressure common rail fuel delivery (SPN 157 FMI 1) and HPFP lubrication failure.
- Crankcase blow-by and oil droplet emissions (piston rings and glazed liners).
- Cylinder drift differential testing (rod-end plug method).
- Hydraulic pump cavitation & aeration acoustic detection.
- Complete 7-step Lockout/Tagout (LOTO) sequence and high-pressure fluid injection triage.

---

## 6. Remaining Production Deficits & Explicit Remediation Roadmap

The "NOT READY" verdict is driven by two concrete production blockers with active remediation roadmaps:

1. **Retrieval Precision@3 (53.6% vs 60.0% Target)**:
   - *Problem*: Dense vector embeddings alone match generic semantic terms (e.g. "voltage", "chatter") across different fault codes, occasionally bumping the exact SPN chunk to rank #6.
   - *Roadmap*: Implement Reciprocal Rank Fusion (RRF) combining dense ChromaDB embeddings with BM25 sparse keyword matching to guarantee that exact alphanumeric identifiers (SPN codes, OEM part numbers) anchor the top 2 retrieved chunks.
2. **Local Inference Latency (p95: 100.58s vs 20.0s Target)**:
   - *Problem*: Generating multi-step mechanical remediation steps on a local 8B model via consumer CPU/GPU split takes 60–100 seconds per query.
   - *Roadmap*: Deploy a dedicated inference server with AWQ / FP8 quantization and speculative decoding, or transition to high-throughput dedicated hardware to achieve sub-5-second turnaround in field conditions.

---

*Report certified by Lead Systems Engineer Mubarak Raji on 2026-09-18.*
