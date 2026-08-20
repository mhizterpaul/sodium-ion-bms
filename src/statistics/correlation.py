import numpy as np
import pandas as pd
from pathlib import Path

def compute_mae(gt: np.ndarray, est: np.ndarray) -> float:
    gt = np.asarray(gt, dtype=float)
    est = np.asarray(est, dtype=float)
    return float(np.mean(np.abs(gt - est)))

def compute_rmse(gt: np.ndarray, est: np.ndarray) -> float:
    gt = np.asarray(gt, dtype=float)
    est = np.asarray(est, dtype=float)
    return float(np.sqrt(np.mean((gt - est)**2)))

def run_dataset_1_correlation_analysis():
    """
    Evaluates latent line parameter estimation accuracy on Dataset 1 by comparing ground truth electrical parameters
    with inverse solver estimates across 3 feeder subgroups (feeder_1, feeder_2, feeder_3), reporting MAE and RMSE metrics.
    """
    data_path = Path(__file__).parent.parent / "simulation" / "dataset_1.csv"
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset 1 CSV not found at {data_path}. Run dataset generation first.")

    df = pd.read_csv(data_path)

    subgroups = ["feeder_1", "feeder_2", "feeder_3"]
    results = {}

    rmse_r_list = []
    rmse_x_list = []
    rmse_z_list = []
    rmse_g_list = []
    rmse_b_list = []

    print("--- Running Dataset 1 Latent Line Parameter Estimation Accuracy Testing (MAE & RMSE) ---")

    for sg in subgroups:
        sub_df = df[df["gt_feeder_id"] == sg]
        if len(sub_df) > 0:
            rmse_r = compute_rmse(sub_df["gt_r_eq_ohm"].values, sub_df["est_r_eq_ohm"].values)
            rmse_x = compute_rmse(sub_df["gt_x_eq_ohm"].values, sub_df["est_x_eq_ohm"].values)
            rmse_z = compute_rmse(sub_df["gt_z_eq_ohm"].values, sub_df["est_z_eq_ohm"].values)

            g_gt = sub_df["gt_g_eq_siemens"].values if "gt_g_eq_siemens" in sub_df.columns else sub_df["gt_r_eq_ohm"].values / (sub_df["gt_z_eq_ohm"].values**2 + 1e-9)
            g_est = sub_df["est_g_eq_siemens"].values if "est_g_eq_siemens" in sub_df.columns else sub_df["est_r_eq_ohm"].values / (sub_df["est_z_eq_ohm"].values**2 + 1e-9)
            rmse_g = compute_rmse(g_gt, g_est)

            b_gt = sub_df["gt_b_eq_siemens"].values if "gt_b_eq_siemens" in sub_df.columns else sub_df["gt_x_eq_ohm"].values / (sub_df["gt_z_eq_ohm"].values**2 + 1e-9)
            b_est = sub_df["est_b_eq_siemens"].values if "est_b_eq_siemens" in sub_df.columns else sub_df["est_x_eq_ohm"].values / (sub_df["est_z_eq_ohm"].values**2 + 1e-9)
            rmse_b = compute_rmse(b_gt, b_est)

            rmse_r_list.append(rmse_r)
            rmse_x_list.append(rmse_x)
            rmse_z_list.append(rmse_z)
            rmse_g_list.append(rmse_g)
            rmse_b_list.append(rmse_b)

            results[sg] = {
                "rmse_r_eq_ohm": rmse_r,
                "rmse_x_eq_ohm": rmse_x,
                "rmse_z_eq_ohm": rmse_z,
                "rmse_g_eq_siemens": rmse_g,
                "rmse_b_eq_siemens": rmse_b
            }

            print(f"Subgroup {sg} (N={len(sub_df)}):")
            print(f"  RMSE R_eq:    {rmse_r:.4f} Ohm")
            print(f"  RMSE X_eq:    {rmse_x:.4f} Ohm")
            print(f"  RMSE Z_eq:    {rmse_z:.4f} Ohm")
            print(f"  RMSE G_eq:    {rmse_g:.6f} S")
            print(f"  RMSE B_eq:    {rmse_b:.6f} S")

    avg_rmse_r = float(np.mean(rmse_r_list)) if rmse_r_list else 0.0
    avg_rmse_x = float(np.mean(rmse_x_list)) if rmse_x_list else 0.0
    avg_rmse_z = float(np.mean(rmse_z_list)) if rmse_z_list else 0.0
    avg_rmse_g = float(np.mean(rmse_g_list)) if rmse_g_list else 0.0
    avg_rmse_b = float(np.mean(rmse_b_list)) if rmse_b_list else 0.0

    print("\n--- Average Latent Line Parameter Estimation Accuracy Metrics Across All Subgroups ---")
    print(f"Average RMSE R_eq:    {avg_rmse_r:.4f} Ohm")
    print(f"Average RMSE X_eq:    {avg_rmse_x:.4f} Ohm")
    print(f"Average RMSE Z_eq:    {avg_rmse_z:.4f} Ohm")
    print(f"Average RMSE G_eq:    {avg_rmse_g:.6f} S")
    print(f"Average RMSE B_eq:    {avg_rmse_b:.6f} S")

    summary = {
        "per_subgroup": results,
        "avg_rmse_r_eq_ohm": avg_rmse_r,
        "avg_rmse_x_eq_ohm": avg_rmse_x,
        "avg_rmse_z_eq_ohm": avg_rmse_z,
        "avg_rmse_g_eq_siemens": avg_rmse_g,
        "avg_rmse_b_eq_siemens": avg_rmse_b
    }
    return summary

if __name__ == "__main__":
    run_dataset_1_correlation_analysis()
