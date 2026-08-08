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

def extract_transformer_terminal_data(transformer_name: str, terminal: int = 1):
    """
    Obtains the actual terminal voltage, current, active/reactive powers, etc.
    associated with transformer_name terminal (1=HV, 2=LV).
    """
    dss.Circuit.SetActiveElement(f"transformer.{transformer_name}")
    buses = dss.CktElement.BusNames()
    bus_name = buses[0] if terminal == 1 else buses[1]

    # Voltage
    v_mags, v_angs = extract_bus_voltages(bus_name)
    v_seq = compute_symmetrical_components(v_mags, v_angs)

    # Current
    i_mags, i_angs = extract_element_currents(f"transformer.{transformer_name}", terminal=terminal)
    i_seq = compute_symmetrical_components(i_mags, i_angs)

    # Powers
    powers = dss.CktElement.Powers()
    offset = 0 if terminal == 1 else 6
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

def get_boundary_measurements(transformer_names=["trans1", "trans2", "trans3"]):
    """
    Extracts all physical parameters of the known plant boundary.
    """
    measurements = {}
    freq = float(dss.Solution.Frequency())

    # Main Bus
    v_main_mags, v_main_angs = extract_bus_voltages("main_bus")
    main_seq = compute_symmetrical_components(v_main_mags, v_main_angs)

    for i, t_name in enumerate(transformer_names, start=1):
        hv_data = extract_transformer_terminal_data(t_name, terminal=1)
        lv_data = extract_transformer_terminal_data(t_name, terminal=2)

        v_hv_avg = np.mean(hv_data["v_mags"])
        i_hv_avg = np.mean(hv_data["i_mags"])
        z_hv_mag = (v_hv_avg / (i_hv_avg + 1e-6)) if i_hv_avg > 0 else 0.0

        r_tr_ohm = 0.645
        x_tr_ohm = 4.03

        loading_pct = (hv_data["s_kva"] / 1500.0) * 100.0

        dss.Circuit.SetActiveElement(f"transformer.{t_name}")
        tap_pos = float(dss.Transformers.Tap())

        sin_phi = np.sqrt(1.0 - hv_data["pf"]**2)
        v_reg = (loading_pct / 100.0) * (0.8 * hv_data["pf"] + 5.0 * sin_phi)

        measurements[f"transformer{i}_hv_voltage"] = v_hv_avg
        measurements[f"transformer{i}_hv_current"] = i_hv_avg
        measurements[f"transformer{i}_lv_voltage"] = np.mean(lv_data["v_mags"])
        measurements[f"transformer{i}_lv_current"] = np.mean(lv_data["i_mags"])
        measurements[f"transformer{i}_p_kw"] = hv_data["p_kw"]
        measurements[f"transformer{i}_q_kvar"] = hv_data["q_kvar"]
        measurements[f"transformer{i}_s_kva"] = hv_data["s_kva"]
        measurements[f"transformer{i}_pf"] = hv_data["pf"]
        measurements[f"transformer{i}_loading_pct"] = loading_pct
        measurements[f"transformer{i}_tap_position"] = tap_pos
        measurements[f"transformer{i}_voltage_regulation_pct"] = v_reg
        measurements[f"transformer{i}_z_hv_mag_ohm"] = z_hv_mag
        measurements[f"transformer{i}_r_tr_ohm"] = r_tr_ohm
        measurements[f"transformer{i}_x_tr_ohm"] = x_tr_ohm

        # Symmetrical components at HV side
        measurements[f"transformer{i}_hv_voltage_pos_mag"] = hv_data["v_pos_mag"]
        measurements[f"transformer{i}_hv_voltage_pos_ang"] = hv_data["v_pos_ang"]
        measurements[f"transformer{i}_hv_voltage_unbalance_pct"] = hv_data["v_unbalance_pct"]
        measurements[f"transformer{i}_hv_current_pos_mag"] = hv_data["i_pos_mag"]
        measurements[f"transformer{i}_hv_current_unbalance_pct"] = hv_data["i_unbalance_pct"]

        # Symmetrical components at LV side
        measurements[f"transformer{i}_lv_voltage_pos_mag"] = lv_data["v_pos_mag"]
        measurements[f"transformer{i}_lv_voltage_unbalance_pct"] = lv_data["v_unbalance_pct"]
        measurements[f"transformer{i}_lv_current_pos_mag"] = lv_data["i_pos_mag"]
        measurements[f"transformer{i}_lv_current_unbalance_pct"] = lv_data["i_unbalance_pct"]

    measurements["frequency_hz"] = freq
    return measurements

MEASUREMENT_POINTS = {
    "feeder1": {
        "element": "line.feeder1",
        "bus": "main_bus",
    },
    "feeder2": {
        "element": "line.feeder2",
        "bus": "main_bus",
    },
    "feeder3": {
        "element": "line.feeder3",
        "bus": "main_bus",
    },
    "transformer1": {
        "element": "transformer.trans1",
        "bus": "feeder1_head",
    },
    "transformer2": {
        "element": "transformer.trans2",
        "bus": "feeder2_head",
    },
    "transformer3": {
        "element": "transformer.trans3",
        "bus": "feeder3_head",
    },
}

def configure_measurement_monitors():
    commands = [
        "new monitor.feeder1_vi element=line.feeder1 terminal=1 mode=0",
        "new monitor.feeder2_vi element=line.feeder2 terminal=1 mode=0",
        "new monitor.feeder3_vi element=line.feeder3 terminal=1 mode=0",
        "new monitor.trans1_vi element=transformer.trans1 terminal=1 mode=0",
        "new monitor.trans2_vi element=transformer.trans2 terminal=1 mode=0",
        "new monitor.trans3_vi element=transformer.trans3 terminal=1 mode=0",
    ]
    for command in commands:
        dss.run_command(command)

def configure_power_monitors():
    commands = [
        "new monitor.feeder1_pq element=line.feeder1 terminal=1 mode=1",
        "new monitor.feeder2_pq element=line.feeder2 terminal=1 mode=1",
        "new monitor.feeder3_pq element=line.feeder3 terminal=1 mode=1",
        "new monitor.trans1_pq element=transformer.trans1 terminal=1 mode=1",
        "new monitor.trans2_pq element=transformer.trans2 terminal=1 mode=1",
        "new monitor.trans3_pq element=transformer.trans3 terminal=1 mode=1",
    ]
    for command in commands:
        dss.run_command(command)
