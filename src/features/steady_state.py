import numpy as np

def extract_steady_state_features(measurements: dict) -> dict:
    """
    Extracts steady-state features from the canonical BoundaryMeasurements.
    """
    features = {}
    for f_name, m in measurements.items():
        features[f"{f_name}_voltage_mag_avg"] = float(np.mean(m.voltage_abc))
        features[f"{f_name}_current_mag_avg"] = float(np.mean(m.current_abc))
        features[f"{f_name}_p_kw"] = m.p_kw
        features[f"{f_name}_q_kvar"] = m.q_kvar
        features[f"{f_name}_s_kva"] = m.s_kva
        features[f"{f_name}_pf"] = float(m.p_kw / (m.s_kva + 1e-6))
    return features
