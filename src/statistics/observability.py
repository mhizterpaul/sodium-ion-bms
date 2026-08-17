import numpy as np
from src.statistics.dependence import distance_correlation, hsic_statistic

def run_observability_analysis():
    """
    Tests whether the joint station-boundary representation Y_joint = [FFT + SWT]
    carries statistically significant observability regarding hidden network states and perturbations
    across 3 subgroups (feeder_1, feeder_2, feeder_3), reporting average values across subgroups.
    """
    from src.statistics.data import load_dataset_2, extract_joint_representation

    df = load_dataset_2()
    subgroups = ["feeder_1", "feeder_2", "feeder_3"]
    dcor_list = []
    hsic_list = []

    print("--- Test 5: Observability Across 3 Subgroups ---")
    for sg in subgroups:
        sub_df = df[df["gt_feeder_id"] == sg]
        if len(sub_df) > 0:
            X_sg, Y_sg = extract_joint_representation(sub_df)
            dcor_sg = distance_correlation(X_sg, Y_sg)
            hsic_sg = hsic_statistic(X_sg, Y_sg)
            dcor_list.append(dcor_sg)
            hsic_list.append(hsic_sg)
            print(f"Subgroup {sg} (N={len(sub_df)}): Joint dCor = {dcor_sg:.6f}, Joint HSIC = {hsic_sg:.6f}")

    avg_dcor = float(np.mean(dcor_list)) if dcor_list else 0.0
    avg_hsic = float(np.mean(hsic_list)) if hsic_list else 0.0

    print(f"\nAverage Joint dCor across 3 subgroups: {avg_dcor:.6f}")
    print(f"Average Joint HSIC across 3 subgroups: {avg_hsic:.6f}")

    return {
        "subgroups": subgroups,
        "dcor_per_subgroup": dcor_list,
        "hsic_per_subgroup": hsic_list,
        "avg_dcor": avg_dcor,
        "avg_hsic": avg_hsic
    }

if __name__ == "__main__":
    run_observability_analysis()
