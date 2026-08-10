import numpy as np

def dispersion_test(Y, groups, n_permutations=100, seed=42):
    """
    Multivariate homogeneity of groups dispersions (PERMDISP-like).
    Computes distance of each observation to its group centroid (mean),
    then performs a permutation test on the F-statistic of these distances.
    """
    rng = np.random.default_rng(seed)
    Y = np.atleast_2d(Y)
    n = Y.shape[0]
    unique_groups, group_indices = np.unique(groups, return_inverse=True)
    k = len(unique_groups)

    # Calculate group centroids
    centroids = []
    for g in range(k):
        mask = (group_indices == g)
        if np.any(mask):
            centroids.append(np.mean(Y[mask], axis=0))
        else:
            centroids.append(np.zeros(Y.shape[1]))

    # Calculate distance from each point to its group centroid
    distances = np.zeros(n)
    for i in range(n):
        g = group_indices[i]
        distances[i] = np.sqrt(np.sum((Y[i] - centroids[g])**2))

    def compute_f_disp(dists, g_indices):
        grand_mean = np.mean(dists)
        SSB = 0.0
        SSW = 0.0
        for g in range(k):
            mask = (g_indices == g)
            n_g = np.sum(mask)
            if n_g > 0:
                group_mean = np.mean(dists[mask])
                SSB += n_g * (group_mean - grand_mean)**2
                SSW += np.sum((dists[mask] - group_mean)**2)
        df_between = k - 1
        df_within = n - k
        if SSW == 0:
            return 0.0
        return (SSB / df_between) / (SSW / df_within)

    obs_F = compute_f_disp(distances, group_indices)

    # Permutation test
    count = 0
    perm_Fs = []
    for _ in range(n_permutations):
        perm_indices = rng.permutation(group_indices)
        p_F = compute_f_disp(distances, perm_indices)
        perm_Fs.append(p_F)
        if p_F >= obs_F:
            count += 1

    p_value = (count + 1) / (n_permutations + 1)
    return {
        "F_dispersion": obs_F,
        "p_value": p_value,
        "n_permutations": n_permutations
    }
