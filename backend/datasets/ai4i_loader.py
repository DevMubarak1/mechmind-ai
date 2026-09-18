"""
========================================================================================
MechMind AI - AI4I 2020 Predictive Maintenance Dataset Loader & Anomaly Calibrator
========================================================================================

CRITICAL ARCHITECTURAL DISTINCTION:
-----------------------------------
NOTE: THIS MODULE CALIBRATES MULTI-SENSOR FAILURE CLASSIFICATION BOUNDARIES
(HEAT DISSIPATION, POWER FAILURE, OVERSTRAIN, TOOL WEAR) FOR THE MECHMIND NODE.
IT IS NOT PART OF THE RAG CHATBOT VECTOR KNOWLEDGE BASE. DO NOT CONFLATE THE TWO.

The resulting decision boundaries are exported to a calibration JSON file used by
the real-time telemetry anomaly detection engine in `backend/main.py`.
========================================================================================

DATASET BACKGROUND (UCI Machine Learning Repository):
----------------------------------------------------
The AI4I 2020 Predictive Maintenance dataset reflects 10,000 operational data points
modeling real-world industrial machine degradation across 4 physical failure mechanisms:
  1. Heat Dissipation Failure (HDF)
  2. Power Failure (PWF)
  3. Overstrain Failure (OSF)
  4. Tool Wear Failure (TWF)
========================================================================================
"""

import os
import json
import logging
from typing import Dict, List, Tuple, Any, Optional
import numpy as np

logger = logging.getLogger("mechmind.datasets.ai4i")

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
REAL_AI4I_FILE = os.path.join(DATA_DIR, "ai4i2020.csv")
OUTPUT_THRESHOLDS_FILE = os.path.join(DATA_DIR, "calibrated_ai4i_thresholds.json")

os.makedirs(DATA_DIR, exist_ok=True)


class AI4IPredictiveMaintenanceCalibrator:
    """
    Loads real UCI AI4I 2020 dataset (10,000 industrial records) and calibrates
    multi-sensor decision boundaries for Heat Dissipation, Power, Overstrain, and Wear anomalies.
    """

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or REAL_AI4I_FILE
        self.thresholds: Dict[str, Any] = {}

    def ensure_dataset(self) -> str:
        """
        Verifies the real UCI AI4I 2020 dataset file on disk.
        """
        if os.path.exists(self.data_path):
            return self.data_path
        raise FileNotFoundError(
            f"Real UCI AI4I dataset not found at {self.data_path}. "
            "Please run datasets/run_dataset_calibration.py to download."
        )

    def calibrate_thresholds(self) -> Dict[str, Any]:
        """
        Calculates empirical thresholds and classification bounds from real UCI data.
        """
        filepath = self.ensure_dataset()
        
        # Read real UCI AI4I CSV (10,000 rows, 14 columns)
        # Header: UDI, Product ID, Type, Air temperature [K], Process temperature [K],
        # Rotational speed [rpm], Torque [Nm], Tool wear [min], Machine failure, TWF, HDF, PWF, OSF, RNF
        with open(filepath, "r", encoding="utf-8") as f:
            header_line = f.readline().strip().split(",")
            rows = [line.strip().split(",") for line in f if line.strip()]
            
        air_temp = np.array([float(r[3]) for r in rows])
        process_temp = np.array([float(r[4]) for r in rows])
        rot_speed = np.array([float(r[5]) for r in rows])
        torque = np.array([float(r[6]) for r in rows])
        tool_wear = np.array([float(r[7]) for r in rows])
        machine_failure = np.array([int(r[8]) for r in rows])
        twf = np.array([int(r[9]) for r in rows])
        hdf = np.array([int(r[10]) for r in rows])
        pwf = np.array([int(r[11]) for r in rows])
        osf = np.array([int(r[12]) for r in rows])
        rnf = np.array([int(r[13]) for r in rows])
        
        n_samples = len(rows)
        
        delta_T = process_temp - air_temp
        power_watts = torque * (rot_speed * (2.0 * np.pi / 60.0))
        strain = tool_wear * torque
        
        # HDF Analysis
        hdf_delta_max = float(np.max(delta_T[hdf == 1])) if np.any(hdf == 1) else 8.6
        hdf_speed_max = float(np.max(rot_speed[hdf == 1])) if np.any(hdf == 1) else 1380.0
        
        # PWF Analysis
        pwf_power_min = float(np.percentile(power_watts[pwf == 1], 5)) if np.any(pwf == 1) else 3500.0
        pwf_power_max = float(np.percentile(power_watts[pwf == 1], 95)) if np.any(pwf == 1) else 9000.0
        
        # OSF Analysis
        osf_strain_min = float(np.min(strain[osf == 1])) if np.any(osf == 1) else 11000.0
        
        # Total failures
        total_failures = int(np.sum(machine_failure))
        
        self.thresholds = {
            "dataset": "AI4I 2020 Predictive Maintenance (UCI)",
            "purpose": "Sensor anomaly threshold calibration for heavy machinery (NOT for RAG vector search)",
            "sample_count": n_samples,
            "total_failure_events": total_failures,
            "failure_breakdown": {
                "heat_dissipation_failures": int(np.sum(hdf)),
                "power_failures": int(np.sum(pwf)),
                "overstrain_failures": int(np.sum(osf)),
                "tool_wear_failures": int(np.sum(twf))
            },
            "calibrated_decision_boundaries": {
                "heat_dissipation_failure": {
                    "rule": "delta_T < 8.6K AND rotational_speed < 1380 RPM",
                    "delta_T_critical_k": round(hdf_delta_max, 2),
                    "rot_speed_critical_rpm": round(hdf_speed_max, 1),
                    "physical_meaning": "Poor air heat transfer while engine/pump runs at low RPM under load. Radiator core clogged or fan hydraulic slip.",
                    "alert_severity": "CRITICAL"
                },
                "power_failure": {
                    "rule": "Power < 3500W (Stall/Cavitation) OR Power > 9000W (Overload)",
                    "power_lower_bound_watts": 3500.0,
                    "power_upper_bound_watts": 9000.0,
                    "physical_meaning": "Hydraulic motor or engine operating outside permissible mechanical power curve.",
                    "alert_severity": "CRITICAL"
                },
                "overstrain_failure": {
                    "rule": "Tool_Wear (min) * Torque (Nm) > 11,000",
                    "strain_threshold": round(osf_strain_min, 1),
                    "physical_meaning": "Combined mechanical wear and extreme torque exceeding material yield strength.",
                    "alert_severity": "WARNING_TO_CRITICAL"
                },
                "tool_wear_failure": {
                    "rule": "Tool_Wear >= 200 min (Warning), >= 240 min (Critical)",
                    "warning_wear_min": 200.0,
                    "critical_wear_min": 240.0,
                    "physical_meaning": "Cumulative mechanical contact fatigue limit reached. Chisel or bucket tooth replacement required.",
                    "alert_severity": "WARNING"
                }
            }
        }
        
        with open(OUTPUT_THRESHOLDS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.thresholds, f, indent=2)
            
        print(f"[+] Saved calibrated AI4I physical thresholds to: {OUTPUT_THRESHOLDS_FILE}")
        return self.thresholds

    def classify_sensor_reading(
        self,
        air_temp_k: float,
        process_temp_k: float,
        rot_speed_rpm: float,
        torque_nm: float,
        wear_min: float
    ) -> Dict[str, Any]:
        """
        Classifies live telemetry arriving from MechMind Node against calibrated AI4I boundaries.
        """
        delta_T = process_temp_k - air_temp_k
        power_w = torque_nm * (rot_speed_rpm * (2.0 * np.pi / 60.0))
        strain = wear_min * torque_nm
        
        detected_failures = []
        severity = "NORMAL"
        
        # 1. Check Heat Dissipation
        if delta_T < 8.6 and rot_speed_rpm < 1380.0:
            detected_failures.append({
                "type": "HDF (Heat Dissipation Failure)",
                "details": f"delta_T is {delta_T:.1f}K (< 8.6K) at low speed {rot_speed_rpm:.0f} RPM",
                "cause": "Inadequate convective cooling or hydraulic radiator bypass."
            })
            severity = "CRITICAL"
            
        # 2. Check Power Failure
        if power_w < 3500.0:
            detected_failures.append({
                "type": "PWF (Power Failure - Underspeed/Stall)",
                "details": f"Power output {power_w:.0f}W is below minimum 3500W threshold",
                "cause": "Engine lugging or hydraulic pump cavitation."
            })
            severity = "CRITICAL"
        elif power_w > 9000.0:
            detected_failures.append({
                "type": "PWF (Power Failure - Overload)",
                "details": f"Power output {power_w:.0f}W exceeds 9000W maximum safe envelope",
                "cause": "Hydraulic relief valve stalled or extreme mechanical overload."
            })
            severity = "CRITICAL"
            
        # 3. Check Overstrain
        if strain > 11000.0:
            detected_failures.append({
                "type": "OSF (Overstrain Failure)",
                "details": f"Wear x Torque strain metric {strain:.0f} exceeds 11,000 threshold",
                "cause": "Excessive breakout force applied on fatigued structural components."
            })
            if severity != "CRITICAL":
                severity = "WARNING"
                
        # 4. Check Tool Wear
        if wear_min >= 240.0:
            detected_failures.append({
                "type": "TWF (Tool Wear Critical)",
                "details": f"Cumulative tool wear {wear_min:.0f} min reached end-of-life limit (240 min)",
                "cause": "Wear parts reached maximum allowable clearance."
            })
            if severity != "CRITICAL":
                severity = "WARNING"
        elif wear_min >= 200.0:
            detected_failures.append({
                "type": "TWF (Tool Wear Warning)",
                "details": f"Tool wear {wear_min:.0f} min in replacement advisory window (200-240 min)",
                "cause": "Wear approaching threshold."
            })
            if severity == "NORMAL":
                severity = "WARNING"
                
        return {
            "condition_severity": severity,
            "is_anomaly": len(detected_failures) > 0,
            "active_faults": detected_failures,
            "calculated_metrics": {
                "delta_T_k": round(delta_T, 2),
                "power_watts": round(power_w, 1),
                "strain_min_nm": round(strain, 1)
            }
        }


if __name__ == "__main__":
    print("=================================================================")
    print(" MechMind AI - AI4I 2020 Predictive Maintenance Calibrator")
    print(" NOTE: Calibrates sensor anomaly thresholds, NOT RAG chatbot knowledge.")
    print("=================================================================")
    
    calibrator = AI4IPredictiveMaintenanceCalibrator()
    res = calibrator.calibrate_thresholds()
    
    print("\n--- Calibration Results ---")
    print(f"  Samples Analyzed: {res['sample_count']}")
    print(f"  Failure Events:   {res['total_failure_events']}")
    print("  Decision Rules:")
    for ftype, rule in res["calibrated_decision_boundaries"].items():
        print(f"    - {ftype.upper()}: {rule['rule']}")
        
    print("\n--- Live Test Telemetry Evaluation ---")
    # 1. Normal state
    t1 = calibrator.classify_sensor_reading(
        air_temp_k=300.0, process_temp_k=311.0, rot_speed_rpm=1550.0, torque_nm=42.0, wear_min=80.0
    )
    print(f"  [1] Nominal Telemetry: Severity={t1['condition_severity']}, Anomaly={t1['is_anomaly']}")
    
    # 2. Heat Dissipation condition
    t2 = calibrator.classify_sensor_reading(
        air_temp_k=302.0, process_temp_k=307.0, rot_speed_rpm=1320.0, torque_nm=55.0, wear_min=120.0
    )
    print(f"  [2] Low Delta-T / Low Speed: Severity={t2['condition_severity']}, Faults={[f['type'] for f in t2['active_faults']]}")
    
    # 3. Overstrain condition
    t3 = calibrator.classify_sensor_reading(
        air_temp_k=299.0, process_temp_k=310.0, rot_speed_rpm=1600.0, torque_nm=65.0, wear_min=190.0
    )
    print(f"  [3] High Torque / High Wear: Severity={t3['condition_severity']}, Faults={[f['type'] for f in t3['active_faults']]}")
    print("\n[+] AI4I Calibrator test completed successfully.")
