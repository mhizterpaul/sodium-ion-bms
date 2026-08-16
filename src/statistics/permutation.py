import numpy as np

def run_permutation_test(statistic_func, X, Y, n_permutations=100, seed=42):
    """
    Utility to run a generic permutation test on two datasets X and Y
    for a given statistic function statistic_func(X, Y).
    Returns observed statistic, p-value with finite-sample correction,
    and null distribution.
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

    # Finite sample correction: (count + 1) / (n_permutations + 1)
    p_value = float((count + 1) / (n_permutations + 1))

    return {
        "statistic": obs_stat,
        "p_value": p_value,
        "n_permutations": n_permutations,
        "null_distribution": perm_stats
    }
