from dataclasses import dataclass
import numpy as np
from opendssdirect import dss
from src.power_plant.sources import apply_generator_profile
from src.power_plant.measurements import get_boundary_measurements

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

    m = get_boundary_measurements()

    feeder_p = {
        "feeder1": m.get("transformer1_p_kw", 0.0),
        "feeder2": m.get("transformer2_p_kw", 0.0),
        "feeder3": m.get("transformer3_p_kw", 0.0)
    }

    feeder_q = {
        "feeder1": m.get("transformer1_q_kvar", 0.0),
        "feeder2": m.get("transformer2_q_kvar", 0.0),
        "feeder3": m.get("transformer3_q_kvar", 0.0)
    }

    loading = {
        "transformer1": m.get("transformer1_loading_pct", 0.0),
        "transformer2": m.get("transformer2_loading_pct", 0.0),
        "transformer3": m.get("transformer3_loading_pct", 0.0)
    }

    voltage_pu = {
        "transformer1": m.get("transformer1_hv_voltage", 11000.0) / 11000.0,
        "transformer2": m.get("transformer2_hv_voltage", 11000.0) / 11000.0,
        "transformer3": m.get("transformer3_hv_voltage", 11000.0) / 11000.0
    }

    return OperatingPoint(
        time_s=time_s,
        generator_p_kw=p_kw,
        generator_q_kvar=q_kvar,
        feeder_p_kw=feeder_p,
        feeder_q_kvar=feeder_q,
        transformer_loading=loading,
        voltage_pu=voltage_pu,
        frequency_hz=m.get("frequency_hz", 50.0)
    )
