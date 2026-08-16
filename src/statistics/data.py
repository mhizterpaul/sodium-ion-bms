import json
from pathlib import Path
import pandas as pd
import numpy as np

from src.signal_processing.fft import compute_fft
from src.signal_processing.swt import compute_three_phase_swt

def parse_json_array(val):
    if pd.isna(val) or val is None or val == "" or val == "[]" or val == "{}":
        return np.array([])
    if isinstance(val, (list, tuple, np.ndarray)):
        return np.asarray(val)
    try:
        parsed = json.loads(val)
        return np.asarray(parsed)
    except Exception:
        return np.array([])

def load_dataset_1(data_path: str | Path = None) -> pd.DataFrame:
    if data_path is None:
        data_path = Path(__file__).parent.parent / "simulation" / "dataset_1.csv"
    data_path = Path(data_path)
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset 1 CSV not found at {data_path}. Generate dataset first.")
    df = pd.read_csv(data_path)
    return df

def load_dataset_2(data_path: str | Path = None) -> pd.DataFrame:
    if data_path is None:
        data_path = Path(__file__).parent.parent / "simulation" / "dataset_2.csv"
    data_path = Path(data_path)
    if not data_path.exists():
        raise FileNotFoundError(f"Dataset 2 CSV not found at {data_path}. Generate dataset first.")
    df = pd.read_csv(data_path)
    return df

def extract_joint_representation(df_2: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """
    Deserializes Dataset 2 normalized transient waveforms, computes FFT and SWT,
    and constructs the joint feature matrix Y_joint along with hidden state target X.

    Returns:
        X: (N, num_gt_features) or (N, 1) target array
        Y_joint: (N, num_spectral_wavelet_features) feature matrix
    """
    X_list = []
    Y_joint_list = []

    for idx, row in df_2.iterrows():
        # X: effective load or hidden network state
        eff_load = float(row.get("gt_effective_load_kw", 0.0))
        X_list.append([eff_load])

        # Extract normalized transient waveforms
        norm_v = parse_json_array(row.get("obs_norm_transient_v"))
        norm_i = parse_json_array(row.get("obs_norm_transient_i"))
        time_s = parse_json_array(row.get("obs_raw_transient_time"))

        if len(time_s) == 0:
            time_s = np.linspace(0, 0.1, 1000)

        # Fallback if norm_v / norm_i are missing or empty
        if norm_v.size == 0:
            norm_v = np.zeros((3, len(time_s)))
        if norm_i.size == 0:
            norm_i = np.zeros((3, len(time_s)))

        if norm_v.ndim == 1:
            norm_v = np.array([norm_v, norm_v, norm_v])
        elif norm_v.shape[0] != 3 and norm_v.shape[1] == 3:
            norm_v = norm_v.T

        if norm_i.ndim == 1:
            norm_i = np.array([norm_i, norm_i, norm_i])
        elif norm_i.shape[0] != 3 and norm_i.shape[1] == 3:
            norm_i = norm_i.T

        # 1. FFT features
        v_fft = compute_fft(time_s, norm_v)["magnitude"]
        i_fft = compute_fft(time_s, norm_i)["magnitude"]

        v_fft_arr = np.asarray(v_fft)
        i_fft_arr = np.asarray(i_fft)

        v_fft_summary = [np.mean(v_fft_arr), np.std(v_fft_arr), np.max(v_fft_arr)]
        i_fft_summary = [np.mean(i_fft_arr), np.std(i_fft_arr), np.max(i_fft_arr)]

        # 2. SWT features
        v_swt = compute_three_phase_swt(norm_v, wavelet="db1", level=2)
        i_swt = compute_three_phase_swt(norm_i, wavelet="db1", level=2)

        swt_features = []
        for p_key in ["phase_a", "phase_b", "phase_c"]:
            p_v_coeffs = v_swt.get(p_key, [])
            for lvl_idx, coeff in enumerate(p_v_coeffs):
                cA = np.asarray(coeff["approximation"])
                cD = np.asarray(coeff["detail"])
                swt_features.extend([np.std(cA), np.std(cD), float(np.sum(cD**2))])

            p_i_coeffs = i_swt.get(p_key, [])
            for lvl_idx, coeff in enumerate(p_i_coeffs):
                cA = np.asarray(coeff["approximation"])
                cD = np.asarray(coeff["detail"])
                swt_features.extend([np.std(cA), np.std(cD), float(np.sum(cD**2))])

        row_y = np.concatenate([v_fft_summary, i_fft_summary, swt_features])
        Y_joint_list.append(row_y)

    X = np.array(X_list)
    Y_joint = np.array(Y_joint_list)
    return X, Y_joint
