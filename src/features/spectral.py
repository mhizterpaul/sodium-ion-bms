import numpy as np

def extract_spectral_features(emt_waveforms=None, fs: float = 10000.0) -> dict:
    """
    Computes spectral features including dominant frequency, spectral centroid,
    and wavelet subband energy proxies from EMT high-frequency waveforms.
    """
    features = {
        "spectral_centroid_hz": 50.0,
        "dominant_frequency_hz": 50.0,
        "wavelet_energy_low_pct": 100.0,
        "wavelet_energy_mid_pct": 0.0,
        "wavelet_energy_high_pct": 0.0
    }

    if emt_waveforms is not None and len(emt_waveforms.feeder_voltage_abc) > 0:
        f_name = list(emt_waveforms.feeder_voltage_abc.keys())[0]
        v_wave = emt_waveforms.feeder_voltage_abc[f_name][:, 0]

        N = len(v_wave)
        freqs = np.fft.rfftfreq(N, 1.0/fs)
        v_fft = np.abs(np.fft.rfft(v_wave)) / N

        sum_v = np.sum(v_fft) + 1e-9

        spectral_centroid = float(np.sum(freqs * v_fft) / sum_v)

        dom_idx = np.argmax(v_fft[1:]) + 1 if len(v_fft) > 1 else 0
        dominant_frequency = float(freqs[dom_idx])

        b1_mask = (freqs >= 50) & (freqs <= 250)
        b2_mask = (freqs > 250) & (freqs <= 1000)
        b3_mask = (freqs > 1000) & (freqs <= 5000)

        e_band1 = float(np.sum(v_fft[b1_mask]**2))
        e_band2 = float(np.sum(v_fft[b2_mask]**2))
        e_band3 = float(np.sum(v_fft[b3_mask]**2))

        total_energy = e_band1 + e_band2 + e_band3 + 1e-9

        features["spectral_centroid_hz"] = round(spectral_centroid, 2)
        features["dominant_frequency_hz"] = round(dominant_frequency, 2)
        features["wavelet_energy_low_pct"] = round(e_band1 / total_energy * 100.0, 2)
        features["wavelet_energy_mid_pct"] = round(e_band2 / total_energy * 100.0, 2)
        features["wavelet_energy_high_pct"] = round(e_band3 / total_energy * 100.0, 2)

    return features
