import numpy as np
from src.statistics.dependence import dist_matrix

def permanova_statistic(Y, groups):
    """
    PERMANOVA pseudo-F statistic and R2_network on Euclidean distance matrix.
    """
    Y = np.atleast_2d(Y)
    n = Y.shape[0]

    unique_groups, group_indices = np.unique(groups, return_inverse=True)
    k = len(unique_groups)

    D = dist_matrix(Y)
    SST = np.sum(D**2) / (2 * n) if n > 0 else 0.0

    SSW = 0.0
    for g in range(k):
        mask = (group_indices == g)
        n_g = np.sum(mask)
        if n_g > 1:
            D_sub = D[mask][:, mask]
            SSW += np.sum(D_sub**2) / (2 * n_g)
    SSB = SST - SSW

    df_between = k - 1
    df_within = n - k

    if SSW == 0 or df_within <= 0 or df_between <= 0:
        f_pseudo = 0.0
    else:
        f_pseudo = float((SSB / df_between) / (SSW / df_within))

    r_squared = float(SSB / SST) if SST > 0 else 0.0

    return {
        "F_pseudo": f_pseudo,
        "r_squared": r_squared
    }


def run_permanova_analysis():
    """
    Runs PERMANOVA and PERMDISP across 3 subgroups (feeder_1, feeder_2, feeder_3)
    and reports average values across subgroups.
    """
    from src.statistics.data import load_dataset_2, extract_joint_representation
    from src.statistics.dispersion import dispersion_statistic

    df = load_dataset_2()
    subgroups = ["feeder_1", "feeder_2", "feeder_3"]
    f_pseudo_list = []
    r2_list = []
    f_disp_list = []

    print("--- Running PERMANOVA and PERMDISP Across 3 Subgroups ---")
    for sg in subgroups:
        sub_df = df[df["gt_feeder_id"] == sg]
        if len(sub_df) > 0:
            _, Y_sg = extract_joint_representation(sub_df)
            groups_sg = sub_df["gt_event_type"].values

            res_perm = permanova_statistic(Y_sg, groups_sg)
            res_disp = dispersion_statistic(Y_sg, groups_sg)

            f_pseudo_list.append(res_perm["F_pseudo"])
            r2_list.append(res_perm["r_squared"])
            f_disp_list.append(res_disp["F_dispersion"])

            print(f"Subgroup {sg} (N={len(sub_df)}): F-pseudo = {res_perm['F_pseudo']:.6f}, R2 = {res_perm['r_squared']:.6f}, F-disp = {res_disp['F_dispersion']:.6f}")

    avg_f_pseudo = float(np.mean(f_pseudo_list)) if f_pseudo_list else 0.0
    avg_r2 = float(np.mean(r2_list)) if r2_list else 0.0
    avg_f_disp = float(np.mean(f_disp_list)) if f_disp_list else 0.0

    print(f"\nAverage PERMANOVA F-pseudo across 3 subgroups:   {avg_f_pseudo:.6f}")
    print(f"Average PERMANOVA R2_network across 3 subgroups: {avg_r2:.6f}")
    print(f"Average PERMDISP F-stat across 3 subgroups:       {avg_f_disp:.6f}")

    return {
        "subgroups": subgroups,
        "f_pseudo_per_subgroup": f_pseudo_list,
        "r2_per_subgroup": r2_list,
        "f_disp_per_subgroup": f_disp_list,
        "avg_f_pseudo": avg_f_pseudo,
        "avg_r2": avg_r2,
        "avg_f_disp": avg_f_disp
    }


if __name__ == "__main__":
    run_permanova_analysis()
