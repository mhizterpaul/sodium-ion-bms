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
    Runs multivariate homogeneity of dispersion test (PERMDISP) on Dataset 2.
    """
    from src.statistics.data import load_dataset_2, extract_joint_representation

    df = load_dataset_2()
    _, Y_joint = extract_joint_representation(df)
    groups = df["gt_event_type"].values

    print("--- Running Multivariate Homogeneity of Dispersion Test (PERMDISP) ---")
    res_disp = dispersion_statistic(Y_joint, groups)
    print(f"Dispersion F-stat: {res_disp['F_dispersion']:.6f}")

    return res_disp

if __name__ == "__main__":
    run_dispersion_analysis()
