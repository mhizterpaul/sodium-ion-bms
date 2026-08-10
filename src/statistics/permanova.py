import numpy as np
from src.statistics.dependence import dist_matrix

def permanova(Y, groups, blocks=None, n_permutations=100, seed=42):
    """
    PERMANOVA on Euclidean distance matrix.
    Optionally accounts for experimental blocking structure by permuting within blocks.
    """
    rng = np.random.default_rng(seed)
    Y = np.atleast_2d(Y)
    n = Y.shape[0]

    unique_groups, group_indices = np.unique(groups, return_inverse=True)
    k = len(unique_groups)

    D = dist_matrix(Y)
    SST = np.sum(D**2) / (2 * n)

    def compute_f_stat(g_indices):
        SSW = 0.0
        for g in range(k):
            mask = (g_indices == g)
            n_g = np.sum(mask)
            if n_g > 1:
                D_sub = D[mask][:, mask]
                SSW += np.sum(D_sub**2) / (2 * n_g)
        SSB = SST - SSW

        df_between = k - 1
        df_within = n - k

        if SSW == 0:
            return 0.0
        return (SSB / df_between) / (SSW / df_within)

    obs_F = compute_f_stat(group_indices)

    # Block-aware or standard permutation
    count = 0
    perm_Fs = []

    if blocks is not None:
        blocks = np.array(blocks)
        unique_blocks = np.unique(blocks)

        for _ in range(n_permutations):
            perm_g_indices = np.copy(group_indices)
            for b in unique_blocks:
                b_mask = (blocks == b)
                perm_g_indices[b_mask] = rng.permutation(group_indices[b_mask])
            p_F = compute_f_stat(perm_g_indices)
            perm_Fs.append(p_F)
            if p_F >= obs_F:
                count += 1
    else:
        for _ in range(n_permutations):
            perm_g_indices = rng.permutation(group_indices)
            p_F = compute_f_stat(perm_g_indices)
            perm_Fs.append(p_F)
            if p_F >= obs_F:
                count += 1

    p_value = (count + 1) / (n_permutations + 1)

    # R^2 calculation
    SSW_obs = 0.0
    for g in range(k):
        mask = (group_indices == g)
        n_g = np.sum(mask)
        if n_g > 1:
            D_sub = D[mask][:, mask]
            SSW_obs += np.sum(D_sub**2) / (2 * n_g)
    SSB_obs = SST - SSW_obs
    r_squared = SSB_obs / SST if SST > 0 else 0.0

    return {
        "F_pseudo": obs_F,
        "p_value": p_value,
        "r_squared": r_squared,
        "n_permutations": n_permutations
    }
