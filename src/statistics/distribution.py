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
    Runs MMD two-sample test comparing joint representations between explicit hidden load groups (linear vs non-linear).
    """
    from src.statistics.data import load_dataset_2, extract_joint_representation

    df = load_dataset_2()
    _, Y_joint = extract_joint_representation(df)

    is_linear = (df["gt_load_type"] == "linear").values
    Y_linear = Y_joint[is_linear]
    Y_nonlinear = Y_joint[~is_linear]

    print("--- Running Maximum Mean Discrepancy (MMD) Two-Sample Distribution Test ---")
    print(f"Comparison groups: Linear loads (N={len(Y_linear)}) vs Non-linear/Heavy-duty loads (N={len(Y_nonlinear)})")

    if len(Y_linear) > 0 and len(Y_nonlinear) > 0:
        mmd_val = mmd_statistic(Y_linear, Y_nonlinear)
        print(f"MMD^2 Statistic: {mmd_val:.6f}")
        return {"statistic": mmd_val}
    else:
        print("Skip: Insufficient samples across comparison groups.")
        return None


if __name__ == "__main__":
    run_distribution_analysis()
