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
    Runs PERMANOVA and PERMDISP on joint normalized transient representation Y_joint.
    """
    from src.statistics.data import load_dataset_2, extract_joint_representation
    from src.statistics.dispersion import dispersion_statistic

    df = load_dataset_2()
    _, Y_joint = extract_joint_representation(df)
    groups = df["gt_event_type"].values

    print("--- Running PERMANOVA and Multivariate Dispersion (PERMDISP) Tests ---")
    res_perm = permanova_statistic(Y_joint, groups)
    print(f"PERMANOVA F-pseudo:   {res_perm['F_pseudo']:.6f}")
    print(f"PERMANOVA R2_network: {res_perm['r_squared']:.6f}")

    res_disp = dispersion_statistic(Y_joint, groups)
    print(f"Dispersion F-stat:    {res_disp['F_dispersion']:.6f}")

    return {
        "permanova": res_perm,
        "dispersion": res_disp
    }


if __name__ == "__main__":
    run_permanova_analysis()
