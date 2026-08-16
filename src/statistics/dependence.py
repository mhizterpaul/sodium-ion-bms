import numpy as np

def run_permutation_loop(statistic_func, X, Y, n_permutations=100, seed=42):
    """
    In-line permutation test helper.
    """
    rng = np.random.default_rng(seed)
    X = np.atleast_2d(X)
    Y = np.atleast_2d(Y)

    obs_stat = float(statistic_func(X, Y))
    count = 0
    perm_stats = []
    n = X.shape[0]

    for _ in range(n_permutations):
        perm_indices = rng.permutation(n)
        perm_Y = Y[perm_indices]
        p_stat = float(statistic_func(X, perm_Y))
        perm_stats.append(p_stat)
        if p_stat >= obs_stat:
            count += 1

    p_value = float((count + 1) / (n_permutations + 1))
    return {
        "statistic": obs_stat,
        "p_value": p_value,
        "n_permutations": n_permutations,
        "null_distribution": perm_stats
    }

def dist_matrix(X):
    """
    Computes pairwise Euclidean distance matrix for X.
    """
    X = np.atleast_2d(X)
    diff = X[:, np.newaxis, :] - X[np.newaxis, :, :]
    return np.sqrt(np.sum(diff**2, axis=-1))

def double_center(D):
    """
    Applies double centering to distance matrix D.
    """
    n = D.shape[0]
    row_means = np.mean(D, axis=1, keepdims=True)
    col_means = np.mean(D, axis=0, keepdims=True)
    grand_mean = np.mean(D)
    return D - row_means - col_means + grand_mean

def distance_covariance(A, B):
    n = A.shape[0]
    return np.sqrt(np.sum(A * B) / (n * n))

def distance_correlation(X, Y):
    """
    Computes distance correlation between X and Y.
    """
    X = np.atleast_2d(X)
    Y = np.atleast_2d(Y)
    if X.shape[0] != Y.shape[0]:
        raise ValueError("X and Y must have the same number of samples")

    A = double_center(dist_matrix(X))
    B = double_center(dist_matrix(Y))

    dcov_XX = distance_covariance(A, A)
    dcov_YY = distance_covariance(B, B)
    dcov_XY = distance_covariance(A, B)

    if dcov_XX == 0 or dcov_YY == 0:
        return 0.0
    return float(dcov_XY / np.sqrt(dcov_XX * dcov_YY))

def permutation_test_dcor(X, Y, n_permutations=100, seed=42):
    """
    Permutation test for Distance Correlation.
    """
    return run_permutation_loop(distance_correlation, X, Y, n_permutations=n_permutations, seed=seed)

def rbf_kernel(X, sigma=None):
    D2 = dist_matrix(X)**2
    if sigma is None:
        flat = D2.flatten()
        nonzero = flat[flat > 0]
        sigma = np.sqrt(np.median(nonzero)) if len(nonzero) > 0 else 1.0
    return np.exp(-D2 / (2 * sigma**2))

def hsic_statistic(X, Y):
    """
    Computes Hilbert-Schmidt Independence Criterion (HSIC) using RBF kernel.
    """
    n = X.shape[0]
    K = rbf_kernel(X)
    L = rbf_kernel(Y)

    H = np.eye(n) - np.ones((n, n)) / n
    HK = H @ K
    HL = H @ L
    statistic = np.trace(HK @ HL) / ((n - 1) ** 2) if n > 1 else 0.0
    return max(0.0, float(statistic))

def permutation_test_hsic(X, Y, n_permutations=100, seed=42):
    """
    Permutation test for HSIC.
    """
    return run_permutation_loop(hsic_statistic, X, Y, n_permutations=n_permutations, seed=seed)

def benjamini_hochberg_correction(p_values):
    """
    Applies Benjamini-Hochberg (FDR) multiple-comparison correction.
    """
    p_values = np.array(p_values)
    n = len(p_values)
    if n == 0:
        return []

    sort_idx = np.argsort(p_values)
    sorted_p = p_values[sort_idx]

    adjusted_p = np.zeros(n)
    prev_adj = 1.0

    for i in range(n - 1, -1, -1):
        rank = i + 1
        adj = sorted_p[i] * n / rank
        adj = min(adj, prev_adj)
        adjusted_p[i] = adj
        prev_adj = adj

    rev_sort_idx = np.argsort(sort_idx)
    return list(adjusted_p[rev_sort_idx])


def run_dependence_analysis():
    """
    Runs dependence analysis (Distance Correlation + HSIC) on joint FFT/SWT representation
    extracted from normalized waveforms in Dataset 2.
    """
    from src.statistics.data import load_dataset_2, extract_joint_representation

    df = load_dataset_2()
    X, Y_joint = extract_joint_representation(df)

    print("--- Running Distance Correlation Test on Joint Wavelet/Spectral Representation ---")
    res_dcor = permutation_test_dcor(X, Y_joint, n_permutations=99, seed=42)
    raw_p = res_dcor["p_value"]
    adjusted_p = benjamini_hochberg_correction([raw_p])[0]

    print(f"Distance Correlation Statistic: {res_dcor['statistic']:.4f}")
    print(f"Raw Permutation p-value:        {raw_p:.4f}")
    print(f"Adjusted p-value (FDR):         {adjusted_p:.4f}")

    print("\n--- Running HSIC Nonlinear Confirmation Test on Joint Wavelet/Spectral Representation ---")
    res_hsic = permutation_test_hsic(X, Y_joint, n_permutations=99, seed=42)
    print(f"HSIC Statistic:        {res_hsic['statistic']:.6f}")
    print(f"HSIC Permutation p-val: {res_hsic['p_value']:.4f}")

    return {
        "dcor": res_dcor,
        "hsic": res_hsic,
        "adjusted_p": adjusted_p
    }


if __name__ == "__main__":
    run_dependence_analysis()
