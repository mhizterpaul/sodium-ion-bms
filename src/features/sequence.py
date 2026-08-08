def extract_sequence_features(measurements: dict) -> dict:
    """
    Extracts sequence components and unbalance ratios from synchronized BoundaryMeasurements.
    """
    features = {}
    for f_name, m in measurements.items():
        v_pos = m.v_sequence[0]
        v_neg = m.v_sequence[1]
        v_zero = m.v_sequence[2]

        i_pos = m.i_sequence[0]
        i_neg = m.i_sequence[1]
        i_zero = m.i_sequence[2]

        features[f"{f_name}_voltage_pos_mag"] = v_pos
        features[f"{f_name}_voltage_unbalance_ratio"] = float(v_neg / (v_pos + 1e-6))

        features[f"{f_name}_current_pos_mag"] = i_pos
        features[f"{f_name}_current_unbalance_ratio"] = float(i_neg / (i_pos + 1e-6))
    return features
