import numpy as np
from src.statistics.dependence import permutation_test_dcor, permutation_test_hsic

def run_observability_analysis():
    """
    Tests whether the joint station-boundary representation Y_joint = [FFT + SWT]
    carries statistically significant observability regarding hidden network states and perturbations.
    """
    from src.statistics.data import load_dataset_2, extract_joint_representation

    df = load_dataset_2()
    X, Y_joint = extract_joint_representation(df)

    print("--- Test 5: Observability of Hidden State and Perturbations from Joint Wavelet/Spectral Representations ---")
    res_dcor = permutation_test_dcor(X, Y_joint, n_permutations=99, seed=42)
    res_hsic = permutation_test_hsic(X, Y_joint, n_permutations=99, seed=42)

    print(f"Joint dCor Statistic: {res_dcor['statistic']:.4f} (p-value: {res_dcor['p_value']:.4f})")
    print(f"Joint HSIC Statistic: {res_hsic['statistic']:.6f} (p-value: {res_hsic['p_value']:.4f})")

    return {
        "dcor": res_dcor,
        "hsic": res_hsic
    }

if __name__ == "__main__":
    run_observability_analysis()
