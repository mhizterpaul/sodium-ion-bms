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

def compute_observability_magnitude(v_norm_abc: np.ndarray, i_norm_abc: np.ndarray) -> tuple[float, float]:
    v_norm = np.asarray(v_norm_abc, dtype=float)
    i_norm = np.asarray(i_norm_abc, dtype=float)

    mag_v = float(np.sqrt(np.mean(v_norm**2))) if v_norm.size > 0 else 0.0
    mag_i = float(np.sqrt(np.mean(i_norm**2))) if i_norm.size > 0 else 0.0

    return mag_v, mag_i

def run_dataset_2_factorial_analysis():
    """
    Factorial ANOVA / Mixed-Effects Analysis for Dataset 2 Single-Event Observability (Q1 & Q4).
    """
    data_path = Path(__file__).parent.parent / "simulation" / "dataset_2.csv"
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset 2 CSV not found at {data_path}. Run dataset generation first.")

    df = pd.read_csv(data_path)

    v_mags = []
    i_mags = []

    for idx, row in df.iterrows():
        v_norm = parse_json_array(row.get("obs_norm_transient_v"))
        i_norm = parse_json_array(row.get("obs_norm_transient_i"))
        mv, mi = compute_observability_magnitude(v_norm, i_norm)
        v_mags.append(mv)
        i_mags.append(mi)

    df["voltage_observability_magnitude"] = v_mags
    df["current_observability_magnitude"] = i_mags

    print("--- Dataset 2 Single-Event Observability Factorial Analysis (Q1 & Q4) ---")

    grouped = df.groupby(["gt_event_type", "gt_transformer_spec_id"])

    summary_rows = []
    for (ev_type, tx_spec), group in grouped:
        summary_rows.append({
            "event_type": ev_type,
            "transformer_spec_id": tx_spec,
            "n_samples": len(group),
            "mean_v_observability": float(np.mean(group["voltage_observability_magnitude"])),
            "mean_i_observability": float(np.mean(group["current_observability_magnitude"]))
        })

    summary_df = pd.DataFrame(summary_rows)

    event_groups = [g["current_observability_magnitude"].values for _, g in df.groupby("gt_event_type") if len(g) > 1 and np.std(g["current_observability_magnitude"].values) > 1e-12]
    tx_groups = [g["current_observability_magnitude"].values for _, g in df.groupby("gt_transformer_spec_id") if len(g) > 1 and np.std(g["current_observability_magnitude"].values) > 1e-12]

    if len(event_groups) > 1:
        f_event, p_event = stats.f_oneway(*event_groups)
    else:
        f_event, p_event = 0.0, 1.0

    if len(tx_groups) > 1:
        f_tx, p_tx = stats.f_oneway(*tx_groups)
    else:
        f_tx, p_tx = 0.0, 1.0

    print("\nFactorial Main Effects (Current Observability Magnitude):")
    print(f"  Q1: Event Type Main Effect:          F = {f_event:.4f}, p = {p_event:.4e}")
    print(f"  Q4: Transformer Spec Main Effect:    F = {f_tx:.4f}, p = {p_tx:.4e}")

    results = {
        "summary": summary_df,
        "f_event": float(f_event),
        "p_event": float(p_event),
        "f_transformer": float(f_tx),
        "p_transformer": float(p_tx)
    }
    return results

if __name__ == "__main__":
    run_dataset_2_factorial_analysis()
