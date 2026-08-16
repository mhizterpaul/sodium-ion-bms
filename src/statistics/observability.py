import numpy as np
from src.statistics.dependence import distance_correlation, hsic_statistic

def run_observability_analysis():
    """
    Tests whether the joint station-boundary representation Y_joint = [FFT + SWT]
    carries statistically significant observability regarding hidden network states and perturbations.
    """
    from src.statistics.data import load_dataset_2, extract_joint_representation

    df = load_dataset_2()
    X, Y_joint = extract_joint_representation(df)

    print("--- Test 5: Observability of Hidden State and Perturbations from Joint Wavelet/Spectral Representations ---")
    dcor_val = distance_correlation(X, Y_joint)
    hsic_val = hsic_statistic(X, Y_joint)

    print(f"Joint dCor Statistic: {dcor_val:.6f}")
    print(f"Joint HSIC Statistic: {hsic_val:.6f}")

    return {
        "dcor": dcor_val,
        "hsic": hsic_val
    }

if __name__ == "__main__":
    run_observability_analysis()
