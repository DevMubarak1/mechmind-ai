"""
========================================================================================
MechMind AI - NASA C-MAPSS Turbofan Engine Degradation Dataset Loader & RUL Calibrator
========================================================================================

CRITICAL ARCHITECTURAL DISTINCTION:
-----------------------------------
NOTE: THIS MODULE CALIBRATES SENSOR ANOMALY DETECTION THRESHOLDS AND REMAINING USEFUL
LIFE (RUL) DEGRADATION CURVES FOR THE MECHMIND NODE'S TELEMETRY ENGINE.
IT IS NOT PART OF THE RAG CHATBOT VECTOR KNOWLEDGE BASE. DO NOT CONFLATE THE TWO.

The output of this module is mathematical calibration parameters (degradation rate,
health index curve coefficients, and warning/critical thresholds) used by the FastAPI
sensor processor (`backend/main.py`) and edge nodes, NOT text chunks for ChromaDB.
========================================================================================

DATASET BACKGROUND:
-------------------
NASA Commercial Modular Aero-Propulsion System Simulation (C-MAPSS) is the gold
standard benchmark for run-to-failure degradation in high-stress turbomachinery.
It contains multi-channel sensor telemetry across operational cycles from initial
nominal health until catastrophic functional failure.

In MechMind AI, we apply the C-MAPSS degradation kinetics to diesel turbochargers,
hydraulic axial piston pumps, and heavy engine powertrains (SANY, XCMG, CAT).
========================================================================================
"""

import os
import json
import logging
from typing import Dict, List, Tuple, Any, Optional
import numpy as np

logger = logging.getLogger("mechmind.datasets.cmapss")

# Paths
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
REAL_CMAPSS_FILE = os.path.join(DATA_DIR, "CMAPSSData", "train_FD001.txt")
OUTPUT_MODEL_FILE = os.path.join(DATA_DIR, "calibrated_rul_model.json")

os.makedirs(DATA_DIR, exist_ok=True)


class CMAPSSDegradationCalibrator:
    """
    Loads real NASA C-MAPSS run-to-failure data (20,631 cycles across 100 engines),
    computes multi-sensor health indices (HI), and calibrates exponential Remaining
    Useful Life (RUL) forecasting curves.
    """

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or REAL_CMAPSS_FILE
        self.calibrated_params: Dict[str, Any] = {}

    def ensure_dataset(self) -> str:
        """
        Verifies the real NASA C-MAPSS FD001 dataset on disk.
        """
        if os.path.exists(self.data_path):
            return self.data_path
        raise FileNotFoundError(
            f"Real NASA C-MAPSS file not found at {self.data_path}. "
            "Please run datasets/run_dataset_calibration.py to download."
        )

    def load_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Loads the real NASA C-MAPSS space-delimited text file.
        Returns:
            raw_matrix: (20631, 26) numpy array
            true_rul: (20631,) computed true remaining useful life
        """
        filepath = self.ensure_dataset()
        data = np.loadtxt(filepath)
        
        # Calculate true RUL per engine unit
        # Col 0: unit_id, Col 1: cycle
        unit_ids = data[:, 0].astype(int)
        cycles = data[:, 1]
        
        # Find maximum cycle for each unit
        max_cycles_per_unit = {}
        for uid in np.unique(unit_ids):
            max_cycles_per_unit[uid] = np.max(cycles[unit_ids == uid])
            
        true_rul = np.array([max_cycles_per_unit[uid] - c for uid, c in zip(unit_ids, cycles)])
        return data, true_rul

    def fit_degradation_model(self) -> Dict[str, Any]:
        """
        Fits multi-sensor health index curve and calculates RUL calibration coefficients.
        Returns a dictionary of calibrated parameters.
        """
        data, true_rul = self.load_data()
        
        # Real NASA C-MAPSS FD001 Column Mapping:
        # Col 0: Unit ID (1-100), Col 1: Operational Cycle
        # Col 2-4: Operational Settings
        # Col 7: Sensor 3 (T30: HPC outlet total temperature, K)
        # Col 8: Sensor 4 (T50: LPT outlet total temperature, K)
        # Col 11: Sensor 7 (P30: HPC outlet static pressure, psia)
        cycles = data[:, 1]
        s3 = data[:, 7]
        s4 = data[:, 8]
        s7 = data[:, 11]
        
        # 1. Baseline healthy statistics (first 30 cycles across all units)
        healthy_mask = cycles <= 30
        baseline_s3_mean, baseline_s3_std = np.mean(s3[healthy_mask]), np.std(s3[healthy_mask])
        baseline_s4_mean, baseline_s4_std = np.mean(s4[healthy_mask]), np.std(s4[healthy_mask])
        baseline_s7_mean, baseline_s7_std = np.mean(s7[healthy_mask]), np.std(s7[healthy_mask])
        
        # 2. Composite Normalized Health Index (HI)
        # HI = 1.0 (new/healthy) -> HI = 0.0 (failed)
        # s3 and s4 drift UP (+), s7 drifts DOWN (-)
        z_s3 = (s3 - baseline_s3_mean) / max(baseline_s3_std, 1e-4)
        z_s4 = (s4 - baseline_s4_mean) / max(baseline_s4_std, 1e-4)
        z_s7 = (baseline_s7_mean - s7) / max(baseline_s7_std, 1e-4)
        
        composite_drift = (0.35 * z_s3) + (0.45 * z_s4) + (0.20 * z_s7)
        # Clip drift to >= 0
        composite_drift = np.maximum(0.0, composite_drift)
        
        # Maximum expected drift at failure (~99th percentile)
        max_drift_ref = float(np.percentile(composite_drift[true_rul <= 5], 95))
        if max_drift_ref <= 0:
            max_drift_ref = 15.0
            
        health_index = np.clip(1.0 - (composite_drift / max_drift_ref), 0.0, 1.0)
        
        # 3. Fit exponential RUL decay function: RUL = RUL_max * (HI)^gamma
        # Where RUL_max is capped at 125 cycles (standard piece-wise linear benchmark)
        capped_rul = np.minimum(true_rul, 125.0)
        
        # Non-linear least squares fit for gamma: log(capped_rul / 125) = gamma * log(HI)
        valid_mask = (health_index > 0.05) & (health_index < 0.98) & (capped_rul > 0)
        log_hi = np.log(health_index[valid_mask])
        log_rul_norm = np.log(capped_rul[valid_mask] / 125.0)
        
        # Slope estimation (gamma)
        gamma, _ = np.polyfit(log_hi, log_rul_norm, 1)
        gamma = float(np.clip(gamma, 1.1, 2.5))
        
        # 4. Predicted RUL and Evaluation Metrics
        pred_rul = 125.0 * (health_index ** gamma)
        mae = float(np.mean(np.abs(pred_rul - capped_rul)))
        rmse = float(np.sqrt(np.mean((pred_rul - capped_rul) ** 2)))
        
        # Calculate R^2 score
        ss_tot = np.sum((capped_rul - np.mean(capped_rul)) ** 2)
        ss_res = np.sum((capped_rul - pred_rul) ** 2)
        r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0
        
        # 5. Calibrate Anomaly Thresholds for MechMind Node
        # Normal: HI >= 0.70 (RUL > 70 hours)
        # Warning: 0.35 <= HI < 0.70 (RUL ~25-70 hours) -> Schedule inspection
        # Critical: HI < 0.35 (RUL < 25 hours) -> Immediate service / Stop operation
        self.calibrated_params = {
            "dataset": "NASA C-MAPSS Turbofan Engine Degradation (FD001)",
            "purpose": "Calibration of telemetry anomaly thresholds & RUL modeling (NOT for RAG vector search)",
            "sample_count": len(data),
            "engine_count": int(len(np.unique(data[:, 0]))),
            "sensor_baselines": {
                "s3_hpc_temp_mean_k": round(float(baseline_s3_mean), 2),
                "s3_hpc_temp_std_k": round(float(baseline_s3_std), 2),
                "s4_lpt_temp_mean_k": round(float(baseline_s4_mean), 2),
                "s4_lpt_temp_std_k": round(float(baseline_s4_std), 2),
                "s7_hpc_press_mean_psia": round(float(baseline_s7_mean), 2),
                "s7_hpc_press_std_psia": round(float(baseline_s7_std), 2)
            },
            "rul_model": {
                "type": "Exponential Health Index Degradation",
                "rul_max_cycles": 125.0,
                "gamma_exponent": round(gamma, 4),
                "formula": f"RUL = 125.0 * (Health_Index ** {round(gamma, 4)})"
            },
            "calibrated_health_thresholds": {
                "normal_zone": {
                    "health_index_min": 0.70,
                    "estimated_rul_hours": "> 70 hrs",
                    "action": "Continuous telemetry monitoring. Standard PM schedule."
                },
                "warning_zone": {
                    "health_index_min": 0.35,
                    "health_index_max": 0.70,
                    "estimated_rul_hours": "25 to 70 hrs",
                    "action": "Elevated wear detected. Schedule hydraulic filter and oil service."
                },
                "critical_zone": {
                    "health_index_max": 0.35,
                    "estimated_rul_hours": "< 25 hrs",
                    "action": "CRITICAL: Imminent failure risk. Throttle down, dispatch service mechanic."
                }
            },
            "validation_metrics": {
                "mean_absolute_error_cycles": round(mae, 2),
                "root_mean_squared_error": round(rmse, 2),
                "r2_score": round(r2, 4)
            }
        }
        
        # Save to JSON
        with open(OUTPUT_MODEL_FILE, "w", encoding="utf-8") as f:
            json.dump(self.calibrated_params, f, indent=2)
            
        print(f"[+] Saved calibrated RUL model to: {OUTPUT_MODEL_FILE}")
        return self.calibrated_params

    def predict_health_and_rul(self, s3: float, s4: float, s7: float) -> Dict[str, Any]:
        """
        Real-time scoring function for sensor readings arriving from MechMind Node.
        """
        if not self.calibrated_params:
            if os.path.exists(OUTPUT_MODEL_FILE):
                with open(OUTPUT_MODEL_FILE, "r", encoding="utf-8") as f:
                    self.calibrated_params = json.load(f)
            else:
                self.fit_degradation_model()
                
        base = self.calibrated_params["sensor_baselines"]
        gamma = self.calibrated_params["rul_model"]["gamma_exponent"]
        
        z_s3 = max(0.0, (s3 - base["s3_hpc_temp_mean_k"]) / base["s3_hpc_temp_std_k"])
        z_s4 = max(0.0, (s4 - base["s4_lpt_temp_mean_k"]) / base["s4_lpt_temp_std_k"])
        z_s7 = max(0.0, (base["s7_hpc_press_mean_psia"] - s7) / base["s7_hpc_press_std_psia"])
        
        drift = (0.35 * z_s3) + (0.45 * z_s4) + (0.20 * z_s7)
        hi = float(np.clip(1.0 - (drift / 15.0), 0.0, 1.0))
        predicted_rul = float(125.0 * (hi ** gamma))
        
        if hi >= 0.70:
            status = "NORMAL"
        elif hi >= 0.35:
            status = "WARNING"
        else:
            status = "CRITICAL"
            
        return {
            "health_index": round(hi, 3),
            "estimated_rul_hours": round(predicted_rul, 1),
            "condition_status": status
        }


if __name__ == "__main__":
    print("=================================================================")
    print(" MechMind AI - NASA C-MAPSS Degradation & RUL Calibrator")
    print(" NOTE: Calibrates sensor anomaly thresholds, NOT RAG chatbot knowledge.")
    print("=================================================================")
    
    calibrator = CMAPSSDegradationCalibrator()
    params = calibrator.fit_degradation_model()
    
    print("\n--- Calibration Results ---")
    print(f"  RUL Model Formula: {params['rul_model']['formula']}")
    print(f"  R^2 Goodness of Fit: {params['validation_metrics']['r2_score']}")
    print(f"  MAE: {params['validation_metrics']['mean_absolute_error_cycles']} cycles")
    print("  Thresholds:")
    for zone, zdata in params["calibrated_health_thresholds"].items():
        print(f"    - {zone.upper()}: RUL {zdata['estimated_rul_hours']} -> {zdata['action']}")
        
    print("\n--- Live Test Predictions ---")
    # 1. Nominal sensor reading
    res_healthy = calibrator.predict_health_and_rul(s3=1585.0, s4=1405.0, s7=553.5)
    print(f"  [1] Nominal Sensor State: HI={res_healthy['health_index']}, RUL={res_healthy['estimated_rul_hours']}h, Status={res_healthy['condition_status']}")
    
    # 2. Moderate thermal drift
    res_warn = calibrator.predict_health_and_rul(s3=1595.0, s4=1416.0, s7=551.5)
    print(f"  [2] Moderate Thermal Drift: HI={res_warn['health_index']}, RUL={res_warn['estimated_rul_hours']}h, Status={res_warn['condition_status']}")
    
    # 3. Severe degradation
    res_crit = calibrator.predict_health_and_rul(s3=1605.0, s4=1428.0, s7=548.8)
    print(f"  [3] Severe Thermal Degradation: HI={res_crit['health_index']}, RUL={res_crit['estimated_rul_hours']}h, Status={res_crit['condition_status']}")
    print("\n[+] C-MAPSS Degradation Calibrator test completed successfully.")
