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
    Factorial ANOVA & Levene/Brown-Forsythe Variance Analysis for Dataset 2 Single-Event Observability & Transformer Spec Variation (Q1 & Q4).
      - Q1: Measures observability differences across event classes/types (8 equipment types + fault combinations LG, LL, LLG, LLL, LC, LLC).
      - Q4: Measures the variation in transformer measurements (voltage/current magnitudes and waveform variance) due to specification variation across the 3 LV feeder groups.
    """
    data_path = Path(__file__).parent.parent / "simulation" / "dataset_2.csv"
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset 2 CSV not found at {data_path}. Run dataset generation first.")

    df = pd.read_csv(data_path)

    subgroups = ["feeder_1", "feeder_2", "feeder_3"]
    f_event_list = []
    p_event_list = []
    f_tx_var_list = []
    p_tx_var_list = []

    print("--- Dataset 2 Single-Event Observability & Transformer Spec Variation Analysis (Q1 & Q4) ---")

    for sg in subgroups:
        sub_df = df[df["gt_feeder_id"] == sg]
        if len(sub_df) > 0:
            # Q1: Main effect of event types on observability magnitude
            event_groups = [g["single_event_residual_v_magnitude"].values for _, g in sub_df.groupby("gt_event_type") if len(g) > 1 and np.std(g["single_event_residual_v_magnitude"].values) > 1e-12]
            f_ev, p_ev = stats.f_oneway(*event_groups) if len(event_groups) > 1 else (0.0, 1.0)
            f_event_list.append(f_ev)
            p_event_list.append(p_ev)

            # Q4: Variation in transformer measurements across transformer specifications within LV group
            tx_groups = [g["single_event_residual_v_magnitude"].values for _, g in sub_df.groupby("gt_transformer_spec_id") if len(g) > 1]
            valid_tx_groups = [tg for tg in tx_groups if np.std(tg) > 1e-12]

            if len(valid_tx_groups) > 1:
                stat_tx_var, p_tx_var = stats.levene(*valid_tx_groups, center='median')
            else:
                stat_tx_var, p_tx_var = 0.0, 1.0

            f_tx_var_list.append(stat_tx_var)
            p_tx_var_list.append(p_tx_var)

            print(f"Subgroup {sg} (N={len(sub_df)}):")
            print(f"  Q1 Event Type Main Effect:                     F = {f_ev:.4f}, p = {p_ev:.4e}")
            print(f"  Q4 Transformer Measurement Variation (Levene): F = {stat_tx_var:.4f}, p = {p_tx_var:.4e}")

    avg_f_event = float(np.mean(f_event_list)) if f_event_list else 0.0
    avg_p_event = float(np.mean(p_event_list)) if p_event_list else 1.0
    avg_f_tx_var = float(np.mean(f_tx_var_list)) if f_tx_var_list else 0.0
    avg_p_tx_var = float(np.mean(p_tx_var_list)) if p_tx_var_list else 1.0

    print("\n--- Average Observability and Transformer Spec Variation Across All Subgroups ---")
    print(f"Average Q1 Event Type Main Effect:                     F = {avg_f_event:.4f}, p = {avg_p_event:.4e}")
    print(f"Average Q4 Transformer Measurement Variation (Levene): F = {avg_f_tx_var:.4f}, p = {avg_p_tx_var:.4e}")

    results = {
        "avg_f_event": avg_f_event,
        "avg_p_event": avg_p_event,
        "avg_f_tx_var": avg_f_tx_var,
        "avg_p_tx_var": avg_p_tx_var
    }
    return results

if __name__ == "__main__":
    run_dataset_2_factorial_analysis()
