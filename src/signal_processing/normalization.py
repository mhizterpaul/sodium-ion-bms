import numpy as np

def normalize_waveform(transient_signal: np.ndarray, steady_state_reference: np.ndarray | float | tuple | list) -> np.ndarray:
    """
    Normalizes transient waveform using its corresponding steady-state reference.
    Uses numerically stable division to prevent zero or near-zero denominators.

    Args:
        transient_signal: Array of shape (n_samples,) or (n_phases, n_samples)
        steady_state_reference: Scalar, array of shape (n_phases,), or waveform array

    Returns:
        normalized_signal: Array of same shape as transient_signal
    """
    transient = np.asarray(transient_signal, dtype=float)
    ref = np.asarray(steady_state_reference, dtype=float)

    # Handle multi-phase or 1D signals
    if transient.ndim == 1:
        if ref.ndim == 1 and ref.size == transient.size:
            # Time-domain waveform subtraction or elementwise division
            ref_rms = np.sqrt(np.mean(ref**2)) if ref.size > 0 else 1.0
            denom = max(ref_rms, 1e-6)
            return transient / denom
        else:
            ref_val = float(np.mean(ref)) if ref.size > 0 else 1.0
            denom = max(abs(ref_val), 1e-6)
            return transient / denom
    elif transient.ndim == 2:
        # Shape (3, n_samples) or (n_samples, 3)
        normalized = np.zeros_like(transient)
        if transient.shape[0] == 3 and transient.shape[1] != 3:
            # Shape (3, n_samples)
            for p in range(3):
                ref_p = ref[p] if ref.ndim >= 1 and len(ref) > p else 1.0
                if isinstance(ref_p, (np.ndarray, list, tuple)):
                    ref_rms = np.sqrt(np.mean(np.asarray(ref_p)**2))
                else:
                    ref_rms = float(ref_p)
                denom = max(abs(ref_rms), 1e-6)
                normalized[p, :] = transient[p, :] / denom
        else:
            # Shape (n_samples, 3)
            for p in range(3):
                ref_p = ref[p] if ref.ndim >= 1 and len(ref) > p else 1.0
                if isinstance(ref_p, (np.ndarray, list, tuple)):
                    ref_rms = np.sqrt(np.mean(np.asarray(ref_p)**2))
                else:
                    ref_rms = float(ref_p)
                denom = max(abs(ref_rms), 1e-6)
                normalized[:, p] = transient[:, p] / denom
        return normalized
    else:
        denom = max(float(np.mean(ref)), 1e-6)
        return transient / denom
