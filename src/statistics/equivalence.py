import numpy as np
from scipy import stats

def tost_equivalence(y_a, y_b, margin=0.05):
    """
    Two One-Sided Tests (TOST) for equivalence of two independent groups.
    H01: difference <= -margin
    H02: difference >= +margin
    Only if both nulls are rejected do we conclude the groups are practically equivalent.
    """
    y_a = np.array(y_a)
    y_b = np.array(y_b)

    n_a = len(y_a)
    n_b = len(y_b)

    mean_a = np.mean(y_a)
    mean_b = np.mean(y_b)

    var_a = np.var(y_a, ddof=1) if n_a > 1 else 0.0
    var_b = np.var(y_b, ddof=1) if n_b > 1 else 0.0

    # Pooled standard error
    pooled_se = np.sqrt(((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2)) * np.sqrt(1/n_a + 1/n_b)
    if pooled_se == 0:
        pooled_se = 1e-6

    diff = mean_a - mean_b

    # t-statistics
    t1 = (diff + margin) / pooled_se
    t2 = (diff - margin) / pooled_se

    df = n_a + n_b - 2

    # p-values
    p1 = 1 - stats.t.cdf(t1, df)
    p2 = stats.t.cdf(t2, df)

    p_equivalence = max(p1, p2)
    equivalent = bool(p_equivalence < 0.05)

    return {
        "difference": float(diff),
        "t1": float(t1),
        "t2": float(t2),
        "p1": float(p1),
        "p2": float(p2),
        "p_equivalence": float(p_equivalence),
        "equivalent": equivalent,
        "margin": float(margin)
    }
