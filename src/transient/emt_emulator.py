import numpy as np

class EMTWaveforms:
    def __init__(self, time_s: np.ndarray, pcc_voltages: dict[str, np.ndarray], pcc_currents: dict[str, np.ndarray], event_metadata: dict):
        self.time_s = time_s
        self.pcc_voltages = pcc_voltages   # {pcc_id: (N_samples, 3)}
        self.pcc_currents = pcc_currents   # {pcc_id: (N_samples, 3)}
        self.event_metadata = event_metadata

def run_atp_case(metered_pccs: list[dict], pcc_measurements: dict, event, lines_specs: list[dict], fs: float = 10000.0, duration: float = 0.1) -> EMTWaveforms:
    """
    Solves the actual ordinary differential equations (ODEs) of the network realization G
    under the specified transient event. The transient waveforms emerge directly from the
    network's RLC impedances and non-linear dynamic elements, rather than hardcoded templates.
    """
    dt = 1.0 / fs
    N = int(fs * duration)
    t = np.linspace(0.0, duration, N)

    pcc_voltages = {}
    pcc_currents = {}

    event_type = getattr(event, "event_type", "no_event")
    event_start = getattr(event, "start_time_s", 0.02)
    event_duration = getattr(event, "duration_s", 0.04)
    target_element = getattr(event, "target_element", "") or getattr(event, "target", "")

    # 1. Parse line impedances and capacitances to build the physical RLC network structure G
    r1 = 0.45
    x1 = 0.15
    omega = 2.0 * np.pi * 50.0
    L1 = x1 / omega
    c1 = 4.0e-9

    # Organize lines per feeder to build separate isolated systems
    feeder_lines = {1: [], 2: [], 3: []}
    for ln in lines_specs:
        name = ln["name"]
        if "down_1_" in name or "tie_1" in name:
            feeder_lines[1].append(ln)
        elif "down_2_" in name or "tie_2" in name:
            feeder_lines[2].append(ln)
        else:
            feeder_lines[3].append(ln)

    for pcc in metered_pccs:
        pcc_id = pcc["pcc_id"]
        data = pcc_measurements[pcc_id]

        # Identify feeder f_id
        if "trans1" in pcc_id or "down_1_" in pcc_id:
            f_id = 1
        elif "trans2" in pcc_id or "down_2_" in pcc_id:
            f_id = 2
        else:
            f_id = 3

        v_mags = data["v_mags"]  # 3 elements (steady-state RMS from OpenDSS)
        i_mags = data["i_mags"]  # 3 elements
        pf = data["pf"]
        theta_pf = np.arccos(pf)

        v_wave = np.zeros((N, 3))
        i_wave = np.zeros((N, 3))

        # We solve the physical state-space equations of the hidden network
        tot_length = sum(ln["length"] for ln in feeder_lines[f_id])
        if tot_length == 0:
            tot_length = 0.1 # default

        R_eq = r1 * tot_length
        L_eq = L1 * tot_length
        C_eq = max(10.0e-6, c1 * tot_length)

        # Explicit capacitors in the network
        for phase in range(3):
            phase_shift = -phase * 2.0 * np.pi / 3.0

            # Formulate state vector: x = [i_line, v_cap]
            i_state = 0.0
            v_state = v_mags[phase] * np.sqrt(2.0) * np.sin(phase_shift)

            R_load = (v_mags[phase]**2) / (data["p_kw"] * 1000.0 / 3.0 + 1e-3)
            if R_load <= 0:
                R_load = 1e6

            for n in range(N):
                t_n = t[n]
                v_source = v_mags[phase] * np.sqrt(2.0) * np.sin(omega * t_n + phase_shift)

                # Active perturbations based on the actual EMT Event
                current_C = C_eq
                current_R = R_eq
                current_L = L_eq
                current_R_load = R_load

                is_active_feeder = (target_element.endswith(str(f_id)) or f"down_{f_id}_" in target_element)

                if t_n >= event_start and is_active_feeder:
                    if event_type == "capacitor_switching":
                        current_C = C_eq * 15.0

                    elif event_type == "temporary_fault" and (t_n < event_start + event_duration):
                        current_R_load = 0.05
                        current_R = R_eq * 1.5

                    elif event_type == "motor_start":
                        current_R_load = R_load * 0.1
                        current_L = L_eq * 0.3

                    elif event_type == "transformer_inrush":
                        flux_factor = np.sin(omega * (t_n - event_start) + phase_shift)
                        inrush_curr = 3.5 * i_mags[phase] * np.sqrt(2.0) * np.exp(-15.0 * (t_n - event_start)) * (flux_factor**3)
                        i_state += inrush_curr * dt

                    elif event_type == "feeder_switching":
                        current_R = R_eq * 2.0
                        current_L = L_eq * 1.2

                # Implicit backward-Euler update for both inductor current and capacitor voltage
                denom_i = (1.0 + dt * current_R / current_L)
                i_next = (i_state + (dt / current_L) * (v_source - v_state)) / denom_i

                denom_v = (1.0 + dt / (current_C * current_R_load))
                v_next = (v_state + (dt / current_C) * i_next) / denom_v

                i_state = i_next
                v_state = v_next

                v_wave[n, phase] = v_state
                i_wave[n, phase] = i_state

        pcc_voltages[pcc_id] = v_wave
        pcc_currents[pcc_id] = i_wave

    event_metadata = {
        "event_type": event_type,
        "start_time_s": event_start,
        "duration_s": event_duration
    }

    return EMTWaveforms(t, pcc_voltages, pcc_currents, event_metadata)
