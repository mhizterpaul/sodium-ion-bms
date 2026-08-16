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


def run_dependence_analysis():
    """
    Runs dependence analysis (Distance Correlation + HSIC) across at least 3 subgroups
    (e.g., feeder_1, feeder_2, feeder_3) extracted from normalized waveforms in Dataset 2,
    and reports average values across subgroups.
    """
    from src.statistics.data import load_dataset_2, extract_joint_representation

    df = load_dataset_2()

    subgroups = ["feeder_1", "feeder_2", "feeder_3"]
    dcor_list = []
    hsic_list = []

    print("--- Running Distance Correlation & HSIC Tests Across 3 Subgroups ---")
    for sg in subgroups:
        sub_df = df[df["gt_feeder_id"] == sg]
        if len(sub_df) > 0:
            X_sg, Y_sg = extract_joint_representation(sub_df)
            dcor_sg = distance_correlation(X_sg, Y_sg)
            hsic_sg = hsic_statistic(X_sg, Y_sg)
            dcor_list.append(dcor_sg)
            hsic_list.append(hsic_sg)
            print(f"Subgroup {sg} (N={len(sub_df)}): Distance Correlation = {dcor_sg:.6f}, HSIC = {hsic_sg:.6f}")

    avg_dcor = float(np.mean(dcor_list)) if dcor_list else 0.0
    avg_hsic = float(np.mean(hsic_list)) if hsic_list else 0.0

    print(f"\nAverage Distance Correlation across 3 subgroups: {avg_dcor:.6f}")
    print(f"Average HSIC Statistic across 3 subgroups:       {avg_hsic:.6f}")

    return {
        "subgroups": subgroups,
        "dcor_per_subgroup": dcor_list,
        "hsic_per_subgroup": hsic_list,
        "avg_dcor": avg_dcor,
        "avg_hsic": avg_hsic
    }


if __name__ == "__main__":
    run_dependence_analysis()
