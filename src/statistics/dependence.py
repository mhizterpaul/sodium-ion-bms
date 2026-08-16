import numpy as np

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
    Computes distance correlation between X and Y directly.
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
    Runs dependence analysis (Distance Correlation + HSIC) directly on joint representation
    extracted from normalized waveforms in Dataset 2.
    """
    from src.statistics.data import load_dataset_2, extract_joint_representation

    df = load_dataset_2()
    X, Y_joint = extract_joint_representation(df)

    dcor_stat = distance_correlation(X, Y_joint)
    hsic_stat = hsic_statistic(X, Y_joint)

    print("--- Running Distance Correlation Test on Joint Wavelet/Spectral Representation ---")
    print(f"Distance Correlation Statistic: {dcor_stat:.6f}")

    print("\n--- Running HSIC Nonlinear Confirmation Test on Joint Wavelet/Spectral Representation ---")
    print(f"HSIC Statistic:                 {hsic_stat:.6f}")

    return {
        "dcor": dcor_stat,
        "hsic": hsic_stat
    }


if __name__ == "__main__":
    run_dependence_analysis()
