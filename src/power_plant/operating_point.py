from dataclasses import dataclass
import numpy as np
from opendssdirect import dss
from src.power_plant.sources import apply_generator_profile
from src.power_plant.measurements import extract_pcc_data

@dataclass
class OperatingPoint:
    time_s: float
    generator_p_kw: float
    generator_q_kvar: float
    feeder_p_kw: dict
    feeder_q_kvar: dict
    transformer_loading: dict
    voltage_pu: dict
    frequency_hz: float

def solve_operating_point(p_kw: float, q_kvar: float, time_s: float = 0.0) -> OperatingPoint:
    """
    Applies generator profiles, runs OpenDSS power flow, and extracts the electrical operating point.
    """
    apply_generator_profile(p_kw, q_kvar)

    dss.Solution.Solve()
    if not dss.Solution.Converged():
        dss.run_command("Solve mode=direct")
        if not dss.Solution.Converged():
            raise RuntimeError(f"OpenDSS failed to converge at t={time_s}s")

    feeder_p = {}
    feeder_q = {}
    loading = {}
    voltage_pu = {}

    # We use the three transformers (trans1, trans2, trans3) as our boundaries
    for idx in [1, 2, 3]:
        pcc = {
            "pcc_id": f"trans{idx}_lv_pcc",
            "bus": f"feeder{idx}_sec",
            "parent_bus": f"feeder{idx}_head",
            "branch_id": f"transformer.trans{idx}",
            "branch_type": "transformer"
        }
        data = extract_pcc_data(pcc)

        feeder_p[f"feeder{idx}"] = data["p_kw"]
        feeder_q[f"feeder{idx}"] = data["q_kvar"]
        loading[f"transformer{idx}"] = (data["s_kva"] / 1500.0) * 100.0
        # Use average voltage on secondary (LV) side in PU
        # Nominal is 415 V line-to-line, or 415 / sqrt(3) = 240 V line-to-ground
        v_avg_lv = np.mean(data["v_mags"])
        v_nom_lv = 415.0 / np.sqrt(3.0)
        voltage_pu[f"transformer{idx}"] = v_avg_lv / v_nom_lv

    freq = float(dss.Solution.Frequency())

    return OperatingPoint(
        time_s=time_s,
        generator_p_kw=p_kw,
        generator_q_kvar=q_kvar,
        feeder_p_kw=feeder_p,
        feeder_q_kvar=feeder_q,
        transformer_loading=loading,
        voltage_pu=voltage_pu,
        frequency_hz=freq
    )
