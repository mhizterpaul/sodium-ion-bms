import numpy as np
from dataclasses import dataclass
from typing import Optional
from opendssdirect import dss
from src.power_plant.sources import configure_generator, apply_generator_profile

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
    transient_waveforms: Optional[object] = None # Associated ATP transient waveforms for EMT dynamics not provided in OpenDSS

    def import_atp_cases(self, atp_waveforms):
        """
        Imports and associates high-fidelity ATP-EMTP transient cases
        to provide the transient waveforms not supported by OpenDSS.
        """
        self.transient_waveforms = atp_waveforms

def initialize_known_plant():
    """
    Initializes the fixed upstream distribution station using OpenDSS.
    The known plant has standard distribution voltage levels:
    - Utility Grid Source (33 kV)
    - Injection Substation Transformer (33 kV to 11 kV, 7.5 MVA)
    - Main Distribution Bus / PCC (11 kV)
    - PCU / Shared Generator (coupled at 11 kV main_bus)
    - Medium-voltage Switchgear
    - Three 11 kV Feeders (Line 1, Line 2, Line 3)
    - Fixed set of three 11/0.415 kV step-down Distribution Transformers (1.5 MVA) acting as edge interfaces
    """
    print("INFO: Initializing OpenDSS Physics-Based Known Plant Model (33/11/0.415 kV)...")

    # 1. Clear previous systems and define main circuit at swing bus (33 kV)
    dss.Basic.ClearAll()
    dss.run_command("new circuit.FixedPlant basekv=33.0 pu=1.0 phases=3")

    # 2. Substation Transformer (33 kV to 11 kV, delta-wye, 7.5 MVA)
    dss.run_command(
        "new transformer.substation "
        "phases=3 windings=2 "
        "buses=[sourcebus, main_bus] "
        "conns=[delta, wye] "
        "kvs=[33.0, 11.0] "
        "kvas=[7500, 7500] "
        "%r=0.6 "
        "%loadloss=0.667 "
        "%noloadloss=0.1 "
        "%imag=0.8 "
        "xhl=8.33"
    )

    # 3. Configure Controllable Shared Generator (coupled at 11 kV main_bus)
    configure_generator(p_kw=1500.0, q_kvar=0.0)

    # 4. Outgoing radial 11 kV Feeders (Line 1, Line 2, Line 3)
    dss.run_command("new linecode.feeder nphases=3 r1=0.25 x1=0.35 r0=0.75 x0=1.12 c1=12.0 c0=6.0 units=km")

    # Feeders extending from main_bus to the respective 11 kV feeder head buses
    dss.run_command("new line.feeder1 bus1=main_bus bus2=feeder1_head phases=3 linecode=feeder length=4.5 units=km")
    dss.run_command("new line.feeder2 bus1=main_bus bus2=feeder2_head phases=3 linecode=feeder length=6.2 units=km")
    dss.run_command("new line.feeder3 bus1=main_bus bus2=feeder3_head phases=3 linecode=feeder length=8.5 units=km")

    # 5. Fixed Set of Distribution Transformers (11/0.415 kV, delta-wye, 1.5 MVA)
    dss.run_command("new transformer.trans1 phases=3 windings=2 buses=[feeder1_head, feeder1_sec] conns=[delta, wye] kvs=[11.0, 0.415] kvas=[1500, 1500] %r=0.8 xhl=5.0")
    dss.run_command("new transformer.trans2 phases=3 windings=2 buses=[feeder2_head, feeder2_sec] conns=[delta, wye] kvs=[11.0, 0.415] kvas=[1500, 1500] %r=0.8 xhl=5.0")
    dss.run_command("new transformer.trans3 phases=3 windings=2 buses=[feeder3_head, feeder3_sec] conns=[delta, wye] kvs=[11.0, 0.415] kvas=[1500, 1500] %r=0.8 xhl=5.0")

    print("INFO: OpenDSS Known Plant Model successfully initialized.")

def compute_symmetrical_components(mags, angles_deg):
    """
    Computes symmetrical components (zero, positive, and negative sequence) from three-phase complex phasor inputs.
    """
    if len(mags) < 3 or len(angles_deg) < 3:
        return {
            "zero": (0.0, 0.0),
            "positive": (0.0, 0.0),
            "negative": (0.0, 0.0)
        }
    rad = np.radians(angles_deg)
    phasors = [m * (np.cos(r) + 1j * np.sin(r)) for m, r in zip(mags, rad)]

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

    if branch_id.startswith("transformer.") or branch_id.startswith("line."):
        element_name = branch_id
    else:
        element_name = f"line.{branch_id}"

    dss.Circuit.SetActiveElement(element_name)

    # Extract voltages
    v_mags, v_angs = extract_bus_voltages(bus_name)
    v_seq = compute_symmetrical_components(v_mags, v_angs)

    # Extract currents (use terminal=2 for transformers)
    terminal = 2 if branch_id.startswith("transformer.") else 1
    i_mags, i_angs = extract_element_currents(element_name, terminal=terminal)
    i_seq = compute_symmetrical_components(i_mags, i_angs)

    # Extract Powers
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
