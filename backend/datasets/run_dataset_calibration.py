"""
========================================================================================
MechMind AI - Master Dataset Adapter & Sensor Calibration CLI Runner
========================================================================================

Usage:
  python run_dataset_calibration.py --all
  python run_dataset_calibration.py --j1939
  python run_dataset_calibration.py --cmapss
  python run_dataset_calibration.py --ai4i
  python run_dataset_calibration.py --cwru
  python run_dataset_calibration.py --status
========================================================================================
"""

import sys
import os
import argparse
import json
from typing import Dict, Any

# Ensure path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datasets.j1939_dictionary import J1939Adapter
from datasets.c_mapss_loader import CMAPSSDegradationCalibrator
from datasets.ai4i_loader import AI4IPredictiveMaintenanceCalibrator
from datasets.cwru_bearing_loader import CWRUBearingCalibrator
from ingestion.chroma_storage import ChromaStorage


def run_j1939():
    print("\n" + "="*70)
    print(" [1/4] SAE J1939 Fault Code Dictionary -> Ingesting into ChromaDB")
    print(" NOTE: THIS GOES INTO VECTOR DB FOR WHATSAPP RAG KNOWLEDGE BASE")
    print("="*70)
    adapter = J1939Adapter()
    count = adapter.ingest_to_chromadb()
    
    # Quick retrieval test
    test_q = "SPN 110 FMI 0 engine overheating"
    res = adapter.vector_search_code(test_q, n_results=1)
    if res:
        print(f"[+] Retrieval Check: Query '{test_q}'")
        print(f"    -> Matched: {res[0]['metadata'].get('section_title', res[0]['id'])}")
        print(f"    -> Distance: {res[0].get('distance')}")
    return count


def run_cmapss():
    print("\n" + "="*70)
    print(" [2/4] NASA C-MAPSS Turbofan Degradation Dataset -> Calibrating RUL")
    print(" NOTE: SENSOR THRESHOLD CALIBRATION ONLY (NOT FOR VECTOR DB)")
    print("="*70)
    calibrator = CMAPSSDegradationCalibrator()
    params = calibrator.fit_degradation_model()
    print(f"[+] Model Formula: {params['rul_model']['formula']}")
    print(f"[+] Validation R^2: {params['validation_metrics']['r2_score']}")
    print(f"[+] MAE: {params['validation_metrics']['mean_absolute_error_cycles']} cycles")
    return params


def run_ai4i():
    print("\n" + "="*70)
    print(" [3/4] AI4I 2020 Predictive Maintenance -> Calibrating Physical Boundaries")
    print(" NOTE: SENSOR THRESHOLD CALIBRATION ONLY (NOT FOR VECTOR DB)")
    print("="*70)
    calibrator = AI4IPredictiveMaintenanceCalibrator()
    thresholds = calibrator.calibrate_thresholds()
    print(f"[+] Analyzed {thresholds['sample_count']} samples across 4 failure modes.")
    for k, v in thresholds["calibrated_decision_boundaries"].items():
        print(f"    - {k}: {v['rule']}")
    return thresholds


def run_cwru():
    print("\n" + "="*70)
    print(" [4/4] CWRU Bearing Dataset -> Calibrating Vibration Defect Frequencies")
    print(" NOTE: SENSOR THRESHOLD CALIBRATION ONLY (NOT FOR VECTOR DB)")
    print("="*70)
    calibrator = CWRUBearingCalibrator()
    specs = calibrator.calibrate_bearing_thresholds()
    print("[+] Frequency Multipliers:")
    for k, v in specs["kinematic_frequency_multipliers"].items():
        print(f"    - {k}: {v}x shaft speed")
    print(f"[+] ADXL345 Normal RMS limit: < {specs['calibrated_adxl345_thresholds']['normal']['rms_max_g']}g")
    return specs


def print_status():
    print("\n" + "="*70)
    print(" MECHMIND AI - PHASE 2 CALIBRATION & INGESTION STATUS REPORT")
    print("="*70)
    
    # Check ChromaDB
    try:
        storage = ChromaStorage()
        doc_count = storage.count()
        print(f"  [ChromaDB RAG Engine] Collection '{storage.collection_name}': {doc_count} total chunks indexed")
    except Exception as e:
        print(f"  [ChromaDB RAG Engine] Status check failed: {e}")
        
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
    
    # Check C-MAPSS
    cmapss_file = os.path.join(data_dir, "calibrated_rul_model.json")
    if os.path.exists(cmapss_file):
        with open(cmapss_file, "r") as f:
            cm = json.load(f)
        print(f"  [NASA C-MAPSS Calibrator] Model active (R^2={cm['validation_metrics']['r2_score']}, MAE={cm['validation_metrics']['mean_absolute_error_cycles']})")
    else:
        print("  [NASA C-MAPSS Calibrator] Not yet calibrated. Run with --cmapss")
        
    # Check AI4I
    ai4i_file = os.path.join(data_dir, "calibrated_ai4i_thresholds.json")
    if os.path.exists(ai4i_file):
        with open(ai4i_file, "r") as f:
            ai = json.load(f)
        print(f"  [AI4I 2020 Calibrator] Rules active (4 failure modes calibrated, {ai['total_failure_events']} events)")
    else:
        print("  [AI4I 2020 Calibrator] Not yet calibrated. Run with --ai4i")
        
    # Check CWRU
    cwru_file = os.path.join(data_dir, "calibrated_cwru_bearing.json")
    if os.path.exists(cwru_file):
        with open(cwru_file, "r") as f:
            cw = json.load(f)
        print(f"  [CWRU Bearing Calibrator] Kinematics active (BPFO={cw['kinematic_frequency_multipliers']['bpfo_multiplier']}x, BPFI={cw['kinematic_frequency_multipliers']['bpfi_multiplier']}x)")
    else:
        print("  [CWRU Bearing Calibrator] Not yet calibrated. Run with --cwru")
        
    print("\n" + "="*70)
    print(" SEPARATION SUMMARY:")
    print(" - SAE J1939: Ingested into ChromaDB for dense vector search (WhatsApp)")
    print(" - C-MAPSS:   Calibrated RUL decay exponent for sensor node alerts")
    print(" - AI4I 2020: Calibrated thermal & power bounds for sensor node alerts")
    print(" - CWRU:      Calibrated BPFO/BPFI FFT peaks for ADXL345 vibration node")
    print("="*70)


def main():
    parser = argparse.ArgumentParser(description="MechMind AI Phase 2 Dataset & Calibration Runner")
    parser.add_argument("--all", action="store_true", help="Run all 4 dataset adapters")
    parser.add_argument("--j1939", action="store_true", help="Ingest SAE J1939 codes into ChromaDB")
    parser.add_argument("--cmapss", action="store_true", help="Calibrate NASA C-MAPSS RUL model")
    parser.add_argument("--ai4i", action="store_true", help="Calibrate AI4I physical failure boundaries")
    parser.add_argument("--cwru", action="store_true", help="Calibrate CWRU bearing vibration frequencies")
    parser.add_argument("--status", action="store_true", help="Print status of all calibrated models")
    
    args = parser.parse_args()
    
    if len(sys.argv) == 1 or args.status:
        print_status()
        return
        
    if args.all or args.j1939:
        run_j1939()
    if args.all or args.cmapss:
        run_cmapss()
    if args.all or args.ai4i:
        run_ai4i()
    if args.all or args.cwru:
        run_cwru()
        
    print_status()


if __name__ == "__main__":
    main()
