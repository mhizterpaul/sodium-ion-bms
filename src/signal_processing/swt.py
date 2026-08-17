import numpy as np
import pywt

def compute_swt(signal: np.ndarray | list, wavelet: str = "db1", level: int = 2) -> list:
    """
    Computes Stationary Wavelet Transform (SWT) for a 1D signal.
    Pads/adjusts signal length to a multiple of 2**level if required.

    Args:
        signal: 1D signal array
        wavelet: Wavelet family (default "db1")
        level: Decomposition level (default 2)

    Returns:
        List of dicts containing 'approximation' (cA) and 'detail' (cD) coefficients.
    """
    arr = np.asarray(signal, dtype=float)
    n = len(arr)
    target_len = int(np.ceil(n / (2**level))) * (2**level)
    if target_len == 0:
        target_len = 2**level

    if n < target_len:
        arr = np.pad(arr, (0, target_len - n), mode='edge')
    elif n > target_len:
        arr = arr[:target_len]

    coeffs = pywt.swt(arr, wavelet=wavelet, level=level, norm=True)

    return [
        {
            "approximation": cA.tolist(),
            "detail": cD.tolist()
        }
        for cA, cD in coeffs
    ]

def compute_three_phase_swt(signal_abc: np.ndarray | list, wavelet: str = "db1", level: int = 2) -> dict:
    """
    Computes SWT for a 3-phase signal array of shape (3, n_samples) or (n_samples, 3).
    """
    arr = np.asarray(signal_abc, dtype=float)
    if arr.ndim == 2 and arr.shape[1] == 3 and arr.shape[0] != 3:
        arr = arr.T  # Transpose to (3, n_samples)

    if arr.ndim == 1:
        return {"phase_a": compute_swt(arr, wavelet, level)}

    return {
        "phase_a": compute_swt(arr[0], wavelet, level),
        "phase_b": compute_swt(arr[1], wavelet, level) if arr.shape[0] > 1 else [],
        "phase_c": compute_swt(arr[2], wavelet, level) if arr.shape[0] > 2 else []
    }
