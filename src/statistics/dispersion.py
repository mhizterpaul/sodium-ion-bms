import numpy as np

def dispersion_statistic(Y, groups):
    """
    Multivariate homogeneity of group dispersions (PERMDISP-like).
    Computes distance of each observation to its group centroid (mean),
    then computes the F-statistic of these distances directly.
    """
    Y = np.atleast_2d(Y)
    n = Y.shape[0]
    unique_groups, group_indices = np.unique(groups, return_inverse=True)
    k = len(unique_groups)

    centroids = []
    for g in range(k):
        mask = (group_indices == g)
        if np.any(mask):
            centroids.append(np.mean(Y[mask], axis=0))
        else:
            centroids.append(np.zeros(Y.shape[1]))

    distances = np.zeros(n)
    for i in range(n):
        g = group_indices[i]
        distances[i] = np.sqrt(np.sum((Y[i] - centroids[g])**2))

    grand_mean = np.mean(distances)
    SSB = 0.0
    SSW = 0.0
    for g in range(k):
        mask = (group_indices == g)
        n_g = np.sum(mask)
        if n_g > 0:
            group_mean = np.mean(distances[mask])
            SSB += n_g * (group_mean - grand_mean)**2
            SSW += np.sum((distances[mask] - group_mean)**2)
    df_between = k - 1
    df_within = n - k
    if SSW == 0 or df_within <= 0 or df_between <= 0:
        f_disp = 0.0
    else:
        f_disp = float((SSB / df_between) / (SSW / df_within))

    return {
        "F_dispersion": f_disp
    }

def run_dispersion_analysis():
    """
    Runs multivariate homogeneity of dispersion test (PERMDISP) across 3 subgroups (feeder_1, feeder_2, feeder_3)
    and reports average values across subgroups.
    """
    from src.statistics.data import load_dataset_2, extract_joint_representation

    df = load_dataset_2()
    subgroups = ["feeder_1", "feeder_2", "feeder_3"]
    f_disp_list = []

    print("--- Running Multivariate Homogeneity of Dispersion Test Across 3 Subgroups ---")
    for sg in subgroups:
        sub_df = df[df["gt_feeder_id"] == sg]
        if len(sub_df) > 0:
            _, Y_sg = extract_joint_representation(sub_df)
            groups_sg = sub_df["gt_event_type"].values
            res_sg = dispersion_statistic(Y_sg, groups_sg)
            f_val = res_sg["F_dispersion"]
            f_disp_list.append(f_val)
            print(f"Subgroup {sg} (N={len(sub_df)}): Dispersion F-stat = {f_val:.6f}")

    avg_f_disp = float(np.mean(f_disp_list)) if f_disp_list else 0.0
    print(f"\nAverage Dispersion F-statistic across 3 subgroups: {avg_f_disp:.6f}")

    return {
        "subgroups": subgroups,
        "f_disp_per_subgroup": f_disp_list,
        "avg_f_disp": avg_f_disp
    }

if __name__ == "__main__":
    run_dispersion_analysis()
