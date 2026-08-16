import numpy as np
from scipy import stats

def tost_equivalence(y_a, y_b, margin=0.15):
    """
    Two One-Sided Tests (TOST) for practical equivalence of two independent groups
    evaluated on joint normalized transient representations.
    """
    y_a = np.asarray(y_a, dtype=float)
    y_b = np.asarray(y_b, dtype=float)

    if y_a.ndim > 1:
        y_a = np.mean(y_a, axis=1)
    if y_b.ndim > 1:
        y_b = np.mean(y_b, axis=1)

    n_a = len(y_a)
    n_b = len(y_b)

    if n_a < 2 or n_b < 2:
        return {
            "difference": 0.0,
            "t1": 0.0,
            "t2": 0.0,
            "p1": 1.0,
            "p2": 1.0,
            "p_equivalence": 1.0,
            "equivalent": False,
            "margin": float(margin)
        }

    mean_a = np.mean(y_a)
    mean_b = np.mean(y_b)

    var_a = np.var(y_a, ddof=1)
    var_b = np.var(y_b, ddof=1)

    pooled_se = np.sqrt(((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2)) * np.sqrt(1/n_a + 1/n_b)
    if pooled_se == 0:
        pooled_se = 1e-6

    diff = mean_a - mean_b

    t1 = (diff + margin) / pooled_se
    t2 = (diff - margin) / pooled_se

    df = n_a + n_b - 2

    p1 = 1.0 - stats.t.cdf(t1, df)
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
    """
    Runs TOST practical equivalence test across 3 subgroups (feeder_1, feeder_2, feeder_3)
    and reports average values across subgroups.
    """
    from src.statistics.data import load_dataset_2, extract_joint_representation

    df = load_dataset_2()
    subgroups = ["feeder_1", "feeder_2", "feeder_3"]
    diff_list = []
    p_eq_list = []

    print("--- Running TOST Practical Equivalence Testing Across 3 Subgroups ---")
    margin = 0.15
    for sg in subgroups:
        sub_df = df[df["gt_feeder_id"] == sg]
        if len(sub_df) > 0:
            _, Y_sg = extract_joint_representation(sub_df)
            event_a_mask = (sub_df["gt_event_type"] == "transformer_inrush").values
            event_b_mask = (sub_df["gt_event_type"] == "capacitor_switching").values

            Y_a = Y_sg[event_a_mask]
            Y_b = Y_sg[event_b_mask]

            if len(Y_a) >= 2 and len(Y_b) >= 2:
                res_tost = tost_equivalence(Y_a, Y_b, margin=margin)
                diff_list.append(res_tost["difference"])
                p_eq_list.append(res_tost["p_equivalence"])
                print(f"Subgroup {sg} (Inrush N={len(Y_a)}, Cap Switch N={len(Y_b)}): Mean Diff = {res_tost['difference']:.6f}, p-equiv = {res_tost['p_equivalence']:.4f}")

    avg_diff = float(np.mean(diff_list)) if diff_list else 0.0
    avg_p_eq = float(np.mean(p_eq_list)) if p_eq_list else 1.0

    print(f"\nAverage Mean Difference across 3 subgroups: {avg_diff:.6f}")
    print(f"Average TOST p-value across 3 subgroups:     {avg_p_eq:.4f}")

    return {
        "subgroups": subgroups,
        "diff_per_subgroup": diff_list,
        "p_eq_per_subgroup": p_eq_list,
        "avg_diff": avg_diff,
        "avg_p_eq": avg_p_eq
    }


if __name__ == "__main__":
    run_equivalence_analysis()
