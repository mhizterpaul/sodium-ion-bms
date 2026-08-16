import numpy as np
from src.statistics.dependence import dist_matrix

def mmd_statistic(X, Y, sigma=None):
    """
    Computes Maximum Mean Discrepancy (MMD^2) between X and Y using RBF kernel.
    """
    X = np.atleast_2d(X)
    Y = np.atleast_2d(Y)
    n_x = X.shape[0]
    n_y = Y.shape[0]

    if n_x == 0 or n_y == 0:
        return 0.0

    if sigma is None:
        xy = np.vstack([X, Y])
        D2 = dist_matrix(xy)**2
        flat = D2.flatten()
        nonzero = flat[flat > 0]
        sigma = np.sqrt(np.median(nonzero)) if len(nonzero) > 0 else 1.0

    K_XX = np.exp(-dist_matrix(X)**2 / (2 * sigma**2))
    K_YY = np.exp(-dist_matrix(Y)**2 / (2 * sigma**2))

    diff = X[:, np.newaxis, :] - Y[np.newaxis, :, :]
    D2_XY = np.sum(diff**2, axis=-1)
    K_XY = np.exp(-D2_XY / (2 * sigma**2))

    term_xx = np.sum(K_XX - np.diag(np.diag(K_XX))) / (n_x * (n_x - 1)) if n_x > 1 else np.mean(K_XX)
    term_yy = np.sum(K_YY - np.diag(np.diag(K_YY))) / (n_y * (n_y - 1)) if n_y > 1 else np.mean(K_YY)
    term_xy = np.mean(K_XY)

    mmd2 = term_xx + term_yy - 2 * term_xy
    return float(mmd2)

def run_distribution_analysis():
    """
    Runs MMD two-sample test comparing joint representations between load groups across 3 subgroups (feeder_1, feeder_2, feeder_3)
    and reports average values across subgroups.
    """
    from src.statistics.data import load_dataset_2, extract_joint_representation

    df = load_dataset_2()
    subgroups = ["feeder_1", "feeder_2", "feeder_3"]
    mmd_list = []

    print("--- Running Maximum Mean Discrepancy (MMD) Two-Sample Test Across 3 Subgroups ---")
    for sg in subgroups:
        sub_df = df[df["gt_feeder_id"] == sg]
        if len(sub_df) > 0:
            _, Y_sg = extract_joint_representation(sub_df)
            is_linear = (sub_df["gt_load_type"] == "linear").values
            Y_linear = Y_sg[is_linear]
            Y_nonlinear = Y_sg[~is_linear]

            if len(Y_linear) > 0 and len(Y_nonlinear) > 0:
                mmd_val = mmd_statistic(Y_linear, Y_nonlinear)
                mmd_list.append(mmd_val)
                print(f"Subgroup {sg} (Linear N={len(Y_linear)}, Non-linear N={len(Y_nonlinear)}): MMD^2 = {mmd_val:.6f}")

    avg_mmd = float(np.mean(mmd_list)) if mmd_list else 0.0
    print(f"\nAverage MMD^2 Statistic across 3 subgroups: {avg_mmd:.6f}")

    return {
        "subgroups": subgroups,
        "mmd_per_subgroup": mmd_list,
        "avg_mmd": avg_mmd
    }


if __name__ == "__main__":
    run_distribution_analysis()
