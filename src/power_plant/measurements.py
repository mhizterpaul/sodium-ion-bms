import numpy as np
from opendssdirect import dss

def compute_symmetrical_components(mags, angles_deg):
    """
    Computes symmetrical components (zero, positive, and negative sequence) from three-phase complex phasor inputs.
    T_inv = 1/3 * [[1, 1, 1], [1, a, a^2], [1, a^2, a]] where a = e^(j * 120 deg)
    """
    if len(mags) < 3 or len(angles_deg) < 3:
        return {
            "zero": (0.0, 0.0),
            "positive": (0.0, 0.0),
            "negative": (0.0, 0.0)
        }
    rad = np.radians(angles_deg)
    phasors = [m * (np.cos(r) + 1j * np.sin(r)) for m, r in zip(mags, rad)]

    # operator a
    a = np.cos(2.0*np.pi/3.0) + 1j * np.sin(2.0*np.pi/3.0)
    a_sq = a * a

    x0 = (phasors[0] + phasors[1] + phasors[2]) / 3.0
    x1 = (phasors[0] + a * phasors[1] + a_sq * phasors[2]) / 3.0
    x2 = (phasors[0] + a_sq * phasors[1] + a * phasors[2]) / 3.0

    return {
        "zero": (float(np.abs(x0)), float(np.degrees(np.angle(x0)))),
        "positive": (float(np.abs(x1)), float(np.degrees(np.angle(x1)))),
        "negative": (float(np.abs(x2)), float(np.degrees(np.angle(x2))))
    }

def extract_bus_voltages(bus_name: str):
    """
    Extracts magnitude and phase angles from Bus.VMagAngle() using correct stride slicing:
    [0:6:2] for magnitudes, [1:6:2] for phase angles.
    """
    dss.Circuit.SetActiveBus(bus_name)
    v_mag_angle = dss.Bus.VMagAngle()

    if not v_mag_angle or len(v_mag_angle) < 6:
        return [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]

    mags = v_mag_angle[0:6:2]
    angles = v_mag_angle[1:6:2]
    return list(mags), list(angles)

def extract_element_currents(element_name: str, terminal: int = 1):
    """
    Extracts currents for terminal 1 or 2 of a specific element.
    Uses correct stride slicing.
    """
    dss.Circuit.SetActiveElement(element_name)
    currents_mag_ang = dss.CktElement.CurrentsMagAng()

    if not currents_mag_ang or len(currents_mag_ang) < 6:
        return [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]

    offset = 0 if terminal == 1 else 6
    if len(currents_mag_ang) < offset + 6:
        offset = 0

    mags = currents_mag_ang[offset : offset+6 : 2]
    angles = currents_mag_ang[offset+1 : offset+6 : 2]
    return list(mags), list(angles)

def extract_pcc_data(pcc: dict) -> dict:
    """
    Extracts the electrical measurements at a given PCC from OpenDSS.
    """
    branch_id = pcc["branch_id"] # e.g. "down_1_1" or "transformer.trans1"
    bus_name = pcc["bus"]        # e.g. "f1_node1" or "feeder1_sec"

    # 1. Determine active element name
    if branch_id.startswith("transformer.") or branch_id.startswith("line."):
        element_name = branch_id
    else:
        element_name = f"line.{branch_id}"

    dss.Circuit.SetActiveElement(element_name)

    # 2. Extract voltages
    v_mags, v_angs = extract_bus_voltages(bus_name)
    v_seq = compute_symmetrical_components(v_mags, v_angs)

    # 3. Extract currents (use terminal=2 for transformers/lines)
    terminal = 2 if branch_id.startswith("transformer.") else 1
    i_mags, i_angs = extract_element_currents(element_name, terminal=terminal)
    i_seq = compute_symmetrical_components(i_mags, i_angs)

    # 4. Extract Powers
    powers = dss.CktElement.Powers()
    offset = 6 * (terminal - 1)
    if powers and len(powers) >= offset + 6:
        p_total = sum(powers[offset : offset+6 : 2])
        q_total = sum(powers[offset+1 : offset+6 : 2])
    else:
        p_total = 0.0
        q_total = 0.0

    s_total = np.sqrt(p_total**2 + q_total**2)
    pf = (p_total / (s_total + 1e-6)) if s_total > 0 else 1.0

    return {
        "v_mags": v_mags,
        "v_angs": v_angs,
        "v_pos_mag": v_seq["positive"][0],
        "v_pos_ang": v_seq["positive"][1],
        "v_neg_mag": v_seq["negative"][0],
        "v_zero_mag": v_seq["zero"][0],
        "v_unbalance_pct": (v_seq["negative"][0] / (v_seq["positive"][0] + 1e-6)) * 100.0,

        "i_mags": i_mags,
        "i_angs": i_angs,
        "i_pos_mag": i_seq["positive"][0],
        "i_pos_ang": i_seq["positive"][1],
        "i_neg_mag": i_seq["negative"][0],
        "i_zero_mag": i_seq["zero"][0],
        "i_unbalance_pct": (i_seq["negative"][0] / (i_seq["positive"][0] + 1e-6)) * 100.0,

        "p_kw": p_total,
        "q_kvar": q_total,
        "s_kva": s_total,
        "pf": pf
    }

def get_pcc_measurements(metered_pccs: list[dict]) -> dict:
    """
    Extracts electrical measurements from OpenDSS for the metered PCCs only.
    """
    pcc_measurements = {}
    for pcc in metered_pccs:
        pcc_data = extract_pcc_data(pcc)
        freq = float(dss.Solution.Frequency())
        pcc_data["frequency_hz"] = freq
        pcc_measurements[pcc["pcc_id"]] = pcc_data
    return pcc_measurements
