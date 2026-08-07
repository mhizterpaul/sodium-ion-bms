import numpy as np
from opendssdirect import dss
from src.power_plant.measurements import extract_transformer_terminal_data

def calculate_response_jacobian(feeder_idx: int, topology: dict, trans_name: str) -> np.ndarray:
    """
    Computes a 4x4 response Jacobian matrix J_M = dM / du
    where u = [P_G, Q_G, P_L, Q_L]
    and M = [V_1, I_1, P_total, Q_total] (positive sequence values at trans HV terminal)
    """
    dss.Solution.Solve()
    base_m = extract_transformer_terminal_data(trans_name, terminal=1)
    M_base = np.array([base_m["v_pos_mag"], base_m["i_pos_mag"], base_m["p_kw"], base_m["q_kvar"]])

    J = np.zeros((4, 4))

    dp_g = 50.0  # kW
    dq_g = 50.0  # kvar
    dp_l = 10.0  # kW
    dq_l = 10.0  # kvar

    # 1. Perturb P_G (generator kw)
    kw_orig = float(dss.Generators.kW())
    dss.run_command(f"edit generator.shared_gen kw={kw_orig + dp_g}")
    dss.Solution.Solve()
    m_plus = extract_transformer_terminal_data(trans_name, terminal=1)
    M_plus = np.array([m_plus["v_pos_mag"], m_plus["i_pos_mag"], m_plus["p_kw"], m_plus["q_kvar"]])

    dss.run_command(f"edit generator.shared_gen kw={kw_orig - dp_g}")
    dss.Solution.Solve()
    m_minus = extract_transformer_terminal_data(trans_name, terminal=1)
    M_minus = np.array([m_minus["v_pos_mag"], m_minus["i_pos_mag"], m_minus["p_kw"], m_minus["q_kvar"]])

    dss.run_command(f"edit generator.shared_gen kw={kw_orig}")
    dss.Solution.Solve()
    J[:, 0] = (M_plus - M_minus) / (2.0 * dp_g)

    # 2. Perturb Q_G (generator kvar)
    kvar_orig = float(dss.Generators.kvar())
    dss.run_command(f"edit generator.shared_gen kvar={kvar_orig + dq_g}")
    dss.Solution.Solve()
    m_plus = extract_transformer_terminal_data(trans_name, terminal=1)
    M_plus = np.array([m_plus["v_pos_mag"], m_plus["i_pos_mag"], m_plus["p_kw"], m_plus["q_kvar"]])

    dss.run_command(f"edit generator.shared_gen kvar={kvar_orig - dq_g}")
    dss.Solution.Solve()
    m_minus = extract_transformer_terminal_data(trans_name, terminal=1)
    M_minus = np.array([m_minus["v_pos_mag"], m_minus["i_pos_mag"], m_minus["p_kw"], m_minus["q_kvar"]])

    dss.run_command(f"edit generator.shared_gen kvar={kvar_orig}")
    dss.Solution.Solve()
    J[:, 1] = (M_plus - M_minus) / (2.0 * dq_g)

    # 3. Perturb P_L (loads kw)
    loads = topology.get("loads", [])
    if loads:
        dp_each = dp_l / len(loads)
        for ld in loads:
            dss.run_command(f"edit load.{ld['name']} kw={ld['kw'] + dp_each}")
        dss.Solution.Solve()
        m_plus = extract_transformer_terminal_data(trans_name, terminal=1)
        M_plus = np.array([m_plus["v_pos_mag"], m_plus["i_pos_mag"], m_plus["p_kw"], m_plus["q_kvar"]])

        for ld in loads:
            dss.run_command(f"edit load.{ld['name']} kw={ld['kw'] - dp_each}")
        dss.Solution.Solve()
        m_minus = extract_transformer_terminal_data(trans_name, terminal=1)
        M_minus = np.array([m_minus["v_pos_mag"], m_minus["i_pos_mag"], m_minus["p_kw"], m_minus["q_kvar"]])

        for ld in loads:
            dss.run_command(f"edit load.{ld['name']} kw={ld['kw']}")
        dss.Solution.Solve()
        J[:, 2] = (M_plus - M_minus) / (2.0 * dp_l)

    # 4. Perturb Q_L (loads kvar)
    if loads:
        dq_each = dq_l / len(loads)
        for ld in loads:
            orig_q = ld["kw"] * np.sqrt(1.0 - ld["pf"]**2) / (ld["pf"] + 1e-6)
            dss.run_command(f"edit load.{ld['name']} kvar={orig_q + dq_each}")
        dss.Solution.Solve()
        m_plus = extract_transformer_terminal_data(trans_name, terminal=1)
        M_plus = np.array([m_plus["v_pos_mag"], m_plus["i_pos_mag"], m_plus["p_kw"], m_plus["q_kvar"]])

        for ld in loads:
            orig_q = ld["kw"] * np.sqrt(1.0 - ld["pf"]**2) / (ld["pf"] + 1e-6)
            dss.run_command(f"edit load.{ld['name']} kvar={orig_q - dq_each}")
        dss.Solution.Solve()
        m_minus = extract_transformer_terminal_data(trans_name, terminal=1)
        M_minus = np.array([m_minus["v_pos_mag"], m_minus["i_pos_mag"], m_minus["p_kw"], m_minus["q_kvar"]])

        for ld in loads:
            dss.run_command(f"edit load.{ld['name']} kw={ld['kw']} pf={ld['pf']}")
        dss.Solution.Solve()
        J[:, 3] = (M_plus - M_minus) / (2.0 * dq_l)

    return J

def analyze_observability_svd(J: np.ndarray):
    """
    Performs singular value decomposition on the response Jacobian.
    Returns:
    - singular values: [sigma_1, sigma_2, sigma_3, sigma_4]
    - condition indicator kappa: sigma_max / sigma_min
    """
    U, S, Vt = np.linalg.svd(J)
    sigma_max = S[0]
    sigma_min = S[-1] if S[-1] > 1e-12 else 1e-12
    kappa = sigma_max / sigma_min
    return S.tolist(), float(kappa)
