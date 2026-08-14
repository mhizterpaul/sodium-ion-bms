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


def run_permanova_analysis():
    import pandas as pd
    from pathlib import Path
    from src.statistics.dispersion import dispersion_test

    data_path = Path(__file__).parent.parent / "simulation" / "dataset_2.csv"
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset 2 CSV not found at {data_path}. Run dataset generation first.")

    df = pd.read_csv(data_path)
    groups = df["gt_simulated_event"].values

    # Extract cD1_std, cD2_std, cD1_energy, cD2_energy columns for the active measuring node
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

    Y_wavelet = np.column_stack([col_std1, col_std2, col_en1, col_en2])

    print("--- Running PERMANOVA and dispersion tests ---")
    res_perm = permanova(Y_wavelet, groups, n_permutations=99, seed=42)
    print(f"PERMANOVA F-pseudo:   {res_perm['F_pseudo']:.4f}")
    print(f"PERMANOVA p-value:    {res_perm['p_value']:.4f}")
    print(f"PERMANOVA R2:         {res_perm['r_squared']:.4f}")

    res_disp = dispersion_test(Y_wavelet, groups, n_permutations=99, seed=42)
    print(f"Dispersion F-stat:    {res_disp['F_dispersion']:.4f}")
    print(f"Dispersion p-value:   {res_disp['p_value']:.4f}")

    return {
        "permanova": res_perm,
        "dispersion": res_disp
    }


if __name__ == "__main__":
    run_permanova_analysis()
