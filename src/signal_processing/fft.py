import numpy as np
from scipy.fft import rfft, rfftfreq

def compute_fft(time_s: np.ndarray | list, signal: np.ndarray | list) -> dict:
    """
    Computes real FFT for single-phase or multi-phase signals.

    Args:
        time_s: 1D array of time stamps (seconds)
        signal: 1D array (n_samples,) or 2D array (3, n_samples)

    Returns:
        dict containing 'frequency_hz' and 'magnitude'
    """
    time_s = np.asarray(time_s, dtype=float)
    signal = np.asarray(signal, dtype=float)

    if len(time_s) < 2:
        dt = 0.0001
    else:
        dt = float(np.mean(np.diff(time_s)))
        if dt <= 0:
            dt = 0.0001

    n = signal.shape[-1]
    frequencies_hz = rfftfreq(n, d=dt)

    spectrum = rfft(signal, axis=-1)
    magnitude = np.abs(spectrum)

    return {
        "frequency_hz": frequencies_hz.tolist(),
        "magnitude": magnitude.tolist()
    }

def compute_three_phase_fft(time_s: np.ndarray | list, signal_abc: np.ndarray | list) -> dict:
    """
    Computes FFT for a three-phase signal array of shape (3, n_samples) or (n_samples, 3).
    """
    signal = np.asarray(signal_abc, dtype=float)
    if signal.ndim == 2 and signal.shape[1] == 3 and signal.shape[0] != 3:
        signal = signal.T  # Transpose to (3, n_samples)

    res = compute_fft(time_s, signal)
    return {
        "frequency_hz": res["frequency_hz"],
        "voltage_fft" if "v" in str(type(signal_abc)).lower() else "magnitude": res["magnitude"]
    }
