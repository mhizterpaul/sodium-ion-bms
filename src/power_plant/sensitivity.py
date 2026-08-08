import numpy as np
from opendssdirect import dss
from src.power_plant.measurements import extract_transformer_terminal_data

def calculate_voltage_sensitivities(feeder_idx: int, topology: dict, trans_name: str, delta_p: float = 10.0, delta_q: float = 10.0):
    """
    Perturbs actual downstream loads in OpenDSS by +-delta, solves the powerflow,
    and calculates the numerical derivatives: dV/dP and dV/dQ.
    Returns (dv_dp, dv_dq) for the positive sequence voltage at the HV terminal of trans_name.
    """
    loads = topology.get("loads", [])
    if not loads:
        return 0.0, 0.0

    # 1. Base voltages
    hv_data_base = extract_transformer_terminal_data(trans_name, terminal=1)

    # --- perturb P ---
    dp_each = delta_p / len(loads)
    for ld in loads:
        dss.run_command(f"edit load.{ld['name']} kw={ld['kw'] + dp_each}")
    dss.Solution.Solve()
    v_plus = extract_transformer_terminal_data(trans_name, terminal=1)["v_pos_mag"]

    for ld in loads:
        dss.run_command(f"edit load.{ld['name']} kw={ld['kw'] - dp_each}")
    dss.Solution.Solve()
    v_minus = extract_transformer_terminal_data(trans_name, terminal=1)["v_pos_mag"]

    # restore P
    for ld in loads:
        dss.run_command(f"edit load.{ld['name']} kw={ld['kw']}")
    dss.Solution.Solve()

    dv_dp = (v_plus - v_minus) / (2.0 * delta_p) if delta_p > 0 else 0.0

    # --- perturb Q ---
    dq_each = delta_q / len(loads)
    for ld in loads:
        orig_q = ld["kw"] * np.sqrt(1.0 - ld["pf"]**2) / (ld["pf"] + 1e-6)
        dss.run_command(f"edit load.{ld['name']} kvar={orig_q + dq_each}")
    dss.Solution.Solve()
    v_q_plus = extract_transformer_terminal_data(trans_name, terminal=1)["v_pos_mag"]

    for ld in loads:
        orig_q = ld["kw"] * np.sqrt(1.0 - ld["pf"]**2) / (ld["pf"] + 1e-6)
        dss.run_command(f"edit load.{ld['name']} kvar={orig_q - dq_each}")
    dss.Solution.Solve()
    v_q_minus = extract_transformer_terminal_data(trans_name, terminal=1)["v_pos_mag"]

    # restore Q (by setting kw and pf, OpenDSS automatically re-allocates kvar)
    for ld in loads:
        dss.run_command(f"edit load.{ld['name']} kw={ld['kw']} pf={ld['pf']}")
    dss.Solution.Solve()

    dv_dq = (v_q_plus - v_q_minus) / (2.0 * delta_q) if delta_q > 0 else 0.0

    return float(dv_dp), float(dv_dq)
