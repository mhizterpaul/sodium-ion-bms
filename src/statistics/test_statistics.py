import numpy as np
from src.statistics.dependence import distance_correlation, permutation_test_dcor, permutation_test_hsic
from src.statistics.distribution import permutation_test_mmd
from src.statistics.permanova import permanova
from src.statistics.dispersion import dispersion_test
from src.statistics.equivalence import tost_equivalence

def test_distance_correlation():
    X = np.random.normal(0, 1, (10, 2))
    # Y is highly dependent on X
    Y = X * 2.0 + np.random.normal(0, 0.1, (10, 2))
    dcor = distance_correlation(X, Y)
    assert dcor > 0.5

    res = permutation_test_dcor(X, Y, n_permutations=10, seed=42)
    assert "statistic" in res
    assert "p_value" in res

def test_hsic():
    X = np.random.normal(0, 1, (10, 2))
    Y = X * 2.0
    res = permutation_test_hsic(X, Y, n_permutations=10, seed=42)
    assert res["statistic"] >= 0.0

def test_mmd():
    X = np.random.normal(0, 1, (5, 2))
    Y = np.random.normal(2, 1, (5, 2))
    res = permutation_test_mmd(X, Y, n_permutations=10, seed=42)
    assert "statistic" in res

def test_permanova_and_dispersion():
    Y = np.random.normal(0, 1, (10, 2))
    groups = ["radial", "radial", "radial", "radial", "radial", "ring", "ring", "ring", "ring", "ring"]
    res_perm = permanova(Y, groups, n_permutations=10, seed=42)
    assert "F_pseudo" in res_perm

    res_disp = dispersion_test(Y, groups, n_permutations=10, seed=42)
    assert "F_dispersion" in res_disp

def test_tost_equivalence():
    y_a = [1.0, 1.01, 0.99, 1.0, 1.01]
    y_b = [1.01, 1.0, 1.0, 0.99, 1.01]
    res = tost_equivalence(y_a, y_b, margin=0.05)
    assert res["equivalent"] is True
