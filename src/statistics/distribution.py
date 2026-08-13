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

    if sigma is None:
        xy = np.vstack([X, Y])
        D2 = dist_matrix(xy)**2
        flat = D2.flatten()
        nonzero = flat[flat > 0]
        sigma = np.sqrt(np.median(nonzero)) if len(nonzero) > 0 else 1.0

    K_XX = np.exp(-dist_matrix(X)**2 / (2 * sigma**2))
    K_YY = np.exp(-dist_matrix(Y)**2 / (2 * sigma**2))

    # Compute pairwise distance between X and Y
    diff = X[:, np.newaxis, :] - Y[np.newaxis, :, :]
    D2_XY = np.sum(diff**2, axis=-1)
    K_XY = np.exp(-D2_XY / (2 * sigma**2))

    term_xx = np.sum(K_XX - np.diag(np.diag(K_XX))) / (n_x * (n_x - 1)) if n_x > 1 else np.mean(K_XX)
    term_yy = np.sum(K_YY - np.diag(np.diag(K_YY))) / (n_y * (n_y - 1)) if n_y > 1 else np.mean(K_YY)
    term_xy = np.mean(K_XY)

    mmd2 = term_xx + term_yy - 2 * term_xy
    return float(mmd2)

def permutation_test_mmd(X, Y, n_permutations=100, seed=42):
    """
    Permutation test for MMD.
    """
    rng = np.random.default_rng(seed)
    X = np.atleast_2d(X)
    Y = np.atleast_2d(Y)
    obs_mmd = mmd_statistic(X, Y)

    n_x = X.shape[0]
    combined = np.vstack([X, Y])
    n_total = combined.shape[0]

    count = 0
    perm_mmds = []
    for _ in range(n_permutations):
        perm_indices = rng.permutation(n_total)
        perm_combined = combined[perm_indices]
        perm_X = perm_combined[:n_x]
        perm_Y = perm_combined[n_x:]

        p_mmd = mmd_statistic(perm_X, perm_Y)
        perm_mmds.append(p_mmd)
        if p_mmd >= obs_mmd:
            count += 1

    p_value = (count + 1) / (n_permutations + 1)
    return {
        "statistic": obs_mmd,
        "p_value": p_value,
        "n_permutations": n_permutations,
        "null_distribution": perm_mmds
    }


def run_distribution_analysis():
    import json
    from pathlib import Path
    data_path = Path(__file__).parent.parent / "simulation" / "dataset_1.json"
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset 1 not found at {data_path}. Run dataset generation first.")

    with open(data_path, "r") as f:
        dataset_1 = json.load(f)

    Y_radial = []
    Y_ring = []
    for item in dataset_1:
        gt = item["ground_truth"]
        obs = item["observations"]["features"]
        f_num = gt["feeder_id"].split("_")[-1]
        pcc_id = f"trans{f_num}_lv_pcc"
        y_val = [
            obs.get(f"{pcc_id}_voltage_mag_avg", 0.0),
            obs.get(f"{pcc_id}_current_mag_avg", 0.0),
            obs.get(f"{pcc_id}_p_kw", 0.0)
        ]
        if gt["topology_type"] == "radial":
            Y_radial.append(y_val)
        else:
            Y_ring.append(y_val)

    Y_radial = np.array(Y_radial)
    Y_ring = np.array(Y_ring)

    print("--- Running Maximum Mean Discrepancy (MMD) Two-Sample Test ---")
    if len(Y_ring) > 0 and len(Y_radial) > 0:
        res_mmd = permutation_test_mmd(Y_radial, Y_ring, n_permutations=99, seed=42)
        print(f"MMD^2 Statistic:       {res_mmd['statistic']:.6f}")
        print(f"MMD Permutation p-val: {res_mmd['p_value']:.4f}")
        return res_mmd
    else:
        print("Skip: Not enough samples for both Radial and Ring topologies to execute MMD test.")
        return None


if __name__ == "__main__":
    run_distribution_analysis()
