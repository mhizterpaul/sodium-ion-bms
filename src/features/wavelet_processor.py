import numpy as np
import pywt

class WaveletProcessedResult:
    def __init__(self, pcc_id: str, raw_voltage: np.ndarray, raw_current: np.ndarray,
                 normalized_voltage: np.ndarray, normalized_current: np.ndarray,
                 voltage_fft: np.ndarray, current_fft: np.ndarray,
                 voltage_swt: list, current_swt: list,
                 features: dict):
        self.pcc_id = pcc_id
        self.raw_voltage = raw_voltage
        self.raw_current = raw_current
        self.normalized_voltage = normalized_voltage
        self.normalized_current = normalized_current
        self.voltage_fft = voltage_fft
        self.current_fft = current_fft
        self.voltage_swt = voltage_swt  # list of (cA, cD) per level
        self.current_swt = current_swt  # list of (cA, cD) per level
        self.features = features

def process_pcc_waveforms(pcc_id: str, t: np.ndarray, v_wave: np.ndarray, i_wave: np.ndarray, event_start: float = 0.02) -> WaveletProcessedResult:
    """
    Normalizes three-phase voltage and current waveforms using their pre-event steady-state references,
    and applies FFT and SWT decomposition to extract wavelet-domain features.
    """
    N = len(t)
    pre_mask = t < event_start

    normalized_voltage = np.zeros_like(v_wave)
    normalized_current = np.zeros_like(i_wave)

    # 50Hz fundamental fit and subtraction for each phase
    pre_t = t[pre_mask]

    # Standard 1024 samples for SWT power-of-2 requirement
    swt_len = 1024

    v_fft_list = []
    i_fft_list = []
    v_swt_list = []
    i_swt_list = []

    features = {}

    for phase in range(3):
        # 1. Normalization of voltage
        v_phase = v_wave[:, phase]
        v_pre = v_phase[pre_mask]
        v_rms = np.sqrt(np.mean(v_pre**2)) if len(v_pre) > 0 else 1.0
        if v_rms == 0:
            v_rms = 1e-6

        if len(pre_t) >= 3:
            A_v = np.column_stack([np.sin(2.0*np.pi*50.0*pre_t), np.cos(2.0*np.pi*50.0*pre_t), np.ones_like(pre_t)])
            coeffs_v, _, _, _ = np.linalg.lstsq(A_v, v_pre, rcond=None)
            v_fundamental = coeffs_v[0] * np.sin(2.0*np.pi*50.0*t) + coeffs_v[1] * np.cos(2.0*np.pi*50.0*t) + coeffs_v[2]
        else:
            v_fundamental = v_rms * np.sqrt(2.0) * np.sin(2.0*np.pi*50.0*t)

        v_norm = (v_phase - v_fundamental) / v_rms
        normalized_voltage[:, phase] = v_norm

        # 2. Normalization of current
        i_phase = i_wave[:, phase]
        i_pre = i_phase[pre_mask]
        i_rms = np.sqrt(np.mean(i_pre**2)) if len(i_pre) > 0 else 1.0
        if i_rms == 0:
            i_rms = 1e-6

        if len(pre_t) >= 3:
            A_i = np.column_stack([np.sin(2.0*np.pi*50.0*pre_t), np.cos(2.0*np.pi*50.0*pre_t), np.ones_like(pre_t)])
            coeffs_i, _, _, _ = np.linalg.lstsq(A_i, i_pre, rcond=None)
            i_fundamental = coeffs_i[0] * np.sin(2.0*np.pi*50.0*t) + coeffs_i[1] * np.cos(2.0*np.pi*50.0*t) + coeffs_i[2]
        else:
            i_fundamental = i_rms * np.sqrt(2.0) * np.sin(2.0*np.pi*50.0*t)

        i_norm = (i_phase - i_fundamental) / i_rms
        normalized_current[:, phase] = i_norm

        # 3. FFT Representation (magnitudes)
        v_fft = np.abs(np.fft.rfft(v_norm))
        i_fft = np.abs(np.fft.rfft(i_norm))
        v_fft_list.append(v_fft)
        i_fft_list.append(i_fft)

        # 4. SWT Representation
        # Pad or trim to swt_len
        def adjust_length(arr, target_len):
            if len(arr) < target_len:
                return np.pad(arr, (0, target_len - len(arr)), mode='edge')
            return arr[:target_len]

        v_norm_swt = adjust_length(v_norm, swt_len)
        i_norm_swt = adjust_length(i_norm, swt_len)

        # Level 2 SWT using db1 (Haar) wavelet
        v_swt = pywt.swt(v_norm_swt, wavelet='db1', level=2)
        i_swt = pywt.swt(i_norm_swt, wavelet='db1', level=2)

        v_swt_list.append(v_swt)
        i_swt_list.append(i_swt)

        # Extract features (energies and standard deviations of approximation and detail coefficients)
        # level 2 has coefficients: [(cA2, cD2), (cA1, cD1)]
        # We index them from the SWT list
        cA2, cD2 = v_swt[0]
        cA1, cD1 = v_swt[1]

        features[f"v_{phase}_cA2_std"] = float(np.std(cA2))
        features[f"v_{phase}_cD2_std"] = float(np.std(cD2))
        features[f"v_{phase}_cD1_std"] = float(np.std(cD1))
        features[f"v_{phase}_cD2_energy"] = float(np.sum(cD2**2))
        features[f"v_{phase}_cD1_energy"] = float(np.sum(cD1**2))

        cA2_i, cD2_i = i_swt[0]
        cA1_i, cD1_i = i_swt[1]

        features[f"i_{phase}_cA2_std"] = float(np.std(cA2_i))
        features[f"i_{phase}_cD2_std"] = float(np.std(cD2_i))
        features[f"i_{phase}_cD1_std"] = float(np.std(cD1_i))
        features[f"i_{phase}_cD2_energy"] = float(np.sum(cD2_i**2))
        features[f"i_{phase}_cD1_energy"] = float(np.sum(cD1_i**2))

    # Aggregated PCC-level features
    pcc_features = {}
    for k, v in features.items():
        pcc_features[f"{pcc_id}_{k}"] = v

    return WaveletProcessedResult(
        pcc_id=pcc_id,
        raw_voltage=v_wave,
        raw_current=i_wave,
        normalized_voltage=normalized_voltage,
        normalized_current=normalized_current,
        voltage_fft=np.array(v_fft_list),
        current_fft=np.array(i_fft_list),
        voltage_swt=v_swt_list,
        current_swt=i_swt_list,
        features=pcc_features
    )
