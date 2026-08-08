import numpy as np

def extract_transient_features(measurements: dict, emt_waveforms=None) -> dict:
    """
    Extracts dynamic transient features such as peak values, dV/dt, dI/dt, and integral transient energy.
    """
    features = {}

    for f_name, m in measurements.items():
        features[f"{f_name}_dv_dt"] = 0.0
        features[f"{f_name}_di_dt"] = 0.0
        features[f"{f_name}_rocof"] = m.rocof_hz_s
        features[f"{f_name}_transient_peak_v"] = float(max(m.voltage_abc))
        features[f"{f_name}_transient_peak_i"] = float(max(m.current_abc))
        features[f"{f_name}_transient_energy_v"] = 0.0

    if emt_waveforms is not None:
        for f_name in emt_waveforms.feeder_voltage_abc.keys():
            v_wave = emt_waveforms.feeder_voltage_abc[f_name]
            i_wave = emt_waveforms.feeder_current_abc[f_name]
            t = emt_waveforms.time_s

            dt = np.diff(t)
            # Prevent division by zero
            dt = np.where(dt == 0.0, 1e-6, dt)

            # Compute gradient derivatives along time axis
            dv_dt = np.diff(v_wave, axis=0) / dt[:, None]
            di_dt = np.diff(i_wave, axis=0) / dt[:, None]

            features[f"{f_name}_dv_dt"] = float(np.max(np.abs(dv_dt)))
            features[f"{f_name}_di_dt"] = float(np.max(np.abs(di_dt)))

            # Integral transient energy
            features[f"{f_name}_transient_energy_v"] = float(np.sum(v_wave**2) * (t[1] - t[0]))

    return features
