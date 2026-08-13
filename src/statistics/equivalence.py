import numpy as np
from scipy import stats

def tost_equivalence(y_a, y_b, margin=0.05):
    """
    Two One-Sided Tests (TOST) for equivalence of two independent groups.
    H01: difference <= -margin
    H02: difference >= +margin
    Only if both nulls are rejected do we conclude the groups are practically equivalent.
    """
    y_a = np.array(y_a)
    y_b = np.array(y_b)

    n_a = len(y_a)
    n_b = len(y_b)

    mean_a = np.mean(y_a)
    mean_b = np.mean(y_b)

    var_a = np.var(y_a, ddof=1) if n_a > 1 else 0.0
    var_b = np.var(y_b, ddof=1) if n_b > 1 else 0.0

    # Pooled standard error
    pooled_se = np.sqrt(((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2)) * np.sqrt(1/n_a + 1/n_b)
    if pooled_se == 0:
        pooled_se = 1e-6

    diff = mean_a - mean_b

    # t-statistics
    t1 = (diff + margin) / pooled_se
    t2 = (diff - margin) / pooled_se

    df = n_a + n_b - 2

    # p-values
    p1 = 1 - stats.t.cdf(t1, df)
    p2 = stats.t.cdf(t2, df)

    p_equivalence = max(p1, p2)
    equivalent = bool(p_equivalence < 0.05)

    return {
        "difference": float(diff),
        "t1": float(t1),
        "t2": float(t2),
        "p1": float(p1),
        "p2": float(p2),
        "p_equivalence": float(p_equivalence),
        "equivalent": equivalent,
        "margin": float(margin)
    }


def run_equivalence_analysis():
    import json
    from pathlib import Path

    data_path = Path(__file__).parent.parent / "simulation" / "dataset_2.json"
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset 2 not found at {data_path}. Run dataset generation first.")

    with open(data_path, "r") as f:
        dataset_2 = json.load(f)

    y_a_wavelet = []
    y_b_wavelet = []
    for item in dataset_2:
        event = item["ground_truth"]["simulated_event"]
        pcc_id = item["observations"]["pcc_id"]
        val = item["observations"]["features"].get(f"{pcc_id}_v_0_cD1_std", 0.0)
        if event == "transformer_inrush":
            y_a_wavelet.append(val)
        elif event == "capacitor_switching":
            y_b_wavelet.append(val)

    print("--- Running TOST Practical Equivalence Testing ---")
    if len(y_a_wavelet) > 1 and len(y_b_wavelet) > 1:
        res_tost = tost_equivalence(y_a_wavelet, y_b_wavelet, margin=0.15)
        print(f"Mean Diff:            {res_tost['difference']:.6f}")
        print(f"Equivalence Margin:   {res_tost['margin']:.4f}")
        print(f"TOST p-value:         {res_tost['p_equivalence']:.4f}")
        print(f"Practically Equiv?:   {res_tost['equivalent']}")
        return res_tost
    else:
        print("Skip: Not enough samples for TOST equivalence testing.")
        return None


if __name__ == "__main__":
    run_equivalence_analysis()
