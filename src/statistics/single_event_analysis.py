import json
import numpy as np
import pandas as pd
from pathlib import Path
from scipy import stats

def parse_json_array(val):
    if pd.isna(val) or val is None or val == "" or val == "[]" or val == "{}":
        return np.array([])
    if isinstance(val, (list, tuple, np.ndarray)):
        return np.asarray(val)
    try:
        parsed = json.loads(val)
        return np.asarray(parsed)
    except Exception:
        return np.array([])

def run_dataset_2_factorial_analysis():
    """
    Factorial ANOVA / Mixed-Effects Analysis for Dataset 2 Single-Event Observability & Residual Variability (Q1 & Q4).
    Evaluates:
      1. Main effect of event class/type (8 equipment types + fault combinations LG, LL, LLG, LLL, LC, LLC)
      2. Main effect of transformer specification
      3. Residual composition variability across 3 feeder subgroups.
    """
    data_path = Path(__file__).parent.parent / "simulation" / "dataset_2.csv"
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset 2 CSV not found at {data_path}. Run dataset generation first.")

    df = pd.read_csv(data_path)

    subgroups = ["feeder_1", "feeder_2", "feeder_3"]
    f_event_list = []
    p_event_list = []
    f_tx_list = []
    p_tx_list = []

    print("--- Dataset 2 Single-Event Observability & Residual Variability Factorial Analysis (Q1 & Q4) ---")

    for sg in subgroups:
        sub_df = df[df["gt_feeder_id"] == sg]
        if len(sub_df) > 0:
            event_groups = [g["single_event_residual_variability"].values for _, g in sub_df.groupby("gt_event_type") if len(g) > 1 and np.std(g["single_event_residual_variability"].values) > 1e-12]
            tx_groups = [g["single_event_residual_variability"].values for _, g in sub_df.groupby("gt_transformer_spec_id") if len(g) > 1 and np.std(g["single_event_residual_variability"].values) > 1e-12]

            f_ev, p_ev = stats.f_oneway(*event_groups) if len(event_groups) > 1 else (0.0, 1.0)
            f_tx, p_tx = stats.f_oneway(*tx_groups) if len(tx_groups) > 1 else (0.0, 1.0)

            f_event_list.append(f_ev)
            p_event_list.append(p_ev)
            f_tx_list.append(f_tx)
            p_tx_list.append(p_tx)

            print(f"Subgroup {sg} (N={len(sub_df)}):")
            print(f"  Q1 Event Type Effect:       F = {f_ev:.4f}, p = {p_ev:.4e}")
            print(f"  Q4 Transformer Spec Effect: F = {f_tx:.4f}, p = {p_tx:.4e}")

    avg_f_event = float(np.mean(f_event_list)) if f_event_list else 0.0
    avg_p_event = float(np.mean(p_event_list)) if p_event_list else 1.0
    avg_f_tx = float(np.mean(f_tx_list)) if f_tx_list else 0.0
    avg_p_tx = float(np.mean(p_tx_list)) if p_tx_list else 1.0

    print("\n--- Average Factorial Main Effects Across All Subgroups ---")
    print(f"Average Q1 Event Type Effect:       F = {avg_f_event:.4f}, p = {avg_p_event:.4e}")
    print(f"Average Q4 Transformer Spec Effect: F = {avg_f_tx:.4f}, p = {avg_p_tx:.4e}")

    results = {
        "avg_f_event": avg_f_event,
        "avg_p_event": avg_p_event,
        "avg_f_tx": avg_f_tx,
        "avg_p_tx": avg_p_tx
    }
    return results

if __name__ == "__main__":
    run_dataset_2_factorial_analysis()
