import numpy as np
import pandas as pd
from pathlib import Path
from src.statistics.dependence import permutation_test_dcor, permutation_test_hsic

def run_observability_analysis():
    data_path = Path(__file__).parent.parent / "simulation" / "dataset_2.csv"
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset 2 CSV not found at {data_path}. Run dataset generation first.")

    df = pd.read_csv(data_path)
    X = df[["gt_effective_load_kw"]].values

    col_std1 = []
    col_std2 = []
    col_en1 = []
    col_en2 = []
    for idx, row in df.iterrows():
        pcc_id = row.get("obs_pcc_id")
        if not pcc_id or pd.isna(pcc_id):
            pcc_id = "trans1_lv_pcc"
        col_std1.append(row[f"obs_{pcc_id}_v_0_cD1_std"] if f"obs_{pcc_id}_v_0_cD1_std" in row and not pd.isna(row[f"obs_{pcc_id}_v_0_cD1_std"]) else 0.0)
        col_std2.append(row[f"obs_{pcc_id}_v_0_cD2_std"] if f"obs_{pcc_id}_v_0_cD2_std" in row and not pd.isna(row[f"obs_{pcc_id}_v_0_cD2_std"]) else 0.0)
        col_en1.append(row[f"obs_{pcc_id}_v_0_cD1_energy"] if f"obs_{pcc_id}_v_0_cD1_energy" in row and not pd.isna(row[f"obs_{pcc_id}_v_0_cD1_energy"]) else 0.0)
        col_en2.append(row[f"obs_{pcc_id}_v_0_cD2_energy"] if f"obs_{pcc_id}_v_0_cD2_energy" in row and not pd.isna(row[f"obs_{pcc_id}_v_0_cD2_energy"]) else 0.0)

    Y_joint = np.column_stack([col_std1, col_std2, col_en1, col_en2])

    print("--- Test 5: Observability of Hidden State and Perturbations ---")
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
